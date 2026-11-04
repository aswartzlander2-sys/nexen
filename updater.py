"""Update an installer-managed Nexen tree without touching the state directory."""
import ast, io, os, shutil, stat, tempfile, urllib.request, zipfile
from pathlib import Path, PurePosixPath

URL='https://github.com/aswartzlander2-sys/nexen/archive/refs/heads/main.zip'
MAX_DOWNLOAD=50 * 1024 * 1024
MAX_UNPACKED=150 * 1024 * 1024
REQUIRED=('nexen.py','isolated.py','updater.py','identity.py','index.html','assets/js/config.js','README.md')

def install_root():
    if os.name == 'nt':
        local=os.environ.get('LOCALAPPDATA')
        if not local: raise RuntimeError('LOCALAPPDATA is not set')
        return Path(local)/'Nexen'/'app'
    return Path.home()/'.local'/'share'/'nexen'

def download():
    request=urllib.request.Request(URL,headers={'User-Agent':'Nexen-Updater/2.1.0'})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read(MAX_DOWNLOAD+1)
    if len(data)>MAX_DOWNLOAD: raise ValueError('Download exceeds 50 MB')
    return data

def apply_archive(data,target,state):
    target=Path(target).resolve();state=Path(state).resolve()
    if target == state or target in state.parents:
        raise ValueError('State directory is inside the installation; refusing to update')
    if not target.is_dir(): raise ValueError('Installation directory is missing')
    with tempfile.TemporaryDirectory(prefix='.nexen-update-',dir=target.parent) as temp:
        temp=Path(temp); staged=temp/'new';staged.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items=archive.infolist()
            if len(items)>10000 or sum(i.file_size for i in items)>MAX_UNPACKED: raise ValueError('Archive too large')
            for entry in items:
                name=PurePosixPath(entry.filename)
                if name.is_absolute() or not name.parts or name.parts[0]!='nexen-main' or any(p in ('..','.') for p in name.parts) or '\\' in entry.filename:
                    raise ValueError('Invalid archive path')
                if stat.S_ISLNK(entry.external_attr >> 16): raise ValueError('Archive symlinks are not allowed')
                rel=name.parts[1:]
                if not rel: continue
                out=staged.joinpath(*rel)
                if entry.is_dir(): out.mkdir(parents=True,exist_ok=True);continue
                out.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(entry) as source, out.open('xb') as dest: shutil.copyfileobj(source,dest)
                if os.name!='nt' and entry.external_attr >> 16 & 0o111: out.chmod(0o755)
        for item in REQUIRED:
            if not (staged/item).is_file(): raise ValueError('Update is incomplete: missing '+item)
        for item in ('nexen.py','isolated.py','updater.py','identity.py'):
            ast.parse((staged/item).read_text(encoding='utf-8'),filename=item)
        # Keep rollback outside the temporary directory so a failed restore is
        # never removed by TemporaryDirectory cleanup.
        backup=Path(tempfile.mkdtemp(prefix='.nexen-previous-',dir=target.parent))
        backup.rmdir()
        os.rename(target,backup)
        try: os.rename(staged,target)
        except BaseException as original:
            try: os.rename(backup,target)
            except OSError as restore_error:
                raise RuntimeError('Could not restore the previous install. Your files are saved at '+str(backup)+': '+str(restore_error)) from original
            raise
        try: shutil.rmtree(backup)
        except OSError: print('Old installation retained at '+str(backup))
