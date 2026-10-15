"""Local Qwen adapter. Database persistence belongs to the API's item_cache pipeline.

AttributeDescriber is callable and accepts an optional shared mapping keyed by
(model_version, name). Cache-only reads never wait for model inference.
"""
import hashlib
import http.client
import json
import logging
import os
from pathlib import Path
import re
import threading
import unicodedata
from urllib.parse import urlsplit

from .fields import FIELDS

PROMPT = Path(__file__).with_name("attribute-prompt.txt").read_text(encoding="utf-8")
MODEL_VERSION = "qwen3-4b:2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e:" + hashlib.sha256(PROMPT.encode()).hexdigest() + ":guards-v1:input-v2:batch1"
BOOLEAN_FIELDS = tuple(key for key in FIELDS if key not in ("sugar", "fun", "species"))
FUN = {"movie": "電影", "singing": "唱歌", "show": "展演", "game": "遊樂"}


def wire_schema(ids):
    labels = {"type": "array", "items": {"enum": list(BOOLEAN_FIELDS)}, "maxItems": len(BOOLEAN_FIELDS)}
    props = {"id": {"enum": ids}, "yes": labels, "unknown": labels,
             "sugar": {"enum": [None, 0, 0.2, 0.3, 0.5, 0.7, 1]},
             "fun": {"enum": [None, *FUN]}, "species": {"enum": [None, "cat", "dog"]}}
    item = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    return {"type": "object", "properties": {"items": {"type": "array", "items": item,
            "minItems": len(ids), "maxItems": len(ids)}}, "required": ["items"], "additionalProperties": False}


def decode(value, name):
    """Validate sparse wire fields, preserve unknowns and apply the frozen lab guards."""
    if not isinstance(value, dict) or set(value) != {"id", "yes", "unknown", "sugar", "fun", "species"}:
        raise ValueError("invalid prediction fields")
    yes, unknown = value["yes"], value["unknown"]
    if not all(isinstance(labels, list) and all(type(k) is str for k in labels) for labels in (yes, unknown)):
        raise ValueError("invalid labels")
    if len(set(yes)) != len(yes) or len(set(unknown)) != len(unknown) or set(yes) & set(unknown):
        raise ValueError("contradictory labels")
    if not (set(yes) | set(unknown)).issubset(BOOLEAN_FIELDS):
        raise ValueError("unknown labels")
    sugar, fun, species = value["sugar"], value["fun"], value["species"]
    if sugar is not None and (type(sugar) not in (int, float) or sugar not in (0, .2, .3, .5, .7, 1)):
        raise ValueError("invalid sugar")
    if fun is not None and (type(fun) is not str or fun not in FUN):
        raise ValueError("invalid fun")
    if species is not None and (type(species) is not str or species not in ("cat", "dog")):
        raise ValueError("invalid species")
    answer = {key: None if key in unknown else key in yes for key in BOOLEAN_FIELDS}
    normalized = unicodedata.normalize("NFKC", name)
    explicit = any(word in normalized for word in ("無糖", "无糖", "零分糖", "微糖", "半糖", "少糖", "全糖", "正常甜")) or re.search(r"\d+\s*分\s*糖", normalized)
    answer.update(sugar=sugar if explicit else None, fun=FUN.get(fun), species=species)
    # The public interface has names only: quantity=1 and merchant="". Never
    # cache a row's quantity-dependent inference under a name-only cache key.
    if re.search(r"\d+\s*入", name) or any(word in name for word in ("整箱", "箱裝", "家庭號", "量販包")):
        answer["bulk"] = True
    return answer


