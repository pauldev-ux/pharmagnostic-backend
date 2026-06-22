"""Extracción de texto de documentos PDF, TXT y DOCX (imports perezosos)."""

from fastapi import HTTPException


def extract_text(path: str, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext == "txt":
        return _extract_txt(path)
    if ext == "pdf":
        return _extract_pdf(path)
    if ext == "docx":
        return _extract_docx(path)
    raise HTTPException(status_code=400, detail=f"Formato no soportado para extracción: {ext}")


def _extract_txt(path: str) -> str:
    with open(path, "rb") as fh:
        raw = fh.read()
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="pypdf no está instalado") from exc
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(path: str) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="python-docx no está instalado") from exc
    document = docx.Document(path)
    return "\n".join(p.text for p in document.paragraphs)
