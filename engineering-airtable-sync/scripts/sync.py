#!/usr/bin/env python3
"""Preview and apply an Airtable project progress update. Python 3.9+."""
import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

HOME = Path.home() / '.config' / 'engineering-airtable-sync'
CONFIG = HOME / 'config.json'
STATE = HOME / 'state.json'
LOCK = HOME / 'sync.lock'
FIELDS_PROJECT = {'name': 'Name', 'project_id': 'Project ID', 'stage': 'Current Stage', 'latest': 'Latest Progress', 'blockers': 'Blockers', 'next': 'Next Steps', 'synced': 'Last Synced'}
FIELDS_UPDATE = {'name': 'Name', 'update_id': 'Update ID', 'project': 'Project', 'completed': 'Completed', 'in_progress': 'In Progress', 'blockers': 'Blockers', 'next': 'Next Steps', 'verification': 'Verification', 'evidence': 'Evidence', 'source': 'Source', 'time': 'Recorded At'}

PLANNING = {'overview': 'Overview', 'goals': 'Goals', 'scope': 'Scope', 'plan': 'Plan', 'open_questions': 'Open Questions', 'planning_status': 'Planning Status'}
TASK_FIELDS = {'name': 'Name', 'task_id': 'Task ID', 'status': 'Status', 'description': 'Description', 'acceptance': 'Acceptance Criteria', 'phase': 'Phase', 'priority': 'Priority', 'dependencies': 'Dependencies', 'evidence': 'Evidence'}

class SyncError(Exception): pass

def read_json(path, default=None):
    try:
        with path.open(encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError:
        if default is not None: return default
        raise SyncError(f'Missing file: {path}')
    except (ValueError, OSError) as e: raise SyncError(f'Cannot read {path}: {e}')

def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)

@contextlib.contextmanager
def locked():
    HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
    with LOCK.open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield

def load_config(project=None):
    path = CONFIG
    if project is not None:
        from project import destination
        path = destination(project)
    c = read_json(path)
    for k in ('base_id', 'projects_table', 'updates_table'):
        if not isinstance(c.get(k), str) or not c[k].strip(): raise SyncError(f'Configuration needs {k}: {CONFIG}')
    return c

def token(c):
    try:
        p = subprocess.run(['security', 'find-generic-password', '-s', c.get('keychain_service', 'engineering-airtable-sync'), '-w'], capture_output=True, text=True, check=True)
        if p.stdout.strip(): return p.stdout.strip()
    except (OSError, subprocess.CalledProcessError): pass
    secret_path = HOME / 'token'
    if secret_path.exists():
        if secret_path.stat().st_mode & 0o077: raise SyncError('Token file permissions must be 600.')
        value = secret_path.read_text().strip()
        if value: return value
    raise SyncError('Airtable token unavailable. In a local terminal, run python3 <installed-skill-dir>/scripts/credentials.py to enter it privately. Never paste the token into chat or a browser form.')

