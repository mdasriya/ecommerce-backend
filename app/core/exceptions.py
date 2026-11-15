import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import error_response

logger = logging.getLogger(__name__)


class AppException(Exception):
    """
    Raise this from services for any expected business error.
    Example: raise AppException("Category not found", status_code=404)

    `headers` is optional; used e.g. for 401 responses, which should send
    `WWW-Authenticate: Bearer` per the HTTP spec.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        errors: dict | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors
        self.headers = headers

        super().__init__(message)


def _format_validation_errors(exc: RequestValidationError) -> dict[str, list[str]]:
    """
    Convert Pydantic's error list into {"field": ["message", ...]}.

    SECURITY: FastAPI's default 422 response echoes back the submitted
    `input` value. For auth endpoints that would echo passwords into responses
    (and into any logs that capture responses). We deliberately return only
    the field name and the message.
    """
    errors: dict[str, list[str]] = {}

    for err in exc.errors():
        loc = err.get("loc", ())
        # Drop the leading "body"/"query"/"path"/"header" part for a
        # frontend-friendly key, e.g. ("body", "email") -> "email".
        # Errors about the body as a whole (model validators, missing body)
        # have loc == ("body",) and are reported under "request".
        field = ".".join(str(p) for p in loc[1:]) or "request"

        message = err.get("msg", "Invalid value")
        # Pydantic prefixes custom validator messages with "Value error, ".
        message = message.removeprefix("Value error, ")

        errors.setdefault(field, []).append(message)

    return errors


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to the app."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message=exc.message, errors=exc.errors),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_response(
                message="Validation failed",
                errors=_format_validation_errors(exc),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Covers framework-raised errors: unknown route (404), wrong method
        # (405), missing Bearer header (401/403 from HTTPBearer), etc.
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(message=message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log full details server-side; never leak internals to the client.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(message="Internal server error"),
        )
