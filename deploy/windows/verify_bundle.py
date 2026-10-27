"""Check all immutable bundle files using the shipped SHA-256 manifest."""
import hashlib,json,sys
from pathlib import Path,PurePosixPath
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def safe_file(root,rel):
    p=PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts or '\\' in rel:raise ValueError('Unsafe manifest path')
    target=root.joinpath(*p.parts).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('Path escapes bundle')
    return target
def main():
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
    manifest=json.loads((root/'bundle_manifest.json').read_text(encoding='utf-8'))
    rows=manifest['files']
    for i,row in enumerate(rows,1):
        path=safe_file(root,row['path'])
        if not path.is_file() or path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
            raise SystemExit('CHECKSUM FAILED: '+row['path'])
        print(f'[{i}/{len(rows)}] OK {row["path"]}',flush=True)
    print('All bundle files verified.')
if __name__=='__main__':main()
