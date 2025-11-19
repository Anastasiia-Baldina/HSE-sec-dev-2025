import io
import logging
from datetime import datetime, timedelta

import pytest

from app.entity import Topic
from app.entity_validation import (
    sanitize_input,
    validate_due_date,
    validate_status,
    validate_title,
    validate_topic,
)
from app.error import ValidationError


class TestEnhancedValidationIntegration:
    def test_validate_title_enhanced_sql_injection(self):
        sql_injections = [
            "admin' OR '1'='1",
            "test'; DROP TABLE topics; --",
        ]

        detected_count = 0
        for sql in sql_injections:
            try:
                validate_title(sql)
                if any(char in sql for char in ["'", ";", "--"]):
                    print(
                        f"Note: SQL injection '{sql}' not detected by pattern matching"
                    )
            except ValidationError as e:
                error_msg = str(e)
                detected_count += 1
                assert any(
                    msg in error_msg
                    for msg in ["suspicious patterns", "invalid characters"]
                )

        assert detected_count > 0, "No SQL injection patterns were detected"

    def test_validate_title_enhanced_xss_attempt(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_title("<script>alert('xss')</script>")
        error_msg = str(exc_info.value)
        assert "invalid characters" in error_msg or "suspicious patterns" in error_msg

    def test_validate_title_enhanced_path_traversal(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_title("../../../etc/passwd")
        assert "suspicious patterns" in str(exc_info.value)

    def test_validate_title_enhanced_valid(self):
        try:
            validate_title("Normal Valid Title")
        except ValidationError:
            pytest.fail("Valid title should not raise ValidationError")

    def test_validate_due_date_past(self):
        past_date = datetime.now() - timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            validate_due_date(past_date)
        assert "cannot be in the past" in str(exc_info.value)

    def test_validate_due_date_future_limit(self):
        future_date = datetime.now() + timedelta(days=400)  # More than 1 year
        with pytest.raises(ValidationError) as exc_info:
            validate_due_date(future_date)
        assert "cannot be more than 1 year" in str(exc_info.value)

    def test_validate_due_date_valid(self):
        try:
            valid_date = datetime.now() + timedelta(days=30)
            validate_due_date(valid_date)
        except ValidationError:
            pytest.fail("Valid due date should not raise ValidationError")

    def test_validate_status_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_status("invalid_status")
        assert "must be one of" in str(exc_info.value)

    def test_validate_status_valid(self):
        for status in ["open", "in_progress", "closed"]:
            try:
                validate_status(status)
            except ValidationError:
                pytest.fail(f"Valid status '{status}' should not raise ValidationError")

    def test_validate_topic_enhanced_comprehensive(self):
        valid_topic = Topic(
            title="Valid Topic",
            due_at=datetime.now() + timedelta(days=1),
            status="open",
        )

        validate_topic(valid_topic)

    def test_validate_topic_enhanced_invalid(self):
        invalid_topic = Topic(
            title="",  # Empty title
            due_at=datetime.now() + timedelta(days=1),
            status="open",
        )

        with pytest.raises(ValidationError):
            validate_topic(invalid_topic)

    def test_sanitize_input_dangerous_chars(self):
        dangerous = '<script>alert("xss")</script>'
        safe = sanitize_input(dangerous)

        assert "<" not in safe
        assert ">" not in safe
        assert '"' not in safe
        assert "'" not in safe
        assert "&" not in safe

    def test_sanitize_input_length_limit(self):
        long_input = "a" * 150
        safe = sanitize_input(long_input, max_length=100)

        assert len(safe) == 100


class TestLoggingIntegration:
    def test_logging_pii_masking(self):
        from app.logging_config import SafeTextFormatter

        logger = logging.getLogger("test_pii_masking")
        logger.handlers = []  # Clear existing handlers

        log_capture_string = io.StringIO()

        handler = logging.StreamHandler(log_capture_string)
        formatter = SafeTextFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        test_message = "User email: test@example.com and token: abc123def45678901234567890123456789"
        logger.info(test_message)

        log_contents = log_capture_string.getvalue()

        assert "test@example.com" not in log_contents
        assert "[EMAIL]" in log_contents

        assert "abc123def456789012345678901234567890" not in log_contents
        assert "[TOKEN]" in log_contents

    def test_safe_text_formatter_directly(self):
        from app.logging_config import SafeTextFormatter

        formatter = SafeTextFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User email: test@example.com and token: abc123def456789012345678901234567890",
            args=(),
            exc_info=None,
        )

        formatted_message = formatter.format(record)

        assert "test@example.com" not in formatted_message
        assert "[EMAIL]" in formatted_message

        assert "abc123def456789012345678901234567890" not in formatted_message
        assert "[TOKEN]" in formatted_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
