import contextlib,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nexen
class RepairTests(unittest.TestCase):
 def test_repair_runs_installer_and_propagates_result(self):
  class Result: returncode=7
  with patch.object(sys,'argv',['nexen','repair']), patch('nexen.subprocess.run',return_value=Result()) as run, contextlib.redirect_stdout(io.StringIO()) as out:
   self.assertEqual(nexen.main(),7)
   run.assert_called_once_with([sys.executable,str(nexen.ROOT/'install.py')])
   self.assertIn('local data and ID will be kept',out.getvalue())
