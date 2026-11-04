"""Small standalone Nexen backend. No external services or dependencies."""
import base64, hashlib, hmac, json, mimetypes, os, secrets, sqlite3, time
from pathlib import Path
from urllib.parse import urlsplit

MAX_FILE=8*1024*1024

def dbopen(state):
    state.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(state/'isolated.sqlite3', timeout=10)
    c.row_factory=sqlite3.Row
    c.executescript('''PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE COLLATE NOCASE NOT NULL, salt TEXT NOT NULL, hash TEXT NOT NULL, owner INTEGER NOT NULL DEFAULT 0, banned INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, username TEXT NOT NULL, text TEXT NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS policy(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    ''')
    return c

def pw_hash(p,salt): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),310000).hex()
def valid_user(u): return 2<=len(u)<=32 and all(c.isascii() and (c.isalnum() or c=='_') for c in u)
def create_owner(state, username, password):
    if not valid_user(username) or len(password)<8: raise ValueError('Username must be 2–32 ASCII letters, digits or underscores; password must be at least 8 characters.')
    with dbopen(state) as c:
        if c.execute('SELECT 1 FROM users WHERE owner=1').fetchone(): raise ValueError('An owner already exists')
        salt=secrets.token_hex(16)
        c.execute('INSERT INTO users(username,salt,hash,owner) VALUES(?,?,?,1)',(username,salt,pw_hash(password,salt)))

def owner_exists(state):
    with dbopen(state) as c: return bool(c.execute('SELECT 1 FROM users WHERE owner=1').fetchone())

