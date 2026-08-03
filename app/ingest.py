import argparse
from pathlib import Path
import sqlite3

from pdf_utils import chunk_text, read_pdf_text, select_pdf_path


DB_PATH = Path("rag.db")


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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bir PDF'i okuyup chunk'larını yerel RAG veritabanına kaydeder."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="İşlenecek PDF'in yolu. Verilmezse interaktif olarak sorulur.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        pdf_path = select_pdf_path(args.pdf)
    except ValueError as error:
        print(error)
        return

    print("PDF okunuyor...")
    text = read_pdf_text(pdf_path)

    print("Metin chunk'lara bölünüyor...")
    chunks = chunk_text(text)

    print("Database hazırlanıyor...")
    create_database()

    print("Eski chunk'lar temizleniyor...")
    clear_old_chunks()

    print("Yeni chunk'lar kaydediliyor...")
    save_chunks(pdf_path.name, chunks)

    print("\nIngestion tamamlandı.")
    print(f"Kaynak PDF: {pdf_path.name}")
    print(f"Toplam karakter: {len(text)}")
    print(f"Kaydedilen chunk sayısı: {len(chunks)}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
