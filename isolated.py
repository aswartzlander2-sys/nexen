"""Small standalone Nexen backend. No external services or dependencies."""
import base64, hashlib, hmac, json, mimetypes, os, secrets, sqlite3, time
from pathlib import Path
from urllib.parse import urlsplit

MAX_FILE=8*1024*1024
OWNER_PERMISSIONS=frozenset(('ban_users','manage_roles','view_all_servers','post_anywhere','delete_messages','reset_passwords','delete_users','post_announcements','manage_storage','manage_storage_endpoints','review_appeals','view_audit'))

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try: return super().__exit__(exc_type, exc, tb)
        finally: self.close()

def dbopen(state):
    state.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(state/'isolated.sqlite3', timeout=10, factory=ClosingConnection)
    c.row_factory=sqlite3.Row
    c.executescript('''PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE NOT NULL, salt TEXT NOT NULL, hash TEXT NOT NULL, owner INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, username TEXT NOT NULL, text TEXT NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS policy(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS user_metadata(user_id INTEGER PRIMARY KEY,created_at TEXT,last_sign_in_at TEXT);
    CREATE TABLE IF NOT EXISTS nx_servers(id TEXT PRIMARY KEY,name TEXT NOT NULL,owner_id INTEGER NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS nx_channels(id TEXT PRIMARY KEY,server_id TEXT NOT NULL,name TEXT NOT NULL,type TEXT NOT NULL,position INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS nx_server_messages(id TEXT PRIMARY KEY,channel_id TEXT NOT NULL,author_id INTEGER NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS local_nitro(user_id INTEGER PRIMARY KEY, since TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS nitro_requests(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, message TEXT, status TEXT NOT NULL DEFAULT 'pending', review_note TEXT, created_at TEXT NOT NULL, reviewed_by INTEGER, reviewed_at TEXT);
    CREATE UNIQUE INDEX IF NOT EXISTS one_pending_nitro ON nitro_requests(user_id) WHERE status='pending';
    CREATE TABLE IF NOT EXISTS admin_audit(id INTEGER PRIMARY KEY, actor_id INTEGER NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
    ''')
    return c