class Airtable:
    def __init__(self, config): self.c, self.token = config, token(config)
    def request(self, table, method='GET', data=None, params=None):
        base = urllib.parse.quote(self.c['base_id'], safe='')
        url = 'https://api.airtable.com/v0/' + base + '/' + urllib.parse.quote(table, safe='')
        if params: url += '?' + urllib.parse.urlencode(params)
        body = json.dumps(data).encode() if data is not None else None
        for attempt in range(3):
            req = urllib.request.Request(url, data=body, method=method, headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2: time.sleep(30); continue
                # No automatic retry on ambiguous write errors; the next apply reconciles by ID.
                raise SyncError(f'Airtable HTTP {e.code}; check permissions, table and field types. Retry the same plan after resolving.')
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                raise SyncError(f'Airtable connection failed ({type(e).__name__}); outcome may be unknown. Retry the same plan.')
        raise SyncError('Airtable rate limit persists.')
    def find(self, table, field, value):
        # Quote Airtable formula string literals, including backslashes and apostrophes.
        val = value.replace('\\', '\\\\').replace("'", "\\'")
        params = {'filterByFormula': "{" + field + "}='" + val + "'", 'pageSize': 100}
        result = []
        while True:
            page = self.request(table, params=params); result.extend(page.get('records', []))
            if not page.get('offset'): break
            params['offset'] = page['offset']
        if len(result) > 1: raise SyncError(f'Duplicate {field}={value} in {table}; resolve manually before retrying.')
        return result[0] if result else None
    def upsert(self, table, key, fields):
        return self.request(table, 'PATCH', {'performUpsert': {'fieldsToMergeOn': [key]}, 'records': [{'fields': fields}]})['records'][0]

def git_output(path, *args):
    try:
        return subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''

def repo_identity(path):
    p = Path(path).expanduser().resolve()
    root = git_output(p, 'rev-parse', '--show-toplevel')
    if not root:
        return str(p), str(p), ''
    common = git_output(p, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    identity = str(Path(common).resolve()) if common else str(Path(root).resolve() / '.git')
    return identity, root, git_output(p, 'remote', 'get-url', 'origin')

def git_snapshot(path, baseline=None):
    p = Path(path).expanduser().resolve()
    root = git_output(p, 'rev-parse', '--show-toplevel')
    if not root:
        return {'kind': 'directory', 'root': str(p), 'baseline_status': 'not_applicable'}
    branch = git_output(p, 'symbolic-ref', '--quiet', '--short', 'HEAD') or None
    head = git_output(p, 'rev-parse', 'HEAD') or None
    result = {'kind': 'git', 'root': root, 'branch': branch, 'head': head,
              'dirty': bool(git_output(p, 'status', '--porcelain')), 'baseline': baseline}
    if not baseline:
        result['baseline_status'] = 'initial'
    elif not head:
        result['baseline_status'] = 'unborn_head'
    elif subprocess.run(['git', '-C', str(p), 'merge-base', '--is-ancestor', baseline, head], capture_output=True).returncode == 0:
        result['baseline_status'] = 'ancestor'
        result['commits_since_baseline'] = git_output(p, 'log', '--format=%H', baseline + '..' + head).splitlines()[:100]
    else:
        result['baseline_status'] = 'diverged_or_missing'
    return result

def validate_payload(p):
    if not isinstance(p, dict): raise SyncError('Input must be a JSON object.')
    allowed = {'project_name', 'title', 'completed', 'in_progress', 'blockers', 'next_steps', 'verification', 'evidence', 'source', 'current_stage', 'latest_progress', 'record_type', 'content', 'record_status'}
    allowed |= set(PLANNING) | {'tasks'}
    if set(p) - allowed: raise SyncError('Unknown input fields: ' + ', '.join(sorted(set(p)-allowed)))
    tasks = p.get('tasks', [])
    if not isinstance(tasks, list) or len(tasks) > 200: raise SyncError('tasks must be a list of at most 200 tasks.')
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) - set(TASK_FIELDS): raise SyncError('Unknown task fields.')
        if any(not isinstance(v, str) or len(v) > 50000 for v in task.values()): raise SyncError('Task values must be strings of at most 50000 characters.')
        if any(not task.get(k, '').strip() for k in ('task_id', 'name', 'status', 'description', 'acceptance')): raise SyncError('Each task needs task_id, name, status, description and acceptance.')
        if task['task_id'] in ids: raise SyncError('Duplicate task_id in input.')
        ids.add(task['task_id'])
    for k, v in p.items():
        if k == 'tasks': continue
        if not isinstance(v, str): raise SyncError(f'{k} must be a string.')
        if len(v) > 50000: raise SyncError(f'{k} is too long.')
    kind = p.get('record_type', 'progress')
    if kind not in ('idea', 'requirement', 'decision', 'progress', 'blocker', 'plan', 'analysis', 'brief'): raise SyncError('Invalid record_type.')
    body = 'completed' if kind == 'progress' else 'content'
    if kind != 'progress' and not p.get('record_status', '').strip(): raise SyncError('Non-progress records require an explicit record_status.')
    if kind != 'progress' and any(k in p for k in ('completed','latest_progress','in_progress')): raise SyncError('Non-progress notes must not claim completed engineering work.')
    for k in ('project_name', 'title', body):
        if not p.get(k, '').strip(): raise SyncError(f'{k} is required; no empty progress records.')
    return p

def project_fields(payload, project_id, timestamp):
    f = FIELDS_PROJECT
    out = {f['name']: payload['project_name'], f['project_id']: project_id, f['synced']: timestamp}
    if payload.get('record_type','progress') == 'progress':
        out[f['latest']] = payload.get('latest_progress') or payload['completed']
    for source, key in [('current_stage','stage'), ('blockers','blockers'), ('next_steps','next')]:
        if source in payload: out[f[key]] = payload[source]
    for source, field in PLANNING.items():
        if source in payload: out[field] = payload[source]
    return out

def update_fields(payload, update_id, project_record_id, timestamp, version=1):
    f = FIELDS_UPDATE
    out = {f['name']: payload['title'], f['update_id']: update_id, f['project']: [project_record_id], f['time']: timestamp}
    kind = payload.get('record_type', 'progress')
    if kind == 'progress': out[f['completed']] = payload['completed']
    else:
        out[f['name']] = '[' + kind + ' / ' + payload['record_status'] + '] ' + payload['title']
        out[f['in_progress']] = payload['content']
    for source, key in [('in_progress','in_progress'), ('blockers','blockers'), ('next_steps','next'), ('verification','verification'), ('evidence','evidence'), ('source','source')]:
        if source in payload: out[f[key]] = payload[source]
    if version >= 2:
        out['Content'] = payload.get('content') or payload.get('completed', '')
        out['Type'] = kind
        out['Status'] = payload.get('record_status', 'recorded')
        if kind != 'progress': out.pop(f['in_progress'], None)
    return out

def fingerprint(project_id, p, config, evidence=None):
    git_marker = [evidence.get('branch'), evidence.get('head')] if evidence and evidence.get('kind') == 'git' and p.get('record_type', 'progress') == 'progress' else None
    return hashlib.sha256(json.dumps([config['base_id'], config['projects_table'], config['updates_table'], config.get('tasks_table'), config.get('schema_version', 1), project_id, p, git_marker], ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def preview(args, c, state, api):
    payload = validate_payload(read_json(Path(args.input)))
    if (set(payload) & set(PLANNING) or payload.get('tasks') or payload.get('record_type') in ('plan', 'analysis', 'brief')) and c.get('schema_version', 1) < 2:
        raise SyncError('Planning requires schema v2. Run auto.py upgrade --project <path> first.')
    identity, root, remote = repo_identity(args.project)
    from project import project_key
    identity = project_key(args.project)
    projects = state.setdefault('projects', {})
    if identity not in projects: projects[identity] = {'project_id': 'proj_' + uuid.uuid4().hex, 'root': root, 'remote': remote}
    project = projects[identity]; pid = project['project_id']
    branch = git_output(root, 'symbolic-ref', '--quiet', '--short', 'HEAD') or None
    baseline = state.setdefault('baselines', {}).get(pid, {}).get(branch) if branch else None
    evidence = git_snapshot(root, baseline)
    fp = fingerprint(pid, payload, c, evidence)
    # Identical payloads are intentionally no-ops; edit content to report genuinely new work.
    for plan in state.setdefault('plans', {}).values():
        if plan['fingerprint'] == fp and not (args.refresh and not plan['project_done']):
            print(json.dumps({'message': 'Existing plan for identical content', 'plan': plan}, ensure_ascii=False, indent=2)); write_json(STATE, state); return
    existing = api.find(c['projects_table'], FIELDS_PROJECT['project_id'], pid)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    pf = project_fields(payload, pid, timestamp)
    # Only guard fields the plan intends to modify, not unrelated human-owned fields.
    before = {k: existing.get('fields', {}).get(k) for k in pf if k != FIELDS_PROJECT['synced']} if existing else None
    plan_id = 'upd_' + uuid.uuid4().hex
    plan = {'id': plan_id, 'fingerprint': fp, 'config_snapshot': c, 'destination': [c['base_id'], c['projects_table'], c['updates_table']], 'project_id': pid, 'project_root': root, 'project_remote': remote, 'git_evidence': evidence, 'payload': payload, 'timestamp': timestamp, 'project_record_id': existing['id'] if existing else None, 'before': before, 'project_fields': pf, 'project_done': False, 'update_done': False}
    plan['tasks'] = []
    for task in payload.get('tasks', []):
        # Scope task IDs by project; stable across retries and plan revisions.
        key = pid + ':' + task['task_id']
        fields = {TASK_FIELDS[k]: v for k, v in task.items()}
        fields['Task ID'] = key
        old = api.find(c['tasks_table'], 'Task ID', key)
        if old and (not existing or old['fields'].get('Project') != [existing['id']]): raise SyncError('Task belongs to another project.')
        plan['tasks'].append({'fields': fields, 'before': {k: old['fields'].get(k) for k in [*fields, 'Project']} if old else None, 'done': False})
    state['plans'][plan_id] = plan; write_json(STATE, state)
    print(json.dumps({'message': 'Preview only; no Airtable writes', 'plan': plan}, ensure_ascii=False, indent=2))

def equal_fields(actual, expected):
    for key, value in expected.items():
        got = actual.get(key)
        if value == '' and got is None: continue
        if key == FIELDS_UPDATE['time'] and isinstance(got, str) and isinstance(value, str):
            try:
                if dt.datetime.fromisoformat(got.replace('Z', '+00:00')) == dt.datetime.fromisoformat(value.replace('Z', '+00:00')): continue
            except ValueError: pass
        if got != value: return False
    return True

def apply(args, c, state, api):
    plan = state.get('plans', {}).get(args.plan_id)
    if not plan: raise SyncError('Unknown plan ID. Run preview first.')
    if plan.get('destination') != [c['base_id'], c['projects_table'], c['updates_table']]: raise SyncError('Configuration destination changed since preview; restore it before retrying this plan.')
    ptable, utable = c['projects_table'], c['updates_table']
    pf, uf = FIELDS_PROJECT, FIELDS_UPDATE
    if not plan['project_done']:
        current = api.find(ptable, pf['project_id'], plan['project_id'])
        now = {k: current.get('fields', {}).get(k) for k in plan['before']} if current and plan['before'] is not None else None
        desired = {k: v for k, v in plan['project_fields'].items() if k != pf['synced']}
        # Reconcile an ambiguous previous write when it already matches desired state.
        already = current and equal_fields(current.get('fields', {}), desired)
        if not already:
            if (current is None) != (plan['before'] is None) or (current and now != plan['before']):
                raise SyncError('Project changed since preview. Create a fresh preview after inspecting the remote record.')
            current = api.upsert(ptable, pf['project_id'], plan['project_fields'])
        verified = api.find(ptable, pf['project_id'], plan['project_id'])
        if not verified or not equal_fields(verified.get('fields', {}), desired): raise SyncError('Project write could not be verified; retry the same plan.')
        plan['project_record_id'] = current['id']; plan['project_done'] = True; write_json(STATE, state)
    for task in plan.get('tasks', []):
        if task['done']: continue
        fields = dict(task['fields'], Project=[plan['project_record_id']])
        current = api.find(c['tasks_table'], 'Task ID', fields['Task ID'])
        if not current or not equal_fields(current.get('fields', {}), fields):
            now = {k: current['fields'].get(k) for k in task['before']} if current and task['before'] is not None else None
            if (current is None) != (task['before'] is None) or now != task['before']: raise SyncError('Task changed since preview; inspect before retrying.')
            current = api.upsert(c['tasks_table'], 'Task ID', fields)
        verified = api.find(c['tasks_table'], 'Task ID', fields['Task ID'])
        if not verified or not equal_fields(verified.get('fields', {}), fields): raise SyncError('Task write could not be verified; retry the same plan.')
        task['record_id'] = current['id']; task['done'] = True; write_json(STATE, state)
    if not plan['update_done']:
        existing = api.find(utable, uf['update_id'], plan['id'])
        fields = update_fields(plan['payload'], plan['id'], plan['project_record_id'], plan['timestamp'], c.get('schema_version', 1))
        if existing:
            if not equal_fields(existing.get('fields', {}), fields):
                raise SyncError('Existing work record differs from this plan; inspect it before retrying.')
            record = existing
        else: record = api.upsert(utable, uf['update_id'], fields)
        verified = api.find(utable, uf['update_id'], plan['id'])
        if not verified or not equal_fields(verified.get('fields', {}), fields): raise SyncError('Update write could not be verified; retry the same plan.')
        plan['update_record_id'] = record['id']; plan['update_done'] = True; write_json(STATE, state)
    evidence = plan.get('git_evidence', {})
    if plan['payload'].get('record_type', 'progress') == 'progress' and evidence.get('kind') == 'git' and evidence.get('branch') and evidence.get('head'):
        current = git_snapshot(plan['project_root'])
        if current.get('branch') == evidence['branch'] and current.get('head') == evidence['head']:
            state.setdefault('baselines', {}).setdefault(plan['project_id'], {})[evidence['branch']] = evidence['head']
            write_json(STATE, state)
    base = c['base_id']
    print(json.dumps({'status': 'synced', 'plan_id': plan['id'], 'project_record_id': plan['project_record_id'], 'update_record_id': plan['update_record_id'], 'tasks': [{'record_id': t['record_id'], 'url': f"https://airtable.com/{base}/{c['tasks_table']}/{t['record_id']}"} for t in plan.get('tasks', [])], 'baseline_status': plan.get('git_evidence', {}).get('baseline_status'), 'project_url': f'https://airtable.com/{base}/{ptable}/{plan["project_record_id"]}', 'update_url': f'https://airtable.com/{base}/{utable}/{plan["update_record_id"]}'}, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    pre = sub.add_parser('preview'); pre.add_argument('--input', required=True); pre.add_argument('--project', default='.'); pre.add_argument('--refresh', action='store_true', help='refresh a preview after a conflict before project write')
    ap = sub.add_parser('apply'); ap.add_argument('plan_id')
    status_parser = sub.add_parser('status'); status_parser.add_argument('--project')
    plan_parser = sub.add_parser('plan'); plan_parser.add_argument('plan_id')
    args = parser.parse_args()
    try:
        with locked():
            state = read_json(STATE, {'projects': {}, 'plans': {}})
            if args.cmd == 'plan':
                plan = state.get('plans', {}).get(args.plan_id)
                if not plan: raise SyncError('Unknown plan ID.')
                print(json.dumps({'plan': plan, 'recovery': 'If partially written, retry apply with the same plan ID after inspecting the remote change.'}, ensure_ascii=False, indent=2)); return 0
            if args.cmd == 'apply':
                c = state.get('plans', {}).get(args.plan_id, {}).get('config_snapshot') or load_config()
            else:
                c = load_config(getattr(args, 'project', None))
            if args.cmd == 'status':
                api = Airtable(c); api.request(c['projects_table'], params={'maxRecords': 1}); api.request(c['updates_table'], params={'maxRecords': 1})
                print(json.dumps({'status': 'connected', 'projects': len(state.get('projects', {})), 'pending_plans': [p['id'] for p in state.get('plans', {}).values() if not p['update_done']]}, ensure_ascii=False, indent=2))
            elif args.cmd == 'preview': preview(args, c, state, Airtable(c))
            else: apply(args, c, state, Airtable(c))
    except (SyncError, KeyError, ValueError) as e:
        if args.cmd == 'apply':
            saved = read_json(STATE, {}).get('plans', {}).get(args.plan_id, {})
            print(json.dumps({'status': 'partial_failure' if saved.get('project_done') else 'failed_or_unknown', 'plan_id': args.plan_id, 'project_confirmed': bool(saved.get('project_done')), 'update_confirmed': bool(saved.get('update_done')), 'error': str(e), 'recovery': 'Resolve the error and retry the same plan ID; unconfirmed writes may have reached Airtable.'}, ensure_ascii=False), file=sys.stderr)
        else:
            print(f'Error: {e}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
