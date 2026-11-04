#!/bin/sh
set -eu
command -v python3 >/dev/null || { echo 'Python 3.9+ is required.' >&2; exit 1; }
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
curl -fsSL https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.py -o "$tmp/install.py"
python3 "$tmp/install.py"
