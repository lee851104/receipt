import json
from pathlib import Path
import subprocess
from huggingface_hub.constants import HF_TOKEN_PATH

import argparse
import shutil
parser=argparse.ArgumentParser(description='Local-only credential/volume audit; prints counts, never token values.')
parser.add_argument('--docker',default=shutil.which('docker') or 'docker')
parser.add_argument('--image',required=True)
parser.add_argument('--container',action='append',required=True,help='Stopped acceptance container; repeat for each')
parser.add_argument('--model-volume',required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
if args.out.exists(): parser.error('--out must be a new file')
docker=args.docker
image=args.image
token = Path(HF_TOKEN_PATH).read_bytes().strip()
assert token

def run(*args):
    p = subprocess.run([docker, *args], capture_output=True, timeout=90)
    assert p.returncode == 0
    return p.stdout

containers=args.container
result = {'containers_checked': len(containers), 'token_matches_logs_inspect_history': 0, 'running_acceptance_containers': 0}
for container in containers:
    logs = subprocess.run([docker,'logs',container],capture_output=True,timeout=30)
    assert logs.returncode == 0
    metadata = run('inspect',container)
    result['token_matches_logs_inspect_history'] += sum(token in data for data in [logs.stdout, logs.stderr, metadata])
    info = json.loads(metadata)[0]
    result['running_acceptance_containers'] += int(info['State']['Running'])
result['token_matches_logs_inspect_history'] += int(token in run('image','history','--no-trunc',image))
assert result['token_matches_logs_inspect_history'] == 0
assert result['running_acceptance_containers'] == 0
code = "from pathlib import Path; import json; from src.ml.category import verified_manifest; p=Path('/models/category'); m=verified_manifest(p); actual={x.relative_to(Path('/models')).as_posix() for x in Path('/models').rglob('*') if x.is_file()}; expected={'category/'+x for x in m['files']}|{'category/classifier-manifest.json'}; assert actual==expected; assert list(Path('/models').iterdir())==[p]; print(json.dumps({'files':len(actual),'only_verified_inference_files':True}))"
result['remote_volume'] = json.loads(run('run','--rm','--network','none','--mount','type=volume,src='+args.model_volume+',dst=/models,readonly','--entrypoint','python',image,'-c',code))
result['status']='passed'
output=args.out
output.parent.mkdir(parents=True,exist_ok=True)
assert not output.exists()
output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
