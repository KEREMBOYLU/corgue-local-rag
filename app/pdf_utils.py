from pathlib import Path

from pypdf import PdfReader


def select_pdf_path(provided_path: str | None) -> Path:
    raw_path = provided_path

    if raw_path is None:
        raw_path = input("Enter the PDF path: ").strip()

    raw_path = raw_path.strip().strip('"').strip("'")

    if not raw_path:
        raise ValueError("The PDF path cannot be empty.")

    pdf_path = Path(raw_path).expanduser().resolve()

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"The selected file is not a PDF: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"PDF not found: {pdf_path}")

    return pdf_path


def read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_text.append(f"\n--- Page {page_number} ---\n{text}")

    return "\n".join(pages_text)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap cannot be negative and must be smaller than chunk_size.")

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def calculate_file_hash(pdf_path: Path) -> str:
    import hashlib

    sha256 = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)

    return sha256.hexdigest()
