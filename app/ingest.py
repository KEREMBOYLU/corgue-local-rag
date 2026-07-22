from pathlib import Path
import sqlite3
from pypdf import PdfReader


DB_PATH = Path("rag.db")
PDF_PATH = Path("data/documents/data_types.pdf")


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


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def clear_old_chunks():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM chunks")

    conn.commit()
    conn.close()


def save_chunks(source: str, chunks: list[str]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for index, chunk in enumerate(chunks):
        cursor.execute(
            """
            INSERT INTO chunks (source, chunk_index, chunk_text)
            VALUES (?, ?, ?)
            """,
            (source, index, chunk)
        )

    conn.commit()
    conn.close()


def main():
    if not PDF_PATH.exists():
        print(f"PDF bulunamadı: {PDF_PATH}")
        return

    print("PDF okunuyor...")
    text = read_pdf_text(PDF_PATH)

    print("Metin chunk'lara bölünüyor...")
    chunks = chunk_text(text)

    print("Database hazırlanıyor...")
    create_database()

    print("Eski chunk'lar temizleniyor...")
    clear_old_chunks()

    print("Yeni chunk'lar kaydediliyor...")
    save_chunks(PDF_PATH.name, chunks)

    print("\nIngestion tamamlandı.")
    print(f"Kaynak PDF: {PDF_PATH.name}")
    print(f"Toplam karakter: {len(text)}")
    print(f"Kaydedilen chunk sayısı: {len(chunks)}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()