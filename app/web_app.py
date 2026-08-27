import atexit
import json
import os
import queue
import shutil
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from embed_chunks import get_chunks_without_embeddings, save_embedding
from ingest import (
    create_conversation, create_database, create_project, delete_conversation,
    delete_document, delete_project, get_conversation, get_conversation_messages,
    get_document_by_hash, get_or_create_default_project, get_project_by_id,
    list_conversations, list_documents, list_projects, save_document_and_chunks,
    save_message, update_conversation_title,
)
from pdf_utils import calculate_file_hash, chunk_text, read_pdf_text
from rag_cli import (
    MIN_SIMILARITY_SCORE, build_context, build_messages_with_context,
    get_foundry_manager, load_chat_model, load_chunks_with_embeddings,
    load_embedding_model, build_retrieval_query, is_document_overview_request,
    retrieve_top_chunks,
)
from settings import get_saved_system_prompt, get_system_prompt, reset_system_prompt, save_system_prompt


STATIC_DIR = Path(__file__).parent / "static"
FALLBACK_MESSAGES = {
    "en": "I could not find the answer to this question in the project documents.",
    "tr": "Bu sorunun cevabını projedeki belgelerde bulamadım.",
}
AVAILABLE_MODELS = [
    {
        "id": "qwen2.5-1.5b",
        "name": "Qwen 2.5 1.5B",
        "tag": "Fast & Lightweight",
        "desc": "Default local model (low memory use, quick responses)",
        "downloaded": True,
    },
    {
        "id": "qwen2.5-7b",
        "name": "Qwen 2.5 7B",
        "tag": "Powerful & Detailed",
        "desc": "Stronger comprehension and detailed analysis",
        "downloaded": False,
    },
    {
        "id": "llama3.2-3b",
        "name": "Llama 3.2 3B",
        "tag": "Meta Llama",
        "desc": "Compact and balanced local model",
        "downloaded": False,
    },
    {
        "id": "deepseek-r1-distill-qwen-1.5b",
        "name": "DeepSeek R1 1.5B",
        "tag": "Reasoning",
        "desc": "Step-by-step reasoning",
        "downloaded": False,
    },
]


class ProjectInput(BaseModel):
    name: str
    description: str = ""


class ConversationInput(BaseModel):
    project_id: int
    title: str = "New Chat"


class ChatInput(BaseModel):
    project_id: int
    conversation_id: int
    question: str
    model_alias: str = "qwen2.5-1.5b"
    language: str = "en"


class SystemPromptInput(BaseModel):
    prompt: str


class LocalRAGEngine:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.manager = None
        self.embedding_model = None
        self.embedding_client = None
        self.chat_model = None
        self.chat_client = None
        self.current_chat_alias = None

    def ensure_models(self, chat_alias: str = "qwen2.5-1.5b") -> None:
        with self.lock:
            if self.manager is None:
                self.manager = get_foundry_manager()
            if self.embedding_client is None:
                self.embedding_model, self.embedding_client = load_embedding_model(self.manager)
            if self.chat_client is None or self.current_chat_alias != chat_alias:
                if self.chat_model is not None:
                    try:
                        self.chat_model.unload()
                    except Exception:
                        pass
                self.chat_model, self.chat_client = load_chat_model(self.manager, chat_alias)
                self.current_chat_alias = chat_alias

    def embed_pending_chunks(self) -> int:
        self.ensure_models()
        pending = get_chunks_without_embeddings()
        with self.lock:
            for chunk_id, content in pending:
                response = self.embedding_client.generate_embedding(content)
                save_embedding(chunk_id, response.data[0].embedding)
        return len(pending)

    def close(self) -> None:
        with self.lock:
            for model in (self.embedding_model, self.chat_model):
                if model is not None:
                    try:
                        model.unload()
                    except Exception:
                        pass


engine = LocalRAGEngine()
model_downloads: dict[str, dict] = {}
model_metadata: dict[str, dict] = {}
chat_stop_events: dict[int, threading.Event] = {}
app = FastAPI(title="Corgue")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
atexit.register(engine.close)


def _cached_variant(model):
    """Return a cached CPU/GPU variant, since Foundry tracks them separately."""
    if model is None:
        return None
    variants = getattr(model, "variants", [])
    return next((variant for variant in variants if variant.is_cached), None)


