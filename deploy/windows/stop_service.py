"""Stop this inference process only, after validating its identity."""
import os,signal,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=BASE/'server.pid'
if not p.exists():raise SystemExit('No recorded inference PID.')
pid=int(p.read_text());proc=Path('/proc')/str(pid)
if not proc.exists():raise SystemExit('Inference process is already stopped.')
argv=(proc/'cmdline').read_bytes().split(b'\0')
cwd=(proc/'cwd').resolve()
if cwd!=BASE or b'inference_server.py' not in argv:
    raise SystemExit('PID belongs to another process; nothing stopped.')
os.kill(pid,signal.SIGTERM)
for _ in range(50):
    if not proc.exists():break
    try:
        if (proc/'stat').read_text().split(') ',1)[1].startswith('Z'):break
    except FileNotFoundError:break
    time.sleep(.1)
else:raise SystemExit('Process still exists; inspect the startup window.')
print('Inference stopped. This is not a robot emergency stop.')
