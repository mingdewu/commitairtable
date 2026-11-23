#!/usr/bin/env python3
"""Discover authorized Airtable destinations and persist project workflow preferences."""
import argparse
import hashlib
import json
from pathlib import Path
from sync import HOME, CONFIG, STATE, SyncError, read_json, write_json, locked, repo_identity, token
from setup import MetaAPI

ROUTES = HOME / 'project-routes.json'

def project_key(path):
    raw = repo_identity(path)[0]
    return read_json(ROUTES, {}).get('_aliases', {}).get(raw, raw)

def link_path(source_key, target):
    routes = read_json(ROUTES, {})
    state = read_json(STATE, {'projects': {}, 'plans': {}})
    if source_key not in routes and source_key not in state.get('projects', {}):
        raise SyncError('Source project identity has no saved route or project. Use project.py info to inspect it.')
    target_raw = repo_identity(target)[0]
    existing = routes.get('_aliases', {}).get(target_raw, target_raw)
    if existing != target_raw and existing != source_key:
        raise SyncError('Target path already belongs to another project.')
    if target_raw in state.get('projects', {}) and target_raw != source_key:
        raise SyncError('Target path already has a different project identity.')
    if target_raw in routes and target_raw != source_key:
        raise SyncError('Target path already has its own route.')
    routes.setdefault('_aliases', {})[target_raw] = source_key
    write_json(ROUTES, routes)
    return {'source_key': source_key, 'target_identity': target_raw, 'canonical_project_key': source_key}

def destination(path):
    route = read_json(ROUTES, {}).get(project_key(path), {})
    if not route.get('config_path'): return CONFIG
    return Path(route['config_path'])

def config_path(path):
    return HOME / 'destinations' / (hashlib.sha256(project_key(path).encode()).hexdigest() + '.json')

def register(path, config):
    routes = read_json(ROUTES, {})
    entry = routes.setdefault(project_key(path), {})
    entry['config_path'] = str(config)
    write_json(ROUTES, routes)

def enable_reminders(path):
    root = Path(repo_identity(path)[1])
    if not root.is_dir(): raise SyncError('Project directory does not exist.')
    marker = '<!-- engineering-airtable-sync:start -->'
    text = '''<!-- engineering-airtable-sync:start -->
## Engineering progress recording

Use engineering-airtable-sync for this project. After an important requirement clarification, decision, substantive implementation, verification, release or blocker, briefly offer to record the change to Airtable. Group small edits into one meaningful update and do not repeat a declined reminder unless there is new progress. Do not interrupt an unfinished task just to ask. Git commit, Git push and Airtable recording are separate actions; ask which are wanted if ambiguous.

Examples are not project facts. Clarify material uncertainty about purpose, project, destination and status before preparing a record. Preserve tentative ideas as tentative. Show the exact destination and proposed changes, then wait for user confirmation before writing. Report actual saved changes and record links, including partial failures. These reminders apply only while an agent reads and follows these project instructions; no background monitoring is installed.
<!-- engineering-airtable-sync:end -->
'''
    file = root / 'AGENTS.md'
    old = file.read_text() if file.exists() else ''
    if marker not in old:
        file.write_text(old.rstrip() + '\n\n' + text if old else text)
    routes = read_json(ROUTES, {})
    routes.setdefault(project_key(path), {})['reminders'] = True
    write_json(ROUTES, routes)
    return str(file)

