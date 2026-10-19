"""Build a reproducible source-only acceptance context; never copy private data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--context',type=Path,required=True,help='New directory for tracked source files only')
parser.add_argument('--image',required=True)
parser.add_argument('--docker',default=shutil.which('docker') or 'docker')
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
context=args.context.resolve()
if context.exists(): parser.error('--context must not already exist')
paths=subprocess.check_output(['git','-C',str(repo),'ls-files','-z','--','Dockerfile','.dockerignore',
    'requirements.txt','requirements-docker.txt','configs','src']).decode().split('\0')
selected=[]
for name in filter(None,paths):
    path=Path(name)
    if name.startswith('src/web/') or path.suffix in ('.csv','.jsonl','.tsv','.db','.safetensors','.bin') or name.endswith('-data.js'): continue
    source=repo/path
    if source.is_symlink() or not source.resolve().is_relative_to(repo): raise RuntimeError('invalid_source_path')
    selected.append((name,source))
context.mkdir(parents=True)
hashes={}
for name,source in selected:
    target=context/name;target.parent.mkdir(parents=True,exist_ok=True)
    contents=source.read_bytes();target.write_bytes(contents)
    hashes[name]=hashlib.sha256(contents).hexdigest()
metadata={'source_commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
          'working_tree_dirty':bool(subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'])),
          'files':hashes,'image':args.image}
(context/'acceptance-source.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
result=subprocess.run([args.docker,'build','--pull','--progress','plain','-t',args.image,str(context)])
raise SystemExit(result.returncode)
