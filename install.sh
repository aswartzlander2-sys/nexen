#!/bin/sh
set -eu
command -v python3 >/dev/null || { echo 'Python 3.9+ is required.' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
base="${HOME}/.local/share/nexen"; bin="${HOME}/.local/bin"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
curl -fsSL https://github.com/aswartzlander2-sys/nexen/archive/refs/heads/main.zip -o "$tmp/repo.zip"
python3 - "$tmp" <<'PY'
import sys, zipfile
from pathlib import Path
z=zipfile.ZipFile(Path(sys.argv[1])/'repo.zip')
root=Path(sys.argv[1]).resolve()
for item in z.infolist():
    if not (root/item.filename).resolve().is_relative_to(root): raise SystemExit('Unsafe archive path')
z.extractall(root)
PY
mkdir -p "$bin" "$(dirname "$base")"
rm -rf "$base"; mv "$tmp/nexen-main" "$base"
printf '#!/bin/sh\nexec python3 "%s/nexen.py" "$@"\n' "$base" > "$bin/nexen"
chmod +x "$bin/nexen"
echo "Installed. Add $bin to PATH if necessary, then run: nexen start"
