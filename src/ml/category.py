"""CPU BERT service adapter. No training imports, downloads, or item persistence.

load(model_dir) verifies the local bundle and returns a thread-safe callable.
The caller owns lifecycle: load once at startup; restart after model replacement.
"""
import hashlib
import json
import math
from pathlib import Path
import threading
import unicodedata

CATEGORIES = ("正餐", "飲品", "零食甜點", "生鮮食材", "運動", "其他服務",
              "交通", "住宿", "日用品", "電子產品")
_ALLOWED = {"config.json", "model.safetensors", "tokenizer_config.json",
            "tokenizer.json", "vocab.txt", "special_tokens_map.json", "added_tokens.json"}
_REQUIRED = {"config.json", "model.safetensors", "tokenizer_config.json"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verified_manifest(directory):
    """Strict file whitelist and hashes; the manifest must come from a trusted release."""
    root = Path(directory).resolve()
    manifest = root / "classifier-manifest.json"
    if manifest.is_symlink():
        raise ValueError("invalid_manifest")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    files = metadata.get("files")
    if (metadata.get("format_version") != "bert-category-1"
            or metadata.get("categories") != list(CATEGORIES)
            or not isinstance(files, dict)
            or not _REQUIRED <= files.keys() <= _ALLOWED
            or not {"tokenizer.json", "vocab.txt"} & files.keys()
            or type(metadata.get("max_length")) is not int
            or not 2 <= metadata["max_length"] <= 512):
        raise ValueError("invalid_manifest")
    actual = {p.name for p in root.iterdir() if p.is_file() and p.name != manifest.name}
    if actual != set(files):
        raise ValueError("unverified_files")
    for name, expected in files.items():
        path = root / name
        if (path.is_symlink() or path.resolve().parent != root
                or not isinstance(expected, str) or digest(path) != expected):
            raise ValueError("file_integrity_failed")
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    if (config.get("model_type") != "bert"
            or config.get("id2label") != {str(i): name for i, name in enumerate(CATEGORIES)}):
        raise ValueError("invalid_label_mapping")
    return metadata


def _dependencies():
    # Keep fake mode and ordinary API tests independent of the optional ML stack.
    import torch
    from transformers import AutoTokenizer, BertForSequenceClassification
    return torch, AutoTokenizer, BertForSequenceClassification


def load(model_dir, *, batch_size=16, threads=1):
    """Return classify(names); invalid bundle or dependencies raise a sanitized error."""
    try:
        if type(batch_size) is not int or batch_size < 1 or type(threads) is not int or threads < 1:
            raise ValueError("invalid_inference_settings")
        root = Path(model_dir).resolve()
        metadata = verified_manifest(root)
        torch, tokenizer_type, model_type = _dependencies()
        torch.set_num_threads(threads)
        tokenizer = tokenizer_type.from_pretrained(root, local_files_only=True, trust_remote_code=False)
        model, info = model_type.from_pretrained(
            root, local_files_only=True, trust_remote_code=False, use_safetensors=True,
            attn_implementation="eager", output_loading_info=True)
        if (any(info.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs"))
                or model.config.num_labels != 10 or model.config.model_type != "bert"
                or model.config.id2label != dict(enumerate(CATEGORIES))):
            raise ValueError("incomplete_or_invalid_checkpoint")
        model = model.to(device="cpu", dtype=torch.float32).eval()
        # Detect file replacement during startup before publishing the callable.
        if verified_manifest(root) != metadata:
            raise ValueError("bundle_changed_during_load")
        return _Classifier(model, tokenizer, torch, metadata["max_length"], batch_size)
    except Exception:
        # Do not attach third-party exception text: it can contain inputs or local paths.
        raise RuntimeError("category_model_unavailable") from None


class _Classifier:
    def __init__(self, model, tokenizer, torch, max_length, batch_size):
        self.model, self.tokenizer, self.torch = model, tokenizer, torch
        self.max_length, self.batch_size = max_length, batch_size
        self.lock = threading.Lock()

    def __call__(self, names):
        if not isinstance(names, list) or any(not isinstance(n, str) or not n.strip() for n in names):
            raise ValueError("invalid_category_input")
        if not names:
            return []
        normalized = [unicodedata.normalize("NFKC", name).strip() for name in names]
        try:
            answers = []
            # Release between batches so other requests can acquire the model lock.
            # Lock fairness is implementation-dependent; this is not a latency guarantee.
            for start in range(0, len(normalized), self.batch_size):
                with self.lock, self.torch.inference_mode():
                    batch = normalized[start:start + self.batch_size]
                    tokens = self.tokenizer(batch, padding=True, truncation=True,
                                            max_length=self.max_length, return_tensors="pt")
                    rows = self.model(**tokens).logits.softmax(-1).cpu().tolist()
                    if len(rows) != len(batch):
                        raise ValueError("wrong_row_count")
                    for row in rows:
                        probs = [float(p) for p in row]
                        if (len(probs) != 10 or any(not math.isfinite(p) or not 0 <= p <= 1 for p in probs)
                                or not math.isclose(sum(probs), 1.0, abs_tol=.001)):
                            raise ValueError("invalid_probabilities")
                        answers.append({"category": max(range(10), key=probs.__getitem__), "probs": probs})
            return answers
        except Exception:
            raise RuntimeError("category_inference_failed") from None
