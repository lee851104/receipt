"""Run the committed Compose files against isolated volumes and a pinned image."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from huggingface_hub.constants import HF_TOKEN_PATH

import argparse
import shutil
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--docker', default=shutil.which('docker') or 'docker')
parser.add_argument('--image', required=True, help='Already built acceptance image; never pushed')
parser.add_argument('--out-dir', type=Path, required=True, help='Local ignored evidence directory')
parser.add_argument('--context',type=Path,required=True,help='Prepared source-only build context')
args=parser.parse_args()
repo=Path(__file__).resolve().parents[1]
data=args.out_dir.resolve(); data.mkdir(parents=True,exist_ok=True)
docker=args.docker
image=args.image
source=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
sha = '16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79'
revision = '29b655b96b4ced268bb0c3994e901c72dfd65420'
project = 'receipt-r2-compose-' + str(time.time_ns())
folder = data / project
folder.mkdir()
(folder / 'empty.env').write_text('', encoding='utf-8')
override = folder / 'acceptance.yml'
override.write_text('services:\n  app:\n    image: '+image+'\n    ports: !override\n      - "127.0.0.1::8000"\n    environment:\n      DEMO_MODE: "0"\n      ATTRIBUTES_MODEL: fake\n    labels:\n      receipt.role: 2-acceptance\n', encoding='utf-8')
env = os.environ.copy()
env.update(HF_TOKEN_FILE=HF_TOKEN_PATH, CATEGORY_MODEL_REPO='lee851104/receipt-model-lab', CATEGORY_MODEL_REVISION=revision, CATEGORY_MODEL_SHA256=sha)
base = [docker, 'compose', '--env-file', str(folder/'empty.env'), '--project-directory', str(args.context.resolve()), '-p', project, '-f', str(repo/'docker-compose.yml'), '-f', str(repo/'docker-compose.category.yml'), '-f', str(override)]
result = {'project': project, 'image': image, 'source_commit': source, 'revision': revision}

def command(args, content=None, timeout=240):
    p = subprocess.run(args, input=content, env=env, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('command_failed')
    return p.stdout.decode('utf-8').strip()

try:
    config = json.loads(command(base + ['config', '--format', 'json']))
    service = config['services']['app']
    assert service['image'] == image
    assert service['environment']['HF_TOKEN_FILE'] == '/run/secrets/hf_token'
    assert service['environment']['CATEGORY_MODEL_REVISION'] == revision
    assert service['environment']['CATEGORY_MODEL_SHA256'] == sha
    assert 'HF_TOKEN' not in service['environment']
    assert all(p['host_ip'] == '127.0.0.1' for p in service['ports'])
    assert not any(command([docker, 'volume', 'ls', '--filter', 'label=com.docker.compose.project='+project, '-q']).splitlines())
    result['fresh_volumes_before_up'] = True
    command(base + ['up', '-d', '--no-build', '--pull', 'never'])
    container = command(base + ['ps', '-q', 'app'])
    metadata = json.loads(command([docker, 'inspect', container]))[0]
    secret = [m for m in metadata['Mounts'] if m['Destination'] == '/run/secrets/hf_token']
    assert len(secret) == 1 and not secret[0]['RW']
    result['runtime_secret_readonly'] = True
    probe = (repo/'scripts/verify_category_http.py').read_bytes()
    result['http'] = json.loads(command([docker, 'exec', '-i', container, 'python', '-', 'bert'], content=probe))
    port = metadata['NetworkSettings']['Ports']['8000/tcp'][0]
    assert port['HostIp'] == '127.0.0.1'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:'+port['HostPort']+'/api/health', timeout=20) as response:
        assert response.status == 200 and json.loads(response.read())['models']['category'] == 'bert'
    result['host_loopback_health'] = 200
    check = "import json; from pathlib import Path; from src.ml.category import digest,verified_manifest; p=Path('/models/category'); verified_manifest(p); print(json.dumps({'sha256':digest(p/'model.safetensors'),'model_files':len(list(p.iterdir())),'hf_cache_token_exists':Path('/root/.cache/huggingface/token').exists()}))"
    result['model'] = json.loads(command([docker, 'exec', container, 'python', '-c', check]))
    assert result['model']['sha256'] == sha and not result['model']['hf_cache_token_exists']
    result['status'] = 'passed'
except Exception as error:
    result['status'] = 'failed'
    result['error_type'] = type(error).__name__
finally:
    subprocess.run(base + ['stop'], env=env, capture_output=True, timeout=40)
    (folder/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    print('evidence='+str(folder/'result.json'))
if result['status'] != 'passed':
    raise SystemExit(1)
