#!/usr/bin/env python3
"""
dropbox_archive.py
APEX Hyper Engine | Spoke 4
Organizes all Dropbox files into the APEX archive structure:
  /APEX/evidence/
  /APEX/filings/
  /APEX/correspondence/
  /APEX/exhibits/
  /APEX/actors/
  /APEX/research/
All existing files are moved losslessly. Nothing is deleted.
"""

import os
import sys
import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode
from datetime import datetime

DROPBOX_ACCESS_TOKEN = os.environ.get('DROPBOX_ACCESS_TOKEN', '')
DROPBOX_REFRESH_TOKEN = os.environ.get('DROPBOX_REFRESH_TOKEN', '')
DROPBOX_APP_KEY = os.environ.get('DROPBOX_APP_KEY', '')
DROPBOX_APP_SECRET = os.environ.get('DROPBOX_APP_SECRET', '')

# APEX folder structure
APEX_FOLDERS = [
    '/APEX',
    '/APEX/evidence',
    '/APEX/filings',
    '/APEX/correspondence',
    '/APEX/exhibits',
    '/APEX/actors',
    '/APEX/research',
    '/APEX/legal-docs',
    '/APEX/media',
    '/APEX/archive'
]

# Routing rules: keyword in filename/path -> destination folder
ROUTING_RULES = [
    (['evidence', 'exhibit', 'photo', 'video', 'audio', 'recording', 'screenshot'], '/APEX/evidence'),
    (['motion', 'filing', 'complaint', 'petition', 'brief', 'tro', 'restraining'], '/APEX/filings'),
    (['email', 'letter', 'correspondence', 'message', 'communication'], '/APEX/correspondence'),
    (['exhibit-', 'exh-', 'exh_'], '/APEX/exhibits'),
    (['actor', 'judge', 'attorney', 'counsel', 'opposing'], '/APEX/actors'),
    (['research', 'case-law', 'statute', 'precedent', 'legal-research'], '/APEX/research'),
    (['order', 'judgment', 'ruling', 'decision', 'opinion'], '/APEX/legal-docs'),
    (['photo', 'video', 'mp4', 'mp3', 'wav', 'jpg', 'jpeg', 'png', 'heic'], '/APEX/media'),
]


def get_dbx():
    """Get Dropbox client with OAuth2."""
    if DROPBOX_ACCESS_TOKEN:
        try:
            dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
            dbx.users_get_current_account()
            print('[APEX] Dropbox connected via access token')
            return dbx
        except AuthError:
            pass
    
    if DROPBOX_REFRESH_TOKEN and DROPBOX_APP_KEY and DROPBOX_APP_SECRET:
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET
        )
        print('[APEX] Dropbox connected via refresh token')
        return dbx
    
    print('[ERR] No valid Dropbox credentials')
    sys.exit(1)


def ensure_apex_folders(dbx):
    """Create all APEX folder structure if it doesn't exist."""
    for folder in APEX_FOLDERS:
        try:
            dbx.files_create_folder_v2(folder)
            print(f'  [CREATED] {folder}')
        except ApiError as e:
            if 'path/conflict/folder' in str(e):
                pass  # Already exists
            else:
                print(f'  [WARN] Could not create {folder}: {e}')


def classify_file(path):
    """Determine destination folder based on file path keywords."""
    path_lower = path.lower()
    filename = os.path.basename(path_lower)
    
    # Skip files already in APEX structure
    if path_lower.startswith('/apex/'):
        return None
    
    for keywords, dest in ROUTING_RULES:
        if any(kw in path_lower for kw in keywords):
            return dest
    
    return '/APEX/archive'


def list_all_files(dbx, path=''):
    """List all files in Dropbox recursively."""
    files = []
    try:
        result = dbx.files_list_folder(path, recursive=True)
        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    files.append(entry)
            if not result.has_more:
                break
            result = dbx.files_list_folder_continue(result.cursor)
    except ApiError as e:
        print(f'[ERR] list_folder failed: {e}')
    return files


def move_file(dbx, from_path, to_folder):
    """Move a file to the destination folder."""
    filename = os.path.basename(from_path)
    to_path = f'{to_folder}/{filename}'
    
    try:
        dbx.files_move_v2(from_path, to_path, autorename=True)
        return True
    except ApiError as e:
        print(f'  [ERR] Move failed {from_path} -> {to_path}: {e}')
        return False


def main():
    print('[APEX] Starting Dropbox APEX archive organization')
    
    dbx = get_dbx()
    
    # Create APEX folder structure
    print('[APEX] Creating APEX folder structure...')
    ensure_apex_folders(dbx)
    
    # List all existing files
    print('[APEX] Scanning all Dropbox files...')
    files = list_all_files(dbx)
    print(f'[APEX] Found {len(files)} files to process')
    
    moved = 0
    skipped = 0
    errors = 0
    moves_by_folder = {}
    
    for entry in files:
        dest = classify_file(entry.path_lower)
        
        if dest is None:
            skipped += 1
            continue
        
        success = move_file(dbx, entry.path_display, dest)
        
        if success:
            moved += 1
            moves_by_folder[dest] = moves_by_folder.get(dest, 0) + 1
            print(f'  [MOVED] {entry.name} -> {dest}')
        else:
            errors += 1
    
    print(f'\n[APEX] Dropbox archive complete:')
    print(f'  Moved: {moved} | Skipped (already in APEX): {skipped} | Errors: {errors}')
    print(f'  Distribution:')
    for folder, count in sorted(moves_by_folder.items()):
        print(f'    {folder}: {count} files')


if __name__ == '__main__':
    main()
