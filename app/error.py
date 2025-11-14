class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


class NotFoundError(ApiError):
    def __init__(self):
        super().__init__(code="not_found", message="topic not found", status=404)


class ValidationError(ApiError):
    def __init__(self, message: str):
        super().__init__(code="validation_error", message=message, status=422)


class WriteConflictError(ApiError):
    def __init__(self):
        super().__init__(
            code="already_exists", message="topic already exists", status=409
        )
