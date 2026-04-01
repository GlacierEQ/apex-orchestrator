#!/usr/bin/env python3
"""
supermemory_ingest.py
APEX Hyper Engine | Spiral-Engine Spoke 1
Fetches all Notion pages for Case 1FDV-23-0001009 and pushes
them into the APEX-LEGAL Supermemory collection.
Bidirectional: reads Notion, writes Supermemory.
"""

import os
import sys
import json
import requests
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
NOTION_TOKEN = os.environ['NOTION_TOKEN']
SUPERMEMORY_API_KEY = os.environ['SUPERMEMORY_API_KEY']
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')

CASE_ID = os.environ.get('CASE_ID', '1FDV-23-0001009')
COLLECTION_NAME = 'APEX-LEGAL'
SUPERMEMORY_BASE = 'https://api.supermemory.ai/v3'

NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

SUPERMEMORY_HEADERS = {
    'Authorization': f'Bearer {SUPERMEMORY_API_KEY}',
    'Content-Type': 'application/json'
}

# ============================================================
# FETCH NOTION PAGES
# ============================================================
def fetch_notion_pages():
    """Fetch all pages from the case Notion database."""
    pages = []
    url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
    payload = {'page_size': 100}
    
    while True:
        resp = requests.post(url, headers=NOTION_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        pages.extend(data.get('results', []))
        
        if not data.get('has_more'):
            break
        payload['start_cursor'] = data['next_cursor']
    
    print(f'[APEX] Fetched {len(pages)} Notion pages')
    return pages


def fetch_page_content(page_id):
    """Fetch full text content of a Notion page block tree."""
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    all_text = []
    
    resp = requests.get(url, headers=NOTION_HEADERS)
    if resp.status_code != 200:
        return ''
    
    blocks = resp.json().get('results', [])
    for block in blocks:
        block_type = block.get('type', '')
        block_data = block.get(block_type, {})
        rich_text = block_data.get('rich_text', [])
        for rt in rich_text:
            all_text.append(rt.get('plain_text', ''))
    
    return ' '.join(all_text)


# ============================================================
# PUSH TO SUPERMEMORY
# ============================================================
def push_to_supermemory(title, content, metadata):
    """Push a memory item to the APEX-LEGAL Supermemory collection."""
    url = f'{SUPERMEMORY_BASE}/memories'
    
    payload = {
        'content': f'{title}\n\n{content}',
        'metadata': {
            **metadata,
            'collection': COLLECTION_NAME,
            'case_id': CASE_ID,
            'ingested_at': datetime.utcnow().isoformat(),
            'source': 'notion'
        },
        'spaces': [COLLECTION_NAME]
    }
    
    resp = requests.post(url, headers=SUPERMEMORY_HEADERS, json=payload)
    if resp.status_code in (200, 201):
        return resp.json().get('id')
    else:
        print(f'[WARN] Supermemory push failed: {resp.status_code} {resp.text[:200]}')
        return None


# ============================================================
# MAIN
# ============================================================
def main():
    print(f'[APEX] Starting Supermemory ingest for case {CASE_ID}')
    print(f'[APEX] Target collection: {COLLECTION_NAME}')
    
    if not NOTION_DATABASE_ID:
        print('[WARN] No NOTION_DATABASE_ID set — ingesting search results instead')
        # Fall back to searching for case-related pages
        search_url = 'https://api.notion.com/v1/search'
        payload = {'query': CASE_ID, 'page_size': 50}
        resp = requests.post(search_url, headers=NOTION_HEADERS, json=payload)
        pages = resp.json().get('results', []) if resp.status_code == 200 else []
        print(f'[APEX] Search found {len(pages)} pages')
    else:
        pages = fetch_notion_pages()
    
    success_count = 0
    fail_count = 0
    
    for page in pages:
        try:
            page_id = page['id']
            props = page.get('properties', {})
            
            # Extract title
            title = ''
            for prop_name, prop_data in props.items():
                if prop_data.get('type') == 'title':
                    title_arr = prop_data.get('title', [])
                    title = ''.join([t.get('plain_text', '') for t in title_arr])
                    break
            
            if not title:
                title = f'Notion Page {page_id}'
            
            # Fetch page content
            content = fetch_page_content(page_id)
            
            # Build metadata
            metadata = {
                'notion_page_id': page_id,
                'notion_url': page.get('url', ''),
                'last_edited': page.get('last_edited_time', ''),
                'created_time': page.get('created_time', ''),
                'title': title
            }
            
            # Push to Supermemory
            mem_id = push_to_supermemory(title, content, metadata)
            
            if mem_id:
                success_count += 1
                print(f'  [OK] {title[:60]} -> mem:{mem_id}')
            else:
                fail_count += 1
                
        except Exception as e:
            fail_count += 1
            print(f'  [ERR] Page {page.get("id", "?")} failed: {e}')
    
    print(f'\n[APEX] Ingest complete: {success_count} success, {fail_count} failed')
    
    if fail_count > success_count and success_count == 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
