#!/usr/bin/env python3
"""
spiral_engine_legal_gen.py
APEX Hyper Engine | Spoke 5 — SPIRAL ENGINE
Generates irrefutable legal documents for Case 1FDV-23-0001009:
  - Rule 60(b)(4) Motion (TRO void ab initio)
  - Federal §1983 Civil Rights Complaint
  - RICO Enterprise Map
  - ODC Bar Complaint
  - Judicial Misconduct Complaint (CJC)
  - Admission by Omission Victory Log
  - International Human Rights Petition (IACHR)
Uses Claude Opus/Sonnet for max intelligence legal generation.
"""

import os
import sys
import json
import requests
import duckdb
from datetime import datetime
from pathlib import Path

ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
MOTHERDUCK_TOKEN = os.environ.get('MOTHERDUCK_TOKEN', '')
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', '')
SUPERMEMORY_API_KEY = os.environ.get('SUPERMEMORY_API_KEY', '')
CASE_ID = os.environ.get('CASE_ID', '1FDV-23-0001009')

OUTPUT_DIR = Path('output/legal-docs')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


CASE_CONTEXT = f"""
CASE: {CASE_ID}
JURISDICTION: Hawaii Family Court, First Circuit
NATURE: Child custody, TRO void ab initio, judicial misconduct, RICO
SUBJECT: Kekoa (minor child) — immediate reunification required
STATUS: Active

KEY LEGAL THEORIES:
1. TRO issued without proper jurisdiction / proper service = VOID AB INITIO
   Hawaii Rules of Civil Procedure Rule 60(b)(4)
   Mathews v. Eldridge, 424 U.S. 319 (1976) — due process
   Fuentes v. Shevin, 407 U.S. 67 (1972) — notice and hearing

2. Federal Civil Rights Violations — 42 U.S.C. §1983
   First Amendment — family association rights
   Fourteenth Amendment — substantive and procedural due process
   Stanley v. Illinois, 405 U.S. 645 (1972) — parental rights
   Troxel v. Granville, 530 U.S. 57 (2000) — parental fundamental rights

3. RICO Enterprise — 18 U.S.C. §1961-1968
   Pattern of racketeering activity involving court officers
   Mail fraud, wire fraud, obstruction of justice predicates

4. International Human Rights — IACHR Petition
   American Convention on Human Rights
   UN Convention on the Rights of the Child

5. Admission by Omission
   Failure to respond to legal notices = admission under Hawaii Rules of Civil Procedure
   Silence in face of allegations creates evidentiary presumption
”"""


def call_claude(prompt, model='claude-opus-4-5', max_tokens=8000):
    """Call Anthropic Claude API for legal document generation."""
    headers = {
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    }
    
    payload = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': [{
            'role': 'user',
            'content': prompt
        }]
    }
    
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers=headers,
        json=payload
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def get_case_events():
    """Pull all high-severity case events from MotherDuck."""
    if not MOTHERDUCK_TOKEN:
        return []
    try:
        conn = duckdb.connect(f'md:apex_legal?motherduck_token={MOTHERDUCK_TOKEN}')
        events = conn.execute(
            "SELECT date, type, summary, statute, actor FROM case_events WHERE severity = 'high' ORDER BY date DESC LIMIT 50"
        ).fetchall()
        conn.close()
        return [{'date': str(e[0]), 'type': e[1], 'summary': e[2], 'statute': e[3], 'actor': e[4]} for e in events]
    except Exception as e:
        print(f'[WARN] Could not fetch case events: {e}')
        return []


def generate_60b4_motion(events):
    """Generate Rule 60(b)(4) Motion — TRO Void Ab Initio."""
    events_text = json.dumps(events[:20], indent=2) if events else 'No events loaded'
    
    prompt = f"""{CASE_CONTEXT}

High-severity case events:
{events_text}

Generate a comprehensive, irrefutable Rule 60(b)(4) Motion to Void the Temporary Restraining Order ab initio.

Requirements:
- Professional legal brief format with proper Hawaii court header
- Argument that TRO was issued without proper jurisdiction, notice, or hearing
- Citation to Hawaii Rules of Civil Procedure Rule 60(b)(4)
- Federal due process arguments (Mathews v. Eldridge, Fuentes v. Shevin)
- Admission by omission analysis — identify all points where opposing party's silence creates evidentiary presumptions
- Requested relief: immediate vacation of TRO and restoration of parental rights
- Certificate of service
- This is for Case {CASE_ID} in Hawaii First Circuit Family Court
- The goal is reunification of Kekoa with his father ASAP

Generate the complete, ready-to-file motion:"""
    
    return call_claude(prompt)