@app.get("/api/models")
def get_models() -> list[dict]:
    try:
        # Do not initialize Foundry merely to open the model picker. This also
        # avoids competing with an active model download after a page refresh.
        manager = engine.manager
        if manager is None and not model_downloads:
            manager = get_foundry_manager()
            engine.manager = manager
        result = []
        listed_aliases = set()
        for item in AVAILABLE_MODELS:
            model = manager.catalog.get_model(item["id"]) if manager else None
            # Only expose models that are actually present in Foundry Local's catalog.
            if model is None:
                continue
            cached_variant = _cached_variant(model)
            if cached_variant is not None:
                model.select_variant(cached_variant)
            if model and model._selected_variant:
                info = model._selected_variant._model_info
                model_metadata[item["id"]] = {"size_mb": info.file_size_mb}
            metadata = model_metadata.get(item["id"], {})
            download = model_downloads.get(item["id"], {})
            cached = cached_variant is not None or (model.is_cached if model else item.get("downloaded", False))
            # The normal chat picker must contain only models already in cache.
            if not cached:
                continue
            listed_aliases.add(item["id"])
            result.append({**item, "downloaded": cached, "cached": cached,
                           "downloading": False,
                           "progress": download.get("progress"),
                           "size_mb": download.get("size_mb", metadata.get("size_mb")),
                           "downloaded_mb": download.get("downloaded_mb", 0),
                           "available": model is not None})

        # Models downloaded from Settings > Modeller are also available in the
        # normal picker, without exposing undownloaded catalog entries there.
        if manager:
            for model in manager.catalog.list_models():
                variant = getattr(model, "_selected_variant", None)
                info = getattr(variant, "_model_info", None)
                alias = getattr(info, "alias", None) if info else None
                cached_variant = _cached_variant(model)
                if not info or info.task != "chat-completion" or not alias or alias in listed_aliases or cached_variant is None:
                    continue
                model.select_variant(cached_variant)
                info = cached_variant._model_info
                result.append({
                    "id": alias,
                    "name": alias,
                    "tag": "Foundry Local",
                    "desc": "Downloaded from the catalog",
                    "downloaded": True,
                    "cached": True,
                    "downloading": False,
                    "progress": 100,
                    "size_mb": info.file_size_mb,
                    "downloaded_mb": info.file_size_mb,
                    "available": True,
                })
        return result
    except Exception:
        return []


def _model_alias_or_404(model_alias: str) -> str:
    if not any(item["id"] == model_alias for item in AVAILABLE_MODELS):
        raise HTTPException(status_code=404, detail="Model not found.")
    return model_alias


def _get_model(model_alias: str):
    alias = model_alias.strip()
    if not alias:
        raise HTTPException(status_code=404, detail="Model not found.")
    try:
        if engine.manager is None:
            engine.manager = get_foundry_manager()
        model = engine.manager.catalog.get_model(alias)
        if model is None:
            raise HTTPException(status_code=404, detail="This model was not found in the Foundry Local catalog.")
        info = getattr(getattr(model, "_selected_variant", None), "_model_info", None)
        if info is None or info.task != "chat-completion":
            raise HTTPException(status_code=400, detail="This model is not a chat model.")
        return alias, model
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"The model catalog could not be read: {error}") from error


@app.get("/api/models/catalog")
def get_catalog_models() -> list[dict]:
    """Return downloadable chat-completion models from Foundry Local."""
    try:
        if engine.manager is None:
            engine.manager = get_foundry_manager()
        models = []
        for model in engine.manager.catalog.list_models():
            variant = getattr(model, "_selected_variant", None)
            info = getattr(variant, "_model_info", None)
            if info is None or info.task != "chat-completion":
                continue
            alias = getattr(info, "alias", None) or getattr(model, "alias", None)
            if not alias:
                continue
            cached_variant = _cached_variant(model)
            if cached_variant is not None:
                model.select_variant(cached_variant)
                info = cached_variant._model_info
            size_mb = getattr(info, "file_size_mb", None)
            model_metadata[alias] = {"size_mb": size_mb}
            download = model_downloads.get(alias, {})
            cached = cached_variant is not None or bool(model.is_cached)
            models.append({
                "id": alias,
                "name": alias,
                "task": "chat-completion",
                "size_mb": download.get("size_mb", size_mb),
                "downloaded_mb": download.get("downloaded_mb", size_mb if cached else 0),
                "cached": cached,
                "downloaded": cached,
                "downloading": bool(download.get("downloading")) and not cached,
                "progress": download.get("progress"),
            })
        return sorted(models, key=lambda item: item["name"].lower())
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"The model catalog could not be read: {error}") from error


