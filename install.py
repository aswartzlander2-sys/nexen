#!/usr/bin/env python3
"""Install the newest stable Nexen version from a release or main; no dependencies."""
import ast, io, json, os, re, shutil, socket, stat, sys, tempfile, urllib.request, zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote
API='https://api.github.com/repos/aswartzlander2-sys/nexen/releases'

def request(url,limit):
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'Nexen-Installer/3.1.0'})
    with urllib.request.urlopen(req,timeout=60) as r: data=r.read(limit+1)
    if len(data)>limit: raise ValueError('Download too large')
    return data

def main():
    try:
        with socket.create_connection(('127.0.0.1',63936),timeout=1):
            raise RuntimeError('Port 63936 is in use. Stop Nexen before installing.')
    except (ConnectionRefusedError,TimeoutError): pass
    releases=[]
    for page in range(1,11):
        batch=json.loads(request(API+'?per_page=100&page='+str(page),5*1024*1024))
        if not isinstance(batch,list): raise ValueError('Invalid GitHub release response')
        releases.extend(batch)
        if len(batch)<100: break
    else: raise ValueError('Too many releases to check safely')
    choices=[]
    for release in releases:
        tag=release.get('tag_name','');m=re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',tag)
        if m and not release.get('draft') and not release.get('prerelease'): choices.append((tuple(map(int,m.groups())),tag))
    commit=json.loads(request('https://api.github.com/repos/aswartzlander2-sys/nexen/git/ref/heads/main',1024*1024)).get('object',{}).get('sha','')
    if not re.fullmatch(r'[0-9a-f]{40}',commit): raise ValueError('Invalid main commit')
    version_src=request('https://raw.githubusercontent.com/aswartzlander2-sys/nexen/'+commit+'/identity.py',65536).decode('utf-8')
    tree=ast.parse(version_src)
    versions=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='VERSION' for x in n.targets) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)]
    if len(versions)!=1: raise ValueError('Invalid main version')
    m=re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)',versions[0])
    if m: choices.append((tuple(map(int,m.groups())),'v'+versions[0],commit))
    choices=[(c[0],c[1],None) if len(c)==2 else c for c in choices]
    if not choices: raise RuntimeError('No stable Nexen version is available.')
    _,tag,sha=max(choices,key=lambda x:(x[0],x[2] is None))
    print('Installing stable '+tag+(' from main...' if sha else ' release...'))
    url=('https://codeload.github.com/aswartzlander2-sys/nexen/zip/'+sha if sha else 'https://github.com/aswartzlander2-sys/nexen/archive/refs/tags/'+quote(tag,safe='')+'.zip')
    data=request(url,50*1024*1024)
    if os.name=='nt':
        base=Path(os.environ['LOCALAPPDATA'])/'Nexen';target=base/'app';bin_dir=base/'bin'
    else:
        target=Path.home()/'.local'/'share'/'nexen';bin_dir=Path.home()/'.local'/'bin'
    # Reinstalling must not delete a user-selected state or identity path.
    target=target.resolve()
    state=Path(os.environ.get('NEXEN_STATE_DIR',str(Path.home()/'.nexen'))).expanduser().resolve()
    ident=Path(os.environ.get('NEXEN_IDENTITY_FILE',str(Path.home()/'.nexen-identity'))).expanduser().resolve()
    if state == target or target in state.parents or ident == target or target in ident.parents:
        raise RuntimeError('The data or identity path is inside the application directory; move it before installing.')
    target.parent.mkdir(parents=True,exist_ok=True);bin_dir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nexen-install-',dir=target.parent) as tmp:
        tmp=Path(tmp);stage=tmp/'app';stage.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            entries=z.infolist()
            if len(entries)>10000 or sum(e.file_size for e in entries)>150*1024*1024: raise ValueError('Archive too large')
            root=None
            for e in entries:
                path=PurePosixPath(e.filename)
                if path.is_absolute() or not path.parts or not path.parts[0].startswith('nexen-') or any(x in ('.','..') for x in path.parts) or '\\' in e.filename or stat.S_ISLNK(e.external_attr>>16): raise ValueError('Unsafe archive path')
                if root is None: root=path.parts[0]
                if root!=path.parts[0]: raise ValueError('Multiple archive roots')
                if len(path.parts)==1: continue
                dest=stage.joinpath(*path.parts[1:])
                if e.is_dir(): dest.mkdir(parents=True,exist_ok=True);continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(e) as src,dest.open('xb') as out: shutil.copyfileobj(src,out)
        for name in ('nexen.py','identity.py','updater.py','isolated.py','index.html','assets/js/config.js','README.md'):
            if not (stage/name).is_file(): raise ValueError('Incomplete release: missing '+name)
        if tuple(map(int, tag.lstrip('v').split('.'))) >= (3,0,0) and not (stage/'origin-ui/index.html').is_file(): raise ValueError('Incomplete release: missing origin-ui/index.html')
        if tuple(map(int, tag.lstrip('v').split('.'))) >= (3,1,0) and (not (stage/'assets/app/nx-app.js').is_file() or 'assets/app/nx-app.js' not in (stage/'index.html').read_text(encoding='utf-8')): raise ValueError('Incomplete release: missing the root Origin SPA')
        tree=ast.parse((stage/'identity.py').read_text(encoding='utf-8'))
        values=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='VERSION' for x in n.targets) and isinstance(n.value,ast.Constant)]
        if values != [tag.removeprefix('v')]: raise ValueError('Release tag and bundled version do not match')
        backup=None
        if target.exists():
            backup=Path(tempfile.mkdtemp(prefix='.nexen-previous-',dir=target.parent));backup.rmdir();os.rename(target,backup)
        try: os.rename(stage,target)
        except BaseException as ex:
            if backup:
                try: os.rename(backup,target)
                except OSError as restore: raise RuntimeError('Restore failed; previous files remain at '+str(backup)) from restore
            raise ex
        if backup:
            try: shutil.rmtree(backup)
            except OSError: print('Old files retained at '+str(backup))
    if os.name=='nt':
        (bin_dir/'nexen.cmd').write_text('@echo off\r\npython "'+str(target/'nexen.py')+'" %*\r\n',encoding='utf-8')
    else:
        import shlex
        launcher=bin_dir/'nexen';launcher.write_text('#!/bin/sh\nexec python3 '+shlex.quote(str(target/'nexen.py'))+' "$@"\n');launcher.chmod(0o755)
    print('Installed '+tag+'. Data and Nexen ID were not removed. Run nexen start.')
    print('If nexen is not found, add '+str(bin_dir)+' to PATH or open a new terminal.')

if __name__=='__main__':
    try: main()
    except Exception as e: print('Installation failed: '+str(e),file=sys.stderr);sys.exit(1)
