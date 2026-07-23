from pathlib import Path
import json
import sqlite3

from foundry_local_sdk import Configuration, FoundryLocalManager


DB_PATH = Path("rag.db")
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"


def add_embedding_column_if_needed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(chunks)")
    columns = [row[1] for row in cursor.fetchall()]

    if "embedding" not in columns:
        print("embedding kolonu ekleniyor...")
        cursor.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT")
    else:
        print("embedding kolonu zaten var.")

    conn.commit()
    conn.close()


def get_chunks_without_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, chunk_text
        FROM chunks
        WHERE embedding IS NULL OR embedding = ''
        ORDER BY id
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def save_embedding(chunk_id: int, embedding: list[float]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    embedding_json = json.dumps(embedding)

    cursor.execute(
        """
        UPDATE chunks
        SET embedding = ?
        WHERE id = ?
        """,
        (embedding_json, chunk_id)
    )

    conn.commit()
    conn.close()


def main():
    if not DB_PATH.exists():
        print(f"Database bulunamadı: {DB_PATH}")
        return

    add_embedding_column_if_needed()

    chunks = get_chunks_without_embeddings()

    if not chunks:
        print("Embedding üretilecek chunk yok. Hepsi zaten dolu.")
        return

    print(f"Embedding üretilecek chunk sayısı: {len(chunks)}")

    print("Foundry Local başlatılıyor...")
    config = Configuration(app_name="embed_chunks")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Execution providers hazırlanıyor...")
    manager.download_and_register_eps()

    print("Embedding modeli alınıyor...")
    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)

    print("Model indiriliyor...")
    model.download()

    print("Model yükleniyor...")
    model.load()

    embedding_client = model.get_embedding_client()

    for index, (chunk_id, chunk_text) in enumerate(chunks, start=1):
        print(f"[{index}/{len(chunks)}] Chunk {chunk_id} embedding üretiliyor...")

        response = embedding_client.generate_embedding(chunk_text)
        embedding = response.data[0].embedding

        save_embedding(chunk_id, embedding)

    print("Model kapatılıyor...")
    model.unload()

    print("\nTüm chunk embedding'leri kaydedildi.")


if __name__ == "__main__":
    main()
