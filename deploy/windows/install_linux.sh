#!/usr/bin/env bash
set -euo pipefail
BUNDLE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BASE="${PI05_INSTALL_DIR:-$HOME/pi05/ckpt3000}"
INDEX="${PI05_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple}"
if [ "$(uname -m)" != x86_64 ]; then echo 'This bundle requires x86_64 Linux/WSL2.'; exit 1; fi
echo "Install directory: $BASE"
echo 'Model files and dependencies need approximately 20 GB; allow at least 35 GB free.'
mkdir -p "$BASE/python" "$BASE/reports" "$BASE/cache"
cd "$BUNDLE/bootstrap"
sha256sum -c python-runtime.sha256
if [ ! -x "$BASE/python/bin/python3.11" ]; then
 tar -xzf python-3.11.17-linux-x86_64.tar.gz -C "$BASE/python"
fi
PY="$BASE/python/bin/python3.11"
"$PY" "$BUNDLE/verify_bundle.py" "$BUNDLE"
"$PY" "$BUNDLE/install_payload.py" "$BUNDLE" "$BASE"
"$PY" -m venv "$BASE/tools"
"$BASE/tools/bin/python" -m pip install --index-url "$INDEX" 'uv==0.13.5'
UV="$BASE/tools/bin/uv"
export UV_CACHE_DIR="$BASE/cache/uv"
export UV_INDEX_URL="$INDEX"
if [ ! -x "$BASE/venv/bin/python" ]; then "$UV" venv --python "$PY" "$BASE/venv"; fi
mkdir -p "$BASE/src"
tar -xf "$BASE/model/ke_openpi_source.tar" -C "$BASE/src"
"$UV" pip install --python "$BASE/venv/bin/python" --no-deps -r "$BASE/requirements-linux.lock"
"$UV" pip install --python "$BASE/venv/bin/python" --no-deps --index-url https://download.pytorch.org/whl/cpu 'torch==2.7.1+cpu'
"$UV" pip install --python "$BASE/venv/bin/python" --no-deps -e "$BASE/src" -e "$BASE/src/packages/openpi-client"
"$BASE/venv/bin/python" "$BASE/diagnose.py" --check-imports
printf '\nInstallation finished. Use 02_start.cmd on Windows.\n'
