"""Download pinned PUBLIC model files only; this command never reads item data."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


REPO = "BAAI/bge-small-zh-v1.5"
REVISION = "7999e1d3359715c523056ef9478215996d62a620"
FILES = ("config.json", "model.safetensors", "tokenizer.json",
         "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "README.md")


def verified(path, metadata):
    if not path.is_file():
        return False
    if metadata.get("lfs"):
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest() == metadata["lfs"]["sha256"]
    contents = path.read_bytes()
    git_blob = b"blob " + str(len(contents)).encode("ascii") + b"\0" + contents
    return hashlib.sha1(git_blob).hexdigest() == metadata["blobId"]


def download(directory):
    directory = Path(directory)
    request = f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true"
    with urllib.request.urlopen(request, timeout=60) as response:
        info = json.load(response)
    if info["sha"] != REVISION:
        raise ValueError("Model revision mismatch")
    available = {entry["rfilename"]: entry for entry in info["siblings"]}
    directory.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in FILES:
        target = directory / name
        if not verified(target, available[name]):
            url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
            temporary = directory / (name + ".part")
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    stream.write(chunk)
            if not verified(temporary, available[name]):
                raise ValueError("Downloaded file failed upstream hash verification")
            temporary.replace(target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(f"Verified {name}: {target.stat().st_size} bytes", flush=True)
    manifest = dict(repo=REPO, revision=REVISION, files=hashes)
    (directory / "encoder-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    download(parser.parse_args().out)
