import importlib.util
import json
import logging
import os
import re
import sys
from datetime import datetime

JSON_LOGGER_AVAILABLE = importlib.util.find_spec("pythonjsonlogger") is not None


class SafeJsonFormatter:
    def __init__(self):
        self.format = self.json_format

    def json_format(self, record):
        log_data = {
            "asctime": datetime.fromtimestamp(record.created).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "levelname": record.levelname,
            "name": record.name,
            "message": self.sanitize_message(record.getMessage()),
            "filename": record.filename,
            "lineno": record.lineno,
        }

        if record.exc_info:
            log_data["exc_info"] = self.format_exception(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

    def sanitize_message(self, message):
        if not isinstance(message, str):
            return message

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        message = re.sub(email_pattern, "[EMAIL]", message)

        token_pattern = r"\b[a-fA-F0-9]{32,}\b"
        message = re.sub(token_pattern, "[TOKEN]", message)

        card_pattern = r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
        message = re.sub(card_pattern, "[CARD]", message)

        message = re.sub(r'[<>"\']', "", message)

        if len(message) > 200:
            message = message[:200] + "..."

        return message

    def format_exception(self, exc_info):
        import traceback

        try:
            lines = traceback.format_exception(*exc_info)
            tb_text = "".join(lines)
            return self.sanitize_message(tb_text)
        except Exception:
            return "[Unable to format exception]"

    def format(self, record):
        return self.json_format(record)


class SafeTextFormatter(logging.Formatter):

    def __init__(self):
        super().__init__("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    def format(self, record):
        record_copy = logging.LogRecord(
            name=record.name,
            level=record.levelno,
            pathname=record.pathname,
            lineno=record.lineno,
            msg=self.sanitize_message(record.msg),
            args=record.args,
            exc_info=record.exc_info,
        )
        return super().format(record_copy)

    def sanitize_message(self, message):
        if not isinstance(message, str):
            return message

        # Mask email addresses
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        message = re.sub(email_pattern, "[EMAIL]", message)

        # Mask long tokens
        token_pattern = r"\b[a-fA-F0-9]{32,}\b"
        message = re.sub(token_pattern, "[TOKEN]", message)

        # Remove dangerous characters
        message = re.sub(r'[<>"\']', "", message)

        # Limit length
        if len(message) > 200:
            message = message[:200] + "..."

        return message


def setup_safe_logging():
    handler = logging.StreamHandler(sys.stdout)

    if JSON_LOGGER_AVAILABLE:
        formatter = SafeJsonFormatter()
    else:
        formatter = SafeTextFormatter()

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    print(f"✓ Safe logging configured with level: {log_level}")

    return root_logger


logger = setup_safe_logging()