@app.post("/api/models/{model_alias}/prepare")
def prepare_model(model_alias: str) -> dict:
    alias, model = _get_model(model_alias)
    info = getattr(getattr(model, "_selected_variant", None), "_model_info", None)
    if info is None or info.task != "chat-completion":
        raise HTTPException(status_code=400, detail="This model is not a chat model.")
    try:
        engine.ensure_models(chat_alias=alias)
        model = engine.manager.catalog.get_model(alias)
        return {"id": alias, "downloaded": model.is_cached, "loaded": model.is_loaded}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"The model could not be prepared: {error}") from error


@app.post("/api/models/{model_alias}/download")
def download_model(model_alias: str) -> StreamingResponse:
    alias, _ = _get_model(model_alias)
    events: queue.Queue = queue.Queue()
    already_downloading = bool(model_downloads.get(alias, {}).get("downloading"))

    def work():
        try:
            if not already_downloading:
                model_downloads[alias] = {"downloading": True, "progress": 0}
            with engine.lock:
                if engine.manager is None:
                    engine.manager = get_foundry_manager()
                model = engine.manager.catalog.get_model(alias)
                size_mb = model._selected_variant._model_info.file_size_mb
                model_metadata[alias] = {"size_mb": size_mb}
                if model.is_cached:
                    model_downloads[alias] = {"downloading": False, "progress": 100, "size_mb": size_mb, "downloaded_mb": size_mb}
                    events.put({"type": "progress", "progress": 100})
                else:
                    def report(progress):
                        value = round(progress, 1)
                        downloaded_mb = round(size_mb * value / 100, 1)
                        model_downloads[alias] = {"downloading": True, "progress": value, "size_mb": size_mb, "downloaded_mb": downloaded_mb}
                        events.put({"type": "progress", "progress": value, "size_mb": size_mb, "downloaded_mb": downloaded_mb})
                    model.download(report)
                    model_downloads[alias] = {"downloading": False, "progress": 100, "size_mb": size_mb, "downloaded_mb": size_mb}
            events.put({"type": "done"})
        except Exception as error:
            model_downloads[alias] = {"downloading": False, "progress": 0, "error": str(error)}
            events.put({"type": "error", "message": str(error)})
        finally:
            events.put(None)

    def stream():
        yield ndjson({"type": "status", "message": "Downloading model…"})
        if already_downloading:
            while model_downloads.get(alias, {}).get("downloading"):
                yield ndjson({"type": "progress", "progress": model_downloads.get(alias, {}).get("progress", 0)})
                threading.Event().wait(1)
            if model_downloads.get(alias, {}).get("error"):
                yield ndjson({"type": "error", "message": model_downloads[alias]["error"]})
            else:
                yield ndjson({"type": "progress", "progress": 100})
                yield ndjson({"type": "done"})
            return
        model_downloads[alias] = {"downloading": True, "progress": 0}
        threading.Thread(target=work, daemon=True).start()
        while True:
            event = events.get()
            if event is None:
                return
            yield ndjson(event)

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/api/settings/system-prompt")
def read_system_prompt() -> dict:
    saved = get_saved_system_prompt()
    return {
        "prompt": get_system_prompt(),
        "has_custom_prompt": saved is not None,
        "source": "saved" if saved is not None else ("environment" if os.getenv("SYSTEM_PROMPT", "").strip() else "default"),
    }


@app.put("/api/settings/system-prompt")
def update_system_prompt(payload: SystemPromptInput) -> dict:
    try:
        prompt = save_system_prompt(payload.prompt)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"prompt": prompt, "has_custom_prompt": True, "source": "saved"}


@app.delete("/api/settings/system-prompt")
def restore_system_prompt() -> dict:
    prompt = reset_system_prompt()
    return {"prompt": prompt, "has_custom_prompt": False, "source": "environment" if os.getenv("SYSTEM_PROMPT", "").strip() else "default"}


