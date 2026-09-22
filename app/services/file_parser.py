from pathlib import Path

import fitz
from docx import Document


def parse_pdf(file_path: str) -> str:
    text = []

    document = fitz.open(file_path)

    try:
        for page in document:
            text.append(page.get_text())
    finally:
        document.close()

    return "\n".join(text)


def parse_docx(file_path: str) -> str:
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs)


def extract_text_from_file(file_path: str) -> str:
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return parse_pdf(file_path)

    if extension == ".docx":
        return parse_docx(file_path)

    raise ValueError(
        "Only PDF and DOCX files are supported."
    )


def parse_document(file_path: str) -> str:
    return extract_text_from_file(file_path)