"""Update an installer-managed Nexen tree without touching the state directory."""
import ast, io, json, os, re, shutil, stat, tempfile, urllib.request, urllib.error, zipfile
from urllib.parse import quote
from pathlib import Path, PurePosixPath

RELEASES_URL='https://api.github.com/repos/aswartzlander2-sys/nexen/releases'
ARCHIVE_URL='https://github.com/aswartzlander2-sys/nexen/archive/refs/tags/'
MAX_DOWNLOAD=50 * 1024 * 1024
MAX_UNPACKED=150 * 1024 * 1024
REQUIRED=('nexen.py','isolated.py','updater.py','identity.py','index.html','assets/js/config.js','README.md')

# Stable updates exclude B and E. Preview updates opt in to either B or E.
def version_key(tag):
    m=re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)([BE]?)',tag)
    if not m: return None
    stage={'E':0,'B':1,'':2}[m.group(4)]
    return tuple(int(m.group(i)) for i in range(1,4))+(stage,)

def find_update(current, beta=False):
    cur=version_key(current)
    if cur is None: raise ValueError('Unrecognised installed version: '+current)
    releases=[]
    for page in range(1,11):
        req=urllib.request.Request(RELEASES_URL+'?per_page=100&page='+str(page),headers={'Accept':'application/vnd.github+json','User-Agent':'Nexen-Updater/3.2.4'})
        with urllib.request.urlopen(req,timeout=30) as r:
            raw=r.read(5*1024*1024+1)
        if len(raw)>5*1024*1024: raise ValueError('GitHub release listing is too large')
        batch=json.loads(raw)
        if not isinstance(batch,list): raise ValueError('Invalid GitHub release response')
        releases.extend(batch)
        if len(batch)<100: break
    else: raise ValueError('Too many GitHub releases to check safely')
    choices=[]
    for release in releases:
        if not isinstance(release,dict) or release.get('draft'): continue
        tag=release.get('tag_name')
        if not isinstance(tag,str): continue
        key=version_key(tag)
        if key is None or key<=cur: continue
        if beta:
            if not tag.endswith(('B','E')): continue
        elif tag.endswith(('B','E')) or release.get('prerelease'): continue
        choices.append((key,tag))
    return max(choices)[1] if choices else None

def branch_candidate(branch, beta=False):
    """Pin the branch to its commit; read the version at that same commit."""
    req=urllib.request.Request('https://api.github.com/repos/aswartzlander2-sys/nexen/git/ref/heads/'+branch,headers={'Accept':'application/vnd.github+json','User-Agent':'Nexen-Updater/3.2.4'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: raw=r.read(1024*1024+1)
    except urllib.error.HTTPError as e:
        if e.code == 404 and beta: return None
        raise
    if len(raw)>1024*1024: raise ValueError('Commit response is too large')
    sha=json.loads(raw).get('object',{}).get('sha','')
    if not re.fullmatch(r'[0-9a-f]{40}',sha): raise ValueError('Invalid branch commit')
    req=urllib.request.Request('https://raw.githubusercontent.com/aswartzlander2-sys/nexen/'+sha+'/identity.py',headers={'User-Agent':'Nexen-Updater/3.2.4'})
    with urllib.request.urlopen(req,timeout=30) as r: source=r.read(65537)
    if len(source)>65536: raise ValueError('Version file is too large')
    tree=ast.parse(source.decode('utf-8'))
    versions=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)]
    if len(versions)!=1 or version_key(versions[0]) is None: raise ValueError('Invalid version on '+branch)
    version=versions[0]
    if beta != version.endswith(('B','E')): return None
    return {'version':'v'+version,'sha':sha,'branch':branch}

def find_best_update(current, beta=False):
    tag=find_update(current,beta=beta)
    candidates=[{'version':tag,'sha':None,'branch':None}] if tag else []
    branch=branch_candidate('experimental' if beta else 'main',beta=beta)
    if branch and version_key(branch['version'])>version_key(current): candidates.append(branch)
    return max(candidates,key=lambda c: (version_key(c['version']), not c['sha'])) if candidates else None

def download_candidate(candidate):
    if not candidate['sha']: return download(candidate['version'])
    sha=candidate['sha']
    if not re.fullmatch(r'[0-9a-f]{40}',sha): raise ValueError('Invalid commit')
    req=urllib.request.Request('https://codeload.github.com/aswartzlander2-sys/nexen/zip/'+sha,headers={'User-Agent':'Nexen-Updater/3.2.4'})
    with urllib.request.urlopen(req,timeout=60) as r: data=r.read(MAX_DOWNLOAD+1)
    if len(data)>MAX_DOWNLOAD: raise ValueError('Download exceeds 50 MB')
    return data

def install_root():
    if os.name == 'nt':
        local=os.environ.get('LOCALAPPDATA')
        if not local: raise RuntimeError('LOCALAPPDATA is not set')
        return Path(local)/'Nexen'/'app'
    return Path.home()/'.local'/'share'/'nexen'

def download(tag):
    if version_key(tag) is None: raise ValueError('Invalid release tag')
    request=urllib.request.Request(ARCHIVE_URL+quote(tag,safe='')+'.zip',headers={'User-Agent':'Nexen-Updater/3.2.4'})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read(MAX_DOWNLOAD+1)
    if len(data)>MAX_DOWNLOAD: raise ValueError('Download exceeds 50 MB')
    return data

def apply_archive(data,target,state,expected_version=None):
    target=Path(target).resolve();state=Path(state).resolve()
    if target == state or target in state.parents:
        raise ValueError('State directory is inside the installation; refusing to update')
    if not target.is_dir(): raise ValueError('Installation directory is missing')
    with tempfile.TemporaryDirectory(prefix='.nexen-update-',dir=target.parent) as temp:
        temp=Path(temp); staged=temp/'new';staged.mkdir()
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items=archive.infolist()
            if len(items)>10000 or sum(i.file_size for i in items)>MAX_UNPACKED: raise ValueError('Archive too large')
            archive_root=None
            for entry in items:
                name=PurePosixPath(entry.filename)
                if name.is_absolute() or not name.parts or not name.parts[0].startswith('nexen-') or any(p in ('..','.') for p in name.parts) or '\\' in entry.filename:
                    raise ValueError('Invalid archive path')
                if archive_root is None: archive_root=name.parts[0]
                elif archive_root != name.parts[0]: raise ValueError('Archive has multiple top-level directories')
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
        if expected_version is not None and version_key(expected_version) >= (3,0,0,0) and not (staged/'origin-ui/index.html').is_file(): raise ValueError('Update is incomplete: missing origin-ui/index.html')
        if expected_version is not None and version_key(expected_version) >= (3,1,0,0) and (not (staged/'assets/app/nx-app.js').is_file() or 'assets/app/nx-app.js' not in (staged/'index.html').read_text(encoding='utf-8')): raise ValueError('Update is incomplete: missing the root Origin SPA')
        for item in ('nexen.py','isolated.py','updater.py','identity.py'):
            ast.parse((staged/item).read_text(encoding='utf-8'),filename=item)
        if expected_version is not None:
            tree=ast.parse((staged/'identity.py').read_text(encoding='utf-8'))
            versions=[n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)]
            if versions != [expected_version.removeprefix('v')]: raise ValueError('Release tag and bundled version do not match')
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
