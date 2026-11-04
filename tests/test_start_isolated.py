import contextlib,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nexen

class Starts(unittest.TestCase):
 def start(self,args,old_login_only=True):
  with tempfile.TemporaryDirectory() as d:
   state=Path(d);(state/'config.json').write_text(json.dumps({'mode':'isolated','login_only':old_login_only}))
   with patch.object(nexen,'STATE',state),patch.object(sys,'argv',['nexen',*args]),patch('nexen.record',return_value=None),patch('nexen.request',return_value=True),patch('nexen.subprocess.Popen'),patch('isolated.owner_exists',return_value=True),patch('identity.get_id',return_value='012345'),contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(nexen.main(),0)
    return json.loads((state/'config.json').read_text())
 def test_new_command_enables_signup_despite_old_saved_lock(self):
  c=self.start(['start-isolated']);self.assertEqual(c['mode'],'isolated');self.assertFalse(c['login_only'])
 def test_explicit_lock(self):
  c=self.start(['start-isolated','-L'],False);self.assertTrue(c['login_only'])
 def test_legacy_alias_also_defaults_to_signup(self):
  c=self.start(['start','--no-contact']);self.assertEqual(c['mode'],'isolated');self.assertFalse(c['login_only'])
 def test_plain_start_is_connected(self):
  c=self.start(['start']);self.assertEqual(c['mode'],'connected')
