from pathlib import Path
import json
import sqlite3
import numpy as np
from settings import get_system_prompt

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
        SELECT c.id, c.document_id, COALESCE(d.filename, c.source) AS source, c.chunk_index, c.chunk_text, c.embedding
        FROM chunks c
        LEFT JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL AND c.embedding != ''
        ORDER BY c.id
    """)

    rows = cursor.fetchall()
    conn.close()

    chunks = []

    for row in rows:
        chunk_id, doc_id, source, chunk_index, chunk_text, embedding_json = row
        embedding = json.loads(embedding_json)

        chunks.append({
            "id": chunk_id,
            "document_id": doc_id,
            "source": source,
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "embedding": embedding,
        })

    return chunks


def get_foundry_manager():
    if FoundryLocalManager.instance is None:
        config = Configuration(app_name="rag_chat")
        FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance

    print("Preparing execution providers...")
    manager.download_and_register_eps()

    return manager


def get_query_embedding(manager, query: str):
    print("Loading the embedding model...")

    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)
    model.download()
    model.load()

    embedding_client = model.get_embedding_client()

    response = embedding_client.generate_embedding(query)
    query_embedding = response.data[0].embedding

    model.unload()

    return query_embedding


def retrieve_top_chunks(
    manager,
    query: str,
    top_k: int = 1,
    min_score: float = MIN_SIMILARITY_SCORE,
):
    chunks = load_chunks_with_embeddings()

    if not chunks:
        return []

    print(f"Toplam embedding'li chunk: {len(chunks)}")
    print("Converting the question to an embedding...")

    query_embedding = get_query_embedding(manager, query)

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


def answer_question(manager, question: str):
    print("Searching for relevant chunks...")

    top_chunks = retrieve_top_chunks(manager, question, top_k=1)

    if not top_chunks:
        message = "I could not find the answer to this question in the documents."
        print(message)
        return message, []

    context = build_context(top_chunks)

    print("Loading the chat model...")

    chat_model = manager.catalog.get_model(CHAT_MODEL_ALIAS)
    chat_model.download()
    chat_model.load()

    chat_client = chat_model.get_chat_client()

    messages = [
        {
            "role": "system",
            "content": get_system_prompt()
        },
        {
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"Question:\n{question}\n\n"
                "Answer using this exact format:\n"
                "Definition: <direct definition from the context>\n"
                "Details: <supporting details from the context only>\n"
                "Source: <source document name>"
            )
        }
    ]

    print("\nAssistant response:\n")

    answer_parts = []

    for chunk in chat_client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue

        content = chunk.choices[0].delta.content

        if content:
            print(content, end="", flush=True)
            answer_parts.append(content)

    print("\n")

    chat_model.unload()

    return "".join(answer_parts), top_chunks


def main():
    manager = get_foundry_manager()

    question = "Define primitive data types according to the context."

    print(f"Question: {question}\n")

    answer, chunks = answer_question(manager, question)

    if chunks:
        print("\nSource chunks used:\n")

        for chunk in chunks:
            print(
                f"- {chunk['source']} | chunk {chunk['chunk_index']} | score {chunk['score']:.4f}"
            )


if __name__ == "__main__":
    main()
