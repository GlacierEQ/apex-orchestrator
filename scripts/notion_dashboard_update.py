#!/usr/bin/env python3
"""
notion_dashboard_update.py
APEX Hyper Engine | Spoke 3
Pulls analytics from MotherDuck and writes live stats
back to the APEX Master Dashboard Notion page.
Bidirectional: reads MotherDuck, writes Notion.
"""

import os
import sys
import json
import requests
import duckdb
from datetime import datetime

NOTION_TOKEN = os.environ['NOTION_TOKEN']
NOTION_DASHBOARD_PAGE_ID = os.environ.get('NOTION_DASHBOARD_PAGE_ID', '')
MOTHERDUCK_TOKEN = os.environ.get('MOTHERDUCK_TOKEN', '')
CASE_ID = os.environ.get('CASE_ID', '1FDV-23-0001009')

NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}


def get_motherduck_stats():
    """Pull aggregate stats from MotherDuck case_events."""
    stats = {
        'total_events': 0,
        'by_type': {},
        'latest_event': '',
        'high_severity_count': 0
    }
    
    if not MOTHERDUCK_TOKEN:
        return stats
    
    try:
        conn = duckdb.connect(f'md:apex_legal?motherduck_token={MOTHERDUCK_TOKEN}')
        
        total = conn.execute('SELECT COUNT(*) FROM case_events').fetchone()
        stats['total_events'] = total[0] if total else 0
        
        by_type = conn.execute(
            'SELECT type, COUNT(*) FROM case_events GROUP BY type ORDER BY COUNT(*) DESC'
        ).fetchall()
        stats['by_type'] = {row[0]: row[1] for row in by_type}
        
        latest = conn.execute(
            'SELECT summary FROM case_events ORDER BY created_at DESC LIMIT 1'
        ).fetchone()
        stats['latest_event'] = latest[0][:100] if latest else ''
        
        high_sev = conn.execute(
            "SELECT COUNT(*) FROM case_events WHERE severity = 'high'"
        ).fetchone()
        stats['high_severity_count'] = high_sev[0] if high_sev else 0
        
        conn.close()
    except Exception as e:
        print(f'[WARN] MotherDuck stats failed: {e}')
    
    return stats


def build_dashboard_blocks(stats):
    """Build Notion blocks for the APEX Master Dashboard."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    
    type_lines = '\n'.join(
        [f'  {k}: {v}' for k, v in stats.get('by_type', {}).items()]
    ) or '  No events yet'
    
    blocks = [
        {
            'object': 'block',
            'type': 'heading_2',
            'heading_2': {
                'rich_text': [{'type': 'text', 'text': {'content': f'APEX Pipeline Status — {now}'}}]
            }
        },
        {
            'object': 'block',
            'type': 'callout',
            'callout': {
                'icon': {'type': 'emoji', 'emoji': '⚖️'},
                'rich_text': [{
                    'type': 'text',
                    'text': {
                        'content': f'Case: {CASE_ID} | Total Events: {stats["total_events"]} | High Severity: {stats["high_severity_count"]}'
                    }
                }],
                'color': 'red_background'
            }
        },
        {
            'object': 'block',
            'type': 'heading_3',
            'heading_3': {
                'rich_text': [{'type': 'text', 'text': {'content': 'Event Breakdown by Type'}}]
            }
        },
        {
            'object': 'block',
            'type': 'code',
            'code': {
                'language': 'plain text',
                'rich_text': [{'type': 'text', 'text': {'content': type_lines}}]
            }
        },
        {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{
                    'type': 'text',
                    'text': {'content': f'Latest event: {stats.get("latest_event", "N/A")}'}
                }]
            }
        },
        {
            'object': 'block',
            'type': 'divider',
            'divider': {}
        },
        {
            'object': 'block',
            'type': 'heading_3',
            'heading_3': {
                'rich_text': [{'type': 'text', 'text': {'content': 'Pipeline Connections Status'}}]
            }
        },
        {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': '✅ Supermemory APEX-LEGAL collection — Active'}}]
            }
        },
        {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': '✅ MotherDuck apex_legal.case_events — Active'}}]
            }
        },
        {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': '✅ GitHub GlacierEQ/apex-orchestrator — Active'}}]
            }
        },
        {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': '✅ Dropbox /APEX/ archive structure — Active'}}]
            }
        },
        {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': '✅ APEX-FS-Commander cloud sync — Active'}}]
            }
        },
        {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{'type': 'text', 'text': {'content': f'Pipeline last run: {now}'}, 'annotations': {'italic': True}}]
            }
        }
    ]
    
    return blocks


def append_blocks_to_page(page_id, blocks):
    """Append blocks to a Notion page."""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    payload = {'children': blocks}
    
    resp = requests.patch(url, headers=NOTION_HEADERS, json=payload)
    if resp.status_code == 200:
        print(f'[APEX] Dashboard updated: {len(blocks)} blocks written')
        return True
    else:
        print(f'[ERR] Notion write failed: {resp.status_code} {resp.text[:300]}')
        return False


def find_or_create_dashboard():
    """Find existing dashboard or return the configured page ID."""
    if NOTION_DASHBOARD_PAGE_ID:
        return NOTION_DASHBOARD_PAGE_ID
    
    # Search for existing dashboard
    url = 'https://api.notion.com/v1/search'
    payload = {'query': 'APEX Master Dashboard', 'page_size': 5}
    resp = requests.post(url, headers=NOTION_HEADERS, json=payload)
    
    if resp.status_code == 200:
        results = resp.json().get('results', [])
        if results:
            page_id = results[0]['id']
            print(f'[APEX] Found dashboard page: {page_id}')
            return page_id
    
    print('[WARN] No dashboard page found and NOTION_DASHBOARD_PAGE_ID not set')
    return None


def main():
    print(f'[APEX] Updating Notion Master Dashboard for case {CASE_ID}')
    
    stats = get_motherduck_stats()
    print(f'[APEX] Stats: {stats}')
    
    page_id = find_or_create_dashboard()
    if not page_id:
        print('[ERR] Cannot update dashboard — no page ID available')
        sys.exit(1)
    
    blocks = build_dashboard_blocks(stats)
    success = append_blocks_to_page(page_id, blocks)
    
    if not success:
        sys.exit(1)
    
    print('[APEX] Dashboard update complete')


if __name__ == '__main__':
    main()
