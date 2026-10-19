"""Local orchestration for isolated role-2 acceptance. Never reads datasets."""
import json
from pathlib import Path
import subprocess
import sys
import time

import argparse
import shutil
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--docker', default=shutil.which('docker') or 'docker')
parser.add_argument('--image', required=True, help='Already built acceptance image; never pushed')
parser.add_argument('--out-dir', type=Path, required=True, help='Local ignored evidence directory')
parser.add_argument('mode', choices=['noauth','local','remote'])
parser.add_argument('--model-dir', type=Path, help='Verified inference bundle for local mode only')
options=parser.parse_args()
if options.mode == 'local' and options.model_dir is None: parser.error('local requires --model-dir')
DOCKER=options.docker
ROOT=options.out_dir.resolve(); ROOT.mkdir(parents=True,exist_ok=True)
REPO=Path(__file__).resolve().parents[1]
IMAGE=options.image
SOURCE=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
SHA = "16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79"
REV = "29b655b96b4ced268bb0c3994e901c72dfd65420"
mode = options.mode
assert mode in ("noauth", "local", "remote")
ident = "receipt-r2-" + mode + "-" + str(time.time_ns())
data_volume, model_volume = ident + "-data", ident + "-models"
probe = (REPO / "scripts/verify_category_http.py").read_bytes()
result = {"mode": mode, "name": ident, "source_commit": SOURCE, "original_test_accessed": False}
names = []

def docker(*args, content=None, timeout=240):
    p = subprocess.run([DOCKER, *args], input=content, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError("docker_command_failed:" + args[0])
    return p.stdout.decode("utf-8").strip()

def start(name, offline=False):
    args = ["run", "-d", "--name", name, "--label", "receipt.role=2-acceptance", "--mount", "type=volume,src=" + data_volume + ",dst=/data"]
    if mode == "local":
        args += ["--mount", "type=bind,src=" + str(options.model_dir.resolve()) + ",dst=/models/category,readonly"]
    else:
        args += ["--mount", "type=volume,src=" + model_volume + ",dst=/models"]
    if offline or mode == "local":
        args += ["--network", "none"]
    else:
        args += ["-p", "127.0.0.1::8000"]
    if mode == "remote" and not offline:
        from huggingface_hub.constants import HF_TOKEN_PATH
        assert Path(HF_TOKEN_PATH).is_file()
        args += ["--mount", "type=bind,src=" + HF_TOKEN_PATH + ",dst=/run/secrets/hf_token,readonly", "-e", "HF_TOKEN_FILE=/run/secrets/hf_token"]
    for value in ["CATEGORY_MODEL=bert", "ATTRIBUTES_MODEL=fake", "CATEGORY_MODEL_REPO_TYPE=space", "CATEGORY_MODEL_REPO=lee851104/receipt-model-lab", "CATEGORY_MODEL_REVISION=" + REV, "CATEGORY_MODEL_SHA256=" + SHA, "DEMO_MODE=0"]:
        args += ["-e", value]
    names.append(name)
    docker(*args, IMAGE)

def check(name):
    return json.loads(docker("exec", "-i", name, "python", "-", "unavailable" if mode == "noauth" else "bert", content=probe))

try:
    result["image_id"] = docker("image", "inspect", IMAGE, "--format", "{{.Id}}")
    docker("volume", "create", "--label", "receipt.role=2-acceptance", data_volume)
    if mode != "local":
        docker("volume", "create", "--label", "receipt.role=2-acceptance", model_volume)
    start(ident)
    result["http"] = check(ident)
    if mode == "noauth":
        check_code = "from pathlib import Path; import json; p=Path('/models'); print(json.dumps({'model_files':len(list(p.rglob('*')))}))"
        result["model_volume"] = json.loads(docker("exec", ident, "python", "-c", check_code))
        assert result["model_volume"]["model_files"] == 0
    else:
        code = "from src.ml.category import digest,verified_manifest; import torch,json; from pathlib import Path; p=Path('/models/category'); verified_manifest(p); print(json.dumps({'sha256':digest(p/'model.safetensors'),'torch':torch.__version__,'cuda_build':torch.version.cuda}))"
        result["model"] = json.loads(docker("exec", ident, "python", "-c", code))
        assert result["model"]["sha256"] == SHA and result["model"]["cuda_build"] is None
        docker("stop", ident)
        second = ident + "-offline"
        start(second, offline=True)
        result["offline_http"] = check(second)
        assert docker("inspect", second, "--format", "{{.HostConfig.NetworkMode}}") == "none"
        mounts = json.loads(docker("inspect", second, "--format", "{{json .Mounts}}"))
        assert not any(m["Destination"] == "/run/secrets/hf_token" for m in mounts)
        result["offline_network"] = "none"
        result["offline_without_token_mount"] = True
    result["status"] = "passed"
except Exception as error:
    result["status"] = "failed"
    result["error_type"] = type(error).__name__
finally:
    for name in names:
        subprocess.run([DOCKER, "stop", name], capture_output=True, timeout=30)
    output = ROOT / (ident + ".json")
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    print("evidence=" + str(output))
if result["status"] != "passed":
    sys.exit(1)
