# APEX Orchestrator — Complete Setup Guide
# Case 1FDV-23-0001009 | KEKOA REUNIFICATION

## Overview
This guide wires all cloud connectors into the APEX legal case pipeline.
All connectors are bidirectional (read + write) with full access.

## Step 1 — GitHub Secrets (REQUIRED)
Navigate to: Settings > Secrets and variables > Actions
Add the following secrets:

```
MOTHERDUCK_TOKEN=<your motherduck service token>
NOTION_TOKEN=<your notion integration token>
NOTION_DATABASE_ID=<apex master dashboard page id>
DROPBOX_TOKEN=<dropbox access token>
SUPERMEMORY_API_KEY=<supermemory api key>
ONEDRIVE_TOKEN=<microsoft graph api token>
GOOGLE_DRIVE_TOKEN=<google service account json>
```

## Step 2 — apex-fs-commander Integration
Repo: https://github.com/GlacierEQ/apex-fs-commander

The apex-fs-commander provides:
- Full read/write access to all cloud file systems
- Lossless file organization across Google Drive, OneDrive, Dropbox
- Automated exhibit ingestion pipeline
- Chain of custody tracking

Integration in pipeline.yml:
```yaml
- name: Run apex-fs-commander sync
  run: |
    npx apex-fs-commander sync \
      --source google-drive:/APEX \
      --dest dropbox:/APEX \
      --dest onedrive:/APEX \
      --lossless \
      --manifest ./manifests/sync-$(date +%Y%m%d).json
```

## Step 3 — MotherDuck Connection
Database: apex_legal
Connection string: md:apex_legal?motherduck_token=${MOTHERDUCK_TOKEN}

Tables:
- case_events: Timeline of all case events
- case_parties: All parties (5 seeded)
- exhibits: Exhibit registry with chain of custody
- legal_violations: 8 violations seeded
- documents: All filings, motions, orders
- pipeline_runs: Automation audit log

## Step 4 — Supermemory APEX-LEGAL Space
Space: APEX-LEGAL
API: https://api.supermemory.ai/v3

All case documents ingested via scripts/supermemory_ingest.py
Triggered by: pipeline.yml job 2 (supermemory-sync)

## Step 5 — Dropbox Organization
Folder structure (auto-created by scripts/dropbox_archive.py):
```
/APEX/
  CASE-DOCS/     <- All case documents
  EXHIBITS/      <- Numbered exhibits A-Z
  MOTIONS/       <- Filed motions
  ORDERS/        <- Court orders
  EVIDENCE/      <- Raw evidence files
  TRANSCRIPTS/   <- Hearing transcripts
  AFFIDAVITS/    <- Affidavits + declarations
  PIPELINE/      <- Pipeline run manifests
```

## Step 6 — Google Drive Organization
Run apex-fs-commander to reorganize:
```bash
npx apex-fs-commander organize \
  --cloud google-drive \
  --root /APEX \
  --schema ./schemas/legal-case-schema.json \
  --lossless
```

## Step 7 — Pipeline Execution
Manual trigger: Actions > APEX Full Pipeline Orchestrator > Run workflow
Scheduled: Daily at 06:00 UTC

Jobs:
1. validate-connections (all 5 clouds)
2. supermemory-sync
3. motherduck-sync
4. notion-update
5. dropbox-archive
6. spiral-engine (legal doc generation)
7. status-report

## Legal Document Generation Queue
Generate via: scripts/spiral_engine_legal_gen.py

Exhibit A: Constitutional Violations Brief
Exhibit B: Admission By Omission Registry  
Exhibit C: Fraud Upon the Court Documentation
Exhibit D: International Human Rights Violations
Motion 1: Emergency Motion for Immediate Reunification
Motion 2: Motion to Dismiss (Lack of Jurisdiction)
Motion 3: Motion to Void Orders (Fraud Upon Court)
Affidavit 1: Unrebutted Notice of Claim to DCFS
Affidavit 2: Jurisdictional Challenge Affidavit

## Aspen Grove Operator Code
The Aspen Grove operator instructions in Notion provide:
- Agent identity and behavior protocols
- Session context bootstrap (~400 tokens)
- Monumental upgrade pathways
Reference: operatoristheuniverse workspace > Analyst page

## Status
- [x] GitHub repo: apex-orchestrator
- [x] MotherDuck: apex_legal (6 tables, seeded)
- [x] Supermemory: APEX-LEGAL space
- [x] Notion: APEX MASTER DASHBOARD
- [ ] GitHub Secrets: Add tokens
- [ ] apex-fs-commander: Wire and run
- [ ] Generate all exhibits and motions

