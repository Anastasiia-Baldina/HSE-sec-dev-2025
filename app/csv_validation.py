import re
import uuid
from pathlib import Path
from typing import Optional

MAX_BYTES = 5_000_000
ALLOWED_MIME_TYPES = {"text/csv", "application/csv", "text/plain"}
CSV_SIGNATURES = [
    b"ID,",
    b"id,",
    b"Title,",
    b"title,",
    b"DueDate,",
    b"due_date,",
    b"Status,",
    b"status,",
]


def detect_mime(data: bytes) -> Optional[str]:
    if data.startswith(b"\xFF\xD8\xFF"):
        return "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1A\n"):
        return "image/png"
    elif data.startswith(b"%PDF"):
        return "application/pdf"
    elif data.startswith(b"PK\x03\x04"):
        return "application/zip"

    csv_type = sniff_csv_type(data)
    if csv_type:
        return csv_type

    return None


def validate_mime_type(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large: exceeds {MAX_BYTES} bytes limit")

    detected_type = detect_mime(data)
    if detected_type and detected_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Unsupported file type: {detected_type}")

    csv_type = sniff_csv_type(data)
    if not csv_type:
        raise ValueError("Invalid file type: not a valid CSV file")

    return csv_type


def sniff_csv_type(data: bytes) -> Optional[str]:
    if not data or len(data) == 0:
        return None

    try:
        text_sample = data.decode("utf-8", errors="ignore")

        if not text_sample.strip():
            return None

        first_line = text_sample.split("\n")[0] if "\n" in text_sample else text_sample

        for sig in CSV_SIGNATURES:
            try:
                sig_str = sig.decode("utf-8", errors="ignore")
                if first_line.startswith(sig_str):
                    return "text/csv"
            except UnicodeDecodeError:
                continue

        if "," in first_line:
            fields = first_line.split(",")
            if len(fields) >= 2:
                return "text/csv"

        if ";" in first_line:
            fields = first_line.split(";")
            if len(fields) >= 2:
                return "text/csv"

    except UnicodeDecodeError:
        return None

    return None


def secure_save(base_dir: str, data: bytes, filename_hint: str = "") -> str:
    if not data or len(data) == 0:
        raise ValueError("Empty file")

    validate_mime_type(data)

    root = Path(base_dir)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    safe_filename = re.sub(r"[^\w\.\-]", "_", filename_hint)
    ext = Path(safe_filename).suffix.lower() if safe_filename else ".csv"

    if ext not in {".csv", ".txt"}:
        ext = ".csv"

    name = f"{uuid.uuid4()}{ext}"
    path = (root / name).resolve()

    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Path traversal detected")

    try:
        path.write_bytes(data)
        return str(path)

    except Exception as e:
        raise ValueError(f"Failed to save file: {str(e)}")


async def check_and_save(file, upload_dir: Path):
    try:
        content = await file.read()

        if not content or len(content) == 0:
            raise ValueError("Empty file")

        await file.seek(0)

        save_path = secure_save(str(upload_dir), content, file.filename)
        return True, save_path

    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Upload failed: {str(e)}"
