import atexit
import os
import sys
from pathlib import Path
import threading

print("⏳ [1/3] Sistem modülleri yükleniyor...", flush=True)

os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import gradio as gr
from jinja2 import Environment, FileSystemLoader

print("⏳ [2/3] Veritabanı ve RAG bileşenleri hazırlanıyor...", flush=True)

from embed_chunks import add_embedding_column_if_needed, save_embedding
from ingest import (
    create_conversation,
    create_database,
    create_project,
    delete_conversation,
    delete_document,
    delete_project,
    get_conversation,
    get_conversation_messages,
    get_document_by_hash,
    get_or_create_default_project,
    list_conversations,
    list_documents,
    list_projects,
    save_document_and_chunks,
    save_message,
    update_conversation_title,
)
from pdf_utils import calculate_file_hash, chunk_text, read_pdf_text
from rag_cli import (
    CHAT_MODEL_ALIAS,
    EMBEDDING_MODEL_ALIAS,
    MIN_SIMILARITY_SCORE,
    build_context,
    build_messages_with_context,
    get_foundry_manager,
    load_chat_model,
    load_chunks_with_embeddings,
    load_embedding_model,
    retrieve_top_chunks,
)
from settings import get_system_prompt


APP_NAME = "Local RAG"
FALLBACK_MESSAGE = "Bu sorunun cevabını projedeki belgelerde bulamadım."

def current_system_prompt():
    return get_system_prompt()

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
html_template = jinja_env.get_template("template_html.j2")

