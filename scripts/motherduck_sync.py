#!/usr/bin/env python3
"""
motherduck_sync.py
APEX Hyper Engine | Spoke 2
Creates the case_events table in MotherDuck and syncs
all case events from Notion. Bidirectional read/write.

Table schema:
  case_events(date, type, source, summary, file_url, actor,
              statute, severity, notion_id, created_at)
"""

import os
import sys
import json
import requests
import duckdb
from datetime import datetime

MOTHERDUCK_TOKEN = os.environ['MOTHERDUCK_TOKEN']
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
CASE_ID = os.environ.get('CASE_ID', '1FDV-23-0001009')
DB_NAME = 'apex_legal'

NOTION_HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}


def connect_motherduck():
    """Connect to MotherDuck cloud DuckDB."""
    conn_str = f'md:{DB_NAME}?motherduck_token={MOTHERDUCK_TOKEN}'
    try:
        conn = duckdb.connect(conn_str)
        print(f'[APEX] Connected to MotherDuck: {DB_NAME}')
        return conn
    except Exception as e:
        print(f'[ERR] MotherDuck connection failed: {e}')
        sys.exit(1)


def ensure_schema(conn):
    """Create the case_events table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS case_events (
            id          VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR,
            date        DATE,
            type        VARCHAR NOT NULL,
            source      VARCHAR,
            summary     TEXT,
            file_url    VARCHAR,
            actor       VARCHAR,
            statute     VARCHAR,
            severity    VARCHAR DEFAULT 'medium',
            case_id     VARCHAR DEFAULT '1FDV-23-0001009',
            notion_id   VARCHAR UNIQUE,
            created_at  TIMESTAMP DEFAULT now(),
            updated_at  TIMESTAMP DEFAULT now()
        )
    """)
    
    # Also create helper views
    conn.execute("""
        CREATE VIEW IF NOT EXISTS case_events_recent AS
        SELECT * FROM case_events
        ORDER BY date DESC NULLS LAST
        LIMIT 100
    """)
    
    conn.execute("""
        CREATE VIEW IF NOT EXISTS case_events_by_type AS
        SELECT type, COUNT(*) as count, MIN(date) as first_date, MAX(date) as last_date
        FROM case_events
        GROUP BY type
        ORDER BY count DESC
    """)
    
    print('[APEX] Schema verified: case_events table ready')


def fetch_notion_events():
    """Fetch case events from Notion via search."""
    url = 'https://api.notion.com/v1/search'
    payload = {'query': CASE_ID, 'page_size': 100, 'filter': {'property': 'object', 'value': 'page'}}
    
    resp = requests.post(url, headers=NOTION_HEADERS, json=payload)
    if resp.status_code != 200:
        print(f'[WARN] Notion search failed: {resp.status_code}')
        return []
    
    return resp.json().get('results', [])


def upsert_event(conn, event):
    """Upsert a case event into MotherDuck."""
    conn.execute("""
        INSERT INTO case_events (date, type, source, summary, file_url, actor, statute, severity, case_id, notion_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now())
        ON CONFLICT (notion_id) DO UPDATE SET
            summary = EXCLUDED.summary,
            updated_at = now()
    """, [
        event.get('date'),
        event.get('type', 'case_document'),
        event.get('source', 'notion'),
        event.get('summary', ''),
        event.get('file_url', ''),
        event.get('actor', ''),
        event.get('statute', ''),
        event.get('severity', 'medium'),
        CASE_ID,
        event.get('notion_id')
    ])


def page_to_event(page):
    """Convert a Notion page to a case_events row."""
    props = page.get('properties', {})
    
    title = ''
    for prop_name, prop_data in props.items():
        if prop_data.get('type') == 'title':
            title_arr = prop_data.get('title', [])
            title = ''.join([t.get('plain_text', '') for t in title_arr])
            break
    
    created = page.get('created_time', '')[:10] if page.get('created_time') else None
    
    # Determine event type from title keywords
    title_lower = title.lower()
    if any(k in title_lower for k in ['tro', 'restraining', 'motion', 'order']):
        event_type = 'court_order'
    elif any(k in title_lower for k in ['evidence', 'exhibit', 'photo', 'video']):
        event_type = 'evidence'
    elif any(k in title_lower for k in ['filing', 'complaint', 'petition']):
        event_type = 'court_filing'
    elif any(k in title_lower for k in ['hearing', 'trial', 'deposition']):
        event_type = 'hearing'
    elif any(k in title_lower for k in ['rico', 'fraud', 'misconduct']):
        event_type = 'misconduct'
    elif any(k in title_lower for k in ['federal', '1983', 'constitutional']):
        event_type = 'federal_action'
    elif any(k in title_lower for k in ['correspondence', 'email', 'letter']):
        event_type = 'correspondence'
    else:
        event_type = 'case_document'
    
    return {
        'date': created,
        'type': event_type,
        'source': 'notion',
        'summary': title,
        'file_url': page.get('url', ''),
        'actor': '',
        'statute': '',
        'severity': 'high' if event_type in ('court_order', 'misconduct', 'federal_action') else 'medium',
        'notion_id': page.get('id')
    }


def main():
    print(f'[APEX] Starting MotherDuck sync for case {CASE_ID}')
    
    conn = connect_motherduck()
    ensure_schema(conn)
    
    # Fetch from Notion
    pages = fetch_notion_events()
    print(f'[APEX] Found {len(pages)} Notion pages to sync')
    
    success = 0
    errors = 0
    
    for page in pages:
        try:
            event = page_to_event(page)
            upsert_event(conn, event)
            success += 1
            print(f'  [OK] {event["summary"][:60]} [{event["type"]}]')
        except Exception as e:
            errors += 1
            print(f'  [ERR] {page.get("id", "?")} -> {e}')
    
    # Print stats
    total = conn.execute('SELECT COUNT(*) FROM case_events').fetchone()[0]
    by_type = conn.execute('SELECT type, COUNT(*) FROM case_events GROUP BY type ORDER BY COUNT(*) DESC').fetchall()
    
    print(f'\n[APEX] MotherDuck sync complete:')
    print(f'  Synced: {success} | Errors: {errors}')
    print(f'  Total case_events rows: {total}')
    print(f'  Event types: {dict(by_type)}')
    
    conn.close()


if __name__ == '__main__':
    main()
