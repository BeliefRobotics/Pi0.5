#!/usr/bin/env bash
set -euo pipefail
BASE="${PI05_INSTALL_DIR:-$HOME/pi05/ckpt3000}"
if [ ! -x "$BASE/python/bin/python3.11" ]; then echo 'This bundle is not installed.'; exit 0; fi
"$BASE/python/bin/python3.11" "$BASE/stop_service.py"
