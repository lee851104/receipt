"""Errors sent as {"detail": code} with an optional message; overview section 5 lists the codes."""
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status, code, message=None, headers=None):
        super().__init__(code)
        self.status, self.code, self.message, self.headers = status, code, message, headers


async def api_error_handler(request: Request, error: ApiError):
    content = {"detail": error.code}
    if error.message is not None:
        content["message"] = error.message
    return JSONResponse(status_code=error.status, content=content, headers=error.headers)


async def validation_error_handler(request: Request, error: RequestValidationError):
    """FastAPI's usual 422 body without the rejected values: one may be a password, and some text (a lone
    surrogate) cannot even be sent back."""
    details = [{key: value for key, value in item.items() if key != "input"} for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(details)})


async def internal_error_handler(request: Request, error: Exception):
    """Any crash still answers JSON, so a page can always read the error; the details stay in the server's log."""
    return JSONResponse(status_code=500, content={"detail": "internal_error"})
