import asyncio
import tempfile
from pathlib import Path

from app.csv_validation import MAX_BYTES, check_and_save, secure_save, sniff_csv_type


class MockUploadFile:
    def __init__(self, content: bytes, filename: str = "test.csv"):
        self.filename = filename
        self.content = content

    async def read(self):
        return self.content

    async def seek(self, offset: int):
        pass


class TestFileValidation:
    def create_upload_file(
        self, content: bytes, filename: str = "test.csv"
    ) -> MockUploadFile:
        return MockUploadFile(content, filename)

    def test_sniff_csv_type_valid(self):
        valid_content = b"ID,Title,DueDate,Status\n1,Test,2024-01-01,open"
        assert sniff_csv_type(valid_content) == "text/csv"

        valid_content2 = b"title,due_at,status\nTest,2024-01-01,open"
        assert sniff_csv_type(valid_content2) == "text/csv"

    def test_sniff_csv_type_invalid(self):
        invalid_content = b"Not a CSV file content here"
        assert sniff_csv_type(invalid_content) is None

    def test_secure_save_success(self):
        csv_content = b"ID,Title\n1,Test"

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = secure_save(tmpdir, csv_content, "test.csv")

            assert Path(save_path).exists()
            assert save_path.endswith(".csv")
            assert not Path(save_path).name.startswith("test")

    def test_secure_save_file_too_big(self):
        large_content = b"ID,Title\n1,Test" + b"x" * (MAX_BYTES + 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                secure_save(tmpdir, large_content, "test.csv")
            except ValueError as e:
                assert "File too large" in str(e)
            else:
                assert False, "Expected ValueError for large file"

    def test_secure_save_bad_type(self):
        invalid_content = b"Not a CSV file"

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                secure_save(tmpdir, invalid_content, "test.csv")
            except ValueError as e:
                assert "Invalid file type" in str(e)
            else:
                assert False, "Expected ValueError for invalid file type"

    def test_complete_upload_validation_success(self):
        csv_content = b"ID,Title,DueDate,Status\n1,Test Topic,2024-01-01,open"

        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = Path(tmpdir)
            file = self.create_upload_file(csv_content, "test.csv")

            success, result = asyncio.run(check_and_save(file, upload_dir))

            assert success is True
            assert result.endswith(".csv")
            assert Path(result).exists()

    def test_complete_upload_validation_failure(self):
        large_content = b"ID,Title,DueDate,Status\n" + b"x" * (MAX_BYTES + 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = Path(tmpdir)
            file = self.create_upload_file(large_content, "test.csv")

            success, result = asyncio.run(check_and_save(file, upload_dir))

            assert success is False
            assert "File too large" in result
