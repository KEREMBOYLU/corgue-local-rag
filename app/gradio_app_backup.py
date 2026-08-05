import atexit
import os
from pathlib import Path
import threading

os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

import gradio as gr

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


APP_NAME = "ContextKit"
FALLBACK_MESSAGE = "Bu sorunun cevabını projedeki belgelerde bulamadım."

def current_system_prompt():
    return get_system_prompt()

CUSTOM_CSS = """
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
}
.hero {
    padding: 1.0rem 0 0.2rem;
}
.hero h1 {
    font-size: 2.1rem !important;
    letter-spacing: -0.04em;
    margin-bottom: 0.2rem !important;
}
.hero p {
    color: #64748b;
    font-size: 0.98rem;
}
.workspace-banner {
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    padding: 0.75rem 1.1rem;
    background: var(--background-fill-secondary);
    color: var(--body-text-color);
    margin-bottom: 0.8rem;
    font-size: 0.95rem;
}
.source-card {
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    padding: 0.85rem 1.1rem;
    background: var(--background-fill-secondary);
    color: var(--body-text-color);
}
.sidebar-panel {
    border: 1px solid var(--border-color-primary);
    border-radius: 16px;
    padding: 0.8rem;
}
#chatbot {
    border-radius: 16px;
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

        # Ensure at least one conversation exists for default project
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
                "",
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
            "Kaynak bilgisi soru sorulduğunda burada görünecektir.",
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
            return [], self.get_workspace_banner(project_id, None), ""

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
            "Kaynak bilgisi soru sorulduğunda burada görünecektir.",
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
            "Yeni sohbet başlatıldı. Sorunuzu yazabilirsiniz.",
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
            yield "", history, "Bir soru yazmalısınız.", gr.update()
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
        yield "", history, "İlgili döküman bölümleri taranıyor…", gr.update(
            choices=self.get_conversation_choices(project_id), value=conv_id
        )

        try:
            self.ensure_models(progress)

            with self.lock:
                # Reload chunks for project if empty
                if not self.chunks:
                    self.chunks = self._load_chunks_for_project(project_id)

                if not self.chunks:
                    msg = "Bu projede henüz hiç belge bulunmuyor. Sol menüden PDF yükleyebilirsiniz."
                    history[-1] = {"role": "assistant", "content": msg}
                    save_message(conv_id, "assistant", msg)
                    yield "", history, msg, gr.update()
                    return

                top_chunks = retrieve_top_chunks(
                    chunks=self.chunks,
                    embedding_client=self.embedding_client,
                    query=question,
                    top_k=3,
                    min_score=MIN_SIMILARITY_SCORE,
                )

                if not top_chunks:
                    history[-1] = {"role": "assistant", "content": FALLBACK_MESSAGE}
                    save_message(conv_id, "assistant", FALLBACK_MESSAGE)
                    yield (
                        "",
                        history,
                        f"Eşiği geçen kaynak bulunamadı (Min. Skor: {MIN_SIMILARITY_SCORE:.2f})",
                        gr.update(),
                    )
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

                # Format source reference card
                sources_md_list = []
                for idx, c in enumerate(top_chunks, start=1):
                    sources_md_list.append(
                        f"**{idx}. {c['source']}** (Parça #{c['chunk_index']} · Benzerlik: `{c['score']:.4f}`)"
                    )
                source_text = "### 📑 Kullanılan Kaynaklar:\n" + "\n".join(sources_md_list)

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
                        yield "", history, source_text, gr.update(
                            choices=self.get_conversation_choices(project_id),
                            value=conv_id,
                        )

                final_answer = "".join(answer_parts).strip()
                if not final_answer:
                    final_answer = FALLBACK_MESSAGE
                    history[-1] = {"role": "assistant", "content": final_answer}

                # Save assistant message to database
                save_message(
                    conv_id, "assistant", final_answer, source_info=source_text
                )

                yield "", history, source_text, gr.update(
                    choices=self.get_conversation_choices(project_id), value=conv_id
                )

        except Exception as error:
            err_msg = f"Model yanıt verirken hata oluştu: {error}"
            history[-1] = {"role": "assistant", "content": err_msg}
            yield "", history, f"### Hata\n`{error}`", gr.update()


def build_app():
    service = LocalRAGService()

    with gr.Blocks(title=APP_NAME) as demo:
        # Header Hero
        with gr.Row(elem_classes=["hero"]):
            with gr.Column():
                gr.Markdown(
                    f"# 🚀 {APP_NAME} <span style='font-size:1.1rem; color:#6366f1; font-weight:normal;'>Local RAG Workspace</span>\n"
                    "İzole Çalışma Alanları (Projects), Çoklu Sohbetler ve Yerel LLM Bağlam Yönetimi."
                )

        # Workspace Banner
        workspace_banner = gr.Markdown(
            value=service.get_workspace_banner(
                service.current_project_id, service.current_conv_id
            ),
            elem_classes=["workspace-banner"],
        )

        with gr.Row():
            # ==========================================
            # LEFT SIDEBAR: Projects & Document Management
            # ==========================================
            with gr.Column(scale=4, elem_classes=["sidebar-panel"]):
                # 1. Project Selection & Management
                gr.Markdown("### 📁 1. Projeler / Çalışma Alanları")
                project_dropdown = gr.Dropdown(
                    label="Aktif Proje Seçin",
                    choices=service.get_project_choices(),
                    value=service.current_project_id,
                    interactive=True,
                )

                with gr.Accordion("➕ Yeni Proje Oluştur", open=False):
                    new_proj_name = gr.Textbox(
                        label="Proje Adı", placeholder="örn. Hukuk Dökümanları"
                    )
                    new_proj_desc = gr.Textbox(
                        label="Açıklama (Opsiyonel)",
                        placeholder="örn. Mahkeme kararları ve kanun maddeleri",
                    )
                    create_proj_btn = gr.Button(
                        "Projeyi Oluştur", variant="primary", size="sm"
                    )

                delete_proj_btn = gr.Button("🗑️ Bu Projeyi Sil", variant="stop", size="sm")

                gr.Markdown("---")

                # 2. Multi-Thread Conversations
                gr.Markdown("### 💬 2. Bu Projedeki Sohbetler")
                with gr.Row():
                    new_conv_btn = gr.Button(
                        "➕ Yeni Sohbet", variant="primary", size="sm"
                    )
                    delete_conv_btn = gr.Button("🗑️ Sil", variant="secondary", size="sm")

                conv_dropdown = gr.Dropdown(
                    label="Sohbet Seç",
                    choices=service.get_conversation_choices(service.current_project_id),
                    value=service.current_conv_id,
                    interactive=True,
                )

                gr.Markdown("---")

                # 3. Project Document Management
                gr.Markdown("### 📄 3. Proje Belgeleri (PDF)")
                pdf_upload = gr.File(
                    label="Bu Projeye PDF Yükle",
                    file_types=[".pdf"],
                    file_count="multiple",
                )
                upload_button = gr.Button(
                    "📥 Belgeyi Projeye Ekle", variant="secondary", size="sm"
                )

                doc_dropdown = gr.Dropdown(
                    label="Projeden Belge Sil",
                    choices=service.get_document_choices(service.current_project_id),
                    value=None,
                    interactive=True,
                )
                delete_doc_btn = gr.Button(
                    "🗑️ Seçili Belgeyi Sil", variant="secondary", size="sm"
                )

                document_status = gr.Markdown(
                    value=service.database_status(service.current_project_id),
                    elem_classes=["status-card"],
                )

            # ==========================================
            # RIGHT MAIN: Chatbot & Context
            # ==========================================
            with gr.Column(scale=8):
                chatbot = gr.Chatbot(
                    label="Sohbet Geçmişi",
                    value=[
                        {"role": m["role"], "content": m["content"]}
                        for m in get_conversation_messages(service.current_conv_id)
                    ],
                    elem_id="chatbot",
                    height=520,
                )

                with gr.Row():
                    question_input = gr.Textbox(
                        label="Sorunuz",
                        placeholder="Bu projedeki belgeler hakkında bir soru yazın... (Enter'a basabilirsiniz)",
                        lines=2,
                        scale=9,
                    )
                    with gr.Column(scale=3, min_width=120):
                        ask_button = gr.Button(
                            "💬 Gönder", variant="primary", size="lg"
                        )
                        clear_button = gr.Button(
                            "🧹 Temizle", variant="secondary", size="sm"
                        )

                source_info = gr.Markdown(
                    value="Kaynak bilgisi soru sorulduğunda burada görünecektir.",
                    elem_classes=["source-card"],
                )

        # ==========================================
        # EVENT BINDINGS
        # ==========================================

        # Switch project
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
                source_info,
            ],
        )

        # Create new project
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
                source_info,
            ],
        )

        # Delete project
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
                source_info,
            ],
        )

        # Switch conversation
        conv_dropdown.change(
            fn=service.switch_conversation,
            inputs=[conv_dropdown, project_dropdown],
            outputs=[chatbot, workspace_banner, source_info],
        )

        # New conversation
        new_conv_btn.click(
            fn=service.new_conversation_action,
            inputs=[project_dropdown],
            outputs=[conv_dropdown, chatbot, workspace_banner, source_info],
        )

        # Delete conversation
        delete_conv_btn.click(
            fn=service.delete_conversation_action,
            inputs=[conv_dropdown, project_dropdown],
            outputs=[conv_dropdown, chatbot, workspace_banner],
        )

        # Upload & Ingest PDF
        upload_button.click(
            fn=service.ingest_documents,
            inputs=[pdf_upload, project_dropdown],
            outputs=[
                document_status,
                doc_dropdown,
                project_dropdown,
                workspace_banner,
                pdf_upload,
                source_info,
            ],
        )

        # Delete document
        delete_doc_btn.click(
            fn=service.delete_selected_document,
            inputs=[doc_dropdown, project_dropdown],
            outputs=[
                document_status,
                doc_dropdown,
                project_dropdown,
                workspace_banner,
                source_info,
            ],
        )

        # Ask question (button and enter key)
        ask_event = ask_button.click(
            fn=service.answer,
            inputs=[
                question_input,
                chatbot,
                conv_dropdown,
                project_dropdown,
            ],
            outputs=[question_input, chatbot, source_info, conv_dropdown],
        )
        question_input.submit(
            fn=service.answer,
            inputs=[
                question_input,
                chatbot,
                conv_dropdown,
                project_dropdown,
            ],
            outputs=[question_input, chatbot, source_info, conv_dropdown],
        )

        # Clear chat view
        clear_button.click(
            fn=lambda: ([], "Kaynak bilgisi sıfırlandı."),
            outputs=[chatbot, source_info],
            cancels=[ask_event],
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
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
