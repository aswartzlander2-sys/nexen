#!/usr/bin/env python3
"""Nexen connected-mode launcher. See README for security and limitations."""
import argparse, getpass, hmac, http.server, json, os, pathlib, secrets, subprocess, sys, threading, time, urllib.request
import isolated
import updater
ROOT = pathlib.Path(__file__).resolve().parent
STATE = pathlib.Path(os.environ.get('NEXEN_STATE_DIR', pathlib.Path.home() / '.nexen'))
PORT = 63936

def progress(message):
    print("[nexen] " + message, flush=True)

def record():
    try: return json.loads((STATE / 'session.json').read_text())
    except (OSError, ValueError): return None

def request(path, token):
    req = urllib.request.Request('http://127.0.0.1:%d%s' % (PORT,path), headers={'X-Nexen-Token':token}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=2) as r: return r.status == 200
    except Exception: return False

def serve(token):
    try: config = json.loads((STATE / "config.json").read_text())
    except (OSError, ValueError): config = {"mode":"connected", "login_only":False}
    if sys.platform.startswith('linux'):
        try:
            import ctypes
            ctypes.CDLL(None).prctl(15, b'NexChats Nexen', 0, 0, 0)
        except Exception: pass
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT), **kwargs)
        def do_POST(self):
            if not self.path.startswith('/__nexen/'):
                if config['mode'] == 'isolated': return isolated.handle(self, STATE, config.get('login_only',False))
                self.send_error(404); return
            if self.client_address[0] != '127.0.0.1' or not hmac.compare_digest(self.headers.get('X-Nexen-Token',''), token):
                self.send_error(403); return
            if self.path not in ('/__nexen/status','/__nexen/stop'):
                self.send_error(404); return
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
            if self.path.endswith('/stop'): threading.Thread(target=self.server.shutdown, daemon=True).start()
        def do_GET(self):
            if config['mode'] == 'isolated' and not config.get('original_ui_test'): return isolated.handle(self, STATE, config.get('login_only',False))
            if config['mode'] == 'isolated' and self.path.startswith('/api/'): return isolated.handle(self, STATE, config.get('login_only',False))
            from urllib.parse import unquote, urlsplit
            path = unquote(urlsplit(self.path).path)
            # Only serve frontend files, never source, configuration state or a directory listing.
            if path == '/': path = '/index.html'
            allowed = (path in ['/index.html','/admin.html','/dms.html','/portal.html','/profile.html','/server-settings.html','/server.html','/nexchat.svg'] or path.startswith('/assets/'))
            file = (ROOT / path.lstrip('/')).resolve()
            if not allowed or not file.is_relative_to(ROOT / 'assets') and file.parent != ROOT or not file.is_file() or 'xhr-transport-polyfill' in path:
                self.send_error(404); return
            if config['mode']=='isolated' and path == '/assets/css/theme.css':
                import re
                css=file.read_text(encoding='utf-8');css=re.sub(r"@import url\('https://fonts\.googleapis\.com/[^']+'\);", "@import url('/assets/vendor/fonts/fonts.css');",css)
                data=css.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if config['mode']=='isolated' and path == '/assets/js/config.js':
                data=b'window.NEXCHAT_CONFIG = { STORAGE_ENDPOINT: "", TURN_SERVERS: [] };'; self.send_response(200);self.send_header('Content-Type','application/javascript; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if config['mode']=='isolated' and path.endswith('.html'):
                text=file.read_text(encoding='utf-8')
                text=text.replace('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css', '/assets/vendor/fontawesome/css/all.min.css')
                text=text.replace('<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>', '')
                text=text.replace('assets/js/supabase-client.js?v=42','assets/js/local-supabase.js')
                # Prevent WebRTC from contacting public STUN/TURN services in this test build.
                text=text.replace('</head>', '<script>window.RTCPeerConnection=undefined;window.webkitRTCPeerConnection=undefined;</script></head>')
                data=text.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self' blob: data:; object-src 'none'; base-uri 'none'");self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            if path == '/assets/js/config.js' and config.get('storage_endpoint'):
                text = file.read_text(encoding='utf-8').replace("STORAGE_ENDPOINT: '',", 'STORAGE_ENDPOINT: ' + json.dumps(config['storage_endpoint']) + ',')
                data=text.encode('utf-8'); self.send_response(200); self.send_header('Content-Type','application/javascript; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
            self.path = path
            return super().do_GET()
    try:
        with http.server.ThreadingHTTPServer(('0.0.0.0', PORT), Handler) as httpd:
            STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
            tmp = STATE / ('session.%d.tmp' % os.getpid())
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f: json.dump({'token': token, 'pid':os.getpid()}, f)
            os.replace(tmp, STATE / 'session.json')
            httpd.serve_forever()
    except OSError as e:
        print('Nexen server failed: %s' % e, file=sys.stderr); return 1
    finally:
        r = record()
        if r and r.get('token') == token:
            (STATE / 'session.json').unlink(missing_ok=True)
    return 0

def main():
    p=argparse.ArgumentParser(prog='nexen', description='Nexen 1.0.0')
    sub=p.add_subparsers(dest='cmd', required=True)
    start=sub.add_parser('start'); start.add_argument('--no-contact', action='store_true'); start.add_argument('--connected', action='store_true'); start.add_argument('-L', action='store_true'); start.add_argument('--allow-signup', action='store_true'); start.add_argument('--original-ui-test', action='store_true'); start.add_argument('--basic-ui', action='store_true')
    sub.add_parser('stop'); sub.add_parser('update'); storage=sub.add_parser('storage-endpoint'); storage.add_argument('url', help='HTTPS signer URL, or off to disable'); rem=sub.add_parser('remove'); rem.add_argument('category', choices=['usr-list','admin-policy','photos','chats','drive-assets','anylist']); rem.add_argument('--yes',action='store_true')
    worker=sub.add_parser('_serve'); worker.add_argument('token')
    args=p.parse_args()
    if args.cmd == '_serve': return serve(args.token)
    if args.cmd == 'update':
        progress('Checking installation and server status...')
        if ROOT != updater.install_root().resolve():
            print('Updates are only supported for installer-managed installations. Update this checkout with git instead.',file=sys.stderr); return 1
        r=record()
        if r and request('/__nexen/status',r.get('token','')):
            print('Stop Nexen before updating.',file=sys.stderr); return 1
        import socket
        try:
            with socket.create_connection(('127.0.0.1',PORT),timeout=1):
                print('Port 63936 is in use; stop the service before updating.',file=sys.stderr); return 1
        except OSError: pass
        try:
            progress('Downloading the latest main branch from GitHub...')
            archive = updater.download()
            progress('Download complete; validating archive and replacing application files...')
            updater.apply_archive(archive,ROOT,STATE)
        except Exception as e:
            print('Update failed; your existing installation and data should be unchanged: '+str(e),file=sys.stderr); return 1
        progress('Update complete; local data and settings were preserved.')
        progress('Next: run nexen start.'); return 0
    if args.cmd == 'storage-endpoint':
        progress('Checking and saving connected-mode storage settings...')
        from urllib.parse import urlsplit
        url='' if args.url=='off' else args.url.strip()
        parsed=urlsplit(url)
        if url and (parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment):
            print('Use an HTTPS endpoint URL without credentials or a fragment, or off.',file=sys.stderr); return 1
        r=record()
        if r and request('/__nexen/status',r.get('token','')): print('Stop Nexen before changing the storage endpoint.',file=sys.stderr); return 1
        STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
        try: config=json.loads((STATE/'config.json').read_text())
        except (OSError,ValueError): config={'mode':'connected','login_only':False}
        config['storage_endpoint']=url
        tmp=STATE/'config.tmp';tmp.write_text(json.dumps(config));os.replace(tmp,STATE/'config.json')
        progress('Storage endpoint %s; stored in %s.' % ('cleared' if not url else 'saved', STATE / 'config.json'))
        progress('Run nexen start to apply the setting.'); return 0
    if args.cmd == 'remove':
        progress('Checking independent-mode data and server status...')
        try: config=json.loads((STATE/'config.json').read_text())
        except (OSError,ValueError): config={}
        if config.get('mode') != 'isolated': print('Removal is only available in isolated mode.',file=sys.stderr); return 1
        r=record()
        if r and request('/__nexen/status',r.get('token','')): print('Stop Nexen before removing data.',file=sys.stderr); return 1
        progress('Target: %s. Data directory: %s' % (args.category, STATE))
        if not args.yes and input('Permanently delete/reset '+args.category+'? Type YES: ') != 'YES': print('Cancelled.'); return 1
        progress('Removing or resetting the selected local data...')
        try: isolated.remove(STATE,args.category)
        except Exception as e: print('Removal failed: '+str(e),file=sys.stderr); return 1
        progress('Completed: '+args.category+'. Hosted NexChat data was not changed.'); return 0
    if args.cmd == 'stop':
        progress('Checking for a running Nexen session...')
        r=record()
        if r and request('/__nexen/stop',r.get('token','')):
            progress('Shutdown requested; waiting for the server to stop...')
            for _ in range(50):
                if not request('/__nexen/status',r.get('token','')):
                    progress('Nexen stopped. Data and settings were kept in %s.' % STATE); return 0
                time.sleep(.1)
            print('Shutdown was requested but could not be confirmed. Check the server log.',file=sys.stderr); return 1
        print('No controllable Nexen session found.', file=sys.stderr); return 1
    progress('Checking for an existing session and loading saved settings...')
    r=record()
    if r and request('/__nexen/status',r.get('token','')):
        if args.no_contact or args.connected or args.L or args.allow_signup or args.original_ui_test or args.basic_ui:
            print('Stop the running session before changing settings.',file=sys.stderr); return 1
        progress('Nexen is already running at http://localhost:%d.' % PORT)
        progress('Use nexen stop before changing settings.'); return 0
    if args.no_contact and args.connected or args.L and args.allow_signup or args.original_ui_test and args.basic_ui:
        print('Conflicting options.',file=sys.stderr); return 1
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    try: config=json.loads((STATE/'config.json').read_text())
    except (OSError,ValueError): config={'mode':'connected','login_only':False}
    if args.no_contact: config['mode']='isolated'
    if args.connected: config['mode']='connected'
    if args.L: config['login_only']=True
    if args.allow_signup: config['login_only']=False
    if args.original_ui_test: config['original_ui_test']=True
    if args.basic_ui: config['original_ui_test']=False
    if config['mode']=='connected' and args.original_ui_test:
        print('The original-UI local test requires --no-contact.',file=sys.stderr); return 1
    if config['mode']=='connected' and config['login_only']:
        print('Login-only mode cannot be enforced against the hosted backend. Use --no-contact or --allow-signup.',file=sys.stderr); return 1
    progress('Mode: %s; data and settings: %s' % (config['mode'], STATE))
    if config['mode']=='isolated':
        progress('Interface: %s; new accounts: %s.' % ('original UI test (incomplete)' if config.get('original_ui_test') else 'basic local chat', 'disabled' if config.get('login_only') else 'allowed'))
    else:
        progress('Interface: original NexChat; data uses the configured hosted services.')
    if config['mode']=='isolated' and not isolated.owner_exists(STATE):
        progress('No local Owner found. Create the local Owner account.')
        try:
            username=input('Owner username: ').strip(); password=getpass.getpass('Owner password: '); confirm=getpass.getpass('Confirm password: ')
            if password != confirm: print('Passwords do not match.',file=sys.stderr); return 1
            isolated.create_owner(STATE,username,password)
        except (ValueError,EOFError,KeyboardInterrupt) as e: print('Owner setup failed: '+str(e),file=sys.stderr); return 1
    tmp=STATE/'config.tmp';tmp.write_text(json.dumps(config));os.replace(tmp,STATE/'config.json')
    progress('Settings saved. Starting server on 0.0.0.0:%d...' % PORT)
    token=secrets.token_urlsafe(32)
    with open(STATE / 'server.log','ab') as log:
        kw = {'stdin':subprocess.DEVNULL, 'stdout':log, 'stderr':log}
        if os.name == 'nt': kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else: kw['start_new_session']=True
        proc=subprocess.Popen([sys.executable, str(ROOT/'nexen.py'), '_serve', token], **kw)
    for _ in range(50):
        if request('/__nexen/status',token):
            progress('Server is running. Open http://localhost:%d or http://<host-LAN-IP>:%d.' % (PORT,PORT))
            progress('To stop: nexen stop. Server log: %s' % (STATE/'server.log'))
            return 0
        if proc.poll() is not None: break
        time.sleep(.1)
    print('Failed to start; inspect %s' % (STATE/'server.log'), file=sys.stderr); return 1
if __name__ == '__main__': sys.exit(main())
