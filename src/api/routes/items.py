"""POST /api/items/classify: one product name's category and attributes, for the classify box."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, StringConstraints, field_validator

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
def classify(body: ItemName, request: Request):
    state = request.app.state
    [answer] = state.backends.classify([body.name])
    # The box never waits for Qwen: only the cache answers, and a name it has not seen yet is pending.
    [attributes] = state.backends.describe_items([body.name], ask_model=False)
    category = answer["category"]
    return {"name": body.name,
            "category": {"id": category, "name": state.categories[category], "prob": answer["probs"][category]},
            "probs": answer["probs"], "attributes": attributes,
            "attributes_status": "pending" if attributes is None else "ready"}
