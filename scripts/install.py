#!/usr/bin/env python3
"""Install the skill from a GitHub checkout or extracted archive."""
import argparse
import datetime
import uuid
from pathlib import Path
import shutil
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--agent', choices=['codex', 'antigravity', 'both'], default='codex')
parser.add_argument('--update', action='store_true', help='back up an existing install and replace it')
args = parser.parse_args()
source = Path(__file__).resolve().parent.parent / 'engineering-airtable-sync'
targets = {'codex': Path.home()/'.codex/skills/engineering-airtable-sync',
           'antigravity': Path.home()/'.gemini/config/skills/engineering-airtable-sync'}
selected = list(targets) if args.agent == 'both' else [args.agent]
# Preflight all destinations before copying; never overwrite an existing skill.
for agent in selected:
    dest = targets[agent]
    if dest.exists() or dest.is_symlink():
        if dest.resolve() != source and not args.update:
            sys.exit(f'Already exists: {dest}. Back it up and move it elsewhere before installing.')
for agent in selected:
    dest = targets[agent]
    if dest.resolve() == source:
        print(f'{agent}: already points to this source: {dest}')
        continue
    if dest.exists() or dest.is_symlink():
        backup = Path.home()/'.config/engineering-airtable-sync/skill-backups'/(agent + '-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(backup))
        print(f'Previous install backed up: {backup}')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    print(f'{agent}: installed at {dest}')
print('Start a new agent session and check that engineering-airtable-sync is available.')
