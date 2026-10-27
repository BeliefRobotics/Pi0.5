#!/usr/bin/env bash
set -euo pipefail
BASE="${PI05_INSTALL_DIR:-$HOME/pi05/ckpt3000}"
if [ ! -x "$BASE/venv/bin/python" ]; then echo 'Run 01_install.cmd first.'; exit 1; fi
cd "$BASE"
mkdir -p reports cache/openpi/big_vision cache/jax
cp model/tokenizer/paligemma_tokenizer.model cache/openpi/big_vision/paligemma_tokenizer.model
export PI05_HOME="$BASE"
export OPENPI_DATA_HOME="$BASE/cache/openpi"
export JAX_PLATFORMS=cuda
export XLA_PYTHON_CLIENT_PREALLOCATE=false
export JAX_COMPILATION_CACHE_DIR="$BASE/cache/jax"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export PYTHONUNBUFFERED=1
"$BASE/venv/bin/python" diagnose.py --gpu-only
exec 9>server.lock
if ! flock -n 9; then echo 'This model service is already running. Check http://127.0.0.1:8796/health'; exit 1; fi
echo $$ > server.pid
echo 'First startup compiles the model. Wait for READY before sending a task. Ctrl+C stops inference only.'
exec "$BASE/venv/bin/python" inference_server.py
