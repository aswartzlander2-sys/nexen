import io, json, os, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import install

@unittest.skipIf(os.name=='nt','Linux/macOS installer test')
class InstallerTests(unittest.TestCase):
    def test_only_stable_installs_and_keeps_identity(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); (home/'.nexen-identity').write_text('001234')
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,'w') as z:
                for name in ['nexen.py','updater.py','isolated.py','identity.py','index.html','assets/js/config.js','README.md']:
                    z.writestr('nexen-2.1.1/'+name, "VERSION='2.1.1'" if name=='identity.py' else 'pass')
            releases=[{'tag_name':'v2.1.1','prerelease':False}, {'tag_name':'v9.0.0B','prerelease':True}, {'tag_name':'v9.0.0E','prerelease':True}]
            def fake(url,limit): return json.dumps(releases).encode() if 'api.github.com' in url else archive.getvalue()
            with patch.dict(os.environ,{'HOME':d}), patch('install.request',side_effect=fake), patch('socket.create_connection',side_effect=ConnectionRefusedError()): install.main()
            self.assertTrue((home/'.local/share/nexen/nexen.py').exists())
            self.assertEqual((home/'.nexen-identity').read_text(),'001234')
if __name__=='__main__': unittest.main()
