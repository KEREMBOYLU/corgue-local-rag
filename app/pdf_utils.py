from pathlib import Path

from pypdf import PdfReader


def select_pdf_path(provided_path: str | None) -> Path:
    raw_path = provided_path

    if raw_path is None:
        raw_path = input("PDF dosyasının yolunu girin: ").strip()

    raw_path = raw_path.strip().strip('"').strip("'")

    if not raw_path:
        raise ValueError("PDF yolu boş bırakılamaz.")

    pdf_path = Path(raw_path).expanduser().resolve()

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Seçilen dosya PDF değil: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"PDF bulunamadı: {pdf_path}")

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
        raise ValueError("chunk_size sıfırdan büyük olmalıdır.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap sıfırdan küçük olamaz ve chunk_size'dan küçük olmalıdır.")

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks
