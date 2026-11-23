import contextlib
import copy
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1] / 'engineering-airtable-sync/scripts'))
import migrate


class MigrationTest(unittest.TestCase):
    def test_preview_apply_preserve_source_and_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            class API:
                rows = [{'id': 'rec1', 'fields': {'Name': '[idea / draft] A need', 'In Progress': 'Original idea'}}, {'id': 'rec2', 'fields': {'Name': 'ordinary progress', 'In Progress': 'Do not reinterpret'}}]
                writes = 0
                def request(self, table, method='GET', data=None, params=None):
                    if method == 'PATCH':
                        self.writes += 1
                        item = data['records'][0]
                        next(r for r in self.rows if r['id'] == item['id'])['fields'].update(item['fields'])
                    return {'records': copy.deepcopy(self.rows)}
            api = API()
            with patch.object(migrate, 'HOME', Path(folder)), patch.object(migrate, 'locked', contextlib.nullcontext), patch.object(migrate, 'load_config', return_value={'schema_version': 2, 'base_id': 'app1', 'updates_table': 'updates'}), patch.object(migrate, 'Airtable', return_value=api), contextlib.redirect_stdout(io.StringIO()):
                with patch.object(sys, 'argv', ['migrate.py', '--project', folder]): migrate.main()
                self.assertEqual(api.writes, 0)
                api.rows[0]['fields']['In Progress'] = 'Human revision'
                with patch.object(sys, 'argv', ['migrate.py', '--project', folder, '--apply']), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit): migrate.main()
                self.assertEqual(api.writes, 0)
                api.rows[0]['fields']['In Progress'] = 'Original idea'
                with patch.object(sys, 'argv', ['migrate.py', '--project', folder, '--apply']):
                    migrate.main(); migrate.main()
                self.assertEqual(api.writes, 1)
                self.assertEqual(api.rows[0]['fields']['Content'], 'Original idea')
                self.assertEqual(api.rows[0]['fields']['In Progress'], 'Original idea')
                self.assertNotIn('Content', api.rows[1]['fields'])
