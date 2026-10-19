"""Install a trusted local BERT bundle into a NEW directory, never overwrite.

python -m scripts.install_category_model --source ... --destination ... --sha256 ...
Only inference fields/files are copied; no training dataset is an input.
"""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from src.ml.category import digest, verified_manifest

def install(source, destination, expected_sha256):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("destination_exists")
    if destination == source or destination.is_relative_to(source):
        raise ValueError("destination_inside_source")
    metadata = verified_manifest(source)
    if digest(source / "model.safetensors") != expected_sha256:
        raise ValueError("unexpected_model_revision")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".category-install-", dir=destination.parent) as staging:
        release = Path(staging) / "model"
        release.mkdir()
        for name in metadata["files"]:
            shutil.copyfile(source / name, release / name)
        safe = {key:metadata[key] for key in ("format_version","categories","max_length","files")}
        (release / "classifier-manifest.json").write_text(json.dumps(safe,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        verified_manifest(release)
        if digest(release / "model.safetensors") != expected_sha256:
            raise ValueError("model_changed_during_copy")
        if destination.exists():
            raise FileExistsError("destination_exists")
        release.rename(destination)
    return {"model_sha256":expected_sha256,"files":len(safe["files"])+1,
            "manifest_sha256":digest(destination/"classifier-manifest.json")}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--destination",type=Path,required=True)
    p.add_argument("--sha256",required=True)
    a=p.parse_args()
    try: print(json.dumps(install(a.source,a.destination,a.sha256)))
    except Exception:p.exit(1,"Category installation failed; no private details printed.\n")
if __name__=="__main__":main()
