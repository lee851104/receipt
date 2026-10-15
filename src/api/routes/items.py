"""POST /api/items/classify: one product name's category and attributes, for the classify box."""
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, StringConstraints, field_validator

from .. import cache
from ..db import SessionDep
from ..errors import ApiError
from ..security import current_user
from ..validation import visible

router = APIRouter(prefix="/api/items", dependencies=[Depends(current_user)])


class ItemName(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    @field_validator("name")
    @classmethod
    def visible_name(cls, name):
        return visible(name, "name")


# A plain def, not async: the models block, so FastAPI runs this in a worker thread.
@router.post("/classify")
def classify(body: ItemName, request: Request, background: BackgroundTasks, session: SessionDep):
    state = request.app.state
    backends = state.backends
    if backends.category == "unavailable":
        raise ApiError(503, "model_unavailable")
    [answer] = backends.classify([body.name])
    # The box never waits for Qwen: only the caches answer, and a name not seen yet is pending...
    [attributes] = cache.describe(session, backends, [body.name], ask_model=False)
    # ...while the model, if it can answer now, judges it in the background for next time.
    if attributes is None and cache.model_ready(backends):
        background.add_task(cache.describe_later, state.engine, backends, body.name)
    category = answer["category"]
    return {"name": body.name,
            "category": {"id": category, "name": state.categories[category], "prob": answer["probs"][category]},
            "probs": answer["probs"], "attributes": attributes,
            "attributes_status": "pending" if attributes is None else "ready"}
