#!/usr/bin/env python3
"""Install this extracted Nexen package locally, preserving data and identity."""
import ast, os, pathlib, shlex, shutil, socket, sys, tempfile

SOURCE = pathlib.Path(__file__).resolve().parent

def main():
    if os.name == 'nt':
        base = pathlib.Path(os.environ['LOCALAPPDATA']) / 'Nexen'
        target, bin_dir = base / 'app', base / 'bin'
    else:
        target, bin_dir = pathlib.Path.home() / '.local/share/nexen', pathlib.Path.home() / '.local/bin'
    target = target.resolve()
    state = pathlib.Path(os.environ.get('NEXEN_STATE_DIR', str(pathlib.Path.home()/'.nexen'))).expanduser().resolve()
    ident = pathlib.Path(os.environ.get('NEXEN_IDENTITY_FILE', str(pathlib.Path.home()/'.nexen-identity'))).expanduser().resolve()
    if SOURCE == target or target in SOURCE.parents or SOURCE in target.parents:
        raise RuntimeError('Extract the ZIP outside the installation directory, then run this script there.')
    if state == target or target in state.parents or ident == target or target in ident.parents:
        raise RuntimeError('Data or ID is inside the application directory; move it before installing.')
    try:
        with socket.create_connection(('127.0.0.1', 63936), timeout=1):
            raise RuntimeError('Port 63936 is in use. Stop Nexen before installing.')
    except (ConnectionRefusedError, TimeoutError):
        pass
    for name in ('nexen.py','identity.py','isolated.py','updater.py','index.html','origin-ui/index.html','assets/app/nx-app.js','assets/app/nx-settings.js'):
        if not (SOURCE/name).is_file(): raise RuntimeError('Incomplete package: missing '+name)
    if 'assets/app/nx-app.js' not in (SOURCE/'index.html').read_text(encoding='utf-8'):
        raise RuntimeError('The package does not contain the Origin SPA at its root.')
    tree=ast.parse((SOURCE/'identity.py').read_text(encoding='utf-8'))
    versions=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)]
    if len(versions)!=1: raise RuntimeError('Invalid version file.')
    if any(p.is_symlink() for p in SOURCE.rglob('*')): raise RuntimeError('Package contains a symlink; refusing to install.')
    target.parent.mkdir(parents=True, exist_ok=True); bin_dir.mkdir(parents=True, exist_ok=True)
    backup=None
    with tempfile.TemporaryDirectory(prefix='.nexen-local-install-', dir=target.parent) as tmp:
        stage=pathlib.Path(tmp)/'app'
        shutil.copytree(SOURCE, stage, ignore=shutil.ignore_patterns('.git','__pycache__','node_modules','.pytest_cache'))
        if target.exists():
            backup=pathlib.Path(tempfile.mkdtemp(prefix='.nexen-previous-',dir=target.parent)); backup.rmdir()
            os.rename(target,backup)
        try:
            os.rename(stage,target)
        except BaseException:
            if backup: os.rename(backup,target)
            raise
        try:
            if os.name=='nt':
                launcher=bin_dir/'nexen.cmd'; content='@echo off\r\npython "'+str(target/'nexen.py')+'" %*\r\n'
            else:
                launcher=bin_dir/'nexen'; content='#!/bin/sh\nexec python3 '+shlex.quote(str(target/'nexen.py'))+' "$@"\n'
            temp=bin_dir/('.nexen-launcher-%d.tmp'%os.getpid())
            temp.write_text(content,encoding='utf-8')
            if os.name!='nt': temp.chmod(0o755)
            os.replace(temp,launcher)
        except BaseException:
            shutil.rmtree(target)
            if backup: os.rename(backup,target)
            raise
        if backup: shutil.rmtree(backup,ignore_errors=True)
    print('Installed Nexen V.'+versions[0]+'. Local data, settings and ID were kept.')
    print('Launcher: '+str(launcher))
    found=shutil.which('nexen')
    if found and pathlib.Path(found).resolve()!=launcher.resolve():
        print('Note: PATH finds '+found+' first; use the launcher above or fix PATH.')
    print('Run the launcher with version, then start or start-isolated.')

if __name__=='__main__':
    try: main()
    except Exception as e:
        print('Installation failed: '+str(e),file=sys.stderr)
        sys.exit(1)
