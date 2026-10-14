"""Errors sent as {"detail": code} with an optional message; overview section 5 lists the codes."""
from fastapi import Request
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
