import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nexen
class OSInstallerTests(unittest.TestCase):
 def test_linux_runs_curl_and_sh(self):
  with patch.object(nexen.sys,'platform','linux'),patch('nexen.subprocess.run') as run:
   nexen.reinstall_stable();a,b=run.call_args_list
   self.assertEqual(a.args[0][:2],['curl','-fsSL']);self.assertTrue(a.args[0][2].endswith('/main/install.sh'));self.assertEqual(b.args[0][0],'sh');self.assertTrue(b.args[0][1].endswith('/install.sh'))
 def test_windows_runs_curl_and_powershell(self):
  with patch.object(nexen.sys,'platform','win32'),patch('nexen.subprocess.run') as run:
   nexen.reinstall_stable();a,b=run.call_args_list
   self.assertEqual(a.args[0][:2],['curl.exe','-fsSL']);self.assertTrue(a.args[0][2].endswith('/main/install.ps1'));self.assertEqual(b.args[0][:4],['powershell','-ExecutionPolicy','Bypass','-File']);self.assertTrue(b.args[0][4].endswith('install.ps1'))
