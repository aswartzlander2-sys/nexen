import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class OriginUITests(unittest.TestCase):
 def test_all_top_level_pages_are_the_origin_spa(self):
  app=(ROOT/'index.html').read_text()
  for marker in ('assets/app/nx-app.js','assets/app/nx-settings.js','assets/app/nx-server.js','assets/app/nx-home.js'):
   self.assertIn(marker,app)
  for name in ('profile.html','portal.html','server.html','dms.html','server-settings.html','admin.html'):
   self.assertEqual((ROOT/name).read_text(),app,name)
 def test_origin_settings_features(self):
  settings=(ROOT/'assets/app/nx-settings.js').read_text()
  for marker in ("id: 'account'", "id: 'profile'", "id: 'drive'", "id: 'appearance'", "id: 'notifications'", "id: 'voice'", "id: 'advanced'", 'Liquid glass'):
   self.assertIn(marker,settings)
 def test_browser_assets_exist(self):
  import re
  html=(ROOT/'index.html').read_text()
  for name in re.findall(r'(?:src|href)="(assets/[^"?]+)',html): self.assertTrue((ROOT/name).is_file(),name)
