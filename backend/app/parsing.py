"""CV file parsing without the heavyweight LangChain community package."""

from __future__ import annotations

import os
import re
import tempfile
from io import BytesIO

import docx2txt
from pypdf import PdfReader

from app.errors import AppError

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def extension_of(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def normalise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _BLANK_LINES.sub("\n\n", _WHITESPACE.sub(" ", text)).strip()


def extract_text(filename: str, data: bytes) -> str:
    ext = extension_of(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise AppError(
            "unsupported_file_type",
            "Only PDF and DOCX files are supported.",
            {"extension": ext or "none"},
        )
    try:
        if ext == ".txt":
            text = data.decode("utf-8", errors="replace")
        elif ext == ".pdf":
            text = "\n\n".join(
                page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages
            )
        else:
            text = _extract_docx(data)
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            "unreadable_file",
            "That file could not be read.",
            {"reason": type(exc).__name__},
        ) from exc

    text = normalise(text)
    if len(text) < 100:
        raise AppError(
            "unreadable_file",
            "That file has almost no readable text. If it is scanned, upload a text-based PDF.",
            {"characters": len(text)},
        )
    return text


def _extract_docx(data: bytes) -> str:
    fd, path = tempfile.mkstemp(suffix=".docx")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        return docx2txt.process(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
