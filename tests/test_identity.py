import os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import identity
class IdentityTests(unittest.TestCase):
    def test_persistence_and_leading_zero(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NEXEN_IDENTITY_FILE':str(Path(tmp)/'id')}), patch('identity.secrets.randbelow',return_value=11323):
            self.assertEqual(identity.get_id(),'011323')
            self.assertEqual(identity.get_id(),'011323')
            self.assertEqual(Path(tmp,'id').read_text().strip(),'011323')
    def test_invalid_not_silently_regenerated(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'NEXEN_IDENTITY_FILE':str(Path(tmp)/'id')}):
            Path(tmp,'id').write_text('broken')
            with self.assertRaises(ValueError): identity.get_id()
            self.assertEqual(Path(tmp,'id').read_text(),'broken')
if __name__=='__main__': unittest.main()
