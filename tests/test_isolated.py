import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import isolated
class LocalBackendTests(unittest.TestCase):
    def test_owner_and_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)
            isolated.create_owner(state,'owner_1','a-long-password')
            self.assertTrue(isolated.owner_exists(state))
            with isolated.dbopen(state) as db:
                db.execute("INSERT INTO messages(user_id,username,text,created) VALUES(1,'owner_1','hi',1)")
            isolated.remove(state,'chats')
            with isolated.dbopen(state) as db: self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0],0)
            isolated.remove(state,'usr-list')
            self.assertFalse(isolated.owner_exists(state))
    def test_owner_credentials_persist_until_user_list_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)
            isolated.create_owner(state,'owner_1','a-long-password')
            with isolated.dbopen(state) as db:
                user=db.execute('SELECT * FROM users WHERE owner=1').fetchone()
                self.assertEqual(user['username'],'owner_1')
                self.assertNotEqual(user['hash'],'a-long-password')
                self.assertEqual(user['hash'],isolated.pw_hash('a-long-password',user['salt']))
            self.assertTrue(isolated.owner_exists(state))
            isolated.remove(state,'usr-list')
            self.assertFalse(isolated.owner_exists(state))
            isolated.create_owner(state,'owner_2','another-password')
            self.assertTrue(isolated.owner_exists(state))

    def test_password_hash(self):
        self.assertNotEqual(isolated.pw_hash('password','00'*16), isolated.pw_hash('password','01'*16))

class BrowserScriptTests(unittest.TestCase):
    def test_embedded_javascript_syntax(self):
        import shutil, subprocess
        node = shutil.which('node')
        if not node: self.skipTest('Node.js is needed for this optional syntax check')
        script = isolated.PAGE.split('<script>', 1)[1].split('</script>', 1)[0]
        result = subprocess.run([node, '--check'], input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__': unittest.main()
