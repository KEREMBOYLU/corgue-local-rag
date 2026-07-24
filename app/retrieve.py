from pathlib import Path
import json
import sqlite3
import numpy as np

from foundry_local_sdk import Configuration, FoundryLocalManager


DB_PATH = Path("rag.db")
EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    vec_a = np.array(a)
    vec_b = np.array(b)

    denominator = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)

    if denominator == 0:
        return 0.0

    return float(np.dot(vec_a, vec_b) / denominator)


def load_chunks_with_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, source, chunk_index, chunk_text, embedding
        FROM chunks
        WHERE embedding IS NOT NULL AND embedding != ''
    """)

    rows = cursor.fetchall()
    conn.close()

    chunks = []

    for row in rows:
        chunk_id, source, chunk_index, chunk_text, embedding_json = row
        embedding = json.loads(embedding_json)

        chunks.append({
            "id": chunk_id,
            "source": source,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding": embedding,
        })

    return chunks


def get_query_embedding(query: str):
    config = Configuration(app_name="retrieve_test")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()

    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)
    model.download()
    model.load()

    embedding_client = model.get_embedding_client()

    response = embedding_client.generate_embedding(query)
    query_embedding = response.data[0].embedding

    model.unload()

    return query_embedding


def retrieve_top_chunks(query: str, top_k: int = 3):
    chunks = load_chunks_with_embeddings()

    if not chunks:
        print("Embedding içeren chunk bulunamadı.")
        return []

    print(f"Toplam embedding'li chunk: {len(chunks)}")
    print("Soru embedding'e çevriliyor...")

    query_embedding = get_query_embedding(query)

    scored_chunks = []

    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk["embedding"])

        scored_chunks.append({
            **chunk,
            "score": score,
        })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    return scored_chunks[:top_k]


def main():
    query = "What are primitive data types?"

    print(f"Soru: {query}\n")

    results = retrieve_top_chunks(query, top_k=3)

    print("\nEn alakalı chunk'lar:\n")

    for result in results:
        print("=" * 80)
        print(f"ID: {result['id']}")
        print(f"Source: {result['source']}")
        print(f"Chunk index: {result['chunk_index']}")
        print(f"Score: {result['score']:.4f}")
        print("\nMetin:")
        print(result["chunk_text"][:700])


if __name__ == "__main__":
    main()