def workspace_payload(project_id: int, conversation_id: int | None = None) -> dict:
    if get_project_by_id(project_id) is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    conversations = list_conversations(project_id)
    if not conversations:
        conversations = [create_conversation(project_id, "New Chat")]
    if conversation_id is None or not any(c["id"] == conversation_id for c in conversations):
        conversation_id = conversations[0]["id"]
    return {
        "projects": list_projects(),
        "project_id": project_id,
        "conversations": list_conversations(project_id),
        "conversation_id": conversation_id,
        "documents": list_documents(project_id=project_id),
        "messages": get_conversation_messages(conversation_id),
    }


def ndjson(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


@app.on_event("startup")
def startup() -> None:
    create_database()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/bootstrap")
def bootstrap() -> dict:
    project = get_or_create_default_project()
    return workspace_payload(project["id"])


@app.get("/api/workspaces/{project_id}")
def get_workspace(project_id: int, conversation_id: int | None = None) -> dict:
    return workspace_payload(project_id, conversation_id)


@app.post("/api/projects")
def add_project(payload: ProjectInput) -> dict:
    try:
        project = create_project(payload.name, payload.description)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    conversation = create_conversation(project["id"], "New Chat")
    return workspace_payload(project["id"], conversation["id"])


@app.delete("/api/projects/{project_id}")
def remove_project(project_id: int) -> dict:
    try:
        if not delete_project(project_id):
            raise HTTPException(status_code=404, detail="Workspace not found.")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    fallback = get_or_create_default_project()
    return workspace_payload(fallback["id"])


@app.post("/api/conversations")
def add_conversation(payload: ConversationInput) -> dict:
    if get_project_by_id(payload.project_id) is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    conversation = create_conversation(payload.project_id, payload.title)
    return workspace_payload(payload.project_id, conversation["id"])


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(conversation_id: int) -> dict:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    delete_conversation(conversation_id)
    return workspace_payload(conversation["project_id"])


class RenameInput(BaseModel):
    title: str


@app.patch("/api/conversations/{conversation_id}/title")
def rename_conversation(conversation_id: int, payload: RenameInput) -> dict:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    update_conversation_title(conversation_id, payload.title)
    return workspace_payload(conversation["project_id"], conversation_id)


@app.post("/api/documents")
def add_documents(project_id: int = Form(...), files: list[UploadFile] = File(...)) -> dict:
    if get_project_by_id(project_id) is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    added, skipped = [], []
    with tempfile.TemporaryDirectory(prefix="local-rag-upload-") as temp_dir:
        temp_root = Path(temp_dir)
        for upload in files:
            filename = Path(upload.filename or "document.pdf").name
            if not filename.lower().endswith(".pdf"):
                skipped.append(f"{filename}: not a PDF")
                continue
            target = temp_root / filename
            with target.open("wb") as output:
                shutil.copyfileobj(upload.file, output)
            file_hash = calculate_file_hash(target)
            if get_document_by_hash(file_hash, project_id=project_id):
                skipped.append(f"{filename}: already exists")
                continue
            chunks = chunk_text(read_pdf_text(target))
            if not chunks:
                skipped.append(f"{filename}: no readable text")
                continue
            save_document_and_chunks(
                filename=filename, chunks=chunks, filepath=filename,
                file_hash=file_hash, project_id=project_id,
            )
            added.append(filename)
    embedded = engine.embed_pending_chunks() if added else 0
    result = workspace_payload(project_id)
    result["upload_result"] = {"added": added, "skipped": skipped, "embedded": embedded}
    return result


@app.delete("/api/documents/{document_id}")
def remove_document(document_id: int, project_id: int) -> dict:
    if not delete_document(document_id):
        raise HTTPException(status_code=404, detail="Source not found.")
    return workspace_payload(project_id)


@app.post("/api/chat")
def chat(payload: ChatInput) -> StreamingResponse:
    question = payload.question.strip()
    conversation = get_conversation(payload.conversation_id)
    if not question:
        raise HTTPException(status_code=400, detail="The question cannot be empty.")
    if conversation is None or conversation["project_id"] != payload.project_id:
        raise HTTPException(status_code=404, detail="Chat not found.")

    previous_messages = get_conversation_messages(payload.conversation_id)
    stop_event = threading.Event()
    chat_stop_events[payload.conversation_id] = stop_event
    save_message(payload.conversation_id, "user", question)
    if conversation["title"] in ("Yeni Sohbet", "İlk Sohbet", "New Chat", "First Chat"):
        update_conversation_title(payload.conversation_id, question[:42])

    def generate():
        try:
            language = "tr" if payload.language == "tr" else "en"
            fallback_message = FALLBACK_MESSAGES[language]
            status_message = (
                f"Yerel model hazırlanıyor ({payload.model_alias})…"
                if language == "tr"
                else f"Preparing local model ({payload.model_alias})…"
            )
            yield ndjson({"type": "status", "message": status_message})
            engine.ensure_models(chat_alias=payload.model_alias)
            if stop_event.is_set():
                return
            chunks = load_chunks_with_embeddings(project_id=payload.project_id)
            if not chunks:
                answer = (
                    "Bu çalışma alanında henüz işlenmiş bir PDF kaynağı yok."
                    if language == "tr"
                    else "This workspace does not have any processed PDF sources yet."
                )
                save_message(payload.conversation_id, "assistant", answer)
                yield ndjson({"type": "sources", "sources": []})
                yield ndjson({"type": "done", "answer": answer})
                return

            with engine.lock:
                system_prompt = get_system_prompt()
                # Anchor short follow-up questions to the previous user topic.
                retrieval_query = build_retrieval_query(question, previous_messages)
                overview_request = is_document_overview_request(question)
                top_chunks = retrieve_top_chunks(
                    chunks=chunks, embedding_client=engine.embedding_client,
                    query=retrieval_query,
                    top_k=min(8, len(chunks)) if overview_request else 4,
                    min_score=0.0 if overview_request else MIN_SIMILARITY_SCORE,
                )

                sources = [
                    {"source": item["source"], "chunk_index": item["chunk_index"],
                     "score": round(item["score"], 4), "excerpt": item["chunk_text"][:360]}
                    for item in top_chunks
                ]
                yield ndjson({"type": "sources", "sources": sources})

                history = [{"role": item["role"], "content": item["content"]} for item in previous_messages]
                context_str = build_context(top_chunks) if top_chunks else ""

                # Context Token Usage Estimation for Context Inspector
                approx_tokens = int((len(system_prompt) + len(context_str) + sum(len(m['content']) for m in history) + len(question)) / 3.6) + 80
                yield ndjson({
                    "type": "context_info",
                    "model": payload.model_alias,
                    "tokens": approx_tokens,
                    "max_tokens": 32768,
                    "chunks": sources,
                    "history_turns": min(len(history), 6),
                })

                if not top_chunks and not history:
                    save_message(payload.conversation_id, "assistant", fallback_message)
                    yield ndjson({"type": "done", "answer": fallback_message})
                    return

                messages = build_messages_with_context(
                    system_prompt=system_prompt, context=context_str,
                    history=history, current_question=question, max_history_turns=6,
                )
                answer_parts = []
                for chunk in engine.chat_client.complete_streaming_chat(messages):
                    if stop_event.is_set():
                        break
                    if not chunk.choices:
                        continue
                    token = chunk.choices[0].delta.content
                    if token:
                        answer_parts.append(token)
                        yield ndjson({"type": "token", "token": token})
                answer = "".join(answer_parts).strip() or fallback_message
            if stop_event.is_set():
                if answer_parts:
                    save_message(payload.conversation_id, "assistant", answer, json.dumps(sources, ensure_ascii=False))
                return
            save_message(payload.conversation_id, "assistant", answer, json.dumps(sources, ensure_ascii=False))
            yield ndjson({"type": "done", "answer": answer})
        except Exception as error:
            # The browser can close the stream when Stop is pressed. Do not
            # turn that normal cancellation into a noisy backend failure.
            if not stop_event.is_set():
                yield ndjson({"type": "error", "message": str(error)})
        finally:
            chat_stop_events.pop(payload.conversation_id, None)

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/chat/{conversation_id}/stop")
def stop_chat(conversation_id: int) -> dict:
    event = chat_stop_events.get(conversation_id)
    if event is not None:
        event.set()
    return {"stopped": event is not None}
