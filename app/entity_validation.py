import re
from datetime import datetime

from app.error import ValidationError


def validate_title(title: str) -> None:
    if not title or len(title.strip()) == 0:
        raise ValidationError(message="Title cannot be empty")

    if len(title) > 100:
        raise ValidationError(message="Title must be 1..100 characters")

    if re.search(r"[{}[\]<>]", title):
        raise ValidationError(message="Title contains invalid characters")

    dangerous_patterns = [
        r"(?i)(select\s.+from|insert\s.+into|update\s.+set|delete\s.+from|drop\s.+table)",  # SQL
        r"(?i)(union\s.+select|or\s.+\=.+|--|\/\*)",
        r"(?i)(script|javascript|onload|onerror|onclick)",
        r"(\.\.\/|\.\.\\|\/etc\/passwd|\/etc\/shadow)",
        r"(\;|\-\-|\|\||\&\&)",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, title):
            raise ValidationError(message="Title contains suspicious patterns")


def validate_due_date(due_at: datetime) -> None:
    if not due_at:
        raise ValidationError(message="Due date is required")

    due_date_date = due_at.replace(hour=0, minute=0, second=0, microsecond=0)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if due_date_date < today:
        raise ValidationError(message="Due date cannot be in the past")

    max_future = today.replace(year=today.year + 1)
    if due_date_date > max_future:
        raise ValidationError(message="Due date cannot be more than 1 year in future")


def validate_status(status: str) -> None:
    allowed_statuses = {"open", "in_progress", "closed"}
    if status not in allowed_statuses:
        raise ValidationError(
            message=f"Status must be one of: {', '.join(sorted(allowed_statuses))}"
        )


def validate_topic(topic) -> None:
    validate_title(topic.title)
    validate_due_date(topic.due_at)
    validate_status(topic.status)


def sanitize_input(text: str, max_length: int = 100) -> str:
    if not text:
        return text

    sanitized = re.sub(r'[<>"\'&]', "", text)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized
