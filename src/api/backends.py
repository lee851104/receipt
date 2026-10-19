"""Which category and attribute models answer, and whether the llama-server running Qwen is up."""
from dataclasses import dataclass
import http.client
import importlib.util
import logging
from pathlib import Path
import time
from typing import Callable
import urllib.request

from ..ml import fakes
from .db import ROOT

log = logging.getLogger(__name__)

REMEMBER = 5.0  # seconds a probe answer is reused; on Windows a refused local connection costs the whole timeout


@dataclass(frozen=True, kw_only=True)
class Backends:
    category: str                    # the name /api/health reports
    classify: Callable               # list[str] -> list[{"category": 0-9, "probs": [10 floats]}]
    attributes: str
    attributes_version: str          # the item_cache key: which model and prompt answered
    describe_items: Callable         # (list[str], ask_model=True) -> list[dict | None]
    gpu_probe: Callable[[], bool]    # whether the llama-server answers right now


def llama_probe(url, timeout=0.5, remember=REMEMBER):
    """A function telling whether the llama-server at url answers its /health check, reusing an answer for
    `remember` seconds. It goes straight to the server, since a system proxy would otherwise take 127.0.0.1 too."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    asked_at, answer = None, False

    def ask():
        try:
            with opener.open(url + "/health", timeout=timeout) as response:
                return response.status == 200
        # Refused, timed out, an error status (such as 503 while the model loads), not HTTP at all, or a bad URL.
        except (OSError, ValueError, http.client.HTTPException):
            return False

    def probe():
        nonlocal asked_at, answer
        now = time.monotonic()
        if asked_at is None or now - asked_at >= remember:
            asked_at, answer = now, ask()
        return answer
    return probe


def model_dir(settings):
    """The folder CATEGORY_MODEL=bert reads; a relative one starts at the repository root."""
    folder = Path(settings.category_model_dir)
    return folder if folder.is_absolute() else ROOT / folder


def unavailable_classify(names):
    raise RuntimeError("the category model is unavailable")


def category_backend(settings):
    """(name, classify) for CATEGORY_MODEL: the fake, or for bert "unavailable" while the model or src/ml/category.py
    cannot load, so the server still starts and reports unavailable."""
    if settings.category_model == "fake":
        return "fake", fakes.classify
    if settings.category_model == "bert":
        try:
            from ..ml.category import load, digest
            if settings.category_model_sha256 and digest(model_dir(settings)/"model.safetensors") != settings.category_model_sha256:
                raise ValueError("category_model_pin_mismatch")
            classify = load(model_dir(settings))
        except Exception:
            # Third-party exception text may expose local paths or private values.
            log.warning("CATEGORY_MODEL=bert could not load its verified local bundle; the category model is unavailable")
            return "unavailable", unavailable_classify
        return "bert", classify
    raise ValueError(f"CATEGORY_MODEL={settings.category_model} does not work yet; use fake or bert")


def attribute_backend(settings):
    """(name, cache key, describe_items) for ATTRIBUTES_MODEL: the fake, or role 3's Qwen (src/ml/attributes.py,
    task 4.3), imported only when asked for. Qwen gets an AttributeDescriber built from Settings.llama_server_url,
    which is the address's only source (the module's own describe_items would read the environment again, and only
    on its first call), so an address the adapter refuses stops the app as it loads. The cache key is the describer's
    model_version: with the batch size of 1 used here, the MODEL_VERSION that role 3's seed writes its rows under."""
    if settings.attributes_model == "fake":
        return "fake", "fake", fakes.describe_items
    if settings.attributes_model == "qwen":
        # The same relative form as find_spec above and `from ..ml import fakes`: the module src.ml.attributes.
        module = importlib.util.resolve_name("..ml.attributes", __package__)
        try:
            # import_module looks in sys.modules first, so a stand-in (or None) there decides, even when something
            # else has already imported the real module and the package keeps it as an attribute.
            attributes = importlib.import_module(module)
        except ModuleNotFoundError as error:
            if error.name != module:
                raise  # the file is there but a package it imports is not: that is the error to show
            raise ValueError("ATTRIBUTES_MODEL=qwen needs src/ml/attributes.py from role 3 (task 4.3): "
                             "merge its branch first, or use ATTRIBUTES_MODEL=fake") from None
        try:
            describer = attributes.AttributeDescriber(server_url=settings.llama_server_url)
        except ValueError:
            # Not role 3's own message, and never the address: it may carry a password. The variable's name only.
            raise ValueError("ATTRIBUTES_MODEL=qwen needs LLAMA_SERVER_URL (DOCKER_LLAMA_SERVER_URL in Docker) to be "
                             "http:// on localhost, 127.0.0.1, [::1] or host.docker.internal, with no path or password") from None
        return "qwen", describer.model_version, describer.describe_items
    raise ValueError(f"ATTRIBUTES_MODEL={settings.attributes_model} does not work; use fake or qwen")


def load_backends(settings):
    """The models settings ask for."""
    category, classify = category_backend(settings)
    attributes, attributes_version, describe_items = attribute_backend(settings)
    return Backends(category=category, classify=classify, attributes=attributes, attributes_version=attributes_version,
                    describe_items=describe_items, gpu_probe=llama_probe(settings.llama_server_url))
