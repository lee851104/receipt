"""Offline frozen CLS embeddings and a validated, non-pickle feature cache."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import zipfile

# Set before transformers imports. This module never downloads a model or sends text.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import numpy as np

from common import fingerprint
from prepare_data import normalize


def local_manifest(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "encoder-manifest.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if not {"config.json", "model.safetensors", "tokenizer_config.json"} <= set(files):
        raise ValueError("Encoder manifest is incomplete")
    if not {"tokenizer.json", "vocab.txt"} & set(files):
        raise ValueError("Encoder tokenizer is missing")
    for name, expected in files.items():
        path = (directory / name).resolve()
        if path.parent != directory or not path.is_file() or fingerprint(path) != expected:
            raise ValueError("Local encoder failed integrity verification")
    # Reject unmanifested tokenizer/model configuration that could change loading.
    actual = {p.name for p in directory.iterdir()
              if p.is_file() and p.suffix in {".json", ".txt", ".safetensors", ".bin"}
              and p.name != "encoder-manifest.json"}
    if actual - set(files):
        raise ValueError("Encoder has unverified configuration or weight files")
    return manifest


class FrozenEncoder:
    def __init__(self, directory, batch_size=16, max_length=512, threads=1):
        if batch_size < 1 or not 2 <= max_length <= 512 or threads < 1:
            raise ValueError("Invalid encoder settings")
        self.directory = Path(directory).resolve()
        manifest = local_manifest(self.directory)
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_num_threads(threads)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.directory, local_files_only=True, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(
            self.directory, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, attn_implementation="eager")
        self.model.to(device="cpu", dtype=torch.float32)
        self.model.eval()
        self.model.requires_grad_(False)
        self.dimension = self.model.config.hidden_size
        self.batch_size, self.max_length = batch_size, max_length
        self.identity = dict(**manifest, pooling="cls", normalize=True,
                             max_length=max_length, batch_size=batch_size, threads=threads,
                             prefix="", dtype="float32", attention="eager", device="cpu",
                             dimension=self.dimension,
                             versions={name: importlib.metadata.version(name) for name in
                                       ("torch", "transformers", "tokenizers", "safetensors", "numpy")})

    @property
    def model_bytes(self):
        return sum((self.directory / name).stat().st_size for name in self.identity["files"])

    def encode(self, names):
        import torch
        names = [normalize(name) for name in names]
        if not names:
            return np.empty((0, self.dimension), dtype=np.float32)
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(names), self.batch_size):
                tokens = self.tokenizer(names[start:start + self.batch_size], padding=True,
                                        truncation=True, max_length=self.max_length,
                                        return_tensors="pt")
                output = self.model(**tokens).last_hidden_state[:, 0]
                vectors.append(torch.nn.functional.normalize(output, p=2, dim=1).cpu().numpy())
        return np.concatenate(vectors).astype(np.float32, copy=False)


def cached_encode(encoder, names, path):
    names = [normalize(name) for name in names]
    key = hashlib.sha256(json.dumps(dict(names=names, encoder=encoder.identity),
                                    sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    path = Path(path)
    if path.suffix.lower() != ".npz":
        raise ValueError("Use a dedicated .npz file for the embedding cache")
    if path.exists():
        with path.open("rb") as stream:
            if stream.read(4) != b"PK\x03\x04":
                raise ValueError("Refusing to overwrite a file that is not an NPZ cache")
        try:
            with path.open("rb") as stream, np.load(stream, allow_pickle=False) as saved:
                metadata = json.loads(str(saved["metadata"]))
                values = saved["vectors"]
            if (metadata["key"] == key and values.dtype == np.float32
                    and values.shape == (len(names), encoder.dimension)
                    and np.isfinite(values).all()
                    and hashlib.sha256(values.tobytes()).hexdigest() == metadata["vectors_sha256"]):
                return values, True
        except (ValueError, KeyError, OSError, EOFError, zipfile.BadZipFile):
            pass
    values = encoder.encode(names)
    if values.shape != (len(names), encoder.dimension) or not np.isfinite(values).all():
        raise ValueError("Encoder returned invalid vectors")
    metadata = dict(key=key, vectors_sha256=hashlib.sha256(values.tobytes()).hexdigest())
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(stream, vectors=values, metadata=json.dumps(metadata))
    temporary.replace(path)
    return values, False
