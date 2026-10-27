#!/usr/bin/env bash
set -euo pipefail
BASE="${PI05_INSTALL_DIR:-$HOME/pi05/ckpt3000}"
BUNDLE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$BUNDLE/results"
if [ -x "$BASE/venv/bin/python" ]; then
 "$BASE/venv/bin/python" "$BASE/diagnose.py" --check-imports || status=$?
 cp "$BASE/reports/diagnostics.json" "$BUNDLE/results/diagnostics.json"
 exit "${status:-0}"
fi
echo 'Environment is not installed yet. Checking visible hardware only.'
if command -v nvidia-smi >/dev/null; then nvidia-smi; elif [ -x /usr/lib/wsl/lib/nvidia-smi ]; then /usr/lib/wsl/lib/nvidia-smi; else echo 'No NVIDIA GPU visible in WSL.'; exit 1; fi
free -h
df -h "$HOME"
