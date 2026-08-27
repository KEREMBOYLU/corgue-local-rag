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


def load_chunks_with_embeddings(project_id: int | None = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if project_id is not None:
        cursor.execute("""
            SELECT c.id, c.document_id, COALESCE(d.filename, c.source) AS source, c.chunk_index, c.chunk_text, c.embedding
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL AND c.embedding != '' AND d.project_id = ?
            ORDER BY c.id
        """, (project_id,))
    else:
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
        try:
            embedding = json.loads(embedding_json)
        except Exception:
            continue

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
        config = Configuration(app_name="rag_cli")
        FoundryLocalManager.initialize(config)

    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    return manager


def load_embedding_model(manager):
    model = manager.catalog.get_model(EMBEDDING_MODEL_ALIAS)
    cached_variant = next((variant for variant in model.variants if variant.is_cached), None)
    if cached_variant is not None:
        model.select_variant(cached_variant)
    model.download()
    model.load()
    embedding_client = model.get_embedding_client()
    return model, embedding_client


def load_chat_model(manager, model_alias: str = CHAT_MODEL_ALIAS):
    model = manager.catalog.get_model(model_alias)
    cached_variant = next((variant for variant in model.variants if variant.is_cached), None)
    if cached_variant is not None:
        model.select_variant(cached_variant)
    model.download()
    model.load()
    chat_client = model.get_chat_client()
    return model, chat_client


def get_query_embedding(embedding_client, query: str):
    response = embedding_client.generate_embedding(query)
    return response.data[0].embedding


def build_retrieval_query(question: str, history: list[dict]) -> str:
    """Keep short follow-up searches anchored to the previous user topic."""
    clean_question = (question or "").strip()
    if not history or len(clean_question.split()) > 8:
        return clean_question

    previous_user_questions = [
        (message.get("content") or "").strip()
        for message in history
        if message.get("role") == "user" and (message.get("content") or "").strip()
    ]
    if not previous_user_questions:
        return clean_question
    return f"{previous_user_questions[-1]} {clean_question}"


def is_document_overview_request(question: str) -> bool:
    """Recognize generic starter prompts that should search broadly."""
    clean = " ".join((question or "").lower().split())
    markers = (
        "bu belgeleri", "bu belgeyi", "belgeleri özetle", "belgeyi özetle",
        "dokümanları özetle", "dokümanı özetle", "kaynakları özetle",
        "en önemli kavramlar", "önemli kavramlar",
    )
    return any(marker in clean for marker in markers)


def retrieve_top_chunks(
    chunks,
    embedding_client,
    query: str,
    top_k: int = 3,
    min_score: float = MIN_SIMILARITY_SCORE,
):
    if not chunks:
        return []

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
            f"--- [Document: {chunk['source']} | Chunk: #{chunk['chunk_index']} | Similarity Score: {chunk['score']:.4f}] ---\n"
            f"{chunk['chunk_text']}"
        )

    return "\n\n".join(context_parts)


def build_messages_with_context(
    system_prompt: str,
    context: str,
    history: list[dict],
    current_question: str,
    max_history_turns: int = 6,
) -> list[dict]:
    """
    Constructs a chat context window with system prompt, sliding window conversation history,
    retrieved RAG context, and the new user question.
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Filter out empty or placeholder messages from history
    valid_history = []
    for msg in history:
        content = (msg.get("content") or "").strip()
        role = msg.get("role")
        if content and role in ("user", "assistant") and content not in ("Preparing response…", "Yanıt hazırlanıyor…"):
            valid_history.append({"role": role, "content": content})

    # Take last N turns for sliding window
    trimmed_history = valid_history[-max_history_turns:] if max_history_turns > 0 else []

    # Add prior conversation turns
    for msg in trimmed_history:
        messages.append(msg)

    # Add the current turn with RAG context
    if context:
        user_prompt = (
            f"Relevant Context from Documents:\n{context}\n\n"
            f"User Question:\n{current_question}"
        )
    else:
        user_prompt = current_question

    messages.append({"role": "user", "content": user_prompt})
    return messages


def answer_question(chunks, embedding_client, chat_client, question: str):
    top_chunks = retrieve_top_chunks(
        chunks=chunks,
        embedding_client=embedding_client,
        query=question,
        top_k=3,
    )

    if not top_chunks:
        message = "I could not find the answer to this question in the documents."
        print(message)
        return message, []

    context = build_context(top_chunks)

    messages = build_messages_with_context(
        system_prompt=get_system_prompt(),
        context=context,
        history=[],
        current_question=question,
    )

    print("\nAssistant response:")
    print("-" * 50)

    answer_parts = []
    for chunk in chat_client.complete_streaming_chat(messages):
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            answer_parts.append(delta)

    print("\n" + "-" * 50)
    print("\nSources used:")
    for c in top_chunks:
        print(f"- {c['source']} (Chunk #{c['chunk_index']}, score: {c['score']:.4f})")

    return "".join(answer_parts), top_chunks


def main():
    manager = get_foundry_manager()
    _, embedding_client = load_embedding_model(manager)
    _, chat_client = load_chat_model(manager)

    chunks = load_chunks_with_embeddings()
    if not chunks:
        print("No stored chunks with embeddings were found.")
        return

    print(f"Ready! Loaded {len(chunks)} chunks.")
    print("Enter 'q' or 'exit' to quit.\n")

    while True:
        try:
            q = input("\nQuestion: ").strip()
            if not q:
                continue
            if q.lower() in ("q", "exit", "quit"):
                break
            answer_question(chunks, embedding_client, chat_client, q)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
