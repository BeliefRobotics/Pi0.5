"""Read-only GPU/environment diagnostics, with an exportable report."""
import argparse,json,os,platform,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--check-imports',action='store_true');p.add_argument('--gpu-only',action='store_true');a=p.parse_args()
result={'python':sys.version,'platform':platform.platform(),'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'errors':[],'warnings':[]}
binary=shutil.which('nvidia-smi')
if not binary and Path('/usr/lib/wsl/lib/nvidia-smi').exists():binary='/usr/lib/wsl/lib/nvidia-smi'
if binary:
    r=subprocess.run([binary,'--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True)
    result['nvidia_smi']=r.stdout.strip()
    if r.returncode:result['errors'].append(r.stderr.strip())
    else:
        fields=r.stdout.splitlines()[0].split(',')
        total=float(fields[1]);free=float(fields[2]);result['vram_total_mib']=total;result['vram_free_mib']=free
        if total<11000:result['warnings'].append('Below 12 GB VRAM: full-model inference is unlikely to fit. No automatic CPU fallback.')
        elif total<22000:result['warnings'].append('12-16 GB VRAM is unverified. Allocation grows on demand; this does not guarantee the model fits.')
        if free<10000:result['warnings'].append('Less than 10 GB VRAM free; close other GPU applications before inference.')
else:result['errors'].append('NVIDIA GPU is not visible. Update the Windows NVIDIA driver and use WSL2.')
if Path('/proc/meminfo').exists():
    mem={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}
    result['wsl_memory_gib']=round(mem['MemTotal']/2**20,2)
    if mem['MemTotal']<20*2**20:result['warnings'].append('WSL sees less than 20 GiB RAM. Recommended: >=32 GB host RAM and >=24 GB assigned to WSL.')
result['disk_free_gib']=round(shutil.disk_usage(ROOT).free/2**30,2)
if a.check_imports:
    try:
        import jax
        result['jax_version']=jax.__version__;result['jax_devices']=[str(x) for x in jax.devices()]
        if not any(x.platform=='gpu' for x in jax.devices()):result['errors'].append('JAX did not find a GPU.')
        import inference_server
        result['model_import_ok']=True
    except Exception as e:result['errors'].append(type(e).__name__+': '+str(e))
path=ROOT/'reports/diagnostics.json';path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if result['errors']:raise SystemExit(1)
