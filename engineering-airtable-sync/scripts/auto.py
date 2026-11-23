#!/usr/bin/env python3
"""Agent-facing Airtable discovery and provisioning; no setup form."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import quote
from project import list_bases, destination, project_key, config_path, register
from setup import MetaAPI, bootstrap
from sync import CONFIG, STATE, SyncError, locked, read_json, repo_identity, token, write_json


def candidates(api, project_name):
    bases = list_bases(api)
    found = []
    for base in bases:
        try:
            tables = api.call('meta/bases/' + base['id'] + '/tables')['tables']
            p = next((t for t in tables if t['name'] == 'Projects'), None)
            u = next((t for t in tables if t['name'] == 'Updates'), None)
            projects = []
            if p and u:
                path = base['id'] + '/' + p['id']; offset = None
                while True:
                    page = api.call(path + ('?offset=' + quote(offset, safe='') if offset else ''))
                    projects.extend({'name': r.get('fields', {}).get('Name'), 'project_id': r.get('fields', {}).get('Project ID')} for r in page.get('records', []))
                    offset = page.get('offset')
                    if not offset: break
            found.append({'base_id': base['id'], 'base_name': base.get('name'), 'workspace_id': base.get('workspaceId'), 'compatible_tracker': bool(p and u), 'projects': projects})
        except SyncError as e:
            found.append({'base_id': base['id'], 'base_name': base.get('name'), 'inspection_error': str(e)})
    return {'project_name': project_name, 'accessible_bases': found,
            'rule': 'These are candidates only. Never treat absent or inaccessible Bases as proof none exists; ask about ambiguous matches before provisioning.'}


def provision(api, path, mode, target, name, project_id=None):
    if mode not in ('new-base', 'existing-base'): raise SyncError('Choose new-base or existing-base.')
    if config_path(path).exists(): raise SyncError('This project already has a configured destination; inspect it before changing.')
    if not target: raise SyncError('A confirmed workspace or Base ID is required.')
    import setup
    setup.CONFIG = config_path(path)
    setup.CHECKPOINT = setup.CONFIG.with_suffix('.setup.json')
    if mode == 'new-base':
        config = bootstrap(api, 'new', target, name)
    else:
        config = bootstrap(api, 'existing', target, name)
    if project_id:
        from sync import Airtable
        if not Airtable(config).find(config['projects_table'], 'Project ID', project_id):
            raise SyncError('Selected existing Project ID was not found in the selected Base.')
        state = read_json(STATE, {'projects': {}, 'plans': {}})
        state.setdefault('projects', {})[project_key(path)] = {'project_id': project_id, 'root': repo_identity(path)[1]}
        write_json(STATE, state)
    target_path = config_path(path)
    write_json(target_path, config)
    register(path, target_path)
    return {'configured': True, 'base_id': config['base_id'], 'projects_table': config['projects_table'], 'updates_table': config['updates_table'], 'project_id': project_id, 'base_url': 'https://airtable.com/' + config['base_id']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('discover'); d.add_argument('--project', required=True); d.add_argument('--name', required=True)
    q = sub.add_parser('provision'); q.add_argument('--project', required=True)
    q.add_argument('--mode', choices=['new-base', 'existing-base'], required=True)
    q.add_argument('--target', required=True, help='Confirmed workspace ID or existing Base ID')
    q.add_argument('--name', default='Engineering Tracker'); q.add_argument('--project-id')
    u = sub.add_parser('upgrade'); u.add_argument('--project', required=True)
    args = p.parse_args()
    try:
        with locked():
            api = MetaAPI(token(read_json(destination(args.project), {})))
            if args.cmd == 'upgrade':
                cpath = destination(args.project)
                c = read_json(cpath)
                tables = api.call('meta/bases/' + c['base_id'] + '/tables')['tables']
                for key, name in [('projects_table', 'Projects'), ('updates_table', 'Updates')]:
                    if not any(t['id'] == c[key] and t['name'].lower() == name.lower() for t in tables):
                        raise SyncError('Configured tables do not match tracker names; inspect before upgrade.')
                upgraded = bootstrap(api, 'existing', c['base_id'], '', upgrade=True)
                if any(upgraded[k] != c[k] for k in ('projects_table', 'updates_table')):
                    raise SyncError('Configured table IDs differ from named tracker tables; inspect before upgrading.')
                upgraded['keychain_service'] = c.get('keychain_service', upgraded['keychain_service'])
                c.update(upgraded); write_json(cpath, c)
                print(json.dumps({'upgraded': True, 'config': c})); return
            result = candidates(api, args.name) if args.cmd == 'discover' else provision(api, args.project, args.mode, args.target, args.name, args.project_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except SyncError as e: p.exit(1, str(e) + '\n')

if __name__ == '__main__': main()
