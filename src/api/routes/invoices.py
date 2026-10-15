"""Uploads: POST /api/invoices parses a month's CSV at once, then a background job classifies it;
GET /api/jobs/{job_id} tells how far that job is."""
import csv
import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, UploadFile
from sqlmodel import col, delete

from ...receipt.invoices import build_month
from ..db import SessionDep
from ..errors import ApiError
from ..jobs import UNFINISHED, run_job
from ..security import current_user
from ..tables import Item, Job, User
from ..validation import PathId

router = APIRouter(prefix="/api")
UserDep = Annotated[User, Depends(current_user)]
MAX_BYTES = 2 * 1024 * 1024
# The limit on a whole request body (limits.UploadLimit): room for the multipart boundary and part headers around the
# file, which the route still checks against MAX_BYTES itself.
MAX_BODY = MAX_BYTES + 64 * 1024
# Real months have about 50 kept lines; this keeps one upload's job under about an hour of Qwen.
MAX_ROWS = 2000


def parse(data):
    """The month key and rows of an uploaded CSV. The bytes go to a temporary file only while they are read."""
    handle = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    try:
        with handle:
            handle.write(data)
        return build_month(Path(handle.name), {}, for_upload=True)
    finally:
        os.unlink(handle.name)


@router.post("/invoices", status_code=202)
def upload(file: UploadFile, user: UserDep, request: Request, background: BackgroundTasks, session: SessionDep):
    # Demo users are shared by everyone: an upload would hang one person's purchases on a public persona.
    if user.is_demo:
        raise ApiError(403, "demo_user_read_only")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ApiError(413, "file_too_large")
    try:
        month_key, month = parse(data)
    # ValueError covers UnicodeDecodeError, bad dates and numbers and every rule build_month enforces; csv.Error a
    # field over csv's 131,072-character limit.
    except (ValueError, csv.Error) as error:
        raise ApiError(400, "invalid_csv", str(error)) from None
    if len(month["rows"]) > MAX_ROWS:
        raise ApiError(400, "invalid_csv", f"A month may have at most {MAX_ROWS} kept lines")
    # The new file replaces the month: its old items go, and so do its finished jobs.
    session.exec(delete(Item).where(Item.user_id == user.id, Item.month == month_key))
    session.exec(delete(Job).where(Job.user_id == user.id, Job.month == month_key, col(Job.status).not_in(UNFINISHED)))
    for row in month["rows"]:
        session.add(Item(user_id=user.id, month=month_key, day=row["day"], invoice=row["invoice"],
                         merchant=row["merchant"], district=row["district"], name=row["name"],
                         quantity=row["quantity"], amount=row["amount"]))
    job = Job(user_id=user.id, month=month_key, total=len({row["name"] for row in month["rows"]}))
    session.add(job)
    session.commit()
    state = request.app.state
    background.add_task(run_job, state.engine, state.backends, state.settings, job.id)
    return {"job_id": job.id, "month": month_key, "rows": len(month["rows"])}


@router.get("/jobs/{job_id}")
def job_status(job_id: PathId, user: UserDep, session: SessionDep):
    job = session.get(Job, job_id)
    # Someone else's job answers exactly like a missing one, so ids tell nothing about other users.
    if job is None or job.user_id != user.id:
        raise ApiError(404, "not_found")
    return {"job_id": job.id, "month": job.month, "status": job.status, "done": job.done, "total": job.total,
            "message": job.message}
