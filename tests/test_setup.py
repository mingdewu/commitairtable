import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

scripts = Path(__file__).parents[1] / 'engineering-airtable-sync/scripts'
sys.path.insert(0, str(scripts))
spec = importlib.util.spec_from_file_location('onboarding', scripts / 'setup.py')
setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)

class FakeMeta:
    def __init__(self): self.tables=[]; self.base_creates=0; self.writes=0
    def call(self,path,data=None):
        if path == 'meta/bases':
            self.base_creates+=1; self.call('meta/bases/appTest/tables', data['tables'][0]); return {'id':'appTest'}
        if data is None: return {'tables':copy.deepcopy(self.tables)}
        self.writes+=1
        if path.endswith('/fields'):
            table=next(t for t in self.tables if '/' + t['id'] + '/' in path)
            field={**copy.deepcopy(data),'id':'fld'+str(len(table['fields']))}
            table['fields'].append(field); return field
        table={'id':'tbl'+str(len(self.tables)), 'name':data['name'], 'fields':[]}
        for i,f in enumerate(data['fields']): table['fields'].append({**copy.deepcopy(f),'id':'fld'+str(i)})
        table['primaryFieldId']='fld0'; self.tables.append(table); return copy.deepcopy(table)

class SetupTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        for k in ['CONFIG','CHECKPOINT']:
            old=getattr(setup,k);setattr(setup,k,Path(self.temp.name)/k);self.addCleanup(setattr,setup,k,old)
    def test_new_base_tables_link_and_recovery_without_duplicate(self):
        api=FakeMeta();c=setup.bootstrap(api,'new','https://airtable.com/wspTest','Engineering')
        self.assertEqual(c['base_id'],'appTest');self.assertEqual(api.base_creates,1)
        link=next(f for f in api.tables[1]['fields'] if f['name']=='Project')
        self.assertEqual(link['options']['linkedTableId'],api.tables[0]['id'])
        n=api.writes;self.assertEqual(setup.bootstrap(api,'new','wspTest','Engineering'),c)
        self.assertEqual(api.writes,n);self.assertEqual(api.base_creates,1)
    def test_existing_base_no_base_create(self):
        api=FakeMeta();setup.bootstrap(api,'existing','https://airtable.com/appTest/tblAnything','')
        self.assertEqual(api.base_creates,0);self.assertEqual(len(api.tables),2)
    def test_wrong_field_type_is_not_modified(self):
        api=FakeMeta();setup.bootstrap(api,'existing','appTest','')
        api.tables[0]['fields'][1]['type']='number';n=api.writes
        with self.assertRaisesRegex(setup.SyncError,'类型不兼容'):setup.bootstrap(api,'existing','appTest','')
        self.assertEqual(api.writes,n)
    def test_unknown_creation_does_not_repeat(self):
        setup.write_json(setup.CHECKPOINT,{'key':['new','wspTest','Engineering'],'creation_pending':True})
        api=FakeMeta()
        with self.assertRaisesRegex(setup.SyncError,'结果未知'):setup.bootstrap(api,'new','wspTest','Engineering')
        self.assertEqual(api.base_creates,0)
    def test_existing_config_is_preserved(self):
        setup.write_json(setup.CONFIG,{'base_id':'appKeep'})
        api=FakeMeta()
        with self.assertRaisesRegex(setup.SyncError,'已有配置'):setup.bootstrap(api,'existing','appTest','')
        self.assertEqual(api.writes,0)

if __name__ == '__main__':unittest.main()
