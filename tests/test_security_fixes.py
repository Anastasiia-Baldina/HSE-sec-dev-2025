import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.csv_validation import check_and_save, detect_mime, secure_save, sniff_csv_type
from app.entity import Topic
from app.error import ValidationError
from app.main import validate_title, validate_topic


class TestCSVValidation:
    def test_sniff_csv_type_valid_with_header(self):
        valid_data = b"Title,DueDate,Status\nTest,2023-01-01,open"
        assert sniff_csv_type(valid_data) == "text/csv"

    def test_sniff_csv_type_valid_without_header(self):
        valid_data = b"Test Topic,2023-01-01,open\nAnother Topic,2023-02-01,in_progress"
        assert sniff_csv_type(valid_data) == "text/csv"

    def test_sniff_csv_type_invalid_binary(self):
        invalid_data = b"\x89PNG\r\n\x1A\n" + b"x" * 100  # PNG header
        assert sniff_csv_type(invalid_data) is None

    def test_sniff_csv_type_empty(self):
        assert sniff_csv_type(b"") is None

    def test_detect_file_type_pdf(self):
        pdf_data = b"%PDF-1.4 fake pdf content"
        assert detect_mime(pdf_data) == "application/pdf"

    def test_detect_file_type_csv(self):
        csv_data = b"Title,Description\nTest,Content"
        result = detect_mime(csv_data)
        assert result == "text/csv"

    def test_secure_save_path_traversal_absolute(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_data = b"Title,DueDate,Status\nTest,2023-01-01,open"

            result_path = secure_save(tmpdir, malicious_data, "/etc/passwd")
            assert Path(result_path).exists()
            assert "etc" not in result_path  # Path should be sanitized

    def test_secure_save_path_traversal_relative(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            malicious_data = b"Title,DueDate,Status\nTest,2023-01-01,open"

            result_path = secure_save(tmpdir, malicious_data, "../../../etc/passwd")
            assert Path(result_path).exists()
            assert ".." not in result_path  # Path traversal should be sanitized

    def test_secure_save_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            large_data = b"x" * 6_000_000  # Exceeds 5MB limit

            with pytest.raises(ValueError, match="File too large"):
                secure_save(tmpdir, large_data, "test.csv")

    def test_secure_save_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_data = b""

            with pytest.raises(ValueError, match="Empty file"):
                secure_save(tmpdir, empty_data, "test.csv")

    def test_secure_save_invalid_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = b"Title,DueDate,Status\nTest,2023-01-01,open"

            result_path = secure_save(tmpdir, data, "malicious.exe")
            assert Path(result_path).suffix == ".csv"

    def test_secure_save_filename_sanitization(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = b"Title,DueDate,Status\nTest,2023-01-01,open"

            result_path = secure_save(tmpdir, data, "file/with/../path.csv")
            assert ".." not in result_path
            assert "//" not in result_path

    def test_secure_save_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = b"Title,DueDate,Status\nTest,2023-01-01,open"

            result_path = secure_save(tmpdir, data, "test.csv")

            assert Path(result_path).exists()
            assert Path(result_path).suffix == ".csv"
            saved_content = Path(result_path).read_bytes()
            assert saved_content == data


class TestInputValidation:
    def test_validate_title_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_title("")
        assert "Title cannot be empty" in str(exc_info.value)

    def test_validate_title_too_long(self):
        long_title = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_title(long_title)
        assert "Title must be 1..100 characters" in str(exc_info.value)

    def test_validate_title_valid(self):
        try:
            validate_title("Normal Title")
        except ValidationError:
            pytest.fail("Valid title should not raise ValidationError")

    def test_validate_topic_missing_status(self):
        topic = Topic(
            title="Test Topic", due_at=datetime.now(), status=""  # Empty status
        )

        with pytest.raises(ValidationError) as exc_info:
            validate_topic(topic)
        assert "Status must be one of" in str(exc_info.value)

    def test_validate_topic_invalid_due_date(self):
        past_date = datetime.now().replace(year=2020)
        topic = Topic(title="Test Topic", due_at=past_date, status="open")

        with pytest.raises(ValidationError) as exc_info:
            from app.entity_validation import validate_topic

            validate_topic(topic)
        assert "cannot be in the past" in str(exc_info.value)


class TestFileUploadSecurity:
    def test_upload_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:

            async def run_test():
                mock_file = AsyncMock()
                mock_file.read.return_value = b""
                mock_file.filename = "test.csv"
                mock_file.seek.return_value = None
                return await check_and_save(mock_file, Path(tmpdir))

            success, result = asyncio.run(run_test())
            assert not success
            assert "Empty file" in result

    def test_upload_pdf_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:

            async def run_test():
                mock_file = AsyncMock()
                mock_file.read.return_value = b"%PDF-1.4 invalid PDF content"
                mock_file.filename = "fake.csv"
                mock_file.seek.return_value = None
                return await check_and_save(mock_file, Path(tmpdir))

            success, result = asyncio.run(run_test())
            assert not success
            assert "Unsupported file type" in result

    def test_upload_binary_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:

            async def run_test():
                mock_file = AsyncMock()
                mock_file.read.return_value = (
                    b"\x00\x01\x02\x03" * 1000
                )  # Random binary
                mock_file.filename = "binary.csv"
                mock_file.seek.return_value = None
                return await check_and_save(mock_file, Path(tmpdir))

            success, result = asyncio.run(run_test())
            assert not success
            assert "Invalid file type" in result

    def test_upload_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:

            async def run_test():
                mock_file = AsyncMock()
                mock_file.read.return_value = b"x" * 6_000_000  # 6MB file
                mock_file.filename = "large.csv"
                mock_file.seek.return_value = None
                return await check_and_save(mock_file, Path(tmpdir))

            success, result = asyncio.run(run_test())
            assert not success
            assert "File too large" in result

    def test_upload_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:

            async def run_test():
                valid_csv = b"Title,DueDate,Status\nTest Topic,2023-01-01,open"
                mock_file = AsyncMock()
                mock_file.read.return_value = valid_csv
                mock_file.filename = "test.csv"
                mock_file.seek.return_value = None
                return await check_and_save(mock_file, Path(tmpdir))

            success, result = asyncio.run(run_test())
            assert success
            assert Path(result).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
