#!/usr/bin/env python3
"""Airtable schema provisioning helpers used by the agent CLI."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from sync import HOME, CONFIG, SyncError, locked, read_json, write_json

CHECKPOINT = HOME / 'setup-state.json'
TOKEN = HOME / 'token'
DATE = {'type': 'dateTime', 'options': {'dateFormat': {'name': 'iso'}, 'timeFormat': {'name': '24hour'}, 'timeZone': 'utc'}}

def fields(project=False):
    result = [{'name': 'Name', 'type': 'singleLineText'}]
    if project:
        result += [{'name': 'Project ID', 'type': 'singleLineText'}]
        names = ['Current Stage', 'Latest Progress', 'Blockers', 'Next Steps']
    else:
        result += [{'name': 'Update ID', 'type': 'singleLineText'}]
        names = ['Completed', 'In Progress', 'Blockers', 'Next Steps', 'Verification', 'Evidence']
    result += [{'name': name, 'type': 'multilineText'} for name in names]
    if not project: result += [{'name': 'Source', 'type': 'singleLineText'}]
    result += [{'name': 'Last Synced' if project else 'Recorded At', **DATE}]
    additions = ['Overview', 'Goals', 'Scope', 'Plan', 'Open Questions', 'Planning Status'] if project else ['Content', 'Type', 'Status']
    result[1:1] = [{'name': n, 'type': 'multilineText'} for n in additions]
    return result

class MetaAPI:
    def __init__(self, token): self.token = token; self.last_request = 0
    def call(self, path, data=None):
        time.sleep(max(0, .26 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        req = urllib.request.Request('https://api.airtable.com/v0/' + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'},
            method='POST' if data is not None else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            # Airtable's error body identifies common causes (scope, workspace
            # access, malformed payload). It contains no credential; retain it
            # so users can diagnose Base creation instead of seeing a generic 4xx.
            try:
                detail = json.loads(e.read().decode('utf-8'))
                error = detail.get('error', {})
                if isinstance(error, dict):
                    reason = error.get('type') or error.get('message')
                else:
                    reason = str(error)
            except (ValueError, UnicodeDecodeError, OSError):
                reason = ''
            suffix = f' ({reason})' if reason else ''
            raise AirtableHTTPError(f'Airtable HTTP {e.code}{suffix}. Check PAT scopes, workspace access, Creator permission, and the requested schema.', e.code)
        except (urllib.error.URLError, OSError, ValueError):
            raise SyncError('连接中断，写入结果可能未知。请到 Airtable 检查；如已创建 Base，请选择连接已有 Base，不要直接重复创建。')

class AirtableHTTPError(SyncError):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status

def extract_id(value, prefix):
    m = re.search(r'(?<![A-Za-z0-9])(' + prefix + r'[A-Za-z0-9]+)(?![A-Za-z0-9])', value)
    if not m: raise SyncError('请填写有效的 Airtable ' + prefix + ' ID 或含该 ID 的链接。')
    return m.group(1)

def bootstrap(api, mode, location, name, upgrade=False):
    if mode not in ('new', 'existing'): raise SyncError('请选择创建或连接。')
    target = extract_id(location, 'wsp' if mode == 'new' else 'app')
    checkpoint = read_json(CHECKPOINT, {})
    key = [mode, target, name]
    if CONFIG.exists() and not upgrade:
        raise SyncError('本机已有配置，已停止以免覆盖。若需切换，请先让 AI 检查并备份现有配置。')
    if mode == 'new':
        if checkpoint.get('key') == key:
            if not checkpoint.get('base_id'):
                raise SyncError('上次创建结果未知。请检查 Airtable；若已有 Base，使用其链接连接；若确认未创建，请让 AI 备份并清除 setup-state.json 后重试。')
            base_id = checkpoint['base_id']
        else:
            if checkpoint:
                raise SyncError('已有未完成的初始化，请先让 AI 检查 setup-state.json 中的目标，避免重复创建。')
            write_json(CHECKPOINT, {'key': key, 'creation_pending': True})
            try:
                created = api.call('meta/bases', {'name': name or 'Engineering Tracker', 'workspaceId': target,
                    'tables': [{'name': 'Projects', 'fields': fields(True)}]})
            except AirtableHTTPError as error:
                # A definite HTTP rejection means no Base was created; allow a
                # corrected retry without leaving a false "outcome unknown" lock.
                if 400 <= error.status < 500 and error.status != 408:
                    CHECKPOINT.unlink(missing_ok=True)
                raise
            base_id = created['id']
            write_json(CHECKPOINT, {'key': key, 'base_id': base_id})
    else: base_id = target
    path = 'meta/bases/' + base_id + '/tables'
    tables = api.call(path)['tables']
    def ensure_table(name, required):
        matches = [t for t in tables if t['name'].lower() == name.lower()]
        if len(matches) > 1: raise SyncError('存在同名表，请先处理：' + name)
        if matches:
            table = matches[0]
            existing = {f['name']: f for f in table['fields']}
            for f in required:
                if f['name'] in existing and existing[f['name']]['type'] != f['type']:
                    raise SyncError(name + '.' + f['name'] + ' 类型不兼容，未修改已有字段。')
            if table.get('primaryFieldId') != existing.get('Name', {}).get('id'):
                raise SyncError(name + ' 的主字段需为 Name 文本字段，未修改已有表。')
            for f in required:
                if f['name'] not in existing:
                    api.call(path + '/' + table['id'] + '/fields', f)
        else: table = api.call(path, {'name': name, 'fields': required})
        return table['id']
    pid = ensure_table('Projects', fields(True))
    uid = ensure_table('Updates', fields())
    tables = api.call(path)['tables']
    updates = next(t for t in tables if t['id'] == uid)
    link = next((f for f in updates['fields'] if f['name'] == 'Project'), None)
    if link:
        if link['type'] != 'multipleRecordLinks' or link.get('options', {}).get('linkedTableId') != pid:
            raise SyncError('Updates.Project 关联不兼容，未修改已有关联。')
    else: api.call(path + '/' + uid + '/fields', {'name': 'Project', 'type': 'multipleRecordLinks', 'options': {'linkedTableId': pid}})
    tid = ensure_table('Tasks', [{'name': 'Name', 'type': 'singleLineText'}] + [{'name': n, 'type': 'multilineText'} for n in ['Status', 'Description', 'Acceptance Criteria', 'Phase', 'Priority', 'Dependencies', 'Evidence', 'Task ID']])
    task_table = next(t for t in api.call(path)['tables'] if t['id'] == tid)
    task_link = next((f for f in task_table['fields'] if f['name'] == 'Project'), None)
    if task_link and (task_link['type'] != 'multipleRecordLinks' or task_link.get('options', {}).get('linkedTableId') != pid):
        raise SyncError('Tasks.Project link is incompatible; existing field preserved.')
    if not task_link:
        api.call(path + '/' + tid + '/fields', {'name': 'Project', 'type': 'multipleRecordLinks', 'options': {'linkedTableId': pid}})
    return {'schema_version': 2, 'tasks_table': tid, 'base_id': base_id, 'projects_table': pid, 'updates_table': uid, 'keychain_service': 'engineering-airtable-sync'}
