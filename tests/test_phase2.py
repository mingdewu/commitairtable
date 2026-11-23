import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).parents[1]/'engineering-airtable-sync/scripts'))
import sync
import project
from test_sync import FakeAPI

class PhaseTwoTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        self.git('init','-b','main');self.git('config','user.email','test@example.invalid');self.git('config','user.name','Tester')
        (self.root/'file.txt').write_text('one');self.git('add','.');self.git('commit','-m','first')
    def git(self,*args):
        return subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True,text=True).stdout.strip()
    def test_worktree_identity_and_branch_baselines(self):
        head=self.git('rev-parse','HEAD')
        worktree=Path(self.temp.name)/'worktree';self.git('worktree','add','-b','feature',str(worktree))
        self.assertEqual(sync.repo_identity(self.root)[0],sync.repo_identity(worktree)[0])
        self.assertEqual(sync.git_snapshot(self.root,head)['baseline_status'],'ancestor')
        self.assertEqual(sync.git_snapshot(worktree,head)['baseline_status'],'ancestor')
        (worktree/'file.txt').write_text('two')
        subprocess.run(['git','-C',str(worktree),'commit','-am','second'],check=True,capture_output=True)
        ev=sync.git_snapshot(worktree,head)
        self.assertEqual(ev['baseline_status'],'ancestor');self.assertEqual(len(ev['commits_since_baseline']),1)
        self.assertEqual(sync.git_snapshot(self.root,ev['head'])['baseline_status'],'diverged_or_missing')
    def test_non_git_and_history_rewrite(self):
        no_git=Path(self.temp.name)/'notes';no_git.mkdir()
        self.assertEqual(sync.git_snapshot(no_git)['kind'],'directory')
        old=self.git('rev-parse','HEAD')
        self.git('commit','--amend','-m','rewritten')
        self.assertEqual(sync.git_snapshot(self.root,old)['baseline_status'],'diverged_or_missing')
    def test_link_second_path_and_rename_without_merging_by_name(self):
        routes=Path(self.temp.name)/'routes.json';state=Path(self.temp.name)/'state.json'
        with mock.patch.object(project,'ROUTES',routes), mock.patch.object(project,'STATE',state):
            key=project.project_key(self.root)
            project.write_json(state,{'projects':{key:{'project_id':'proj1'}},'plans':{}})
            second=Path(self.temp.name)/'second';subprocess.run(['git','clone',str(self.root),str(second)],check=True,capture_output=True)
            self.assertNotEqual(project.project_key(second),key)
            project.link_path(key,second)
            self.assertEqual(project.project_key(second),key)
            moved=Path(self.temp.name)/'moved';self.root.rename(moved)
            project.link_path(key,moved)
            self.assertEqual(project.project_key(moved),key)
    def test_successful_apply_advances_branch_baseline(self):
        state=Path(self.temp.name)/'state.json'; payload=Path(self.temp.name)/'input.json'
        payload.write_text(json.dumps({'project_name':'Actual','title':'First','completed':'Confirmed work'}))
        oldstate=sync.STATE; oldroutes=project.ROUTES
        sync.STATE=state;project.ROUTES=Path(self.temp.name)/'routes.json'
        self.addCleanup(setattr,sync,'STATE',oldstate);self.addCleanup(setattr,project,'ROUTES',oldroutes)
        c={'base_id':'app1','projects_table':'projects','updates_table':'updates'};saved={'projects':{},'plans':{}};api=FakeAPI()
        args=types.SimpleNamespace(project=str(self.root),input=str(payload),refresh=False)
        with contextlib.redirect_stdout(io.StringIO()):sync.preview(args,c,saved,api)
        pid=next(iter(saved['plans']))
        with contextlib.redirect_stdout(io.StringIO()):sync.apply(types.SimpleNamespace(plan_id=pid),c,saved,api)
        project_id=saved['plans'][pid]['project_id']
        self.assertEqual(saved['baselines'][project_id]['main'],self.git('rev-parse','HEAD'))
        self.git('checkout','-b','feature')
        self.assertIsNone(saved['baselines'][project_id].get('feature'))

if __name__=='__main__':unittest.main()
