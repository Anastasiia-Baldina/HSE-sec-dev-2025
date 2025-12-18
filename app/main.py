from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.csv_validation import check_and_save
from app.entity import Topic, TopicStatus
from app.error import ApiError, NotFoundError, ValidationError, WriteConflictError
from app.error_handling import (
    api_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        path = request.url.path

        if path == "/health":
            response.headers["Cache-Control"] = "public, max-age=30"
        else:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


app = FastAPI(title="SecDev Course App", version="0.1.0")

app.add_middleware(SecurityHeadersMiddleware)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

crud_limit = limiter.shared_limit("15/second", scope="crud-limit")
read_limit = limiter.shared_limit("25/second", scope="read-limit")


@app.get("/health")
def health():
    return {"status": "ok"}


_DB = {}


@app.get("/topics/status/{status}")
@read_limit
def get_topic_by_status(request: Request, status: TopicStatus):
    return [topic for topic in _DB.values() if topic.status == status]


@app.get("/topics/title/{title}")
@read_limit
def get_topic_by_title(request: Request, title: str):
    validate_title(title)
    check_exists(title)
    return _DB.get(title)


@app.post("/topics")
@crud_limit
def create_topic(request: Request, topic: Topic):
    validate_topic(topic)
    if topic.title in _DB:
        raise WriteConflictError()
    _DB[topic.title] = topic
    return {"message": "Topic created successfully"}


@app.put("/topics")
@crud_limit
def update_topic(request: Request, topic: Topic):
    validate_topic(topic)
    check_exists(topic.title)
    _DB[topic.title] = topic
    return {"message": "Topic updated successfully"}


@app.delete("/topics/{title}")
@crud_limit
def delete_topic(request: Request, title: str):
    check_exists(title)
    del _DB[title]
    return {"message": "Topic deleted successfully"}


@app.post("/topics/import")
@crud_limit
async def import_topics(request: Request, file: UploadFile):
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        upload_dir = Path(tmpdir)
        success, result = await check_and_save(file, upload_dir)

        if not success:
            raise ValidationError(message=result)

        processed_count = 1

    return {"message": f"Successfully imported {processed_count} topics"}


def check_exists(title: str):
    if title not in _DB:
        raise NotFoundError()


def validate_title(title: str):
    if not title or len(title) > 100:
        raise ValidationError(message="title must be 1..100 chars")


def validate_topic(topic: Topic):
    validate_title(topic.title)
    if not topic.status:
        raise ValidationError(message="status mustn't be null")
    if not topic.due_at:
        raise ValidationError(message="due_at mustn't be null")
