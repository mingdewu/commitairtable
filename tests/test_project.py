import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).parents[1]/'engineering-airtable-sync/scripts'))
import project

class ProjectTest(unittest.TestCase):
    def test_independent_project_routes(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(project,'ROUTES',Path(d)/'routes.json'):
                a=Path(d)/'a';b=Path(d)/'b';a.mkdir();b.mkdir()
                project.register(a,Path(d)/'a.json');project.register(b,Path(d)/'b.json')
                self.assertEqual(project.destination(a),Path(d)/'a.json')
                self.assertEqual(project.destination(b),Path(d)/'b.json')
    def test_reminders_preserve_existing_instructions_without_duplication(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(project,'ROUTES',Path(d)/'routes.json'):
                root=Path(d);file=root/'AGENTS.md';file.write_text('Existing project rules\n')
                project.enable_reminders(root);first=file.read_text();project.enable_reminders(root)
                self.assertEqual(file.read_text(),first)
                self.assertTrue(first.startswith('Existing project rules'))
                self.assertEqual(first.count('<!-- engineering-airtable-sync:start -->'),1)
    def test_discover_paginates(self):
        api=mock.Mock();api.call.side_effect=[{'bases':[{'id':'appA'}],'offset':'next token'},{'bases':[{'id':'appB'}]}]
        self.assertEqual(project.list_bases(api),[{'id':'appA'},{'id':'appB'}])
        self.assertIn('next%20token',api.call.call_args.args[0])

if __name__=='__main__':unittest.main()
