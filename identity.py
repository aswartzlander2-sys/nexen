"""Persistent, non-secret Nexen installation identifier."""
import os, secrets, time
from pathlib import Path

VERSION='3.1.1'

def identity_path():
    # Deliberately outside application and ordinary data directories so a
    # normal reinstall/update or data removal does not delete the identifier.
    return Path(os.environ.get('NEXEN_IDENTITY_FILE', str(Path.home()/'.nexen-identity'))).expanduser()

def valid(value):
    return len(value)==6 and all('0' <= c <= '9' for c in value)

def get_id():
    path=identity_path(); path.parent.mkdir(parents=True,exist_ok=True)
    try:
        fd=os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Another process may be finishing its initial write.
        for _ in range(40):
            value=path.read_text(encoding='ascii').strip()
            if valid(value): return value
            if value: break
            time.sleep(.05)
        raise ValueError('Invalid or empty Nexen identity file: '+str(path)+'; restore it from a backup or remove it to generate a new ID.')
    try:
        value=f'{secrets.randbelow(1000000):06d}'
        with os.fdopen(fd,'w',encoding='ascii') as f:
            f.write(value+'\n'); f.flush(); os.fsync(f.fileno())
        return value
    except BaseException:
        # Do not overwrite an existing identifier on subsequent calls.
        try: path.unlink()
        except OSError: pass
        raise
