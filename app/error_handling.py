import re
from typing import Any, Dict
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import logger


def sanitize_string(value: str) -> str:
    if not value:
        return value
    sanitized = re.sub(r'[<>"\'&]', "", value)
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def mask_pii(data: Any) -> Any:
    if isinstance(data, str):
        # Mask email-like patterns
        data = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", data
        )
        # Mask potential tokens/keys
        data = re.sub(r"\b[A-Za-z0-9]{32,}\b", "[TOKEN]", data)
        # Mask credit card numbers
        data = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[CARD]", data)
    elif isinstance(data, dict):
        return {k: mask_pii(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_pii(item) for item in data]
    return data


def problem(
    status: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    extras: Dict[str, Any] | None = None,
):
    cid = str(uuid4())
    # Sanitize
    safe_detail = sanitize_string(detail)
    safe_title = sanitize_string(title)

    payload = {
        "type": type_,
        "title": safe_title,
        "status": status,
        "detail": safe_detail,
        "correlation_id": cid,
    }
    if extras:
        # Sanitize extras data
        safe_extras = mask_pii(extras)
        payload.update(safe_extras)

    logger.warning(
        "Error response generated",
        extra={
            "correlation_id": cid,
            "status_code": status,
            "error_title": safe_title,
            "path": "N/A",
        },
    )

    return JSONResponse(payload, status_code=status)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning(
        "API error handled",
        extra={
            "error_type": type(exc).__name__,
            "status_code": exc.status,
            "path": sanitize_string(request.url.path),
        },
    )
    return problem(
        status=exc.status,
        title=exc.code,
        detail=exc.message,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    safe_detail = sanitize_string(detail)

    logger.warning(
        "HTTP exception handled",
        extra={
            "status_code": exc.status_code,
            "path": sanitize_string(request.url.path),
            "method": request.method,
        },
    )

    return problem(
        status=exc.status_code,
        title="http_error",
        detail=safe_detail,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    safe_errors = []
    for error in exc.errors():
        safe_error = error.copy()
        if "ctx" in safe_error and "error" in safe_error["ctx"]:
            safe_error["ctx"]["error"] = sanitize_string(
                str(safe_error["ctx"]["error"])
            )
        safe_errors.append(safe_error)

    logger.warning(
        "Validation error",
        extra={
            "path": sanitize_string(request.url.path),
            "method": request.method,
            "error_count": len(safe_errors),
        },
    )

    return problem(
        status=422,
        title="Validation Error",
        detail="Invalid request parameters",
        extras={"errors": safe_errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = str(uuid4())

    logger.error(
        "Unhandled exception",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": sanitize_string(request.url.path),
            "method": request.method,
        },
        exc_info=True,
    )

    return problem(
        status=500,
        title="Internal Server Error",
        detail="An unexpected error occurred",
        type_="https://tools.ietf.org/html/rfc7231#section-6.6.1",
    )
