"""CV file parsing (PDF / DOCX) via LangChain document loaders.

Framework-agnostic: takes bytes, returns text. The loaders want a path, so the
upload is spooled to a temp file and removed immediately afterwards.
"""

from __future__ import annotations

import os
import re
import tempfile

from app.errors import AppError

#: `.txt` is accepted for local development and tests; the UI only offers
#: PDF and DOCX.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def extension_of(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE.sub(" ", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded CV.

    Raises `AppError` with `unsupported_file_type` or `unreadable_file`.
    """
    ext = extension_of(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise AppError(
            "unsupported_file_type",
            "Only PDF and DOCX files are supported.",
            {"extension": ext or "none"},
        )

    if ext == ".txt":
        text = normalise(data.decode("utf-8", errors="replace"))
    else:
        text = normalise(_load_with_langchain(ext, data))

    if len(text) < 100:
        raise AppError(
            "unreadable_file",
            "That file has almost no readable text. If it is a scanned CV, upload a text-based PDF instead.",
            {"characters": len(text)},
        )
    return text


def _load_with_langchain(ext: str, data: bytes) -> str:
    from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader

    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        loader = PyPDFLoader(path) if ext == ".pdf" else Docx2txtLoader(path)
        try:
            documents = loader.load()
        except Exception as exc:  # noqa: BLE001 - any loader failure is the same to the user
            raise AppError(
                "unreadable_file", "That file could not be read.", {"reason": type(exc).__name__}
            ) from exc
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    return "\n\n".join(doc.page_content for doc in documents)
