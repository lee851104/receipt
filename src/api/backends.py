"""Which category and attribute models answer, and whether the llama-server running Qwen is up."""
from dataclasses import dataclass
from typing import Callable
import urllib.request

from ..ml import fakes


@dataclass(frozen=True)
class Backends:
    category: str                    # the name /api/health reports
    classify: Callable               # list[str] -> list[{"category": 0-9, "probs": [10 floats]}]
    attributes: str
    describe_items: Callable         # list[str] -> list[dict | None]
    gpu_probe: Callable[[], bool]    # whether the llama-server answers right now


def llama_probe(url, timeout=0.5):
    """A function telling whether the llama-server at url answers its /health check."""
    def probe():
        try:
            with urllib.request.urlopen(url + "/health", timeout=timeout) as response:
                return response.status == 200
        except (OSError, ValueError):  # refused, timed out, an error status, or a malformed URL
            return False
    return probe


def load_backends(settings):
    """The models settings ask for. Only the fakes exist until src/ml has the real ones."""
    if settings.category_model != "fake" or settings.attributes_model != "fake":
        raise ValueError("Only CATEGORY_MODEL=fake and ATTRIBUTES_MODEL=fake work until src/ml has the real models")
    return Backends(category="fake", classify=fakes.classify, attributes="fake",
                    describe_items=fakes.describe_items, gpu_probe=llama_probe(settings.llama_server_url))
