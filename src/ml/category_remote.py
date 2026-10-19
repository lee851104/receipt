"""Fetch ONLY BERT inference files from an authenticated, immutable HF Space revision.

No training inputs, arbitrary URLs, snapshot of the whole Space, or remote code.
The local cache is temporary and is removed with the staging directory.
"""
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .category import CATEGORIES, _ALLOWED, _REQUIRED, digest, verified_manifest

ENDPOINT = "https://huggingface.co"


def local_token():
    """Token stays in process memory; errors and logs must never contain its value."""
    secret_file = os.environ.get("HF_TOKEN_FILE", "").strip()
    if secret_file:
        return Path(secret_file).read_text(encoding="utf-8").strip()
    from huggingface_hub import get_token
    return get_token()


def validate_source(repo_id, revision, expected_sha256):
    if (not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repo_id)
            or ".." in repo_id or not re.fullmatch(r"[0-9a-f]{40}", revision)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
        raise ValueError("invalid_pinned_source")


def service_manifest(document, expected_sha256):
    spec = document["models"]["bert"]
    remote = spec["files"]
    if document["format"] != "category-demo-1" or document["categories"] != list(CATEGORIES):
        raise ValueError("invalid_remote_manifest")
    if not isinstance(remote, dict) or any(not name.startswith("bert/") for name in remote):
        raise ValueError("invalid_remote_files")
    files = {name.removeprefix("bert/"): value for name, value in remote.items()}
    if (not _REQUIRED <= files.keys() <= _ALLOWED
            or not {"tokenizer.json", "vocab.txt"} & files.keys()
            or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}",v) for v in files.values())
            or files["model.safetensors"] != expected_sha256
            or type(spec["max_length"]) is not int or not 2 <= spec["max_length"] <= 512):
        raise ValueError("invalid_remote_files")
    return dict(format_version="bert-category-1", categories=list(CATEGORIES),
                max_length=spec["max_length"], files=files)


def download_space_model(*, repo_id, revision, destination, expected_sha256, token=None, fetch=None):
    """Return downloaded/present. Existing incomplete or unrelated directories are never overwritten."""
    try:
        validate_source(repo_id, revision, expected_sha256)
        destination = Path(destination).absolute()
        if destination.is_symlink():
            raise ValueError("destination_symlink")
        if destination.exists():
            verified_manifest(destination)
            if digest(destination/"model.safetensors") != expected_sha256:
                raise ValueError("different_model")
            return "present"
        token = local_token() if token is None else token
        if not isinstance(token, str) or not token.strip():
            raise ValueError("missing_credential")
        if fetch is None:
            from huggingface_hub import hf_hub_download
            fetch = hf_hub_download
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".category-download-", dir=destination.parent) as tmp:
            staging = Path(tmp)
            def fetch_file(filename):
                return Path(fetch(repo_id=repo_id, repo_type="space", revision=revision, filename=filename,
                                  endpoint=ENDPOINT, token=token, cache_dir=str(staging/"cache"),
                                  force_download=True, local_files_only=False))
            manifest_path = fetch_file("models/manifest.json")
            if manifest_path.stat().st_size > 1_000_000:
                raise ValueError("manifest_too_large")
            metadata = service_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), expected_sha256)
            release = staging/"release"; release.mkdir()
            for name, expected in metadata["files"].items():
                fetched = fetch_file("models/bert/"+name)
                target = release/name
                shutil.copyfile(fetched, target)
                if digest(target) != expected:
                    raise ValueError("download_integrity_failed")
            (release/"classifier-manifest.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            verified_manifest(release)
            if destination.exists():
                raise FileExistsError("destination_exists")
            release.rename(destination)
        return "downloaded"
    except Exception:
        raise RuntimeError("category_download_failed") from None
