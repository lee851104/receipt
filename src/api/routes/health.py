"""GET /api/health: the server is up, whether the GPU model is reachable, and which models answer."""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/health")
def health(request: Request):
    settings, backends = request.app.state.settings, request.app.state.backends
    gpu = backends.gpu_probe()
    # Without the llama-server, Qwen can only answer from its cache.
    attributes = "cache_only" if backends.attributes == "qwen" and not gpu else backends.attributes
    return {"status": "ok", "gpu_mode": gpu, "demo_mode": settings.demo_mode,
            "models": {"category": backends.category, "attributes": attributes}}
