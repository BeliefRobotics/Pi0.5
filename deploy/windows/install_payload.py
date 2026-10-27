"""Install the verified payload without removing existing user results."""
import hashlib,json,shutil,sys
from pathlib import Path
from verify_bundle import digest,safe_file
source=Path(sys.argv[1]).resolve();target=Path(sys.argv[2]).resolve()
target.mkdir(parents=True,exist_ok=True)
manifest=json.loads((source/'bundle_manifest.json').read_text())
for row in manifest['files']:
    name=row['path']
    if name.startswith('bootstrap/') or name.endswith(('.cmd','.ps1')):continue
    src=safe_file(source,name);dst=safe_file(target,name)
    if dst.exists() and dst.stat().st_size==row['bytes'] and digest(dst)==row['sha256']:continue
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    if digest(dst)!=row['sha256']:raise SystemExit('Copy checksum failed: '+name)
shutil.copy2(source/'bundle_manifest.json',target/'bundle_manifest.json')
print('Payload installed and verified:',target)
