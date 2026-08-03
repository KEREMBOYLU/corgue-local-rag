from pathlib import Path
import json
import sqlite3
import numpy as np

from foundry_local_sdk import Configuration, FoundryLocalManager


DB_PATH = Path("rag.db")

EMBEDDING_MODEL_ALIAS = "qwen3-embedding-0.6b"
CHAT_MODEL_ALIAS = "qwen2.5-1.5b"
MIN_SIMILARITY_SCORE = 0.35


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


def get_foundry_manager():
    config = Configuration(app_name="rag_cli")
    FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Execution providers hazırlanıyor...")
    manager.download_and_register_eps()

    return manager


def load_embedding_model(manager):
    print("Embedding modeli yükleniyor...")

    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)
    model.download()
    model.load()

    embedding_client = model.get_embedding_client()

    return model, embedding_client


def load_chat_model(manager):
    print("Chat modeli yükleniyor...")

    model = manager.catalog.get_model(CHAT_MODEL_ALIAS)
    model.download()
    model.load()

    chat_client = model.get_chat_client()

    return model, chat_client


def get_query_embedding(embedding_client, query: str):
    response = embedding_client.generate_embedding(query)
    return response.data[0].embedding


def retrieve_top_chunks(
    chunks,
    embedding_client,
    query: str,
    top_k: int = 1,
    min_score: float = MIN_SIMILARITY_SCORE,
):
    query_embedding = get_query_embedding(embedding_client, query)

    scored_chunks = []

    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk["embedding"])

        scored_chunks.append({
            **chunk,
            "score": score,
        })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    relevant_chunks = [
        chunk for chunk in scored_chunks if chunk["score"] >= min_score
    ]

    return relevant_chunks[:top_k]


def build_context(chunks):
    context_parts = []

    for chunk in chunks:
        context_parts.append(
            f"[Source: {chunk['source']} | Chunk: {chunk['chunk_index']} | Score: {chunk['score']:.4f}]\n"
            f"{chunk['chunk_text']}"
        )

    return "\n\n---\n\n".join(context_parts)


def answer_question(chunks, embedding_client, chat_client, question: str):
    top_chunks = retrieve_top_chunks(
        chunks=chunks,
        embedding_client=embedding_client,
        query=question,
        top_k=1
    )

    if not top_chunks:
        message = "Bu sorunun cevabını belgelerde bulamadım."
        print(message)
        return message, []

    context = build_context(top_chunks)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict local RAG study assistant. "
                "You must answer only from the provided context. "
                "Do not use outside knowledge. "
                "When the question asks for a definition, first find the direct definition in the context. "
                "A bullet with ':' often contains a direct definition. Prioritize that as the main definition. "
                "Do not treat supporting details as the main definition. "
                "Do not generalize beyond the context. "
                "If the answer is not present in the context, say: I don't know based on the provided context."
            )
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Question:\n{question}\n\n"
                "Answer using this exact format:\n"
                "Definition: <direct answer from the context>\n"
                "Details: <supporting details from the context only>\n"
                "Source: <source document name, chunk index, and score>"
            )
        }
    ]

    answer_parts = []

    for chunk in chat_client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue

        content = chunk.choices[0].delta.content

        if content:
            print(content, end="", flush=True)
            answer_parts.append(content)

    print()

    return "".join(answer_parts), top_chunks


def main():
    if not DB_PATH.exists():
        print(f"Database bulunamadı: {DB_PATH}")
        return

    chunks = load_chunks_with_embeddings()

    if not chunks:
        print("Embedding içeren chunk bulunamadı. Önce embed_chunks.py çalıştır.")
        return

    print(f"Yüklenen chunk sayısı: {len(chunks)}")

    manager = get_foundry_manager()

    embedding_model = None
    chat_model = None

    try:
        embedding_model, embedding_client = load_embedding_model(manager)
        chat_model, chat_client = load_chat_model(manager)

        print("\nLocal RAG Assistant hazır.")
        print("Çıkmak için: exit / quit / q\n")

        while True:
            question = input("Soru: ").strip()

            if question.lower() in ["exit", "quit", "q"]:
                print("Program kapatılıyor...")
                break

            if not question:
                print("Boş soru olmaz aga. Teknolojiye de biraz saygı.")
                continue

            print("\nAssistant cevabı:\n")

            answer, used_chunks = answer_question(
                chunks=chunks,
                embedding_client=embedding_client,
                chat_client=chat_client,
                question=question
            )

            if used_chunks:
                print("\nKullanılan kaynak chunk'lar:")

                for chunk in used_chunks:
                    print(
                        f"- {chunk['source']} | chunk {chunk['chunk_index']} | score {chunk['score']:.4f}"
                    )

            print("\n" + "=" * 80 + "\n")

    finally:
        if embedding_model is not None:
            print("Embedding modeli kapatılıyor...")
            embedding_model.unload()

        if chat_model is not None:
            print("Chat modeli kapatılıyor...")
            chat_model.unload()


if __name__ == "__main__":
    main()