CUSTOM_CSS = """
:root {
    --app-bg: #ffffff;
    --app-panel: #f7f7f8;
    --app-card: #ffffff;
    --app-border: #e5e7eb;
    --app-muted: #6b7280;
    --app-text: #171717;
}
.dark {
    --app-bg: #0b1020;
    --app-panel: #111827;
    --app-card: #172033;
    --app-border: #283449;
    --app-muted: #94a3b8;
    --app-text: #f8fafc;
}
body { overflow: hidden; }
.gradio-container {
    max-width: none !important;
    min-height: 100vh !important;
    padding: 0 !important;
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--app-bg) !important;
    color: var(--app-text) !important;
}
.app-shell {
    display: flex !important;
    flex-flow: row nowrap !important;
    gap: 0 !important;
    min-height: 100vh;
}
.left-rail, .source-rail {
    height: 100vh;
    overflow-y: auto;
    padding: 18px 16px !important;
    background: var(--app-panel);
    flex-wrap: nowrap !important;
}
.left-rail { flex: 0 0 280px !important; border-right: 1px solid var(--app-border); }
.source-rail { flex: 0 0 340px !important; border-left: 1px solid var(--app-border); }
.chat-stage {
    display: flex !important;
    flex: 1 1 auto !important;
    flex-flow: column nowrap !important;
    height: 100vh;
    min-width: 0;
    padding: 0 28px 18px !important;
    background: var(--app-bg);
    overflow: hidden;
}
.brand-lockup { padding: 2px 4px 14px; }
.brand-lockup h1 { font-size: 1.2rem !important; letter-spacing: -0.03em; margin: 0 !important; }
.brand-lockup p { color: var(--app-muted); font-size: .78rem; margin: 3px 0 0 !important; }
.section-kicker {
    color: var(--app-muted);
    font-size: .71rem;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
    margin: 18px 3px 8px;
}
.chat-topbar {
    display: flex !important;
    flex: 0 0 70px !important;
    flex-flow: row nowrap !important;
    min-height: 70px;
    align-items: center;
    border-bottom: 1px solid var(--app-border);
    margin-bottom: 0;
}
.workspace-banner { flex: 1 1 auto !important; min-width: 0; background: transparent !important; padding: 0 !important; }
.workspace-banner p { margin: 0 !important; font-size: .85rem; color: var(--app-muted); }
.workspace-banner code { font-family: inherit; background: transparent; color: var(--app-text); font-weight: 650; }
#clear-button { flex: 0 0 auto !important; width: auto !important; min-width: 76px !important; }
#chatbot {
    flex: 1 1 auto !important;
    height: auto !important;
    min-height: 0 !important;
    border: 0 !important;
    background: transparent !important;
    overflow: hidden;
}
#chatbot .message { max-width: 78%; line-height: 1.65; border-radius: 18px !important; box-shadow: none !important; }
#chatbot .message.user { background: var(--button-primary-background-fill) !important; color: white !important; }
#chatbot .message.bot { background: transparent !important; border: 0 !important; }
.composer {
    display: flex !important;
    flex: 0 0 auto !important;
    flex-flow: row nowrap !important;
    width: min(100%, 860px) !important;
    max-width: 860px;
    margin: 12px auto 0 !important;
    padding: 9px 10px 9px 18px !important;
    border: 1px solid var(--app-border) !important;
    border-radius: 24px !important;
    background: var(--app-card) !important;
    box-shadow: 0 10px 32px rgba(15, 23, 42, .10);
    align-items: end;
    overflow: hidden;
}
#question-box { flex: 1 1 auto !important; min-width: 0 !important; border: 0 !important; background: transparent !important; box-shadow: none !important; }
#question-box textarea { padding: 8px 0 !important; max-height: 150px; }
#send-button { flex: 0 0 46px !important; min-width: 46px !important; width: 46px !important; height: 46px; border-radius: 50% !important; font-size: 1.05rem; }
.rail-button { border-radius: 12px !important; text-align: left !important; }
.danger-button { opacity: .72; }
.left-rail .wrap, .left-rail .form, .source-rail .wrap, .source-rail .form {
    background: var(--app-card) !important;
    border-color: var(--app-border) !important;
}
.status-card {
    border: 1px solid var(--app-border);
    border-radius: 13px;
    padding: 10px 12px;
    background: var(--app-card);
    font-size: .78rem;
}
.status-card h3 { font-size: .82rem !important; margin: 0 0 6px !important; }
.status-card p, .status-card li { font-size: .78rem !important; }
.source-header h2 { font-size: 1rem !important; margin: 3px 0 2px !important; }
.source-header p { color: var(--app-muted); font-size: .76rem; margin: 0 0 12px !important; }
#source-upload { min-height: 100px !important; }
#source-upload .wrap { min-height: 96px !important; padding: 12px !important; }
#source-upload .wrap > div { min-height: 70px !important; }
.rag-inspector-container { padding: 2px; background: transparent; }
.rag-inspector-container > h3, .rag-inspector-container > p { display: none; }
.rag-badge, .doc-box {
    padding: 10px 12px;
    border: 1px solid var(--app-border);
    border-radius: 11px;
    font-size: .78rem;
    line-height: 1.5;
    margin-top: 6px;
    background: var(--app-card);
    color: var(--app-text) !important;
}
.badge-instructions, .badge-query { border-left: 3px solid #6366f1; }
.doc-box { border-left: 3px solid #22c55e; }
.rag-inspector-container span { font-size: .7rem !important; }
footer { display: none !important; }
@media (max-width: 1050px) {
    body { overflow: auto; }
    .app-shell { flex-flow: row wrap !important; }
    .left-rail { flex: 0 0 240px !important; }
    .chat-stage { flex: 1 1 calc(100% - 240px) !important; }
    .left-rail, .source-rail, .chat-stage { height: auto; min-height: auto; }
    .source-rail { flex: 1 1 100% !important; }
    .source-rail { border-left: 0; border-top: 1px solid var(--app-border); }
    #chatbot { height: 62vh !important; }
}
"""


