from pathlib import Path
from pypdf import PdfReader


def read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages_text.append(f"\n--- Page {page_number} ---\n{text}")

    return "\n".join(pages_text)


def main():
    pdf_path = Path("data/documents/data_types.pdf")

    if not pdf_path.exists():
        print(f"PDF bulunamadı: {pdf_path}")
        return

    text = read_pdf_text(pdf_path)

    print("PDF başarıyla okundu.")
    print(f"Toplam karakter: {len(text)}")
    print("\nİlk 1500 karakter:\n")
    print(text[:1500])


if __name__ == "__main__":
    main()