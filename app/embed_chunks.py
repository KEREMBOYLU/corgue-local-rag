from pathlib import Path
import json
import sqlite3

from foundry_local_sdk import Configuration, FoundryLocalManager


DB_PATH = Path("rag.db")
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"


from ingest import create_database


def add_embedding_column_if_needed():
    create_database()



def get_chunks_without_embeddings():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
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
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
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
        print(f"Database not found: {DB_PATH}")
        return

    add_embedding_column_if_needed()

    chunks = get_chunks_without_embeddings()

    if not chunks:
        print("There are no chunks waiting for embeddings.")
        return

    print(f"Chunks to embed: {len(chunks)}")

    print("Starting Foundry Local...")
    if FoundryLocalManager.instance is None:
        config = Configuration(app_name="embed_chunks")
        FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Preparing execution providers...")
    manager.download_and_register_eps()

    print("Getting the embedding model...")
    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)

    print("Model indiriliyor...")
    model.download()

    print("Loading model...")
    model.load()

    embedding_client = model.get_embedding_client()

    for index, (chunk_id, chunk_text) in enumerate(chunks, start=1):
        print(f"[{index}/{len(chunks)}] Creating an embedding for chunk {chunk_id}...")

        response = embedding_client.generate_embedding(chunk_text)
        embedding = response.data[0].embedding

        save_embedding(chunk_id, embedding)

    print("Unloading model...")
    model.unload()

    print("\nAll chunk embeddings were saved.")


if __name__ == "__main__":
    main()
