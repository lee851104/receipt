"""Checks on what people send, shared by the request bodies and paths."""
import unicodedata
from typing import Annotated

from fastapi import Path
from pydantic import AfterValidator, Field, StringConstraints

MAX_ID = 2**63 - 1  # SQLite's largest INTEGER; a bigger number would crash the database lookup
# A database id in a request body: a real JSON integer (not true, "2" or 2.0) from 1 to MAX_ID, else a 422 answer.
RowId = Annotated[int, Field(strict=True, ge=1, le=MAX_ID)]
# The same range for an id in the path, which arrives as text and so cannot be strict.
PathId = Annotated[int, Path(ge=1, le=MAX_ID)]


def visible(text, field):
    """text itself, or a ValueError (so a 422 answer) when it holds a control, invisible, private, unassigned or
    line-breaking character, any of which could make it look blank, break a line or pass for something else."""
    if any(unicodedata.category(char)[0] == "C" or unicodedata.category(char) in ("Zl", "Zp") for char in text):
        raise ValueError(f"{field} holds a control, invisible or line-breaking character")
    return text


# A display name as register and PATCH /api/me take it: trimmed, 1-20 characters, nothing invisible.
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
                        AfterValidator(lambda name: visible(name, "display_name"))]
