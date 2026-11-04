import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nexen,isolated
class RemoveTests(unittest.TestCase):
 def test_anylist_after_connected_session_removes_only_local_data(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d);(s/'config.json').write_text(json.dumps({'mode':'connected'}));(s/'files').mkdir();(s/'files'/'abc').write_text('local')
   isolated.create_owner(s,'owner','password123')
   with isolated.dbopen(s) as c:
    c.execute("INSERT INTO messages(user_id,username,text,created) VALUES (1,'owner','hello',1)")
    c.execute("INSERT INTO files VALUES ('abc',1,'x.png','photos',1)")
    c.execute("INSERT INTO policy VALUES ('x','y')")
   with patch.object(nexen,'STATE',s),patch.object(sys,'argv',['nexen','remove','anylist','--yes']),patch('nexen.record',return_value=None),patch('socket.create_connection',side_effect=ConnectionRefusedError()),contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(nexen.main(),0)
   self.assertFalse(isolated.owner_exists(s));self.assertFalse((s/'files'/'abc').exists())
   with isolated.dbopen(s) as c:
    for t in ('users','sessions','messages','files','policy'):self.assertEqual(c.execute('SELECT count(*) FROM '+t).fetchone()[0],0,t)
 def test_cancel_does_not_delete(self):
  with tempfile.TemporaryDirectory() as d:
   s=Path(d);isolated.create_owner(s,'owner','password123')
   with patch.object(nexen,'STATE',s),patch.object(sys,'argv',['nexen','remove','anylist']),patch('nexen.record',return_value=None),patch('socket.create_connection',side_effect=ConnectionRefusedError()),patch('builtins.input',return_value='NO'),contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(nexen.main(),1)
   self.assertTrue(isolated.owner_exists(s))
