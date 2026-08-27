import pytest

from app.core.errors import BadInputError, DocumentParseError
from app.services import document_service


def test_txt_extraction():
    text = document_service.extract_text("resume.txt", b"Hello world resume")
    assert "Hello world" in text


def test_empty_file_rejected():
    with pytest.raises(BadInputError):
        document_service.extract_text("resume.pdf", b"")


def test_unsupported_extension_rejected():
    with pytest.raises(BadInputError):
        document_service.extract_text("resume.rtf", b"some bytes")


def test_oversized_file_rejected():
    with pytest.raises(BadInputError):
        document_service.extract_text("resume.txt", b"x" * (6 * 1024 * 1024))


def test_corrupt_pdf_raises_parse_error():
    with pytest.raises(DocumentParseError):
        document_service.extract_text("resume.pdf", b"%PDF-1.4 not really a pdf")
