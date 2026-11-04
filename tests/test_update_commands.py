import contextlib,io,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nexen

class CommandTests(unittest.TestCase):
 def run_command(self, args, candidate, failure=None):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'app';root.mkdir();state=Path(tmp)/'state';out=io.StringIO();err=io.StringIO()
   with patch.object(nexen,'ROOT',root),patch.object(nexen,'STATE',state),patch('updater.install_root',return_value=root),patch('updater.find_best_update',side_effect=failure if failure else None,return_value=candidate),patch('updater.download_candidate',return_value=b'archive') as download,patch('updater.apply_archive') as apply,patch('nexen.record',return_value=None),patch('socket.create_connection',side_effect=ConnectionRefusedError()),patch('identity.identity_path',return_value=Path(tmp)/'id'),patch.object(sys,'argv',['nexen','update']+args),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
    result=nexen.main()
    return result,out.getvalue(),err.getvalue(),download.call_count,apply.call_count
 def test_stable_none(self):
  rc,out,err,d,a=self.run_command([],None);self.assertEqual(out.strip(),'There are no updates available at this time.');self.assertEqual(d,0)
 def test_preview_none(self):
  rc,out,err,d,a=self.run_command(['-B'],None);self.assertEqual(out.strip(),'There are no updates or feature previews available at this time.');self.assertEqual(d,0)
 def test_available_installs_in_both_modes(self):
  for args in ([],['-B']):
   rc,out,err,d,a=self.run_command(args,{'version':'v4.0.0','sha':None});self.assertEqual((rc,d,a),(0,1,1));self.assertNotIn('There are no updates',out)
 def test_error_is_not_no_update(self):
  rc,out,err,d,a=self.run_command([],None,OSError('offline'));self.assertEqual(rc,1);self.assertIn('offline',err);self.assertNotIn('There are no updates',out+err)