def pw_hash(p,salt): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),310000).hex()
def valid_user(u): return 2<=len(u)<=32 and all(c.isascii() and (c.isalnum() or c=='_') for c in u)
def create_owner(state, username, password):
    if not valid_user(username) or len(password)<8: raise ValueError('Username must be 2–32 ASCII letters, digits or underscores; password must be at least 8 characters.')
    with dbopen(state) as c:
        if c.execute('SELECT 1 FROM users WHERE owner=1').fetchone(): raise ValueError('An owner already exists')
        salt=secrets.token_hex(16)
        cur=c.execute('INSERT INTO users(username,salt,hash,owner) VALUES(?,?,?,1)',(username,salt,pw_hash(password,salt)))
        c.execute("INSERT INTO user_metadata(user_id,created_at) VALUES(?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(cur.lastrowid,))

def owner_exists(state):
    with dbopen(state) as c: return bool(c.execute('SELECT 1 FROM users WHERE owner=1').fetchone())

def owner_name(state):
    with dbopen(state) as c:
        row=c.execute('SELECT username FROM users WHERE owner=1 ORDER BY id LIMIT 1').fetchone()
        return row['username'] if row else None

def restore_missing_owner(state):
    """If legacy users exist but no Owner, promote the earliest local account.

    Existing Owners and password hashes are never changed. Return the promoted
    username, or None when no promotion is needed or there are no users.
    """
    with dbopen(state) as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM users WHERE owner=1').fetchone(): return None
        row=c.execute('SELECT id,username FROM users ORDER BY id LIMIT 1').fetchone()
        if not row: return None
        c.execute('UPDATE users SET owner=1 WHERE id=?', (row['id'],))
        return row['username']

def remove(state,category):
    with dbopen(state) as c:
        if category in ('usr-list','anylist'):
            c.execute('DELETE FROM user_metadata'); c.execute('DELETE FROM nx_server_messages'); c.execute('DELETE FROM nx_channels'); c.execute('DELETE FROM nx_servers'); c.execute('DELETE FROM sessions'); c.execute('DELETE FROM users'); c.execute('DELETE FROM local_nitro'); c.execute('DELETE FROM nitro_requests')
        if category in ('chats','anylist'): c.execute('DELETE FROM messages')
        if category in ('admin-policy','anylist'):
            c.execute('DELETE FROM policy'); c.execute('UPDATE users SET banned=0')
        categories = ('photos','drive-assets') if category=='anylist' else (category,)
        for cat in categories:
            if cat not in ('photos','drive-assets'): continue
            files=c.execute('SELECT id FROM files WHERE category=?',(cat,)).fetchall()
            for f in files:
                try: (state/'files'/f['id']).unlink(missing_ok=True)
                except OSError as e: raise RuntimeError('Could not delete file: '+str(e))
            c.execute('DELETE FROM files WHERE category=?',(cat,))

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NexChat · Nexen</title><style>
:root{color-scheme:dark;font:15px system-ui;background:#090b12;color:#e8e9f4}*{box-sizing:border-box}body{margin:0}button,input{font:inherit}button{background:#7464ec;color:white;border:0;border-radius:8px;padding:10px 15px;cursor:pointer}button:hover{background:#8a7cf7}input{background:#171b29;color:white;border:1px solid #363b51;border-radius:8px;padding:10px}header{height:64px;border-bottom:1px solid #292d40;display:flex;align-items:center;justify-content:space-between;padding:0 22px;background:#10131e}header b{font-size:20px}main{max-width:1100px;margin:auto;padding:20px}.box{background:#141824;border:1px solid #292f43;border-radius:14px;padding:20px}.auth{max-width:400px;margin:12vh auto}.auth input,.auth button{width:100%;margin:5px 0}.muted{color:#9a9fb6;font-size:13px}.chat{display:flex;flex-direction:column;height:calc(100vh - 110px)}#messages{overflow:auto;flex:1}.msg{padding:12px;border-bottom:1px solid #24283a;white-space:pre-wrap;overflow-wrap:anywhere}.msg b{color:#bcb2ff}.msg time{font-size:12px;color:#8189a1;margin-left:10px}.composer{display:flex;gap:8px;padding-top:15px}.composer input{flex:1;min-width:0}.hidden{display:none!important}a{color:#a89cff}#error{color:#ff9eab}.tabs{display:flex;gap:8px;margin-bottom:14px}#file{max-width:230px}.toolbar{display:flex;gap:12px;align-items:center}
</style></head><body><header><b>✦ NexChat <span class="muted">Nexen V.<span data-nexen-version>2.1.3</span><span data-nexen-id></span> · Independent</span></b><div class="toolbar"><span id="who"></span><button id="logout" class="hidden">Sign out</button></div></header><main>
<div id="auth" class="box auth"><h1>Welcome to NexChat</h1><p class="muted">Your independent Nexen server</p><div class="tabs"><button id="loginTab">Log in</button><button id="signupTab">Sign up</button></div><form id="loginForm"><input id="username" placeholder="Username" autocomplete="username" required><input id="password" type="password" placeholder="Password" autocomplete="current-password" required><button id="submit">Log in</button></form><p id="error"></p><p class="muted">a hobby project · be nice ✌️ • Nexen V.<span data-nexen-version>2.1.3</span><span data-nexen-id></span></p></div>
<div id="app" class="box chat hidden"><div class="toolbar"><h2>＃ general</h2><span class="muted">NexChat v3 · Esc to close · Nexen V.<span data-nexen-version>2.1.3</span><span data-nexen-id></span></span></div><div id="messages"></div><form id="send" class="composer"><input id="text" placeholder="Message #general" maxlength="4000"><button>Send</button></form><div class="composer"><input type="file" id="file"><button id="upload">Upload file</button></div><p id="chatError"></p></div></main><script>
fetch('/__nexen/meta',{cache:'no-store'}).then(r=>r.json()).then(m=>{if(m.version)document.querySelectorAll('[data-nexen-version]').forEach(e=>e.textContent=m.version);if(/^\d{6}$/.test(m.id))document.querySelectorAll('[data-nexen-id]').forEach(e=>e.textContent=' • '+m.id)}).catch(()=>{});let signingUp=false,last='',current=null;const $=id=>document.getElementById(id);async function api(path,method='GET',body){let r;try{r=await fetch(path,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin'})}catch(e){throw Error('Cannot reach this Nexen server. Check that it is running and your network connection, then try again.')}let x;try{x=await r.json()}catch(e){throw Error('The Nexen server returned an unexpected response. Try again.')};if(!r.ok)throw Error(x.error||'Request failed');return x}function mode(up){signingUp=up;$('submit').textContent=up?'Create account':'Log in';$('error').textContent=''}$('loginTab').onclick=()=>mode(false);$('signupTab').onclick=()=>mode(true);$('loginForm').onsubmit=async e=>{e.preventDefault();try{current=await api('/api/'+(signingUp?'signup':'login'),'POST',{username:$('username').value,password:$('password').value});$('password').value='';show();}catch(err){$('error').textContent=err.message}};$('logout').onclick=async()=>{try{await api('/api/logout','POST',{});current=null;last='';show()}catch(e){$('chatError').textContent=e.message}};function show(){ $('auth').classList.toggle('hidden',!!current);$('app').classList.toggle('hidden',!current);$('logout').classList.toggle('hidden',!current);$('who').textContent=current?current.username+(current.owner?' · Owner':'') : '';if(current)poll() }async function poll(){if(!current)return;try{let data=await api('/api/messages');let s=JSON.stringify(data);$('chatError').textContent='';if(s!==last){let m=$('messages'),near=m.scrollTop+m.clientHeight>=m.scrollHeight-80;m.textContent='';for(let x of data){let row=document.createElement('div');row.className='msg';let b=document.createElement('b');b.textContent=x.username;let t=document.createElement('time');t.textContent=new Date(x.created*1000).toLocaleString();let p=document.createElement('div');p.textContent=x.text;let match=x.text.match(/^File: (.+) — (https?:\/\/[^ ]+\/files\/[a-f0-9]{48})$/);if(match){try{let u=new URL(match[2]);if(u.origin===location.origin){p.textContent='File: ';let link=document.createElement('a');link.href=u.pathname;link.textContent=match[1];p.append(link)}}catch(_){}}row.append(b,t,p);m.append(row)}if(near)m.scrollTop=m.scrollHeight;last=s}}catch(e){$('chatError').textContent=e.message}}$('send').onsubmit=async e=>{e.preventDefault();let text=$('text').value.trim();if(!text)return;try{await api('/api/messages','POST',{text});$('text').value='';await poll();$('messages').scrollTop=$('messages').scrollHeight}catch(e){$('chatError').textContent=e.message}};$('upload').onclick=async()=>{let f=$('file').files[0];if(!f)return;if(f.size>8388608){$('chatError').textContent='Maximum file size is 8 MB';return}let reader=new FileReader;reader.onload=async()=>{try{let r=await api('/api/upload','POST',{name:f.name,data:reader.result.split(',')[1]});await api('/api/messages','POST',{text:'File: '+r.name+' — '+location.origin+r.url});$('file').value='';await poll()}catch(e){$('chatError').textContent=e.message}};reader.readAsDataURL(f)};setInterval(poll,3000);api('/api/config').then(c=>{$('signupTab').classList.toggle('hidden',!c.signup)});api('/api/me').then(u=>{current=u;show()}).catch(()=>{});
</script></body></html>'''

def handle(h,state,login_only):
    path=urlsplit(h.path).path
    c=None
    def respond(code,obj,headers=None):
        if c is not None: c.commit()
        body=json.dumps(obj).encode(); h.send_response(code); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Cache-Control','no-store'); h.send_header('Content-Length',str(len(body)))
        for k,v in (headers or {}).items(): h.send_header(k,v)
        h.end_headers(); h.wfile.write(body)
    def getuser(c):
        cookie=h.headers.get('Cookie',''); token=next((s.strip()[6:] for s in cookie.split(';') if s.strip().startswith('nxses=')),'')
        return c.execute('SELECT users.id,users.username,users.owner FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token=? AND users.banned=0 AND sessions.created>?',(token,int(time.time())-30*86400)).fetchone()
    def body():
        n=int(h.headers.get('Content-Length','0'))
        if n>12*1024*1024: raise ValueError('Request too large')
        return json.loads(h.rfile.read(n))
    def origin_ok():
        origin=h.headers.get('Origin')
        if not origin: return False
        parsed=urlsplit(origin)
        return parsed.scheme in ('http','https') and parsed.netloc.lower()==h.headers.get('Host','').lower()
    try:
        if h.command=='POST' and not origin_ok(): return respond(403,{'error':'Invalid request origin'})
        with dbopen(state) as c:
            user=getuser(c)
            if path=='/' and h.command=='GET':
                data=PAGE.encode();h.send_response(200);h.send_header('Content-Type','text/html; charset=utf-8');h.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");h.send_header('Content-Length',str(len(data)));h.end_headers();h.wfile.write(data);return
            if path=='/api/config' and h.command=='GET': return respond(200,{'signup':not login_only})
            if path in ('/api/login','/api/signup') and h.command=='POST':
                b=body();u=str(b.get('username','')).strip();p=str(b.get('password',''))
                if not valid_user(u) or len(p)<8 or len(p)>1024: return respond(400,{'error':'Username must be 2–32 letters, digits or underscores; password must be 8–1024 characters.'})
                if path.endswith('signup'):
                    if login_only: return respond(403,{'error':'Account creation is disabled'})
                    salt=secrets.token_hex(16)
                    try:
                        cur=c.execute('INSERT INTO users(username,salt,hash) VALUES(?,?,?)',(u,salt,pw_hash(p,salt)))
                        c.execute("INSERT INTO user_metadata(user_id,created_at) VALUES(?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(cur.lastrowid,))
                    except sqlite3.IntegrityError: return respond(409,{'error':'Username already exists'})
                row=c.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
                if not row or row['banned'] or not hmac.compare_digest(pw_hash(p,row['salt']),row['hash']): return respond(401,{'error':'Invalid credentials or account unavailable'})
                token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,row['id'],int(time.time())))
                c.execute("INSERT INTO user_metadata(user_id,last_sign_in_at) VALUES(?,strftime('%Y-%m-%dT%H:%M:%fZ','now')) ON CONFLICT(user_id) DO UPDATE SET last_sign_in_at=excluded.last_sign_in_at",(row['id'],))
                return respond(200,{'id':row['id'],'username':row['username'],'owner':bool(row['owner'])},{'Set-Cookie':'nxses='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000'})
            if path=='/api/me' and h.command=='GET' and not user: return respond(200,None)
            if not user: return respond(401,{'error':'Please sign in'})
            if path=='/api/me' and h.command=='GET': return respond(200,{'id':user['id'],'username':user['username'],'owner':bool(user['owner'])})
            if path=='/api/admin-user-auth' and h.command=='POST':
                if not user['owner']: return respond(403,{'error':'Owner access required'})
                keys=('view_all_servers','reset_passwords','delete_users')
                settings={r['key']:r['value']=='1' for r in c.execute("SELECT key,value FROM policy WHERE key LIKE 'owner_perm:%'")}
                if not any(settings.get('owner_perm:'+k,True) for k in keys): return respond(403,{'error':'Permission required'})
                ident=body().get('id')
                if not str(ident).isdigit() or not c.execute('SELECT 1 FROM users WHERE id=?',(ident,)).fetchone(): return respond(404,{'error':'User not found'})
                meta=c.execute('SELECT last_sign_in_at FROM user_metadata WHERE user_id=?',(ident,)).fetchone()
                n=c.execute('SELECT COUNT(*) FROM sessions WHERE user_id=? AND created>?',(ident,int(time.time())-30*86400)).fetchone()[0]
                return respond(200,{'last_sign_in_at':meta['last_sign_in_at'] if meta else None,'sessions':n})
            if path=='/api/owner-permissions':
                if not user['owner']: return respond(403,{'error':'Owner access required'})
                if h.command=='GET':
                    rows=c.execute("SELECT key,value FROM policy WHERE key LIKE '%_perm:%'").fetchall()
                    settings={r['key']:r['value']=='1' for r in rows}
                    admin_default={'ban_users','post_announcements','review_appeals','manage_storage'}
                    return respond(200,{role:{k:settings.get(role+'_perm:'+k, role!='admin' or k in admin_default) for k in OWNER_PERMISSIONS} for role in ('owner','sudo','admin')})
                if h.command=='POST':
                    b=body(); role=b.get('role'); key=b.get('permission'); allowed=b.get('allowed')
                    if role not in ('owner','sudo','admin') or key not in OWNER_PERMISSIONS or type(allowed) is not bool: return respond(400,{'error':'Invalid role or permission'})
                    c.execute('INSERT INTO policy(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(role+'_perm:'+key,'1' if allowed else '0'))
                    c.execute("INSERT INTO admin_audit(actor_id,action,detail,created_at) VALUES(?, 'permission', ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(user['id'],json.dumps({'role':role,'perm':key,'allowed':allowed})))
                    return respond(200,{'ok':True})
            if path=='/api/admin-audit' and h.command=='GET':
                if not user['owner']: return respond(403,{'error':'Owner access required'})
                row=c.execute("SELECT value FROM policy WHERE key='owner_perm:view_audit'").fetchone()
                if row and row['value']=='0': return respond(403,{'error':'Audit permission is disabled'})
                rows=c.execute('SELECT id,actor_id,action,detail,created_at FROM admin_audit ORDER BY id DESC LIMIT 200').fetchall()
                return respond(200,[{'id':r['id'],'actor_id':str(r['actor_id']),'action':r['action'],'detail':json.loads(r['detail']),'created_at':r['created_at']} for r in rows])
            if path=='/api/local-server-data' and h.command=='GET':
                servers=c.execute('SELECT * FROM nx_servers WHERE owner_id=? ORDER BY created_at',(user['id'],)).fetchall()
                ids=[r['id'] for r in servers]
                channels=c.execute('SELECT ch.* FROM nx_channels ch JOIN nx_servers s ON s.id=ch.server_id WHERE s.owner_id=? ORDER BY ch.position',(user['id'],)).fetchall()
                return respond(200,{'servers':[{'id':r['id'],'name':r['name'],'owner_id':str(r['owner_id']),'created_at':r['created_at'],'theme':{},'unread':False} for r in servers], 'channels':[dict(r) for r in channels], 'server_members':[{'server_id':r['id'],'user_id':str(user['id']),'joined_at':r['created_at']} for r in servers]})
            if path=='/api/local-server-create' and h.command=='POST':
                b=body();name=b.get('name')
                if not isinstance(name,str) or not name.strip() or len(name)>100: return respond(400,{'error':'Server name must be 1–100 characters'})
                sid=secrets.token_hex(16);cid=secrets.token_hex(16)
                c.execute("INSERT INTO nx_servers VALUES(?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(sid,name.strip(),user['id']))
                c.execute("INSERT INTO nx_channels VALUES(?,?,?,'text',0)",(cid,sid,'general'))
                r=c.execute('SELECT * FROM nx_servers WHERE id=?',(sid,)).fetchone()
                return respond(200,{'id':r['id'],'name':r['name'],'owner_id':str(r['owner_id']),'created_at':r['created_at'],'theme':{}})
            if path=='/api/local-messages' and h.command=='GET':
                rows=c.execute('SELECT m.* FROM nx_server_messages m JOIN nx_channels ch ON ch.id=m.channel_id JOIN nx_servers s ON s.id=ch.server_id WHERE s.owner_id=? ORDER BY m.created_at DESC LIMIT 2000',(user['id'],)).fetchall()
                return respond(200,[{'id':r['id'],'channel_id':r['channel_id'],'author_id':str(r['author_id']),'content':r['content'],'created_at':r['created_at']} for r in rows])
            if path=='/api/local-messages' and h.command=='POST':
                b=body(); ident=b.get('id'); channel=b.get('channel_id');content=b.get('content')
                if not isinstance(ident,str) or len(ident)>80 or not ident or not isinstance(content,str) or not content.strip() or len(content)>4000 or not isinstance(channel,str): return respond(400,{'error':'Invalid message'})
                if not c.execute('SELECT 1 FROM nx_channels ch JOIN nx_servers s ON s.id=ch.server_id WHERE ch.id=? AND s.owner_id=?',(channel,user['id'])).fetchone(): return respond(403,{'error':'No access to channel'})
                try:c.execute("INSERT INTO nx_server_messages VALUES(?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(ident,channel,user['id'],content))
                except sqlite3.IntegrityError:return respond(409,{'error':'Message already exists'})
                r=c.execute('SELECT * FROM nx_server_messages WHERE id=?',(ident,)).fetchone()
                return respond(200,{'id':r['id'],'channel_id':r['channel_id'],'author_id':str(r['author_id']),'content':r['content'],'created_at':r['created_at']})
            if path=='/api/profiles' and h.command=='GET':
                rows=c.execute('SELECT users.id,users.username,users.owner,users.banned,local_nitro.since,user_metadata.created_at FROM users LEFT JOIN local_nitro ON local_nitro.user_id=users.id LEFT JOIN user_metadata ON user_metadata.user_id=users.id ORDER BY users.id').fetchall()
                profiles=[{'id':str(r['id']),'username':r['username'],'display_name':r['username'],'platform_role':'owner' if r['owner'] else None,'is_platform_admin':False,'is_banned':bool(r['banned']),'created_at':r['created_at'],'is_nitro':bool(r['since']),'nitro_since':r['since'],'theme':{}} for r in rows]
                return respond(200,profiles)
            if path=='/api/nitro-requests' and h.command=='GET':
                rows=c.execute('SELECT n.*,u.username,u.owner FROM nitro_requests n JOIN users u ON u.id=n.user_id WHERE (?=1 OR n.user_id=?) ORDER BY n.id DESC LIMIT 300',(int(user['owner']),user['id'])).fetchall()
                result=[]
                for r in rows:
                    d=dict(r); d['id']=str(d['id']);d['user_id']=str(d['user_id']);d['profiles']={'id':d['user_id'],'username':d.pop('username'),'display_name':r['username'],'platform_role':'owner' if d.pop('owner') else None,'theme':{}};result.append(d)
                return respond(200,result)
            if path=='/api/nitro-requests' and h.command=='POST':
                b=body(); message=b.get('message')
                if message is not None and (not isinstance(message,str) or len(message)>500): return respond(400,{'error':'Message must be at most 500 characters'})
                if c.execute('SELECT 1 FROM local_nitro WHERE user_id=?',(user['id'],)).fetchone(): return respond(409,{'error':'Nitro is already active'})
                try: c.execute("INSERT INTO nitro_requests(user_id,message,created_at) VALUES(?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(user['id'],message))
                except sqlite3.IntegrityError: return respond(409,{'error':'A request is already pending'})
                return respond(200,{'ok':True})
            if path=='/api/nitro-review' and h.command=='POST':
                if not user['owner']: return respond(403,{'error':'Owner access required'})
                b=body(); ident=b.get('id'); status=b.get('status');note=b.get('review_note')
                if not str(ident).isdigit() or status not in ('approved','denied') or (note is not None and (not isinstance(note,str) or len(note)>500)): return respond(400,{'error':'Invalid request'})
                c.execute('BEGIN IMMEDIATE')
                row=c.execute("SELECT user_id FROM nitro_requests WHERE id=? AND status='pending'",(ident,)).fetchone()
                if not row: return respond(409,{'error':'Request is no longer pending'})
                c.execute("UPDATE nitro_requests SET status=?,review_note=?,reviewed_by=?,reviewed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",(status,note,user['id'],ident))
                if status=='approved': c.execute("INSERT OR IGNORE INTO local_nitro(user_id,since) VALUES(?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(row['user_id'],))
                c.execute("INSERT INTO admin_audit(actor_id,action,detail,created_at) VALUES(?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(user['id'],'nitro_given' if status=='approved' else 'nitro_request_denied',json.dumps({'user_id':row['user_id']})))
                return respond(200,{'ok':True})
            if path=='/api/nitro-set' and h.command=='POST':
                if not user['owner']: return respond(403,{'error':'Owner access required'})
                b=body(); target=b.get('id'); on=b.get('on')
                if not str(target).isdigit() or type(on) is not bool or not c.execute('SELECT 1 FROM users WHERE id=?',(target,)).fetchone(): return respond(400,{'error':'Invalid account or value'})
                if on: c.execute("INSERT OR IGNORE INTO local_nitro(user_id,since) VALUES(?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(target,))
                else: c.execute('DELETE FROM local_nitro WHERE user_id=?',(target,))
                c.execute("INSERT INTO admin_audit(actor_id,action,detail,created_at) VALUES(?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(user['id'],'nitro_given' if on else 'nitro_removed',json.dumps({'user_id':target})))
                return respond(200,{'ok':True})
            if path=='/api/logout' and h.command=='POST':
                token=next((s.strip()[6:] for s in h.headers.get('Cookie','').split(';') if s.strip().startswith('nxses=')),'');c.execute('DELETE FROM sessions WHERE token=?',(token,));return respond(200,{'ok':True},{'Set-Cookie':'nxses=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
            if path=='/api/messages' and h.command=='GET':
                rows=c.execute('SELECT id,username,text,created FROM messages ORDER BY id DESC LIMIT 200').fetchall();return respond(200,[dict(x) for x in reversed(rows)])
            if path=='/api/messages' and h.command=='POST':
                text=str(body().get('text','')).strip()
                if not text or len(text)>4000: return respond(400,{'error':'Message must be 1–4000 characters'})
                c.execute('INSERT INTO messages(user_id,username,text,created) VALUES(?,?,?,?)',(user['id'],user['username'],text,int(time.time())));return respond(200,{'ok':True})
            if path=='/api/upload' and h.command=='POST':
                b=body();name=Path(str(b.get('name','file')).replace('\\','/')).name[:160];data=base64.b64decode(b.get('data',''),validate=True)
                if not name or len(data)>MAX_FILE: return respond(400,{'error':'Invalid file or exceeds 8 MB'})
                ident=secrets.token_hex(24);folder=state/'files';folder.mkdir(mode=0o700,exist_ok=True);(folder/ident).write_bytes(data)
                category='photos' if mimetypes.guess_type(name)[0] and mimetypes.guess_type(name)[0].startswith('image/') else 'drive-assets'
                c.execute('INSERT INTO files VALUES(?,?,?,?,?)',(ident,user['id'],name,category,int(time.time())));return respond(200,{'url':'/files/'+ident,'name':name})
            if path.startswith('/files/') and h.command=='GET':
                ident=path[len('/files/'):];row=c.execute('SELECT name FROM files WHERE id=?',(ident,)).fetchone()
                if not row or len(ident)!=48 or not all(x in '0123456789abcdef' for x in ident): return respond(404,{'error':'Not found'})
                f=state/'files'/ident
                if not f.is_file(): return respond(404,{'error':'Not found'})
                data=f.read_bytes();h.send_response(200);h.send_header('Content-Type','application/octet-stream');h.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+__import__('urllib.parse',fromlist=['quote']).quote(row['name']));h.send_header('X-Content-Type-Options','nosniff');h.send_header('Content-Length',str(len(data)));h.end_headers();h.wfile.write(data);return
            return respond(404,{'error':'Not found'})
    except (ValueError,TypeError,UnicodeError,json.JSONDecodeError):
        c=None
        return respond(400,{'error':'Invalid request'})
    except Exception as e:
        c=None
        print('Isolated backend error:',repr(e),flush=True);return respond(500,{'error':'Internal server error'})
