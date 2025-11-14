import logging
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def problem(
    status: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    extras: Dict[str, Any] | None = None,
):
    cid = str(uuid4())
    payload = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "correlation_id": cid,
    }
    if extras:
        payload.update(extras)
    return JSONResponse(payload, status_code=status)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return problem(
        status=exc.status,
        title=exc.code,
        detail=exc.message,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return problem(
        status=exc.status_code,
        title="http_error",
        detail=detail,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return problem(
        status=422,
        title="Validation Error",
        detail="Invalid request parameters",
        extras={"errors": exc.errors()},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = str(uuid4())
    logger.error(
        "Unhandled exception",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "exception_msg": str(exc),
            "path": request.url.path,
        },
        exc_info=True,
    )

    return problem(
        status=500,
        title="Internal Server Error",
        detail="An unexpected error occurred",
        type_="https://tools.ietf.org/html/rfc7231#section-6.6.1",
    )
