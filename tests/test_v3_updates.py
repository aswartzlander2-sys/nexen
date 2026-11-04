import io,json,unittest,sys,urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import updater

class Resp(io.BytesIO):
 def __enter__(self): return self
 def __exit__(self,*a): self.close()

def network(releases, version, branch_missing=False):
 def fetch(req,timeout):
  url=req.full_url
  if '/releases?' in url: return Resp(json.dumps(releases).encode())
  if '/git/ref/heads/' in url:
   if branch_missing: raise urllib.error.HTTPError(url,404,'missing',{},None)
   return Resp(json.dumps({'object':{'sha':'a'*40}}).encode())
  if url.endswith('/identity.py'): return Resp(("VERSION="+repr(version)).encode())
  raise AssertionError(url)
 return fetch

class V3UpdateTests(unittest.TestCase):
 def test_numeric_main_is_detected_and_pinned(self):
  with patch('urllib.request.urlopen',side_effect=network([], '3.2.0')):
   c=updater.find_best_update('3.0.0');self.assertEqual(c['version'],'v3.2.0');self.assertEqual(c['sha'],'a'*40)
 def test_stable_never_selects_experimental_main(self):
  with patch('urllib.request.urlopen',side_effect=network([], '3.2.0E')): self.assertIsNone(updater.find_best_update('3.0.0'))
 def test_opt_in_experimental_branch(self):
  with patch('urllib.request.urlopen',side_effect=network([], '3.2.0E')): self.assertEqual(updater.find_best_update('3.0.0',True)['version'],'v3.2.0E')
 def test_missing_preview_branch_is_not_update(self):
  with patch('urllib.request.urlopen',side_effect=network([], '3.2.0E',True)): self.assertIsNone(updater.find_best_update('3.0.0',True))
 def test_newer_release_beats_branch(self):
  with patch('urllib.request.urlopen',side_effect=network([{'tag_name':'v4.0.0','prerelease':False}], '3.2.0')): self.assertEqual(updater.find_best_update('3.0.0')['version'],'v4.0.0')
 def test_errors_are_not_no_updates(self):
  with patch('urllib.request.urlopen',side_effect=OSError('offline')):
   with self.assertRaises(OSError): updater.find_best_update('3.0.0')
