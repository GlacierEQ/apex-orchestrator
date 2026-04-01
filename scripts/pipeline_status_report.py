#!/usr/bin/env python3
"""
pipeline_status_report.py
APEX Hyper Engine | Final Job
Writes pipeline run status back to Notion and Supermemory
after every pipeline execution. Bidirectional.
"""

import os
import sys
import json
import requests
from datetime import datetime

NOTION_TOKEN = os.environ['NOTION_TOKEN']
NOTION_DASHBOARD_PAGE_ID = os.environ.get('NOTION_DASHBOARD_PAGE_ID', '')
SUPERMEMORY_API_KEY = os.environ.get('SUPERMEMORY_API_KEY', '')
RUN_NUMBER = os.environ.get('RUN_NUMBER', '?')
RUN_ID = os.environ.get('RUN_ID', '?')
CASE_ID = os.environ.get('CASE_ID', '1FDV-23-0001009')
REPO = 'GlacierEQ/apex-orchestrator'

NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}


def write_status_to_notion(page_id, status_text):
    """Append pipeline run status block to Notion dashboard."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    run_url = f'https://github.com/{REPO}/actions/runs/{RUN_ID}'
    
    blocks = [
        {
            'object': 'block',
            'type': 'divider',
            'divider': {}
        },
        {
            'object': 'block',
            'type': 'heading_3',
            'heading_3': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f'Pipeline Run #{RUN_NUMBER} — {now}'}
                }]
            }
        },
        {
            'object': 'block',
            'type': 'callout',
            'callout': {
                'icon': {'type': 'emoji', 'emoji': '🔄'},
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': status_text}
                }],
                'color': 'blue_background'
            }
        },
        {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [
                    {'type': 'text', 'text': {'content': 'View run: '}},
                    {'type': 'text', 'text': {'content': run_url, 'link': {'url': run_url}}}
                ]
            }
        }
    ]
    
    # Find dashboard page if not configured
    if not page_id:
        url = 'https://api.notion.com/v1/search'
        payload = {'query': 'APEX Master Dashboard', 'page_size': 3}
        resp = requests.post(url, headers=NOTION_HEADERS, json=payload)
        if resp.status_code == 200:
            results = resp.json().get('results', [])
            if results:
                page_id = results[0]['id']
    
    if not page_id:
        print('[WARN] No dashboard page ID available')
        return False
    
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    resp = requests.patch(url, headers=NOTION_HEADERS, json={'children': blocks})
    
    if resp.status_code == 200:
        print(f'[APEX] Status written to Notion dashboard')
        return True
    else:
        print(f'[WARN] Notion write failed: {resp.status_code}')
        return False


def write_status_to_supermemory(status_text):
    """Push pipeline run status to Supermemory APEX-LEGAL collection."""
    if not SUPERMEMORY_API_KEY:
        return
    
    now = datetime.utcnow().isoformat()
    run_url = f'https://github.com/{REPO}/actions/runs/{RUN_ID}'
    
    payload = {
        'content': f'APEX Pipeline Run #{RUN_NUMBER} ({now})\n\nStatus: {status_text}\nCase: {CASE_ID}\nRun URL: {run_url}',
        'metadata': {
            'type': 'pipeline_run',
            'run_number': RUN_NUMBER,
            'run_id': RUN_ID,
            'case_id': CASE_ID,
            'timestamp': now,
            'collection': 'APEX-LEGAL'
        },
        'spaces': ['APEX-LEGAL']
    }
    
    resp = requests.post(
        'https://api.supermemory.ai/v3/memories',
        headers={
            'Authorization': f'Bearer {SUPERMEMORY_API_KEY}',
            'Content-Type': 'application/json'
        },
        json=payload
    )
    
    if resp.status_code in (200, 201):
        print('[APEX] Status indexed in Supermemory APEX-LEGAL')
    else:
        print(f'[WARN] Supermemory status push failed: {resp.status_code}')


def main():
    print(f'[APEX] Pipeline Status Report — Run #{RUN_NUMBER}')
    print(f'[APEX] Case: {CASE_ID}')
    
    status_text = (
        f'APEX Full Pipeline Run #{RUN_NUMBER} completed for Case {CASE_ID}\n'
        f'Jobs: Supermemory Ingest, MotherDuck Sync, Notion Dashboard, '
        f'Dropbox Archive, Spiral Engine Legal Gen, FS-Commander Sync\n'
        f'Run ID: {RUN_ID}\n'
        f'Repo: {REPO}'
    )
    
    write_status_to_notion(NOTION_DASHBOARD_PAGE_ID, status_text)
    write_status_to_supermemory(status_text)
    
    print('[APEX] Pipeline status report complete')


if __name__ == '__main__':
    main()
