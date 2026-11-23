import contextlib
import io
import json
import types
import unittest
import test_sync
sync = test_sync.sync


class PlanningTest(unittest.TestCase):
    setUp = test_sync.TestSync.setUp
    preview = test_sync.TestSync.preview
    apply = test_sync.TestSync.apply

    def prepare(self):
        self.config.update(schema_version=2, tasks_table='tasks')
        self.api.tables['tasks'] = {}
        self.payload = {'project_name': 'Actual project', 'title': 'Plan draft', 'record_type': 'plan', 'record_status': 'Proposed', 'content': 'Suggested approach; not implemented', 'overview': 'Solve the agreed problem', 'plan': 'Alternative A and B', 'current_stage': 'Discovery', 'tasks': [{'task_id': 'first', 'name': 'Validate need', 'status': 'Proposed', 'description': 'Interview intended users', 'acceptance': 'Summarise evidence and open questions'}]}
        self.infile.write_text(json.dumps(self.payload))

    def test_plan_has_readable_content_and_linked_task(self):
        self.prepare(); pid = self.preview(); self.apply(pid); self.apply(pid)
        project = next(iter(self.api.tables['projects'].values()))
        update = next(iter(self.api.tables['updates'].values()))['fields']
        task = next(iter(self.api.tables['tasks'].values()))['fields']
        self.assertEqual(project['fields']['Overview'], self.payload['overview'])
        self.assertNotIn('Latest Progress', project['fields'])
        self.assertEqual(update['Content'], self.payload['content'])
        self.assertNotIn('In Progress', update)
        self.assertEqual(task['Project'], [project['id']])
        self.assertEqual(self.api.writes, ['projects', 'tasks', 'updates'])

    def test_task_retry_after_uncertain_write_does_not_duplicate(self):
        self.prepare(); pid = self.preview(); original = self.api.upsert
        def fail(table, key, fields):
            result = original(table, key, fields)
            if table == 'tasks': raise sync.SyncError('lost response')
            return result
        self.api.upsert = fail
        with self.assertRaises(sync.SyncError): self.apply(pid)
        self.api.upsert = original; self.apply(pid)
        self.assertEqual(len(self.api.tables['tasks']), 1)
        self.assertEqual(self.api.writes, ['projects', 'tasks', 'updates'])

    def test_task_human_edit_blocks_plan(self):
        self.prepare(); pid = self.preview(); self.apply(pid)
        self.payload['tasks'][0]['status'] = 'Planned'
        self.infile.write_text(json.dumps(self.payload))
        with contextlib.redirect_stdout(io.StringIO()): sync.preview(self.args, self.config, self.state, self.api)
        task = next(iter(self.api.tables['tasks'].values()))['fields']
        task['Status'] = 'Human change'
        with self.assertRaisesRegex(sync.SyncError, 'Task changed'): self.apply(list(self.state['plans'])[-1])
        self.assertEqual(task['Status'], 'Human change')

    def test_planning_requires_upgrade(self):
        self.prepare(); self.config.pop('schema_version')
        with self.assertRaisesRegex(sync.SyncError, 'schema v2'): self.preview()

    def test_duplicate_task_ids_rejected(self):
        self.prepare(); self.payload['tasks'] *= 2
        with self.assertRaisesRegex(sync.SyncError, 'Duplicate task_id'): sync.validate_payload(self.payload)
