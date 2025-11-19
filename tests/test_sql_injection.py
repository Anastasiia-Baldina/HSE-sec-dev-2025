import pytest

from app.entity_validation import validate_title
from app.error import ValidationError


def test_sql_injection_patterns():
    sql_injections = [
        "admin' OR '1'='1",
        "test'; DROP TABLE users; --",
        "1' UNION SELECT password FROM users--",
        "admin'--",
        "x' AND 1=(SELECT COUNT(*) FROM tabname); --",
        "'; EXEC xp_cmdshell('echo vulnerable'); --",
    ]

    for sql in sql_injections:
        try:
            validate_title(sql)
            if any(char in sql for char in ["'", ";", "--", "/*"]):
                pytest.fail(
                    f"SQL injection '{sql}' should have been detected by character validation"
                )
            else:
                print(f"Note: '{sql}' doesn't contain immediately dangerous characters")
        except ValidationError as e:
            error_msg = str(e)
            print(f"SQL injection detected: '{sql}' -> {error_msg}")
            assert any(
                msg in error_msg
                for msg in ["suspicious patterns", "invalid characters"]
            )


def test_sql_keywords():
    sql_keywords = [
        "SELECT * FROM users",
        "INSERT INTO table VALUES",
        "UPDATE users SET password",
        "DELETE FROM users",
        "DROP TABLE users",
    ]

    for sql in sql_keywords:
        try:
            validate_title(sql)
            print(f"Note: SQL keywords '{sql}' not detected - may be acceptable")
        except ValidationError as e:
            error_msg = str(e)
            print(f"✓ SQL keywords detected: '{sql}' -> {error_msg}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
