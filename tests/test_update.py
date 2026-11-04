import io, tempfile, unittest, zipfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import updater

def archive(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        for name,data in files.items(): z.writestr(name,data)
    return output.getvalue()

def sample():
    return {'nexen-main/'+p: ('print("ok")' if p.endswith('.py') else 'ok') for p in updater.REQUIRED}

class UpdateTests(unittest.TestCase):
    def test_update_preserves_state_and_replaces_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); target=root/'app';target.mkdir();(target/'old').write_text('old'); state=root/'state';state.mkdir();(state/'data').write_text('keep')
            updater.apply_archive(archive(sample()),target,state)
            self.assertFalse((target/'old').exists()); self.assertTrue((target/'nexen.py').is_file());self.assertEqual((state/'data').read_text(),'keep')
    def test_bad_download_keeps_install(self):
        for bad in (archive({'nexen-main/../../escape':'bad'}),archive({'nexen-main/nexen.py':'invalid'}),b'not a zip'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);target=root/'app';target.mkdir();(target/'keep').write_text('original')
                with self.assertRaises(Exception): updater.apply_archive(bad,target,root/'state')
                self.assertEqual((target/'keep').read_text(),'original')
    def test_refuses_state_inside_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'app';target.mkdir()
            with self.assertRaises(ValueError): updater.apply_archive(archive(sample()),target,target/'state')

if __name__=='__main__': unittest.main()