class LocalRAGService:
    def __init__(self):
        self.lock = threading.RLock()
        self.manager = None
        self.embedding_model = None
        self.embedding_client = None
        self.chat_model = None
        self.chat_client = None

        create_database()
        default_proj = get_or_create_default_project()
        self.current_project_id = default_proj["id"]
        self.chunks = self._load_chunks_for_project(self.current_project_id)

        convs = list_conversations(self.current_project_id)
        if not convs:
            new_c = create_conversation(self.current_project_id, "Yeni Sohbet")
            self.current_conv_id = new_c["id"]
        else:
            self.current_conv_id = convs[0]["id"]

    def _load_chunks_for_project(self, project_id: int):
        try:
            return load_chunks_with_embeddings(project_id=project_id)
        except Exception:
            return []

    def get_project_choices(self) -> list[tuple[str, int]]:
        projs = list_projects()
        return [
            (
                f"📁 {p['name']} ({p['doc_count']} Belge · {p['chunk_count']} Chunk)",
                p["id"],
            )
            for p in projs
        ]

    def get_conversation_choices(self, project_id: int) -> list[tuple[str, int]]:
        convs = list_conversations(project_id)
        return [(f"💬 {c['title']} ({c['msg_count']} msj)", c["id"]) for c in convs]

    def get_document_choices(self, project_id: int) -> list[tuple[str, int]]:
        docs = list_documents(project_id=project_id)
        return [
            (
                f"{doc['filename']} (ID: {doc['id']} · {doc['chunk_count']} chunk)",
                doc["id"],
            )
            for doc in docs
        ]

    def get_workspace_banner(self, project_id: int, conv_id: int | None = None) -> str:
        projs = [p for p in list_projects() if p["id"] == project_id]
        proj_name = projs[0]["name"] if projs else "Bilinmeyen Proje"
        docs = list_documents(project_id=project_id)
        total_chunks = sum(d["chunk_count"] for d in docs)

        conv_title = "Yeni Sohbet"
        if conv_id:
            c = get_conversation(conv_id)
            if c:
                conv_title = c["title"]

        return (
            f"📁 **Proje:** `{proj_name}` ｜ 💬 **Sohbet:** `{conv_title}` ｜ "
            f"📄 **Koleksiyon:** `{len(docs)} Belge` · `{total_chunks} Chunk`"
        )

    def database_status(self, project_id: int) -> str:
        docs = list_documents(project_id=project_id)
        if not docs:
            return (
                "### 📂 Bu Projede Henüz Belge Yok\n"
                "Aşağıdan PDF yükleyerek bu projeye özel döküman havuzu oluşturabilirsiniz."
            )

        total_chunks = sum(d["chunk_count"] for d in docs)
        doc_lines = [
            f"- **{doc['filename']}** (ID: {doc['id']} · {doc['chunk_count']} chunk)"
            for doc in docs
        ]
        docs_list_md = "\n".join(doc_lines)
        return (
            f"### 📚 Proje Belgeleri ({len(docs)} Belge · {total_chunks} Chunk)\n"
            f"{docs_list_md}"
        )

    def render_empty_inspector(self) -> str:
        return html_template.render(
            instructions=current_system_prompt(),
            documents=[],
            query="Henüz bir soru sorulmadı.",
        )

    def ensure_models(self, progress=gr.Progress()):
        with self.lock:
            if self.embedding_client is not None and self.chat_client is not None:
                return

            progress(0.05, desc="Foundry Local hazırlanıyor")
            self.manager = get_foundry_manager()

            progress(0.25, desc=f"Embedding modeli yükleniyor: {EMBEDDING_MODEL_ALIAS}")
            self.embedding_model, self.embedding_client = load_embedding_model(
                self.manager
            )

            progress(0.65, desc=f"Chat modeli yükleniyor: {CHAT_MODEL_ALIAS}")
            self.chat_model, self.chat_client = load_chat_model(self.manager)
            progress(1.0, desc="Modeller hazır")

    # ==========================================
    # Project Actions
    # ==========================================
    def switch_project(self, project_id: int):
        if not project_id:
            return (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
                [],
                self.render_empty_inspector(),
            )

        with self.lock:
            self.current_project_id = project_id
            self.chunks = self._load_chunks_for_project(project_id)

            convs = list_conversations(project_id)
            if not convs:
                new_c = create_conversation(project_id, "Yeni Sohbet")
                selected_conv_id = new_c["id"]
            else:
                selected_conv_id = convs[0]["id"]
            self.current_conv_id = selected_conv_id

            messages = get_conversation_messages(selected_conv_id)
            chat_history = [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]

        conv_choices = self.get_conversation_choices(project_id)
        doc_choices = self.get_document_choices(project_id)
        banner = self.get_workspace_banner(project_id, selected_conv_id)
        db_status = self.database_status(project_id)

        return (
            gr.update(value=project_id, choices=self.get_project_choices()),
            gr.update(value=selected_conv_id, choices=conv_choices),
            banner,
            db_status,
            gr.update(choices=doc_choices, value=None),
            chat_history,
            self.render_empty_inspector(),
        )

    def create_new_project_action(self, name: str, description: str):
        name = (name or "").strip()
        if not name:
            gr.Warning("Lütfen geçerli bir proje adı girin.")
            return self.switch_project(self.current_project_id)

        try:
            with self.lock:
                new_p = create_project(name, description)
                new_c = create_conversation(new_p["id"], "İlk Sohbet")
                self.current_project_id = new_p["id"]
                self.current_conv_id = new_c["id"]
                self.chunks = []
            gr.Info(f"'{name}' projesi başarıyla oluşturuldu.")
            return self.switch_project(new_p["id"])
        except ValueError as err:
            gr.Warning(str(err))
            return self.switch_project(self.current_project_id)

    def delete_project_action(self, project_id: int):
        if not project_id:
            return self.switch_project(self.current_project_id)

        try:
            with self.lock:
                delete_project(project_id)
                default_p = get_or_create_default_project()
                self.current_project_id = default_p["id"]
                self.chunks = self._load_chunks_for_project(default_p["id"])
            gr.Info("Proje ve bağlı tüm dökümanlar/sohbetler silindi.")
            return self.switch_project(default_p["id"])
        except ValueError as err:
            gr.Warning(str(err))
            return self.switch_project(project_id)

    # ==========================================
    # Conversation Actions
    # ==========================================
    def switch_conversation(self, conv_id: int, project_id: int):
        if not conv_id:
            return [], self.get_workspace_banner(project_id, None), self.render_empty_inspector()

        with self.lock:
            self.current_conv_id = conv_id
            messages = get_conversation_messages(conv_id)
            chat_history = [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]

        banner = self.get_workspace_banner(project_id, conv_id)
        return (
            chat_history,
            banner,
            self.render_empty_inspector(),
        )

    def new_conversation_action(self, project_id: int):
        with self.lock:
            new_c = create_conversation(project_id, "Yeni Sohbet")
            self.current_conv_id = new_c["id"]

        conv_choices = self.get_conversation_choices(project_id)
        banner = self.get_workspace_banner(project_id, new_c["id"])
        return (
            gr.update(value=new_c["id"], choices=conv_choices),
            [],
            banner,
            self.render_empty_inspector(),
        )

    def delete_conversation_action(self, conv_id: int, project_id: int):
        if not conv_id:
            return gr.update(), [], self.get_workspace_banner(project_id, None)

        with self.lock:
            delete_conversation(conv_id)
            convs = list_conversations(project_id)
            if not convs:
                new_c = create_conversation(project_id, "Yeni Sohbet")
                selected_id = new_c["id"]
            else:
                selected_id = convs[0]["id"]
            self.current_conv_id = selected_id
            messages = get_conversation_messages(selected_id)
            chat_history = [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]

        conv_choices = self.get_conversation_choices(project_id)
        banner = self.get_workspace_banner(project_id, selected_id)
        return (
            gr.update(value=selected_id, choices=conv_choices),
            chat_history,
            banner,
        )

    # ==========================================
    # Ingestion & Documents
    # ==========================================
    def ingest_documents(self, uploaded_files, project_id: int, progress=gr.Progress()):
        if not uploaded_files:
            return (
                self.database_status(project_id),
                gr.update(choices=self.get_document_choices(project_id)),
                gr.update(choices=self.get_project_choices()),
                self.get_workspace_banner(project_id, self.current_conv_id),
                None,
                "### PDF seçilmedi\nLütfen en az bir PDF dosyası seçin.",
            )

        if not isinstance(uploaded_files, list):
            uploaded_files = [uploaded_files]

        added_docs = []
        skipped_docs = []

        try:
            for file_idx, file_item in enumerate(uploaded_files, start=1):
                pdf_path = Path(file_item)
                if pdf_path.suffix.lower() != ".pdf":
                    skipped_docs.append(f"{pdf_path.name} (PDF formatında değil)")
                    continue

                file_hash = calculate_file_hash(pdf_path)
                existing_doc = get_document_by_hash(file_hash, project_id=project_id)
                if existing_doc:
                    skipped_docs.append(f"{pdf_path.name} (Bu projede zaten mevcut)")
                    continue

                progress(
                    0.05 + 0.1 * (file_idx / len(uploaded_files)),
                    desc=f"PDF okunuyor: {pdf_path.name}",
                )
                text = read_pdf_text(pdf_path)
                chunks = chunk_text(text)

                if not chunks:
                    skipped_docs.append(f"{pdf_path.name} (Okunabilir metin yok)")
                    continue

                with self.lock:
                    doc_id = save_document_and_chunks(
                        filename=pdf_path.name,
                        chunks=chunks,
                        filepath=str(pdf_path),
                        file_hash=file_hash,
                        project_id=project_id,
                    )
                    added_docs.append(f"{pdf_path.name} ({len(chunks)} chunk)")

            # Generate embeddings for newly added chunks
            from embed_chunks import get_chunks_without_embeddings

            unembedded = get_chunks_without_embeddings()
            if unembedded:
                self.ensure_models(progress)
                with self.lock:
                    for idx, (chunk_id, chunk_content) in enumerate(
                        unembedded, start=1
                    ):
                        progress(
                            0.2 + (0.75 * idx / len(unembedded)),
                            desc=f"Embedding üretiliyor: {idx}/{len(unembedded)}",
                        )
                        response = self.embedding_client.generate_embedding(
                            chunk_content
                        )
                        save_embedding(chunk_id, response.data[0].embedding)

            with self.lock:
                self.chunks = self._load_chunks_for_project(project_id)

            progress(1.0, desc="İşlem tamamlandı")

            summary_parts = []
            if added_docs:
                summary_parts.append(f"**Eklenen Belgeler:** {', '.join(added_docs)}")
            if skipped_docs:
                summary_parts.append(f"**Atlanan Belgeler:** {', '.join(skipped_docs)}")
            status_msg = "\n\n".join(summary_parts) if summary_parts else "İşlem tamamlandı."

            return (
                self.database_status(project_id),
                gr.update(choices=self.get_document_choices(project_id), value=None),
                gr.update(choices=self.get_project_choices()),
                self.get_workspace_banner(project_id, self.current_conv_id),
                None,
                status_msg,
            )
        except Exception as error:
            return (
                self.database_status(project_id),
                gr.update(choices=self.get_document_choices(project_id)),
                gr.update(choices=self.get_project_choices()),
                self.get_workspace_banner(project_id, self.current_conv_id),
                None,
                f"### Hata oluştu\n`{error}`",
            )

    def delete_selected_document(self, doc_id: int, project_id: int):
        if not doc_id:
            return (
                self.database_status(project_id),
                gr.update(choices=self.get_document_choices(project_id)),
                gr.update(choices=self.get_project_choices()),
                self.get_workspace_banner(project_id, self.current_conv_id),
                "Lütfen silinecek bir belge seçin.",
            )

        with self.lock:
            success = delete_document(doc_id)
            self.chunks = self._load_chunks_for_project(project_id)

        msg = (
            f"Belge (ID: {doc_id}) ve ilişkili tüm chunk kayıtları silindi."
            if success
            else f"Belge (ID: {doc_id}) bulunamadı."
        )

        return (
            self.database_status(project_id),
            gr.update(choices=self.get_document_choices(project_id), value=None),
            gr.update(choices=self.get_project_choices()),
            self.get_workspace_banner(project_id, self.current_conv_id),
            msg,
        )

    # ==========================================
    # Multi-Turn Streaming RAG Answering
    # ==========================================
    def answer(
        self,
        question: str,
        history: list[dict],
        conv_id: int,
        project_id: int,
        progress=gr.Progress(),
    ):
        question = (question or "").strip()
        history = list(history or [])

        if not question:
            yield "", history, self.render_empty_inspector(), gr.update()
            return

        # Ensure conversation exists
        if not conv_id:
            with self.lock:
                new_c = create_conversation(project_id, question[:30])
                conv_id = new_c["id"]
                self.current_conv_id = conv_id

        # Save user message to database
        save_message(conv_id, "user", question)

        # Update conversation title if it's still default
        conv_obj = get_conversation(conv_id)
        if conv_obj and conv_obj["title"] in ("Yeni Sohbet", "İlk Sohbet"):
            new_title = question[:35] + ("…" if len(question) > 35 else "")
            update_conversation_title(conv_id, new_title)

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": "Yanıt hazırlanıyor…"})

        initial_inspector_html = html_template.render(
            instructions=current_system_prompt(),
            documents=[],
            query=question,
        )
        yield "", history, initial_inspector_html, gr.update(
            choices=self.get_conversation_choices(project_id), value=conv_id
        )

        try:
            self.ensure_models(progress)

            with self.lock:
                if not self.chunks:
                    self.chunks = self._load_chunks_for_project(project_id)

                if not self.chunks:
                    msg = "Bu projede henüz hiç belge bulunmuyor. Sol menüden PDF yükleyebilirsiniz."
                    history[-1] = {"role": "assistant", "content": msg}
                    save_message(conv_id, "assistant", msg)
                    inspector_html = html_template.render(
                        instructions=current_system_prompt(),
                        documents=[],
                        query=question,
                    )
                    yield "", history, inspector_html, gr.update()
                    return

                top_chunks = retrieve_top_chunks(
                    chunks=self.chunks,
                    embedding_client=self.embedding_client,
                    query=question,
                    top_k=4,
                    min_score=MIN_SIMILARITY_SCORE,
                )

                inspector_html = html_template.render(
                    instructions=current_system_prompt(),
                    documents=top_chunks,
                    query=question,
                )

                if not top_chunks:
                    history[-1] = {"role": "assistant", "content": FALLBACK_MESSAGE}
                    save_message(conv_id, "assistant", FALLBACK_MESSAGE)
                    yield "", history, inspector_html, gr.update()
                    return

                context = build_context(top_chunks)

                # Build context window with sliding window conversation history
                messages = build_messages_with_context(
                    system_prompt=current_system_prompt(),
                    context=context,
                    history=history[:-2],  # exclude current question & placeholder
                    current_question=question,
                    max_history_turns=6,
                )

                answer_parts = []
                for chunk in self.chat_client.complete_streaming_chat(messages):
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        answer_parts.append(delta)
                        history[-1] = {
                            "role": "assistant",
                            "content": "".join(answer_parts),
                        }
                        yield "", history, inspector_html, gr.update(
                            choices=self.get_conversation_choices(project_id),
                            value=conv_id,
                        )

                final_answer = "".join(answer_parts).strip()
                if not final_answer:
                    final_answer = FALLBACK_MESSAGE
                    history[-1] = {"role": "assistant", "content": final_answer}

                # Save assistant message to database
                save_message(
                    conv_id, "assistant", final_answer, source_info=inspector_html
                )

                yield "", history, inspector_html, gr.update(
                    choices=self.get_conversation_choices(project_id), value=conv_id
                )

        except Exception as error:
            err_msg = f"Model yanıt verirken hata oluştu: {error}"
            history[-1] = {"role": "assistant", "content": err_msg}
            err_html = f"<div class='rag-badge badge-query'><b>Hata:</b> {error}</div>"
            yield "", history, err_html, gr.update()


