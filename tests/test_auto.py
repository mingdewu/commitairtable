import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).parents[1]/'engineering-airtable-sync/scripts'))
import auto

class AutoTest(unittest.TestCase):
    def test_candidates_include_all_bases_without_provisioning(self):
        api=mock.Mock()
        with mock.patch.object(auto,'list_bases',return_value=[{'id':'appA','name':'A'},{'id':'appB','name':'B'}]):
            api.call.side_effect=[{'tables':[]},{'tables':[]}]
            result=auto.candidates(api,'Actual project')
        self.assertEqual([x['base_name'] for x in result['accessible_bases']],['A','B'])
        self.assertEqual(api.call.call_count,2)
    def test_provision_requires_confirmed_target(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(auto.SyncError,'confirmed workspace'):
                auto.provision(mock.Mock(),d,'new-base','','Name')

if __name__=='__main__':unittest.main()
