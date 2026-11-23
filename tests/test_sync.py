import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('sync', Path(__file__).parents[1] / 'engineering-airtable-sync/scripts/sync.py')
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)

class FakeAPI:
    def __init__(self): self.tables = {'projects': {}, 'updates': {}}; self.fail_update = False; self.writes = []
    def find(self, table, field, value):
        values = [v for v in self.tables[table].values() if v['fields'].get(field) == value]
        if len(values) > 1: raise sync.SyncError('duplicate')
        return values[0] if values else None
    def upsert(self, table, key, fields):
        if table == 'updates' and self.fail_update: raise sync.SyncError('simulated failure')
        old = self.find(table, key, fields[key])
        record = {'id': old['id'] if old else 'rec' + str(sum(map(len, self.tables.values()))+1), 'fields': dict(old['fields']) if old else {}}
        record['fields'].update(fields); self.tables[table][record['id']] = record; self.writes.append(table)
        return record

class TestSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.oldstate = sync.STATE; sync.STATE = Path(self.tmp.name)/'state.json'; self.addCleanup(setattr, sync, 'STATE', self.oldstate)
        self.config = {'base_id':'app1','projects_table':'projects','updates_table':'updates'}
        self.api = FakeAPI(); self.state = {'projects': {}, 'plans': {}}
        self.payload = {'project_name':'Example','title':'Login','completed':'Implemented form, not deployed','verification':'Unit tests passed'}
        self.infile = Path(self.tmp.name)/'input.json'; self.infile.write_text(json.dumps(self.payload))
        self.args = types.SimpleNamespace(input=str(self.infile), project=self.tmp.name, refresh=False)
    def preview(self):
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args, self.config, self.state, self.api)
        return next(iter(self.state['plans']))
    def apply(self, pid):
        with contextlib.redirect_stdout(io.StringIO()): sync.apply(types.SimpleNamespace(plan_id=pid), self.config, self.state, self.api)
    def test_preview_no_write_and_idempotent_apply(self):
        pid = self.preview(); self.assertEqual(self.api.writes, [])
        self.apply(pid); self.apply(pid); self.preview()
        self.assertEqual(self.api.writes, ['projects', 'updates']); self.assertEqual(len(self.state['plans']), 1)
        self.assertEqual(next(iter(self.api.tables['updates'].values()))['fields']['Project'], ['rec1'])
    def test_partial_failure_resumes(self):
        pid = self.preview(); self.api.fail_update = True
        with self.assertRaises(sync.SyncError): self.apply(pid)
        self.assertTrue(self.state['plans'][pid]['project_done']); self.assertFalse(self.state['plans'][pid]['update_done'])
        self.api.fail_update = False; self.apply(pid)
        self.assertEqual(self.api.writes, ['projects','updates'])
    def test_remote_human_edit_stops_overwrite(self):
        pid = self.preview(); self.apply(pid)
        self.payload['completed'] = 'New work'; self.infile.write_text(json.dumps(self.payload))
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args,self.config,self.state,self.api)
        new_id = list(self.state['plans'])[-1]
        next(iter(self.api.tables['projects'].values()))['fields']['Latest Progress'] = 'Human edit'
        with self.assertRaisesRegex(sync.SyncError, 'changed since preview'): self.apply(new_id)
    def test_human_owned_fields_preserved(self):
        pid=self.preview(); self.apply(pid)
        rec=next(iter(self.api.tables['projects'].values())); rec['fields'].update({'Owner':'Alice','Priority':'High','Deadline':'2026-12-01'})
        self.payload['completed']='New work'; self.infile.write_text(json.dumps(self.payload))
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args,self.config,self.state,self.api)
        self.apply(list(self.state['plans'])[-1]); fresh=next(iter(self.api.tables['projects'].values()))['fields']
        self.assertEqual({k:fresh[k] for k in ('Owner','Priority','Deadline')}, {'Owner':'Alice','Priority':'High','Deadline':'2026-12-01'})
    def test_ambiguous_update_write_is_reconciled(self):
        pid = self.preview()
        original = self.api.upsert
        def write_then_disconnect(table, key, fields):
            record = original(table, key, fields)
            if table == 'updates':
                record['fields']['Recorded At'] = record['fields']['Recorded At'].replace('+00:00', 'Z')
                raise sync.SyncError('connection lost after write')
            return record
        self.api.upsert = write_then_disconnect
        with self.assertRaises(sync.SyncError): self.apply(pid)
        self.api.upsert = original
        self.apply(pid)
        self.assertEqual(len(self.api.tables['updates']), 1)
        self.assertEqual(self.api.writes, ['projects','updates'])
    def test_destination_change_refused(self):
        pid = self.preview(); self.config['base_id'] = 'appOther'
        with self.assertRaisesRegex(sync.SyncError, 'destination changed'): self.apply(pid)
    def test_refresh_after_conflict(self):
        pid = self.preview(); self.apply(pid)
        self.payload['completed'] = 'New progress'; self.infile.write_text(json.dumps(self.payload))
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args, self.config, self.state, self.api)
        new_id = list(self.state['plans'])[-1]
        next(iter(self.api.tables['projects'].values()))['fields']['Latest Progress'] = 'Human edit'
        with self.assertRaises(sync.SyncError): self.apply(new_id)
        self.args.refresh = True
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args, self.config, self.state, self.api)
        self.apply(list(self.state['plans'])[-1])
    def test_partial_failure_cli_reports_persisted_steps(self):
        pid=self.preview(); self.api.fail_update=True
        stderr=io.StringIO()
        with mock.patch.object(sync, 'locked', contextlib.nullcontext), mock.patch.object(sync, 'load_config', return_value=self.config), mock.patch.object(sync, 'Airtable', return_value=self.api), mock.patch('sys.argv',['sync.py','apply',pid]), contextlib.redirect_stderr(stderr):
            self.assertEqual(sync.main(),1)
        report=json.loads(stderr.getvalue())
        self.assertEqual(report['status'],'partial_failure')
        self.assertTrue(report['project_confirmed']); self.assertFalse(report['update_confirmed'])
        self.assertEqual(report['plan_id'],pid)
    def test_blank_progress_preview_makes_no_remote_writes(self):
        self.payload['completed']='  '
        self.infile.write_text(json.dumps(self.payload))
        with self.assertRaises(sync.SyncError): self.preview()
        self.assertEqual(self.api.writes,[])
        self.assertEqual(self.state['plans'],{})
    def test_same_payload_after_restart_no_extra_record(self):
        pid=self.preview();self.apply(pid)
        self.state=sync.read_json(sync.STATE)
        self.preview();self.apply(pid)
        self.assertEqual(len(self.api.tables['projects']),1)
        self.assertEqual(len(self.api.tables['updates']),1)
        self.assertEqual(self.api.writes,['projects','updates'])
    def test_idea_does_not_claim_completed_progress(self):
        self.payload={'project_name':'Generic Project','title':'Initial thought','record_type':'idea','record_status':'Needs clarification','content':'User supplied thought; audience unknown'}
        self.infile.write_text(json.dumps(self.payload))
        pid=self.preview(); self.apply(pid)
        project=next(iter(self.api.tables['projects'].values()))['fields']
        update=next(iter(self.api.tables['updates'].values()))['fields']
        self.assertNotIn('Latest Progress',project)
        self.assertNotIn('Completed',update)
        self.assertEqual(update['In Progress'],self.payload['content'])
        self.assertIn('idea / Needs clarification',update['Name'])
    def test_non_progress_requires_status_and_rejects_completion_claims(self):
        p={'project_name':'Generic','title':'Thought','record_type':'idea','content':'Thought'}
        with self.assertRaises(sync.SyncError):sync.validate_payload(p)
        with self.assertRaises(sync.SyncError):sync.validate_payload({**p,'record_status':'Tentative','completed':'Done'})
    def test_preview_keeps_destination_snapshot(self):
        pid=self.preview()
        saved=sync.read_json(sync.STATE)['plans'][pid]
        self.assertEqual(saved['config_snapshot'],self.config)
    def test_empty_or_unknown_input_rejected(self):
        with self.assertRaises(sync.SyncError): sync.validate_payload({'project_name':'x','title':'t','completed':''})
        with self.assertRaises(sync.SyncError): sync.validate_payload({**self.payload,'token':'secret'})

if __name__ == '__main__': unittest.main()