def build_app():
    service = LocalRAGService()

    with gr.Blocks(title=APP_NAME) as demo:
        with gr.Row(elem_classes=["app-shell"]):
            # ChatGPT-style navigation rail
            with gr.Column(scale=3, min_width=240, elem_classes=["left-rail"]):
                gr.HTML(
                    "<div class='brand-lockup'><h1>◈ Local RAG</h1>"
                    "<p>Belgelerinle konuş. Tamamen yerel.</p></div>"
                )

                new_conv_btn = gr.Button(
                    "＋  Yeni sohbet",
                    variant="primary",
                    size="lg",
                    elem_classes=["rail-button"],
                )

                gr.HTML("<div class='section-kicker'>Çalışma alanı</div>")
                project_dropdown = gr.Dropdown(
                    label="Aktif proje",
                    choices=service.get_project_choices(),
                    value=service.current_project_id,
                    interactive=True,
                    show_label=False,
                )

                with gr.Accordion("Yeni çalışma alanı", open=False):
                    new_proj_name = gr.Textbox(
                        label="Ad", placeholder="Örn. Ders notları"
                    )
                    new_proj_desc = gr.Textbox(
                        label="Açıklama",
                        placeholder="Bu alanda hangi belgeler var?",
                    )
                    create_proj_btn = gr.Button(
                        "Oluştur", variant="primary", size="sm"
                    )

                gr.HTML("<div class='section-kicker'>Sohbetler</div>")
                conv_dropdown = gr.Dropdown(
                    label="Sohbet seç",
                    choices=service.get_conversation_choices(service.current_project_id),
                    value=service.current_conv_id,
                    interactive=True,
                    show_label=False,
                )
                delete_conv_btn = gr.Button(
                    "Sohbeti sil", size="sm", elem_classes=["rail-button", "danger-button"]
                )

                with gr.Accordion("Ayarlar", open=False):
                    delete_proj_btn = gr.Button(
                        "Çalışma alanını sil", variant="stop", size="sm"
                    )

            # Focused conversation stage
            with gr.Column(scale=8, min_width=500, elem_classes=["chat-stage"]):
                with gr.Row(elem_classes=["chat-topbar"]):
                    workspace_banner = gr.Markdown(
                        value=service.get_workspace_banner(
                            service.current_project_id, service.current_conv_id
                        ),
                        elem_classes=["workspace-banner"],
                    )
                    clear_button = gr.Button(
                        "Temizle", variant="secondary", size="sm", min_width=90
                    )

                chatbot = gr.Chatbot(
                    label="Sohbet",
                    value=[
                        {"role": m["role"], "content": m["content"]}
                        for m in get_conversation_messages(service.current_conv_id)
                    ],
                    elem_id="chatbot",
                    show_label=False,
                    height=620,
                    placeholder=(
                        "<div style='text-align:center;padding-top:18vh'>"
                        "<div style='font-size:2rem'>◈</div>"
                        "<h2 style='margin:.6rem 0 .25rem'>Belgelerine bir şey sor</h2>"
                        "<p style='opacity:.6'>Yanıtlar yalnızca eklediğin kaynaklara dayanır.</p>"
                        "</div>"
                    ),
                )

                with gr.Row(elem_classes=["composer"]):
                    question_input = gr.Textbox(
                        label="Mesaj",
                        placeholder="Belgelerin hakkında sor…",
                        lines=1,
                        max_lines=6,
                        scale=10,
                        show_label=False,
                        elem_id="question-box",
                    )
                    ask_button = gr.Button(
                        "↑", variant="primary", elem_id="send-button", min_width=46
                    )

            # NotebookLM-style source rail
            with gr.Column(scale=4, min_width=300, elem_classes=["source-rail"]):
                gr.HTML(
                    "<div class='source-header'><h2>Kaynaklar</h2>"
                    "<p>Bu çalışma alanının bilgi tabanı</p></div>"
                )
                pdf_upload = gr.File(
                    label="PDF ekle",
                    file_types=[".pdf"],
                    file_count="multiple",
                )
                upload_button = gr.Button(
                    "＋ Kaynakları ekle", variant="primary", size="sm"
                )

                document_status = gr.Markdown(
                    value=service.database_status(service.current_project_id),
                    elem_classes=["status-card"],
                )

                doc_dropdown = gr.Dropdown(
                    label="Kaynak yönetimi",
                    choices=service.get_document_choices(service.current_project_id),
                    value=None,
                    interactive=True,
                )
                delete_doc_btn = gr.Button(
                    "Seçili kaynağı kaldır", variant="secondary", size="sm"
                )

                with gr.Accordion("Yanıtta kullanılan parçalar", open=True):
                    prompt_html = gr.HTML(
                        value=service.render_empty_inspector(),
                    )

        project_dropdown.change(
            fn=service.switch_project,
            inputs=[project_dropdown],
            outputs=[
                project_dropdown,
                conv_dropdown,
                workspace_banner,
                document_status,
                doc_dropdown,
                chatbot,
                prompt_html,
            ],
        )

        create_proj_btn.click(
            fn=service.create_new_project_action,
            inputs=[new_proj_name, new_proj_desc],
            outputs=[
                project_dropdown,
                conv_dropdown,
                workspace_banner,
                document_status,
                doc_dropdown,
                chatbot,
                prompt_html,
            ],
        )

        delete_proj_btn.click(
            fn=service.delete_project_action,
            inputs=[project_dropdown],
            outputs=[
                project_dropdown,
                conv_dropdown,
                workspace_banner,
                document_status,
                doc_dropdown,
                chatbot,
                prompt_html,
            ],
        )

        conv_dropdown.change(
            fn=service.switch_conversation,
            inputs=[conv_dropdown, project_dropdown],
            outputs=[chatbot, workspace_banner, prompt_html],
        )

        new_conv_btn.click(
            fn=service.new_conversation_action,
            inputs=[project_dropdown],
            outputs=[conv_dropdown, chatbot, workspace_banner, prompt_html],
        )

        delete_conv_btn.click(
            fn=service.delete_conversation_action,
            inputs=[conv_dropdown, project_dropdown],
            outputs=[conv_dropdown, chatbot, workspace_banner],
        )

        upload_button.click(
            fn=service.ingest_documents,
            inputs=[pdf_upload, project_dropdown],
            outputs=[
                document_status,
                doc_dropdown,
                project_dropdown,
                workspace_banner,
                pdf_upload,
                prompt_html,
            ],
        )

        delete_doc_btn.click(
            fn=service.delete_selected_document,
            inputs=[doc_dropdown, project_dropdown],
            outputs=[
                document_status,
                doc_dropdown,
                project_dropdown,
                workspace_banner,
                prompt_html,
            ],
        )

        ask_event = ask_button.click(
            fn=service.answer,
            inputs=[
                question_input,
                chatbot,
                conv_dropdown,
                project_dropdown,
            ],
            outputs=[question_input, chatbot, prompt_html, conv_dropdown],
        )
        question_input.submit(
            fn=service.answer,
            inputs=[
                question_input,
                chatbot,
                conv_dropdown,
                project_dropdown,
            ],
            outputs=[question_input, chatbot, prompt_html, conv_dropdown],
        )

        clear_button.click(
            fn=lambda: ([], service.render_empty_inspector()),
            outputs=[chatbot, prompt_html],
            cancels=[ask_event],
        )

    return demo


if __name__ == "__main__":
    print("⏳ [3/3] Web arayüzü kuruluyor...", flush=True)
    demo = build_app()

    print("\n" + "=" * 65, flush=True)
    print("🚀 Local RAG hazır!", flush=True)
    print("👉 Tarayıcı Adresi: http://127.0.0.1:7860", flush=True)
    print("   (Uygulamayı kapatmak için terminalde Ctrl + C tuşlayın)", flush=True)
    print("=" * 65 + "\n", flush=True)

    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        inbrowser=True,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            neutral_hue="slate",
            radius_size="lg",
        ),
        css=CUSTOM_CSS,
        footer_links=[],
    )
