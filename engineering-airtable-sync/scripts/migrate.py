#!/usr/bin/env python3
"""Preview and copy recognised legacy notes into empty v2 content fields."""
import argparse
import json
import re
from sync import Airtable, HOME, SyncError, load_config, locked, read_json, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    try:
        with locked():
            c = load_config(args.project)
            if c.get('schema_version', 1) < 2: raise SyncError('Upgrade the schema first.')
            api = Airtable(c); table = c['updates_table']
            path = HOME / ('migration-' + c['base_id'] + '-' + table + '.json')
            rows = []; params = {}
            while True:
                page = api.request(table, params=params); rows.extend(page.get('records', []))
                if not page.get('offset'): break
                params['offset'] = page['offset']
            if not args.apply:
                changes = []
                for r in rows:
                    f = r.get('fields', {})
                    m = re.fullmatch(r'\[(idea|requirement|decision|blocker) / (.+?)\] .+', f.get('Name', ''))
                    if not m or not f.get('In Progress'): continue
                    values = {'Content': f['In Progress'], 'Type': m[1], 'Status': m[2]}
                    patch = {k: v for k, v in values.items() if not f.get(k)}
                    if patch: changes.append({'id': r['id'], 'before': {k: f.get(k) for k in ['Name', 'In Progress', *patch]}, 'fields': patch})
                write_json(path, {'changes': changes})
                print(json.dumps({'scope': 'All recognised legacy notes in this Base Updates table', 'changes': changes, 'next': 'Review before running the same command with --apply.'}, ensure_ascii=False, indent=2))
            else:
                plan = read_json(path); current = {r['id']: r.get('fields', {}) for r in rows}
                for item in plan['changes']:
                    f = current.get(item['id'])
                    if f is None: raise SyncError('A record was deleted; preview migration again.')
                    if all(f.get(k) == v for k, v in item['fields'].items()): continue
                    if any(f.get(k) != v for k, v in item['before'].items()): raise SyncError('Record changed since migration preview; inspect and preview again.')
                    api.request(table, 'PATCH', {'records': [{'id': item['id'], 'fields': item['fields']}]})
                print(json.dumps({'migrated_or_already_present': len(plan['changes']), 'source_text_preserved': True}))
    except SyncError as e: p.exit(1, str(e) + '\n')


if __name__ == '__main__': main()
