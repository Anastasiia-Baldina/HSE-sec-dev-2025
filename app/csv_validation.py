import uuid
from pathlib import Path

from app.constants import ALLOWED_EXTENSIONS, DEFAULT_EXTENSION

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


def sniff_csv_type(data: bytes) -> str | None:
    first_line = data.split(b"\n")[0] if b"\n" in data else data
    if any(first_line.startswith(sig) for sig in CSV_SIGNATURES):
        return "text/csv"

    if b"," in first_line and len(first_line) > 0:
        return "text/csv"

    return None


def secure_save(base_dir: str, data: bytes, filename_hint: str = "") -> str:
    mt = sniff_csv_type(data)
    if not mt:
        raise ValueError("Invalid file type: not a valid CSV file")

    if len(data) > MAX_BYTES:
        raise ValueError(f"File too large: exceeds {MAX_BYTES} bytes limit")

    root = Path(base_dir).resolve(strict=True)

    ext = Path(filename_hint).suffix.lower() if filename_hint else DEFAULT_EXTENSION
    if ext not in ALLOWED_EXTENSIONS:
        ext = DEFAULT_EXTENSION

    name = f"{uuid.uuid4()}{ext}"
    path = (root / name).resolve()

    if not str(path).startswith(str(root)):
        raise ValueError("Path traversal detected")

    if any(p.is_symlink() for p in path.parents):
        raise ValueError("Symlinks not allowed in file path")

    path.write_bytes(data)
    return str(path)


async def check_and_save(file, upload_dir: Path):
    try:
        content = await file.read()

        await file.seek(0)

        save_path = secure_save(str(upload_dir), content, file.filename)
        return True, save_path

    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Upload failed: {str(e)}"
