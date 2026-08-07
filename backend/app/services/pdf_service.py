from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader


def extract_text(file: UploadFile) -> str:
    raw = file.file.read()
    if not raw:
        raise ValueError("Uploaded resume file is empty")

    reader = PdfReader(BytesIO(raw))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if not text.strip():
        raise ValueError("No extractable text found — this may be a scanned/image PDF")

    return text