def remove(state,category):
    with dbopen(state) as c:
        if category in ('usr-list','anylist'):
            c.execute('DELETE FROM sessions'); c.execute('DELETE FROM users')
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
</style></head><body><header><b>✦ NexChat <span class="muted">Nexen V.2.00<span data-nexen-id></span> · Independent</span></b><div class="toolbar"><span id="who"></span><button id="logout" class="hidden">Sign out</button></div></header><main>
<div id="auth" class="box auth"><h1>Welcome to NexChat</h1><p class="muted">Your independent Nexen server</p><div class="tabs"><button id="loginTab">Log in</button><button id="signupTab">Sign up</button></div><form id="loginForm"><input id="username" placeholder="Username" autocomplete="username" required><input id="password" type="password" placeholder="Password" autocomplete="current-password" required><button id="submit">Log in</button></form><p id="error"></p><p class="muted">a hobby project · be nice ✌️ • Nexen V.2.00<span data-nexen-id></span></p></div>
<div id="app" class="box chat hidden"><div class="toolbar"><h2>＃ general</h2><span class="muted">NexChat v3 · Esc to close · Nexen V.2.00<span data-nexen-id></span></span></div><div id="messages"></div><form id="send" class="composer"><input id="text" placeholder="Message #general" maxlength="4000"><button>Send</button></form><div class="composer"><input type="file" id="file"><button id="upload">Upload file</button></div><p id="chatError"></p></div></main><script>
fetch('/__nexen/meta',{cache:'no-store'}).then(r=>r.json()).then(m=>{if(/^\d{6}$/.test(m.id))document.querySelectorAll('[data-nexen-id]').forEach(e=>e.textContent=' • '+m.id)}).catch(()=>{});let signingUp=false,last='',current=null;const $=id=>document.getElementById(id);async function api(path,method='GET',body){let r;try{r=await fetch(path,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin'})}catch(e){throw Error('Cannot reach this Nexen server. Check that it is running and your network connection, then try again.')}let x;try{x=await r.json()}catch(e){throw Error('The Nexen server returned an unexpected response. Try again.')};if(!r.ok)throw Error(x.error||'Request failed');return x}function mode(up){signingUp=up;$('submit').textContent=up?'Create account':'Log in';$('error').textContent=''}$('loginTab').onclick=()=>mode(false);$('signupTab').onclick=()=>mode(true);$('loginForm').onsubmit=async e=>{e.preventDefault();try{current=await api('/api/'+(signingUp?'signup':'login'),'POST',{username:$('username').value,password:$('password').value});$('password').value='';show();}catch(err){$('error').textContent=err.message}};$('logout').onclick=async()=>{try{await api('/api/logout','POST',{});current=null;last='';show()}catch(e){$('chatError').textContent=e.message}};function show(){ $('auth').classList.toggle('hidden',!!current);$('app').classList.toggle('hidden',!current);$('logout').classList.toggle('hidden',!current);$('who').textContent=current?current.username+(current.owner?' · Owner':'') : '';if(current)poll() }async function poll(){if(!current)return;try{let data=await api('/api/messages');let s=JSON.stringify(data);$('chatError').textContent='';if(s!==last){let m=$('messages'),near=m.scrollTop+m.clientHeight>=m.scrollHeight-80;m.textContent='';for(let x of data){let row=document.createElement('div');row.className='msg';let b=document.createElement('b');b.textContent=x.username;let t=document.createElement('time');t.textContent=new Date(x.created*1000).toLocaleString();let p=document.createElement('div');p.textContent=x.text;let match=x.text.match(/^File: (.+) — (https?:\/\/[^ ]+\/files\/[a-f0-9]{48})$/);if(match){try{let u=new URL(match[2]);if(u.origin===location.origin){p.textContent='File: ';let link=document.createElement('a');link.href=u.pathname;link.textContent=match[1];p.append(link)}}catch(_){}}row.append(b,t,p);m.append(row)}if(near)m.scrollTop=m.scrollHeight;last=s}}catch(e){$('chatError').textContent=e.message}}$('send').onsubmit=async e=>{e.preventDefault();let text=$('text').value.trim();if(!text)return;try{await api('/api/messages','POST',{text});$('text').value='';await poll();$('messages').scrollTop=$('messages').scrollHeight}catch(e){$('chatError').textContent=e.message}};$('upload').onclick=async()=>{let f=$('file').files[0];if(!f)return;if(f.size>8388608){$('chatError').textContent='Maximum file size is 8 MB';return}let reader=new FileReader;reader.onload=async()=>{try{let r=await api('/api/upload','POST',{name:f.name,data:reader.result.split(',')[1]});await api('/api/messages','POST',{text:'File: '+r.name+' — '+location.origin+r.url});$('file').value='';await poll()}catch(e){$('chatError').textContent=e.message}};reader.readAsDataURL(f)};setInterval(poll,3000);api('/api/config').then(c=>{$('signupTab').classList.toggle('hidden',!c.signup)});api('/api/me').then(u=>{current=u;show()}).catch(()=>{});
</script></body></html>'''

def handle(h,state,login_only):
    path=urlsplit(h.path).path
    def respond(code,obj,headers=None):
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
                    try: c.execute('INSERT INTO users(username,salt,hash) VALUES(?,?,?)',(u,salt,pw_hash(p,salt)))
                    except sqlite3.IntegrityError: return respond(409,{'error':'Username already exists'})
                row=c.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
                if not row or row['banned'] or not hmac.compare_digest(pw_hash(p,row['salt']),row['hash']): return respond(401,{'error':'Invalid credentials or account unavailable'})
                token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,row['id'],int(time.time())))
                return respond(200,{'id':row['id'],'username':row['username'],'owner':bool(row['owner'])},{'Set-Cookie':'nxses='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000'})
            if path=='/api/me' and h.command=='GET' and not user: return respond(200,None)
            if not user: return respond(401,{'error':'Please sign in'})
            if path=='/api/me' and h.command=='GET': return respond(200,{'id':user['id'],'username':user['username'],'owner':bool(user['owner'])})
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
    except (ValueError,TypeError,UnicodeError,json.JSONDecodeError): return respond(400,{'error':'Invalid request'})
    except Exception as e:
        print('Isolated backend error:',repr(e),flush=True);return respond(500,{'error':'Internal server error'})
