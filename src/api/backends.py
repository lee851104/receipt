"""Which category and attribute models answer, and whether the llama-server running Qwen is up."""
from dataclasses import dataclass
import http.client
import time
from typing import Callable
import urllib.request

from ..ml import fakes

REMEMBER = 5.0  # seconds a probe answer is reused; on Windows a refused local connection costs the whole timeout


@dataclass(frozen=True, kw_only=True)
class Backends:
    category: str                    # the name /api/health reports
    classify: Callable               # list[str] -> list[{"category": 0-9, "probs": [10 floats]}]
    attributes: str
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


def load_backends(settings):
    """The models settings ask for. Only the fakes exist until src/ml has the real ones."""
    if settings.category_model != "fake" or settings.attributes_model != "fake":
        raise ValueError("Only CATEGORY_MODEL=fake and ATTRIBUTES_MODEL=fake work until src/ml has the real models")
    return Backends(category="fake", classify=fakes.classify, attributes="fake",
                    describe_items=fakes.describe_items, gpu_probe=llama_probe(settings.llama_server_url))
