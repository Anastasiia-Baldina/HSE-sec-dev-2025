from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.error import ApiError, NotFoundError, ValidationError
from app.error_handling import (
    api_error_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

app = FastAPI()

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.middleware("http")
async def catch_all_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return await generic_exception_handler(request, exc)


@app.get("/success")
async def success_endpoint():
    return {"message": "success"}


@app.get("/not-found-test")
async def not_found_endpoint():
    raise NotFoundError()


@app.get("/validation-error-test")
async def validation_error_endpoint():
    raise ValidationError("Invalid input data")


@app.get("/value-error-test")
async def value_error_endpoint():
    # Встроенный ValueError → generic_exception_handler
    raise ValueError("Invalid value provided")


@app.get("/http-exception-test")
async def http_exception_endpoint():
    raise HTTPException(status_code=400, detail="Bad request")


@app.get("/server-error")
async def server_error_endpoint():
    raise Exception("Internal server error")


client = TestClient(app)


class TestProblemDetailsFormat:
    def test_success_response_unchanged(self):
        response = client.get("/success")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_not_found_error_format(self):
        response = client.get("/not-found-test")
        data = response.json()
        assert response.status_code == 404
        assert data["type"] == "about:blank"
        assert data["title"] == "not_found"
        assert data["status"] == 404
        assert data["detail"] == "topic not found"
        assert "correlation_id" in data

    def test_validation_error_format(self):
        response = client.get("/validation-error-test")
        data = response.json()
        assert response.status_code == 422
        assert data["type"] == "about:blank"
        assert data["title"] == "validation_error"
        assert data["status"] == 422
        assert data["detail"] == "Invalid input data"
        assert "correlation_id" in data

    def test_value_error_format(self):
        response = client.get("/value-error-test")
        data = response.json()
        assert response.status_code == 500
        assert data["title"] == "Internal Server Error"
        assert data["detail"] == "An unexpected error occurred"
        assert "correlation_id" in data

    def test_http_exception_format(self):
        response = client.get("/http-exception-test")
        data = response.json()
        assert response.status_code == 400
        assert data["type"] == "about:blank"
        assert data["title"] == "http_error"
        assert data["status"] == 400
        assert data["detail"] == "Bad request"
        assert "correlation_id" in data

    def test_generic_exception_format(self):
        response = client.get("/server-error")
        data = response.json()
        assert response.status_code == 500
        assert data["title"] == "Internal Server Error"
        assert data["detail"] == "An unexpected error occurred"
        assert "correlation_id" in data

    def test_correlation_id_present_in_all_errors(self):
        for path in ["/not-found-test", "/value-error-test", "/http-exception-test"]:
            data = client.get(path).json()
            assert "correlation_id" in data
