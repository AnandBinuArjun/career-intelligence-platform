import io
import re
import zipfile
from pathlib import PurePosixPath

from fastapi import HTTPException

from app.core.config import settings


def safe_filename(name: str) -> str:
    basename = PurePosixPath(name.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", basename).strip("._")
    if not cleaned or len(cleaned) > 180:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return cleaned


def validate_extension(filename: str, content_type: str) -> None:
    expected = {
        "application/pdf": {".pdf"},
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
        "text/plain": {".txt"},
    }
    suffix = PurePosixPath(filename.lower()).suffix
    if suffix not in expected.get(content_type, set()):
        raise HTTPException(
            status_code=415, detail="File extension does not match the declared document type"
        )


def validate_document(data: bytes, content_type: str) -> None:
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if content_type == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise HTTPException(status_code=415, detail="File content is not a valid PDF")
        return

    if content_type == "text/plain":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=415, detail="Text file must be UTF-8") from None
        return

    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        max_uncompressed = settings.max_docx_uncompressed_mb * 1024 * 1024
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                names = {info.filename for info in infos}
                if (
                    "[Content_Types].xml" not in names
                    or "word/document.xml" not in names
                    or len(names) > 5000
                ):
                    raise ValueError("Invalid DOCX package")
                total_uncompressed = sum(max(info.file_size, 0) for info in infos)
                if total_uncompressed > max_uncompressed:
                    raise ValueError("DOCX uncompressed payload exceeds safety limit")
        except (zipfile.BadZipFile, ValueError):
            raise HTTPException(status_code=415, detail="File content is not a valid DOCX") from None
        return

    raise HTTPException(status_code=415, detail="Unsupported document type")
