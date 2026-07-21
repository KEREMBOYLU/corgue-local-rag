from pathlib import Path
from pypdf import PdfReader


def read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_text.append(f"\n--- Page {page_number} ---\n{text}")

    return "\n".join(pages_text)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def main():
    pdf_path = Path("data/documents/data_types.pdf")

    if not pdf_path.exists():
        print(f"PDF bulunamadı: {pdf_path}")
        return

    text = read_pdf_text(pdf_path)
    chunks = chunk_text(text)

    print("PDF başarıyla chunk'lara bölündü.")
    print(f"Toplam karakter: {len(text)}")
    print(f"Toplam chunk sayısı: {len(chunks)}")

    print("\nİlk chunk:\n")
    print(chunks[0])

    print("\n" + "=" * 60)
    print("\nİkinci chunk:\n")
    print(chunks[1] if len(chunks) > 1 else "İkinci chunk yok.")


if __name__ == "__main__":
    main()