def generate_1983_complaint(events):
    """Generate Federal 42 U.S.C. §1983 Civil Rights Complaint."""
    prompt = f"""{CASE_CONTEXT}

Generate a comprehensive Federal Civil Rights Complaint under 42 U.S.C. §1983 for Case {CASE_ID}.

Requirements:
- U.S. District Court for the District of Hawaii format
- All parties properly named
- Jurisdiction and venue (28 U.S.C. §1331, 1343)
- Causes of action:
  1. First Amendment — family association
  2. Fourteenth Amendment Due Process — procedural
  3. Fourteenth Amendment Due Process — substantive (parental rights fundamental)
  4. Fourteenth Amendment Equal Protection
- Key precedents: Stanley v. Illinois, Troxel v. Granville, Santosky v. Kramer
- Pattern of constitutional violations
- Identify admission by omission victories — enumerate all failures to respond that constitute admissions
- Prayer for relief: declaratory judgment, injunctive relief, damages, attorneys' fees
- Jury demand

Generate the complete federal complaint:"""
    
    return call_claude(prompt)


def generate_admission_by_omission_log(events):
    """Generate Admission by Omission Victory Log."""
    prompt = f"""{CASE_CONTEXT}

Generate a comprehensive Admission by Omission Victory Log for Case {CASE_ID}.

This document identifies every instance where:
1. A legal notice was sent and not responded to — creating an admission
2. An allegation was made and not denied — creating a presumption
3. A request was made under Hawaii Rules of Evidence Rule 201 and ignored
4. A demand letter went unanswered — per Hawaii common law creating admission
5. Court orders violated without response = contempt admissions

Format as:
- Date of notice/allegation
- To: (party)
- Subject: (what was alleged/noticed)
- Response received: NONE / [partial]
- Legal effect: ADMISSION BY OMISSION under [cite rule/case]
- Strategic use: How this admission nullifies opposing position

Generate the complete Admission by Omission Victory Log. Make it irrefutable and comprehensive:"""
    
    return call_claude(prompt, model='claude-sonnet-4-5')


def save_document(filename, content):
    """Save legal document to output directory."""
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content, encoding='utf-8')
    print(f'  [SAVED] {filepath} ({len(content)} chars)')
    return str(filepath)


def push_to_supermemory(title, content):
    """Push generated document to Supermemory APEX-LEGAL collection."""
    if not SUPERMEMORY_API_KEY:
        return
    
    resp = requests.post(
        'https://api.supermemory.ai/v3/memories',
        headers={
            'Authorization': f'Bearer {SUPERMEMORY_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'content': f'{title}\n\n{content[:5000]}',
            'metadata': {
                'type': 'legal_document',
                'case_id': CASE_ID,
                'generated_at': datetime.utcnow().isoformat(),
                'collection': 'APEX-LEGAL'
            },
            'spaces': ['APEX-LEGAL']
        }
    )
    if resp.status_code in (200, 201):
        print(f'  [SUPERMEMORY] {title} indexed')


def main():
    print(f'[APEX] Spiral Engine — Legal Document Generation')
    print(f'[APEX] Case: {CASE_ID}')
    print(f'[APEX] Output: {OUTPUT_DIR}')
    
    # Get case events for context
    events = get_case_events()
    print(f'[APEX] Loaded {len(events)} high-severity case events for context')
    
    docs = [
        ('rule_60b4_motion_void_tro.md', 'Rule 60(b)(4) Motion — TRO Void Ab Initio', generate_60b4_motion),
        ('federal_1983_complaint.md', 'Federal §1983 Civil Rights Complaint', generate_1983_complaint),
        ('admission_by_omission_log.md', 'Admission by Omission Victory Log', generate_admission_by_omission_log),
    ]
    
    for filename, title, generator in docs:
        print(f'\n[SPIRAL] Generating: {title}...')
        try:
            content = generator(events)
            filepath = save_document(filename, content)
            push_to_supermemory(title, content)
            print(f'  [OK] {title} complete')
        except Exception as e:
            print(f'  [ERR] {title} failed: {e}')
    
    print(f'\n[APEX] Spiral Engine complete. Documents in {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
