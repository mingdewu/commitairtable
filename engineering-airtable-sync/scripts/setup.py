#!/usr/bin/env python3
"""Local browser onboarding; creates Airtable schema and saves configuration."""
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
            raise SyncError(f'Airtable HTTP {e.code}。请检查令牌的结构读写权限、目标授权和 Creator 权限；已有部分成果会保留。')
        except (urllib.error.URLError, OSError, ValueError):
            raise SyncError('连接中断，写入结果可能未知。请到 Airtable 检查；如已创建 Base，请选择连接已有 Base，不要直接重复创建。')

def extract_id(value, prefix):
    m = re.search(r'(?<![A-Za-z0-9])(' + prefix + r'[A-Za-z0-9]+)(?![A-Za-z0-9])', value)
    if not m: raise SyncError('请填写有效的 Airtable ' + prefix + ' ID 或含该 ID 的链接。')
    return m.group(1)

def bootstrap(api, mode, location, name):
    if mode not in ('new', 'existing'): raise SyncError('请选择创建或连接。')
    target = extract_id(location, 'wsp' if mode == 'new' else 'app')
    checkpoint = read_json(CHECKPOINT, {})
    key = [mode, target, name]
    if CONFIG.exists():
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
            created = api.call('meta/bases', {'name': name or 'Engineering Tracker', 'workspaceId': target,
                'tables': [{'name': 'Projects', 'fields': fields(True)}]})
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
    return {'base_id': base_id, 'projects_table': pid, 'updates_table': uid, 'keychain_service': 'engineering-airtable-sync'}

def save_token(value):
    # Prefer the OS credential store. Never echo credentials or include them in errors.
    if sys.platform == 'darwin':
        try:
            subprocess.run(['security', 'add-generic-password', '-U', '-s', 'engineering-airtable-sync', '-a', 'engineering-airtable-sync', '-w', value], check=True, capture_output=True)
            return 'macOS 钥匙串'
        except (OSError, subprocess.CalledProcessError):
            raise SyncError('钥匙串保存失败。请解锁钥匙串后重试，或由 AI 检查本机凭据存储。')
    HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f: f.write(value)
    os.chmod(TOKEN, 0o600)
    return '本机权限为 600 的令牌文件（未加密）'

PAGE = '''<!doctype html><meta charset="utf-8"><title>Airtable 首次连接</title>
<style>body{font:16px system-ui;max-width:680px;margin:40px auto;padding:16px;line-height:1.7}input,select,button{box-sizing:border-box;display:block;width:100%;padding:10px;margin:8px 0 20px}button{background:#176b52;color:white;border:0;border-radius:6px}small{color:#555}</style>
<h1>连接 Airtable</h1><p>工具会创建所需表、关联字段并生成本机配置。不会删除现有表或记录。</p>
<p>首次使用：在 <a href="https://airtable.com/create/tokens" target="_blank" rel="noreferrer">Airtable 创建访问令牌</a>，勾选 <code>data.records:read</code>、<code>data.records:write</code>、<code>schema.bases:read</code>、<code>schema.bases:write</code>。创建新 Base 时，授权目标工作区的当前及未来 Base，并确保拥有创建权限；连接已有 Base 时，只需授权该 Base。</p>
<form id="f"><label>令牌（只在本机接收并发送给 Airtable，不进入 AI 对话）<input name="token" type="password" autocomplete="off" required></label>
<label>目标<select name="mode"><option value="new">在指定工作区创建新 Base</option><option value="existing">连接已有 Base，自动补齐表结构</option></select></label>
<label>工作区链接 / wsp ID，或已有 Base 链接 / app ID<input name="location" required placeholder="粘贴 Airtable 中的目标链接"></label>
<label>新 Base 名称<input name="name" value="Engineering Tracker"></label>
<p><small>macOS 使用系统钥匙串；Linux / WSL 使用本机权限 600 的未加密令牌文件。设置完成后无需每次输入。</small></p>
<button>创建 / 连接并保存配置</button></form><p id="result" role="status"></p>
<script>document.querySelector('#f').onsubmit=async e=>{e.preventDefault();let f=e.target,b=f.querySelector('button'),r=document.querySelector('#result');b.disabled=true;r.textContent='正在连接，请等待…';let data=Object.fromEntries(new FormData(f));try{let resp=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let j=await resp.json();r.textContent=j.message;if(j.ok){f.reset();f.hidden=true;}}catch{r.textContent='连接中断，请让 AI 检查本机状态后再重试。';}finally{b.disabled=false;f.elements.token.value='';}};</script>'''

def make_handler(secret):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def respond(self, status, body, content_type):
            self.send_response(status); self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer'); self.send_header('X-Content-Type-Options', 'nosniff'); self.end_headers()
            self.wfile.write(body.encode())
        def valid(self):
            expected_host = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == expected_host and hmac.compare_digest(self.path, '/' + secret)
        def do_GET(self):
            if not self.valid(): return self.respond(404, 'Not found', 'text/plain')
            self.respond(200, PAGE, 'text/html; charset=utf-8')
        def do_POST(self):
            if not self.valid() or self.headers.get('Origin') != f'http://127.0.0.1:{self.server.server_port}':
                return self.respond(403, '{}', 'application/json')
            try:
                n = int(self.headers.get('Content-Length', '0'))
                if not 0 < n <= 12000: raise SyncError('输入过长或为空。')
                data = json.loads(self.rfile.read(n))
                if not isinstance(data, dict) or any(not isinstance(v, str) for v in data.values()): raise SyncError('输入格式无效。')
                value = data.get('token', '').strip()
                if not value.startswith('pat'): raise SyncError('请输入有效的 Airtable PAT。')
                with locked():
                    c = bootstrap(MetaAPI(value), data.get('mode'), data.get('location', ''), data.get('name', '').strip())
                    store = save_token(value)
                    # Verify record read permissions as well as schema; no fake test records are inserted.
                    api = MetaAPI(value)
                    for table in (c['projects_table'], c['updates_table']): api.call(c['base_id'] + '/' + table + '?maxRecords=1')
                    write_json(CONFIG, c)
                response = {'ok': True, 'message': '配置已自动保存，令牌保存在' + store + '。表结构和读取已验证，首次同步将验证记录写入权限。可返回 AI 继续同步。'}
            except (SyncError, ValueError, KeyError) as e:
                response = {'ok': False, 'message': str(e) if isinstance(e, SyncError) else '输入或接口响应格式无效。'}
            except Exception:
                response = {'ok': False, 'message': '设置失败，请让 AI 检查本地工具。令牌未写入日志。'}
            self.respond(200, json.dumps(response, ensure_ascii=False), 'application/json; charset=utf-8')
    return Handler

def main():
    global CONFIG, CHECKPOINT
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--no-open', action='store_true'); p.add_argument('--project'); args = p.parse_args()
    if args.project:
        from project import config_path, register
        CONFIG = config_path(args.project)
        CHECKPOINT = CONFIG.with_suffix('.setup.json')
        with locked(): register(args.project, CONFIG)
    if CONFIG.exists():
        print('本机已有配置，请先运行 sync.py status 检查连接；如需切换，先备份配置。'); return
    secret = secrets.token_urlsafe(32)
    server = HTTPServer(('127.0.0.1', 0), make_handler(secret))
    url = f'http://127.0.0.1:{server.server_port}/{secret}'
    print('在本机浏览器完成首次连接：' + url, flush=True)
    if not args.no_open: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == '__main__': main()
