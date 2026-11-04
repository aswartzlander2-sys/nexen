import io, json, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import updater

class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*a): self.close()

def releases(items):
    def get(request,timeout):
        assert 'api.github.com/repos/aswartzlander2-sys/nexen/releases' in request.full_url
        return FakeResponse(json.dumps(items).encode())
    return get

class ReleaseChannelTests(unittest.TestCase):
    def test_stable_never_selects_previews_or_drafts(self):
        data=[{'tag_name':'v2.3.0E'}, {'tag_name':'v2.2.0B','prerelease':True}, {'tag_name':'v2.9.0','draft':True}, {'tag_name':'v2.1.2','prerelease':False}]
        with patch('urllib.request.urlopen',side_effect=releases(data)):
            self.assertEqual(updater.find_update('2.1.1'), 'v2.1.2')
            self.assertEqual(updater.find_update('2.1.1',beta=True), 'v2.3.0E')
    def test_no_updates_and_invalid_or_older_tags(self):
        data=[{'tag_name':'v9.0.0E'},{'tag_name':'v2.1.0B'},{'tag_name':'nonsense'}, {'tag_name':'v2.1.1'}]
        with patch('urllib.request.urlopen',side_effect=releases(data)):
            self.assertIsNone(updater.find_update('2.1.1'))
            self.assertEqual(updater.find_update('2.1.1',beta=True), 'v9.0.0E')
    def test_bugfix_stable_available_to_beta_install(self):
        data=[{'tag_name':'v2.1.2','prerelease':False}]
        with patch('urllib.request.urlopen',side_effect=releases(data)):
            self.assertEqual(updater.find_update('2.1.2B'), 'v2.1.2')
    def test_network_errors_are_not_misreported_as_no_updates(self):
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            with self.assertRaises(OSError): updater.find_update('2.1.1')

class ReleaseArchiveTests(unittest.TestCase):
    def test_tag_mismatch_leaves_previous_install(self):
        import tempfile, zipfile
        from pathlib import Path
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            for name in updater.REQUIRED:
                content = "VERSION='2.2.0B'" if name=='identity.py' else ('pass' if name.endswith('.py') else 'ok')
                z.writestr('nexen-2.2.0B/'+name,content)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'app';target.mkdir();(target/'old').write_text('keep')
            with self.assertRaises(ValueError): updater.apply_archive(out.getvalue(),target,Path(d)/'state',expected_version='v2.3.0B')
            self.assertEqual((target/'old').read_text(),'keep')

if __name__=='__main__': unittest.main()