class AttributeDescriber:
    def __init__(self, server_url="http://127.0.0.1:8080", model_version=MODEL_VERSION, *, cache=None, timeout=60, batch_size=1):
        parsed = urlsplit(server_url)
        if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1", "host.docker.internal")
                or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
            raise ValueError("LLAMA_SERVER_URL must be a local HTTP server")
        self.host, self.port = parsed.hostname, parsed.port or 80
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if type(batch_size) is not int or not 1 <= batch_size <= 3:
            raise ValueError("batch_size must be between 1 and 3")
        self.batch_size = batch_size
        self.timeout = timeout
        # Batch context changes predictions, including when a caller names a custom model.
        self.model_version = re.sub(r":batch[0-9]+$", "", model_version) + f":batch{batch_size}"
        self.cache = cache if cache is not None else {}
        self._lock = threading.Lock()

    def _request(self, payload):
        # Direct connection ignores environment proxies; redirects are rejected.
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
        try:
            connection.request("POST", "/v1/chat/completions", body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                               headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise OSError("local inference unavailable")
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("oversized model response")
            return json.loads(raw)
        finally:
            connection.close()

    def _cached(self, name):
        result = self.cache.get((self.model_version, name))
        return dict(result) if result is not None else None

    def describe_items(self, names, ask_model=True):
        names = list(names)
        if not names:
            return []
        if not ask_model:
            return [self._cached(name) for name in names]
        # Queue model requests; the timeout bounds HTTP, not time waiting for a peer.
        self._lock.acquire()
        try:
            missing = list(dict.fromkeys(name for name in names if self._cached(name) is None))
            for start in range(0, len(missing), self.batch_size):
                batch = missing[start:start + self.batch_size]
                ids = [f"i{i}" for i in range(len(batch))]
                inputs = [{"id": ident, "name": name.removeprefix("示範"), "merchant": "", "quantity": 1} for ident, name in zip(ids, batch)]
                payload = {"model": "local", "messages": [{"role": "system", "content": PROMPT},
                           {"role": "user", "content": json.dumps(inputs, ensure_ascii=False)}],
                           "temperature": 0, "seed": 42, "max_tokens": 1000,
                           "chat_template_kwargs": {"enable_thinking": False},
                           "response_format": {"type": "json_schema", "json_schema": {"name": "items", "strict": True, "schema": wire_schema(ids)}}}
                try:
                    response = self._request(payload)
                    choice = response["choices"][0]
                    if choice["finish_reason"] != "stop":
                        raise ValueError("truncated response")
                    decoded = json.loads(choice["message"]["content"])
                    if not isinstance(decoded, dict) or set(decoded) != {"items"} or not isinstance(decoded["items"], list):
                        raise ValueError("invalid items")
                    records = decoded["items"]
                    if len(records) != len(ids) or any(not isinstance(x, dict) or type(x.get("id")) is not str for x in records):
                        raise ValueError("invalid IDs")
                    by_id = {x["id"]: x for x in records}
                    if set(by_id) != set(ids):
                        raise ValueError("missing or duplicate IDs")
                    results = [decode(by_id[ident], name) for ident, name in zip(ids, batch)]
                except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError, TypeError):
                    continue  # failures remain retryable, never cached as negative answers
                for name, result in zip(batch, results):
                    self.cache[(self.model_version, name)] = result
        finally:
            self._lock.release()
        return [self._cached(name) for name in names]

    __call__ = describe_items


_default = None
_INVALID_DEFAULT = object()
_LOG = logging.getLogger(__name__)
_default_lock = threading.Lock()


def describe_items(names, ask_model=True):
    """Default adapter; API integrations may instead inject an AttributeDescriber instance."""
    global _default
    names = list(names)
    if not names:
        return []
    with _default_lock:
        if _default is None:
            try:
                _default = AttributeDescriber(server_url=os.environ.get("LLAMA_SERVER_URL") or "http://127.0.0.1:8080")
            except ValueError:
                # Never log the URL: it may contain credentials or private text.
                _LOG.error("Invalid LLAMA_SERVER_URL; attribute inference disabled until process restart")
                _default = _INVALID_DEFAULT
        client = _default
    if client is _INVALID_DEFAULT:
        return [None] * len(names)
    return client.describe_items(names, ask_model=ask_model)