def list_bases(api):
    result=[]; path='meta/bases'
    while True:
        page=api.call(path); result.extend(page.get('bases', []))
        if not page.get('offset'): break
        from urllib.parse import quote
        path='meta/bases?offset='+quote(page['offset'], safe='')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='cmd', required=True)
    for name in ['info','enable-reminders','discover','bind','link-path']:
        q=sub.add_parser(name);q.add_argument('--project', default='.')
        if name=='discover': q.add_argument('--base-id')
        if name=='link-path': q.add_argument('--source-key', required=True)
        if name=='bind':
            q.add_argument('--base-id',required=True)
            q.add_argument('--project-id',help='Existing tracker Project ID, selected by the user')
    args=p.parse_args()
    try:
        with locked():
            if args.cmd=='link-path':
                print(json.dumps(link_path(args.source_key, args.project),ensure_ascii=False));return
            if args.cmd=='enable-reminders':
                print(json.dumps({'instructions_file':enable_reminders(args.project),'activation':'Current agent must read AGENTS.md; other hosts may require their own persistent rule integration.'}));return
            cpath=destination(args.project)
            if args.cmd=='info':
                print(json.dumps({'project_identity':project_key(args.project),'config_path':str(cpath),'configured':cpath.exists(),'preferences':read_json(ROUTES,{}).get(project_key(args.project),{}),'git':repo_identity(args.project)[1:]},ensure_ascii=False));return
            api=MetaAPI(token(read_json(cpath, {})))
            if args.cmd=='discover':
                if not args.base_id:
                    print(json.dumps({'accessible_bases':list_bases(api),'note':'Only authorized bases are visible. Names are candidates, not confirmed matches.'},ensure_ascii=False));return
                from setup import extract_id
                bid=extract_id(args.base_id,'app');schema=api.call('meta/bases/'+bid+'/tables')
                candidates=[t for t in schema['tables'] if t['name']=='Projects']
                records=[]
                if len(candidates)==1:
                    from urllib.parse import quote
                    path=bid+'/'+candidates[0]['id'];offset=None
                    while True:
                        page=api.call(path+('?offset='+quote(offset,safe='') if offset else ''))
                        records.extend({'record_id':r['id'],'project_id':r.get('fields',{}).get('Project ID'),'name':r.get('fields',{}).get('Name')} for r in page.get('records',[]))
                        offset=page.get('offset')
                        if not offset:break
                print(json.dumps({'base_id':bid,'tables':schema['tables'],'projects':records},ensure_ascii=False));return
            from setup import extract_id
            bid=extract_id(args.base_id,'app');tables=api.call('meta/bases/'+bid+'/tables')['tables']
            selected={}
            for name in ('Projects','Updates'):
                matches=[t for t in tables if t['name']==name]
                if len(matches)!=1:raise SyncError('Target needs compatible Projects and Updates tables; run the project setup wizard.')
                selected[name]=matches[0]
            from setup import fields
            for name in selected:
                actual={f['name']:f for f in selected[name]['fields']}
                for field in fields(name=='Projects'):
                    if actual.get(field['name'],{}).get('type')!=field['type']:raise SyncError('Incompatible field: '+name+'.'+field['name'])
            link=next((f for f in selected['Updates']['fields'] if f['name']=='Project'),{})
            if link.get('type')!='multipleRecordLinks' or link.get('options',{}).get('linkedTableId')!=selected['Projects']['id']:raise SyncError('Incompatible Project link.')
            c={'base_id':bid,'projects_table':selected['Projects']['id'],'updates_table':selected['Updates']['id'],'keychain_service':'engineering-airtable-sync'}
            if args.project_id:
                from sync import Airtable, STATE
                if not Airtable(c).find(c['projects_table'],'Project ID',args.project_id):raise SyncError('Project ID not found in selected base.')
                state=read_json(STATE,{'projects':{},'plans':{}})
                state.setdefault('projects',{})[project_key(args.project)]={'project_id':args.project_id,'root':repo_identity(args.project)[1]}
                write_json(STATE,state)
            target=config_path(args.project);write_json(target,c);register(args.project,target)
            print(json.dumps({'bound':True,'config_path':str(target),'base_id':bid,'project_id':args.project_id},ensure_ascii=False))
    except (SyncError,KeyError,ValueError) as e:p.exit(1,str(e)+'\n')

if __name__=='__main__':main()
