"""Refuse an oversized upload before any of its body is read."""
from starlette.responses import JSONResponse


class UploadLimit:
    """FastAPI reads a whole multipart body, spooling it to disk past 1 MB, before the route runs and even before
    the login check, so a size check in the route comes after any amount of data was written. uvicorn never passes
    on more body than the Content-Length header says, so checking that header bounds the body. A POST to `path`
    without the header (a chunked upload) is refused 411, and one whose header is not a number or is above `limit`
    is refused 413. Every other request passes through untouched."""

    def __init__(self, app, path, limit):
        self.app, self.path, self.limit = app, path, limit

    async def __call__(self, scope, receive, send):
        limited = scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == self.path
        refusal = self.refusal(scope["headers"]) if limited else None
        if refusal is None:
            await self.app(scope, receive, send)
        else:
            await refusal(scope, receive, send)

    def refusal(self, headers):
        """The response that turns a request away from its headers, or None to let it in."""
        headers = dict(headers)  # the names are lower-case bytes
        # Transfer-Encoding counts as no length: with both headers h11 reads the chunked body to its end and
        # ignores Content-Length.
        if b"content-length" not in headers or b"transfer-encoding" in headers:
            return JSONResponse({"detail": "length_required"}, status_code=411)
        if not self.acceptable(headers[b"content-length"].decode("latin-1")):
            return JSONResponse({"detail": "file_too_large"}, status_code=413)
        return None

    def acceptable(self, length):
        """Whether a Content-Length value is plain digits no larger than the limit."""
        try:
            return length.isdigit() and int(length) <= self.limit
        # int() refuses what isdigit() accepts, such as a superscript two, and more digits than Python converts
        # (4,300), which is above any limit anyway.
        except ValueError:
            return False
