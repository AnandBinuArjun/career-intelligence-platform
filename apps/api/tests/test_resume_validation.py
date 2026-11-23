import io
import zipfile

import pytest
from fastapi import HTTPException

from app.services.documents.validation import safe_filename, validate_document, validate_extension


def test_safe_filename_removes_path_and_unsafe_characters():
    assert safe_filename("../../My CV (final).pdf") == "My_CV__final_.pdf"


def test_safe_filename_rejects_empty_name():
    with pytest.raises(HTTPException):
        safe_filename("../../")


def test_pdf_signature_is_required():
    validate_document(b"%PDF-1.7\nbody", "application/pdf")
    with pytest.raises(HTTPException) as error:
        validate_document(b"not a pdf", "application/pdf")
    assert error.value.status_code == 415


def test_docx_requires_expected_package_entries():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    validate_document(buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_docx_rejects_arbitrary_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "not a document")
    with pytest.raises(HTTPException) as error:
        validate_document(buffer.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert error.value.status_code == 415


def test_extension_must_match_content_type():
    validate_extension("candidate.pdf", "application/pdf")
    with pytest.raises(HTTPException) as error:
        validate_extension("candidate.exe", "application/pdf")
    assert error.value.status_code == 415
