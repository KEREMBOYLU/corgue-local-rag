const state = {
  language: localStorage.getItem("corgue-language") === "tr" ? "tr" : "en",
  projectId: null,
  conversationId: null,
  projects: [],
  conversations: [],
  documents: [],
  messages: [],
  latestSources: [],
  models: [],
  catalogModels: [],
  selectedModel: "qwen2.5-1.5b",
  busy: false,
  chatAbortController: null,
  modelBusy: false,
  modelBusyId: null,
  modelProgress: {},
  modelStatusTimer: null,
  catalogStatusTimer: null,
  projectsCollapsed: false,
  conversationsCollapsed: false,
  systemPromptSource: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const translations = {
  en: {
    "common.close": "Close",
    "common.error": "The operation could not be completed.",
    "projects.title": "Projects",
    "projects.toggle": "Collapse / expand projects",
    "projects.options": "Project options",
    "projects.add": "Add a new project",
    "projects.new": "New Project",
    "projects.manage": "Manage All Projects",
    "projects.deleteActive": "Delete Active Project",
    "projects.workspace": "Workspace",
    "projects.defaultName": "General Project",
    "projects.lastCannotDelete": "You cannot delete the last remaining project.",
    "projects.deleteConfirm": "Delete ‘{name}’ and all of its chats?",
    "projects.deleted": "Project deleted.",
    "projects.nameRequired": "Give the project a name.",
    "projects.created": "‘{name}’ was created.",
    "projects.deleteWorkspaceConfirm": "Delete this workspace and all of its chats?",
    "projects.workspaceDeleted": "Workspace deleted.",
    "chats.title": "Chats",
    "chats.toggle": "Collapse / expand chats",
    "chats.new": "Start a new chat",
    "chat.newTitle": "New Chat",
    "chat.subtitle": "Answers grounded in your sources",
    "chat.rename": "Rename chat",
    "chat.delete": "Delete chat",
    "chat.renameAction": "Rename",
    "chat.deleteAction": "Delete Chat",
    "chat.renamePrompt": "Change the chat title:",
    "chat.deleteConfirm": "Delete this chat?",
    "chat.titleUpdated": "Title updated.",
    "chat.deleted": "Chat deleted.",
    "chat.groundedSubtitle": "{project} · {count} document source(s)",
    "chat.disclaimer": "Answers are generated only from your local documents.",
    "empty.title": "Start chatting with your documents",
    "empty.description": "Summarize your sources, explain concepts, or find specific information.",
    "empty.suggestion": "Briefly summarize these documents",
    "composer.placeholder": "Ask about your sources…",
    "composer.message": "Message",
    "composer.send": "Send",
    "composer.stop": "Stop response",
    "chat.thinking": "Thinking",
    "chat.stopped": "Response stopped.",
    "chat.noResponse": "No response was received.",
    "chat.serverUnavailable": "Could not connect to the server: {message}",
    "sources.tab": "Documents",
    "sources.title": "Documents ({count})",
    "sources.search": "Search sources…",
    "sources.upload": "Add a PDF source",
    "sources.uploadHint": "Choose a file or drag it here",
    "sources.chunkReady": "{count} chunks · Ready",
    "sources.remove": "Remove source",
    "sources.delete": "Delete source",
    "sources.none": "No PDF sources have been added yet.",
    "sources.noMatch": "No matching sources.",
    "sources.processing": "Processing PDF and creating local embeddings…",
    "sources.added": "{count} document(s) added and embeddings created.",
    "sources.removeConfirm": "Remove this PDF source?",
    "sources.removed": "Source removed.",
    "citations.title": "Used in this answer",
    "citations.titleCount": "Used in this answer ({count} chunks)",
    "citations.empty": "Citations used for an answer will appear here.",
    "citations.chunk": "Chunk #{index} · Similarity: {score}%",
    "projectDialog.title": "Projects and Workspaces",
    "projectDialog.description": "Organize your documents and chats by project.",
    "projectDialog.createTitle": "Create a New Project",
    "projectDialog.namePlaceholder": "e.g. Research Notes, Product Docs",
    "projectDialog.descriptionPlaceholder": "Short description (optional)",
    "projectDialog.create": "Create Project",
    "projectDialog.stats": "{documents} documents · {chunks} chunks · {chats} chats",
    "settings.label": "Settings",
    "settings.title": "Application Settings",
    "settings.description": "Manage the interface language, system prompt, and local models.",
    "settings.tabs": "Settings tabs",
    "settings.general": "General",
    "settings.models": "Models",
    "settings.language": "Language",
    "settings.languageHelp": "The interface language changes immediately and is remembered on this device.",
    "settings.reset": "Restore Default",
    "settings.save": "Save",
    "settings.sourceSaved": "Source: custom prompt saved in the application",
    "settings.sourceEnvironment": "Source: SYSTEM_PROMPT environment variable",
    "settings.sourceDefault": "Source: safe default prompt",
    "settings.promptRequired": "System Prompt cannot be empty.",
    "settings.promptSaved": "System Prompt saved.",
    "settings.promptReset": "System Prompt restored to default.",
    "models.change": "Change model",
    "models.local": "Local LLM Models",
    "models.other": "Other Models",
    "models.catalogDescription": "Chat models available in the Foundry Local catalog",
    "models.embeddingHint": "The embedding model runs only while documents are being added.",
    "models.loadingCatalog": "Loading catalog…",
    "models.noSize": "Size unavailable",
    "models.preparing": "Preparing…",
    "models.ready": "Ready",
    "models.download": "Download",
    "models.unavailable": "Not in catalog",
    "models.noChat": "No chat models were found in the catalog.",
    "models.preparingToast": "Preparing {name}…",
    "models.downloadingToast": "Downloading {name}…",
    "models.readyToast": "{name} is ready to use.",
    "models.downloadFailed": "The model could not be downloaded.",
    "inspector.tab": "Context Window",
    "inspector.title": "Model Context Window",
    "inspector.description": "Document chunks, chat history, and token usage sent to the model",
    "inspector.activeModel": "Active Model",
    "inspector.usage": "Context Usage",
    "inspector.chunks": "Chunks Injected into Context",
    "inspector.history": "Chat History Context",
    "inspector.noQuestion": "No question has been asked yet.",
    "inspector.directContext": "The latest answer used direct conversation context.",
    "inspector.noDirectMatch": "No directly matching chunk was found. The answer uses chat history context.",
    "inspector.chunk": "Chunk #{index} · {score}%",
    "inspector.historyDefault": "The last 6 chat turns are kept in memory and sent to the model.",
    "inspector.historyMessages": "The last {count} chat messages are included in context (~{tokens} tokens).",
    "inspector.historyIncluded": "The last {count} messages were included in the context window."
  },
  tr: {
    "common.close": "Kapat", "common.error": "İşlem tamamlanamadı.",
    "projects.title": "Projeler", "projects.toggle": "Projeleri daralt / genişlet", "projects.options": "Proje seçenekleri", "projects.add": "Yeni proje ekle", "projects.new": "Yeni Proje", "projects.manage": "Tüm Projeleri Yönet", "projects.deleteActive": "Aktif Projeyi Sil", "projects.workspace": "Çalışma alanı", "projects.defaultName": "Genel Proje", "projects.lastCannotDelete": "Son kalan projeyi silemezsiniz.", "projects.deleteConfirm": "‘{name}’ projesi ve tüm sohbetleri silinsin mi?", "projects.deleted": "Proje silindi.", "projects.nameRequired": "Projeye bir ad verin.", "projects.created": "‘{name}’ projesi oluşturuldu.", "projects.deleteWorkspaceConfirm": "Bu çalışma alanı ve tüm sohbetleri silinsin mi?", "projects.workspaceDeleted": "Çalışma alanı silindi.",
    "chats.title": "Sohbetler", "chats.toggle": "Sohbetleri daralt / genişlet", "chats.new": "Yeni sohbet başlat", "chat.newTitle": "Yeni Sohbet", "chat.subtitle": "Kaynaklarına dayalı yanıtlar", "chat.rename": "Sohbeti yeniden adlandır", "chat.delete": "Sohbeti sil", "chat.renameAction": "Yeniden Adlandır", "chat.deleteAction": "Sohbeti Sil", "chat.renamePrompt": "Sohbet başlığını değiştirin:", "chat.deleteConfirm": "Bu sohbet silinsin mi?", "chat.titleUpdated": "Başlık güncellendi.", "chat.deleted": "Sohbet silindi.", "chat.groundedSubtitle": "{project} · {count} belge kaynaklı", "chat.disclaimer": "Yanıtlar yalnızca yerel belgelerinden üretilir.",
    "empty.title": "Belgelerinle konuşmaya başla", "empty.description": "Kaynaklarından özet çıkar, kavramları açıkla veya belirli bir bilgiyi bul.", "empty.suggestion": "Bu belgeleri kısaca özetle", "composer.placeholder": "Kaynakların hakkında sor…", "composer.message": "Mesaj", "composer.send": "Gönder", "composer.stop": "Yanıtı durdur", "chat.thinking": "Düşünüyor", "chat.stopped": "Yanıt durduruldu.", "chat.noResponse": "Yanıt alınamadı.", "chat.serverUnavailable": "Sunucuya bağlanılamadı: {message}",
    "sources.tab": "Belgeler", "sources.title": "Belgeler ({count} Belge)", "sources.search": "Kaynaklarda ara…", "sources.upload": "PDF kaynağı ekle", "sources.uploadHint": "Dosyayı seç veya buraya sürükle", "sources.chunkReady": "{count} parça · Hazır", "sources.remove": "Kaynağı kaldır", "sources.delete": "Kaynağı sil", "sources.none": "Henüz PDF kaynağı eklenmedi.", "sources.noMatch": "Eşleşen kaynak yok.", "sources.processing": "PDF işleniyor ve yerel embedding’ler oluşturuluyor…", "sources.added": "{count} belge eklendi ve embedding’leri hazırlandı.", "sources.removeConfirm": "Bu PDF kaynağı kaldırılsın mı?", "sources.removed": "Kaynak kaldırıldı.",
    "citations.title": "Bu yanıtta kullanılanlar", "citations.titleCount": "Bu yanıtta kullanılanlar ({count} parça)", "citations.empty": "Bir soru sorduğunda kullanılan alıntılar burada görünecek.", "citations.chunk": "Parça #{index} · Benzerlik: %{score}",
    "projectDialog.title": "Projeler ve Çalışma Alanları", "projectDialog.description": "Belgelerini ve sohbetlerini projelere göre ayır.", "projectDialog.createTitle": "Yeni Proje Oluştur", "projectDialog.namePlaceholder": "Örn. Araştırma Notları, Ürün Belgeleri", "projectDialog.descriptionPlaceholder": "Kısa açıklama (isteğe bağlı)", "projectDialog.create": "Projeyi Oluştur", "projectDialog.stats": "{documents} belge · {chunks} parça · {chats} sohbet",
    "settings.label": "Ayarlar", "settings.title": "Uygulama Ayarları", "settings.description": "Arayüz dilini, system prompt’u ve yerel modelleri yönetin.", "settings.tabs": "Ayar sekmeleri", "settings.general": "Genel", "settings.models": "Modeller", "settings.language": "Dil", "settings.languageHelp": "Arayüz dili anında değişir ve bu cihazda hatırlanır.", "settings.reset": "Varsayılana Dön", "settings.save": "Kaydet", "settings.sourceSaved": "Kaynak: uygulamaya kaydedilmiş özel prompt", "settings.sourceEnvironment": "Kaynak: SYSTEM_PROMPT ortam değişkeni", "settings.sourceDefault": "Kaynak: güvenli varsayılan prompt", "settings.promptRequired": "System Prompt boş olamaz.", "settings.promptSaved": "System Prompt kaydedildi.", "settings.promptReset": "System Prompt varsayılana döndürüldü.",
    "models.change": "Model değiştir", "models.local": "Yerel LLM Modelleri", "models.other": "Diğer Modeller", "models.catalogDescription": "Foundry Local kataloğundaki sohbet modelleri", "models.embeddingHint": "Embedding modeli yalnızca belge ekleme sırasında çalışır.", "models.loadingCatalog": "Katalog yükleniyor…", "models.noSize": "Boyut bilgisi yok", "models.preparing": "Hazırlanıyor…", "models.ready": "Hazır", "models.download": "İndir", "models.unavailable": "Katalogda yok", "models.noChat": "Katalogda sohbet modeli bulunamadı.", "models.preparingToast": "{name} hazırlanıyor…", "models.downloadingToast": "{name} indiriliyor…", "models.readyToast": "{name} kullanıma hazır.", "models.downloadFailed": "Model indirilemedi.",
    "inspector.tab": "Bağlam Penceresi", "inspector.title": "Model Bağlam Penceresi", "inspector.description": "Modele gönderilen doküman parçaları, sohbet geçmişi ve token kullanımı", "inspector.activeModel": "Aktif Model", "inspector.usage": "Bağlam Kullanımı", "inspector.chunks": "Bağlama Enjekte Edilen Parçalar", "inspector.history": "Sohbet Geçmişi Bağlamı", "inspector.noQuestion": "Henüz bir soru sorulmadı.", "inspector.directContext": "Son yanıtta doğrudan konuşma bağlamı kullanıldı.", "inspector.noDirectMatch": "Doğrudan eşleşen parça bulunamadı. Yanıt sohbet geçmişi bağlamını kullanıyor.", "inspector.chunk": "Parça #{index} · %{score}", "inspector.historyDefault": "Son 6 sohbet turu hafızada tutularak modele aktarılır.", "inspector.historyMessages": "Son {count} sohbet mesajı bağlama dahil ediliyor (~{tokens} token).", "inspector.historyIncluded": "Son {count} mesaj bağlam penceresine dahil edildi."
  }
};

function t(key, variables = {}) {
  const template = translations[state.language]?.[key] ?? translations.en[key] ?? key;
  return Object.entries(variables).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

function applyLanguage() {
  document.documentElement.lang = state.language;
  $$('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach((element) => { element.placeholder = t(element.dataset.i18nPlaceholder); });
  $$('[data-i18n-title]').forEach((element) => { element.title = t(element.dataset.i18nTitle); });
  $$('[data-i18n-aria-label]').forEach((element) => { element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel)); });
  if ($('#language-select')) $('#language-select').value = state.language;
  if (state.systemPromptSource && $('#system-prompt-source')) {
    $('#system-prompt-source').textContent = state.systemPromptSource === 'saved'
      ? t('settings.sourceSaved')
      : state.systemPromptSource === 'environment' ? t('settings.sourceEnvironment') : t('settings.sourceDefault');
  }
}

function refreshLanguageDependentViews() {
  applyLanguage();
  if (state.projects.length) {
    renderProjectsTree();
    renderConversationsTree();
    renderMessages();
    renderSources($('.source-search input')?.value || '');
    renderCitations(state.latestSources);
    renderProjectDialog();
    renderModelsList();
    renderCatalogModels();
    const project = state.projects.find((item) => item.id === state.projectId);
    const conversation = state.conversations.find((item) => item.id === state.conversationId);
    $('#chat-title').textContent = localizedConversationTitle(conversation?.title || t('chat.newTitle'));
    $('#chat-subtitle').textContent = t('chat.groundedSubtitle', {
      project: localizedProjectName(project?.name || t('projects.workspace')),
      count: state.documents.length,
    });
    $('#sources-title').textContent = t('sources.title', {count: state.documents.length});
    syncContextInspectorWithState();
  }
  setBusy(state.busy);
}

function localizedProjectName(name) {
  return ["Genel Proje", "General Project"].includes(name) ? t("projects.defaultName") : name;
}

function localizedConversationTitle(title) {
  return ["Yeni Sohbet", "İlk Sohbet", "New Chat", "First Chat"].includes(title) ? t("chat.newTitle") : title;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => (
    {"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]
  ));
}

function renderMarkdown(value) {
  const lines = escapeHtml(value).split("\n");
  const output = [];
  let list = null;
  let codeBlock = false;
  let codeLines = [];

  const inline = (text) => {
    const code = [];
    text = text.replace(/`([^`]+)`/g, (_, content) => {
      code.push(`<code>${content}</code>`);
      return `@@CODE${code.length - 1}@@`;
    });
    text = text.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
    return text.replace(/@@CODE(\d+)@@/g, (_, index) => code[Number(index)]);
  };
  const closeList = () => {
    if (list) { output.push(`</${list}>`); list = null; }
  };

  for (const line of lines) {
    if (line.trim().startsWith("`````")) continue;
    if (line.trim().startsWith("```")) {
      if (codeBlock) {
        output.push(`<pre><code>${codeLines.join("\n")}</code></pre>`);
        codeLines = [];
      }
      codeBlock = !codeBlock;
      continue;
    }
    if (codeBlock) { codeLines.push(line); continue; }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    const bullet = line.match(/^\s*[-*+]\s+(.+)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (heading) { closeList(); const level = heading[1].length; output.push(`<h${level}>${inline(heading[2])}</h${level}>`); continue; }
    if (bullet || numbered) {
      const type = bullet ? "ul" : "ol";
      if (list !== type) { closeList(); output.push(`<${type}>`); list = type; }
      output.push(`<li>${inline((bullet || numbered)[1])}</li>`);
      continue;
    }
    closeList();
    if (line.trim()) output.push(`<p>${inline(line)}</p>`);
  }
  if (codeBlock && codeLines.length) output.push(`<pre><code>${codeLines.join("\n")}</code></pre>`);
  closeList();
  return output.join("");
}

async function api(url, options = {}) {
  options.headers = {...(options.headers || {}), "Accept-Language": state.language};
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = t("common.error");
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  }
  return response.json();
}

function switchSettingsTab(tab) {
  $$(".settings-tab").forEach((button) => button.classList.toggle("active", button.dataset.settingsTab === tab));
  $("#settings-general-panel")?.classList.toggle("active", tab === "general");
  $("#settings-models-panel")?.classList.toggle("active", tab === "models");
}

async function openSettings(tab = "general") {
  const data = await api("/api/settings/system-prompt");
  state.systemPromptSource = data.source;
  $("#system-prompt-input").value = data.prompt;
  $("#system-prompt-source").textContent = data.source === "saved"
    ? t("settings.sourceSaved")
    : data.source === "environment" ? t("settings.sourceEnvironment") : t("settings.sourceDefault");
  $("#settings-dialog").showModal();
  switchSettingsTab(tab);
  await loadCatalogModels();
}

function showToast(message, isError = false) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.className = "toast"; }, 3200);
}

function setBusy(busy) {
  state.busy = busy;
  const composer = $("#composer");
  const sendBtn = $("#send-btn");
  if (composer) composer.classList.toggle("is-busy", busy);
  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.title = busy ? t("composer.stop") : t("composer.send");
    sendBtn.setAttribute("aria-label", busy ? t("composer.stop") : t("composer.send"));
    sendBtn.innerHTML = busy 
      ? '<i class="fa-solid fa-stop"></i>' 
      : '<i class="fa-solid fa-arrow-right"></i>';
    sendBtn.classList.toggle("stop-generating", busy);
  }
  // Keep the text field ACTIVE so the user can continue typing freely!
  const questionInput = $("#question");
  if (questionInput) questionInput.disabled = false;
}

function renderWorkspace(data, renderChat = true) {
  Object.assign(state, {
    projectId: data.project_id,
    conversationId: data.conversation_id,
    projects: data.projects,
    conversations: data.conversations,
    documents: data.documents,
    messages: data.messages,
  });

  const project = state.projects.find((item) => item.id === state.projectId);
  const activeTitle = localizedProjectName(project?.name || t("projects.workspace"));
  const sourcesTitle = $("#sources-title");
  if (sourcesTitle) sourcesTitle.textContent = t("sources.title", {count: state.documents.length});

  renderProjectsTree();
  renderConversationsTree();

  const activeConv = state.conversations.find((item) => item.id === state.conversationId);
  $("#chat-title").textContent = localizedConversationTitle(activeConv?.title || t("chat.newTitle"));
  $("#chat-subtitle").textContent = t("chat.groundedSubtitle", {project: activeTitle, count: state.documents.length});

  renderSources();
  renderProjectDialog();
  if (renderChat) renderMessages();
  syncContextInspectorWithState();
}

function renderProjectsTree() {
  const list = $("#project-tree-list");
  if (!list) return;

  list.innerHTML = state.projects.map((p) => {
    const isActive = p.id === state.projectId;
    return `
      <button class="project-tree-item ${isActive ? "active" : ""}" data-project="${p.id}" title="${escapeHtml(localizedProjectName(p.name))}">
        <span class="project-folder-icon"><i class="fa-regular fa-folder"></i></span>
        <span class="project-tree-name">${escapeHtml(localizedProjectName(p.name))}</span>
        <span class="project-badge-action">${p.doc_count ? `${p.doc_count} <i class="fa-regular fa-file-pdf"></i>` : `<i class="fa-solid fa-arrow-up-right-from-square"></i>`}</span>
      </button>
    `;
  }).join("");
}

function renderConversationsTree() {
  const list = $("#conversation-list");
  if (!list) return;

  list.innerHTML = state.conversations.map((item) => {
    const isActive = item.id === state.conversationId;
    return `
      <div class="conversation-item-wrap ${isActive ? "active" : ""}" data-conversation="${item.id}" title="${escapeHtml(localizedConversationTitle(item.title))}">
        <span class="conversation-item-text">${escapeHtml(localizedConversationTitle(item.title))}</span>
        <div class="conversation-item-actions">
          <button type="button" class="conv-action-btn edit-btn" data-rename-conv="${item.id}" title="${t("chat.renameAction")}"><i class="fa-regular fa-pen-to-square"></i></button>
          <button type="button" class="conv-action-btn delete-btn" data-delete-conv="${item.id}" title="${t("chat.deleteAction")}"><i class="fa-regular fa-trash-can"></i></button>
        </div>
      </div>
    `;
  }).join("");
}

function renderMessages() {
  const container = $("#messages");
  if (!state.messages.length) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="spark"><i class="fa-solid fa-wand-magic-sparkles"></i></span>
        <h2>${t("empty.title")}</h2>
        <p>${t("empty.description")}</p>
        <div class="suggestions">
          <button>${t("empty.suggestion")}</button>
        </div>
      </div>`;
    return;
  }
  container.innerHTML = state.messages.map((message) => messageHtml(message.role, message.content)).join("");
  container.scrollTop = container.scrollHeight;
}

function messageHtml(role, content, extraClass = "") {
  const assistant = role === "assistant";
  return `
    <article class="message ${assistant ? "assistant" : "user"} ${extraClass}">
      <span class="message-avatar">${assistant ? '<i class="fa-solid fa-wand-magic-sparkles"></i>' : '<i class="fa-solid fa-user"></i>'}</span>
      <div class="message-body">${assistant ? renderMarkdown(content) : escapeHtml(content)}</div>
    </article>`;
}

function renderSources(filter = "") {
  const needle = filter.trim().toLocaleLowerCase(state.language);
  const docs = state.documents.filter((item) => item.filename.toLocaleLowerCase(state.language).includes(needle));
  $("#source-list").innerHTML = docs.length ? docs.map((item) => `
    <article class="source-item" data-id="${item.id}">
      <span class="pdf-icon"><i class="fa-solid fa-file-pdf"></i></span>
      <div class="source-item-meta">
        <strong title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</strong>
        <small>${t("sources.chunkReady", {count: item.chunk_count})}</small>
      </div>
      <button type="button" class="source-delete-btn" data-delete-document="${item.id}" aria-label="${t("sources.remove")}" title="${t("sources.delete")}"><i class="fa-solid fa-xmark"></i></button>
    </article>`).join("") : `<div class="source-empty"><span><i class="fa-regular fa-folder-open"></i></span><p>${needle ? t("sources.noMatch") : t("sources.none")}</p></div>`;
}

function renderCitations(sources) {
  state.latestSources = sources || [];
  const section = $(".answer-sources");
  if (!state.latestSources.length) {
    section.innerHTML = `<p class="eyebrow">${t("citations.title")}</p><div class="source-empty"><span><i class="fa-regular fa-lightbulb"></i></span><p>${t("citations.empty")}</p></div>`;
    return;
  }
  section.innerHTML = `<p class="eyebrow">${t("citations.titleCount", {count: state.latestSources.length})}</p><div class="citation-list">${state.latestSources.map((item) => `
    <article class="citation">
      <strong><i class="fa-regular fa-file-lines"></i> ${escapeHtml(item.source)}</strong>
      <small>${t("citations.chunk", {index: item.chunk_index, score: Math.round(item.score * 100)})}</small>
      <p>${escapeHtml(item.excerpt)}</p>
    </article>
  `).join("")}</div>`;
}

function renderProjectDialog() {
  $("#project-list").innerHTML = state.projects.map((project) => `
    <div class="project-option ${project.id === state.projectId ? "active" : ""}">
      <button type="button" data-project="${project.id}">
        <strong><i class="fa-regular fa-folder"></i> ${escapeHtml(localizedProjectName(project.name))}</strong>
        <small>${t("projectDialog.stats", {documents: project.doc_count, chunks: project.chunk_count || 0, chats: project.conv_count})}</small>
      </button>
      ${state.projects.length > 1 ? `<button type="button" data-delete-project="${project.id}" aria-label="${t("projects.deleteActive")}" title="${t("projects.deleteActive")}"><i class="fa-regular fa-trash-can"></i></button>` : ""}
    </div>`).join("");
}

// Models Rendering and Handling
async function loadModels() {
  try {
    state.models = await api("/api/models");
    state.models.forEach((model) => {
      if (model.downloading && model.progress != null) state.modelProgress[model.id] = model.progress;
      else if (!model.downloading) delete state.modelProgress[model.id];
    });
  } catch (_) {
    state.models = [
      { id: "qwen2.5-1.5b", name: "Qwen 2.5 1.5B", tag: "Fast & Lightweight", desc: "Low memory use and quick responses" },
      { id: "qwen2.5-7b", name: "Qwen 2.5 7B", tag: "Powerful & Detailed", desc: "Stronger comprehension and detailed analysis" },
      { id: "llama3.2-3b", name: "Llama 3.2 3B", tag: "Meta Llama", desc: "Compact and balanced local model" },
      { id: "deepseek-r1-distill-qwen-1.5b", name: "DeepSeek R1 1.5B", tag: "Reasoning", desc: "Step-by-step reasoning" },
    ];
  }
  renderModelsList();
  if (state.models.some((model) => model.downloading)) {
    clearTimeout(state.modelStatusTimer);
    state.modelStatusTimer = setTimeout(loadModels, 1500);
  }
}

function formatModelSize(sizeMb) {
  if (sizeMb == null) return t("models.noSize");
  const size = Number(sizeMb);
  return size >= 1024 ? `${(size / 1024).toFixed(2)} GB` : `${size.toFixed(0)} MB`;
}

async function loadCatalogModels() {
  const list = $("#catalog-model-list");
  if (!list) return;
  list.innerHTML = `<small>${t("models.loadingCatalog")}</small>`;
  try {
    state.catalogModels = await api("/api/models/catalog");
    renderCatalogModels();
    clearTimeout(state.catalogStatusTimer);
    if (state.catalogModels.some((model) => model.downloading)) {
      state.catalogStatusTimer = setTimeout(loadCatalogModels, 1500);
    }
  } catch (error) {
    list.innerHTML = `<small class="catalog-model-error">${escapeHtml(error.message)}</small>`;
  }
}

function renderCatalogModels() {
  const list = $("#catalog-model-list");
  const render = (target, models, emptyText) => {
    if (!target) return;
    target.innerHTML = models.map((model) => {
    const progress = state.modelProgress[model.id] ?? model.progress;
    const size = formatModelSize(model.size_mb);
    const downloaded = formatModelSize(model.downloaded_mb);
    const isPreparing = state.modelBusy && state.modelBusyId === model.id && progress == null;
    const action = isPreparing
      ? `<span class="model-option-tag preparing-tag"><i class="fa-solid fa-circle-notch fa-spin"></i> ${t("models.preparing")}</span>`
      : model.cached
      ? `<span class="model-option-tag ready"><i class="fa-solid fa-check"></i> ${t("models.ready")}</span>`
      : progress != null
        ? `<div class="model-download-progress"><span>${downloaded} / ${escapeHtml(size)} · %${progress}</span><div><i style="width:${progress}%"></i></div></div>`
        : `<button type="button" class="model-download-btn" data-download-catalog-model="${escapeHtml(model.id)}"><i class="fa-solid fa-download"></i> ${t("models.download")}</button>`;
      return `<div class="catalog-model-item"><div><strong>${escapeHtml(model.name)}</strong><small>${escapeHtml(size)}</small></div>${action}</div>`;
    }).join("") || `<small>${emptyText}</small>`;
  };
  render(list, state.catalogModels.filter((model) => model.task === "chat-completion"), t("models.noChat"));
}

function renderModelsList() {
  const container = $("#model-options-list");
  const current = state.models.find((m) => m.id === state.selectedModel) || state.models[0];
  if (current) {
    $("#selected-model-name").textContent = current.name;
  }
  if (!container) return;

  container.innerHTML = state.models.map((m) => {
    const isActive = m.id === state.selectedModel;
    const sizeLabel = formatModelSize(m.size_mb);
    const progress = state.modelProgress[m.id];
    const isPreparing = state.modelBusy && state.modelBusyId === m.id;
    return `
      <div class="model-option-item ${isActive ? "active" : ""} ${isPreparing ? "preparing" : ""}" data-model-id="${m.id}">
        <div class="model-option-main">
          <strong>${escapeHtml(m.name)}</strong>
          <small>${escapeHtml(m.desc || "")} · ${escapeHtml(sizeLabel)}</small>
        </div>
        ${isPreparing ? `<span class="model-option-tag preparing-tag"><i class="fa-solid fa-circle-notch fa-spin"></i> ${t("models.preparing")}</span>` : !m.available ? `<span class="model-option-tag unavailable">${t("models.unavailable")}</span>` : m.cached ? `<span class="model-option-tag ready"><i class="fa-solid fa-check"></i> ${t("models.ready")} · ${escapeHtml(sizeLabel)}</span>` : progress != null ? `<div class="model-download-progress"><span>${formatModelSize(m.downloaded_mb)} / ${escapeHtml(sizeLabel)} · %${progress}</span><div><i style="width:${progress}%"></i></div></div>` : `<button type="button" class="model-download-btn" data-download-model="${escapeHtml(m.id)}"><i class="fa-solid fa-download"></i> ${t("models.download")}</button>`}
      </div>
    `;
  }).join("");
}

async function prepareModel(modelId) {
  if (state.modelBusy) return;
  const model = state.models.find((item) => item.id === modelId);
  state.modelBusy = true;
  state.modelBusyId = modelId;
  renderModelsList();
  showToast(t("models.preparingToast", {name: model?.name || modelId}));
  try {
    const currentModel = state.models.find((item) => item.id === modelId);
    if (!currentModel?.cached) {
      await downloadModelWithProgress(modelId);
    }
    await api(`/api/models/${encodeURIComponent(modelId)}/prepare`, {method: "POST"});
    state.selectedModel = modelId;
    await loadModels();
    syncContextInspectorWithState();
    hideModelMenu();
    showToast(t("models.readyToast", {name: model?.name || modelId}));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    delete state.modelProgress[modelId];
    state.modelBusy = false;
    state.modelBusyId = null;
    renderModelsList();
  }
}

async function downloadModelWithProgress(modelId) {
  const response = await fetch(`/api/models/${encodeURIComponent(modelId)}/download`, {method: "POST"});
  if (!response.ok) throw new Error((await response.json()).detail || t("models.downloadFailed"));
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  while (true) {
    const {value, done} = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), {stream: !done});
    const lines = pending.split("\n");
    pending = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      if (event.type === "progress") {
        state.modelProgress[modelId] = event.progress;
        const model = state.models.find((item) => item.id === modelId)
          || state.catalogModels.find((item) => item.id === modelId);
        if (model) {
          model.size_mb = event.size_mb || model.size_mb;
          model.downloaded_mb = event.downloaded_mb || 0;
        }
        renderModelsList();
        renderCatalogModels();
      }
      if (event.type === "error") throw new Error(event.message);
    }
    if (done) break;
  }
  delete state.modelProgress[modelId];
  renderCatalogModels();
}

async function downloadCatalogModel(modelId) {
  if (state.modelBusy) return;
  const model = state.catalogModels.find((item) => item.id === modelId);
  state.modelBusy = true;
  state.modelBusyId = modelId;
  renderCatalogModels();
  showToast(t("models.downloadingToast", {name: model?.name || modelId}));
  try {
    await downloadModelWithProgress(modelId);
    await api(`/api/models/${encodeURIComponent(modelId)}/prepare`, {method: "POST"});
    await loadModels();
    await loadCatalogModels();
    showToast(t("models.readyToast", {name: model?.name || modelId}));
  } catch (error) {
    showToast(error.message, true);
  } finally {
    delete state.modelProgress[modelId];
    state.modelBusy = false;
    state.modelBusyId = null;
    renderCatalogModels();
  }
}

function toggleModelMenu(btn) {
  const popup = $("#model-menu-popup");
  if (!popup) return;
  const isHidden = popup.hidden || popup.classList.contains("hidden");
  if (!isHidden) {
    hideModelMenu();
  } else {
    hideContextMenu();
    const rect = btn.getBoundingClientRect();
    popup.style.bottom = `${window.innerHeight - rect.top + 8}px`;
    popup.style.left = `${Math.max(10, rect.left)}px`;
    popup.hidden = false;
    popup.classList.remove("hidden");
  }
}

function hideModelMenu() {
  const popup = $("#model-menu-popup");
  if (popup) {
    popup.hidden = true;
    popup.classList.add("hidden");
  }
}

async function switchWorkspace(projectId, conversationId = null) {
  const suffix = conversationId ? `?conversation_id=${conversationId}` : "";
  renderWorkspace(await api(`/api/workspaces/${projectId}${suffix}`));
  renderCitations([]);
}

async function createConversation() {
  const data = await api("/api/conversations", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({project_id: state.projectId, title: t("chat.newTitle")}),
  });
  renderWorkspace(data);
  renderCitations([]);
  $("#question").focus();
}

async function uploadFiles(files) {
  if (!files.length) return;
  const form = new FormData();
  form.append("project_id", state.projectId);
  [...files].forEach((file) => form.append("files", file));
  showToast(t("sources.processing"));
  $(".upload-card").classList.add("is-busy");
  try {
    const data = await api("/api/documents", {method: "POST", body: form});
    renderWorkspace(data, false);
    const result = data.upload_result;
    showToast(result.added.length ? t("sources.added", {count: result.added.length}) : result.skipped.join(" · "));
  } finally {
    $(".upload-card").classList.remove("is-busy");
    $("#file-input").value = "";
  }
}

function appendLiveMessage(role, content, id) {
  const messages = $("#messages");
  if ($(".empty-state")) messages.innerHTML = "";
  messages.insertAdjacentHTML("beforeend", messageHtml(role, content, role === "assistant" ? "typing" : ""));
  const element = messages.lastElementChild;
  if (id) element.id = id;
  messages.scrollTop = messages.scrollHeight;
  return element;
}

function syncContextInspectorWithState() {
  const modelObj = state.models.find((m) => m.id === state.selectedModel) || state.models[0];
  const modelNameEl = $("#inspector-model-name");
  const tokenCountEl = $("#inspector-token-count");
  const meterBarEl = $("#context-meter-bar");
  const chunksListEl = $("#inspector-chunks-list");
  const historyInfoEl = $("#inspector-history-info");

  if (modelNameEl) modelNameEl.textContent = modelObj?.name || state.selectedModel;

  // 1. System prompt tokens (~55 tokens)
  const systemPromptTokens = 55;

  // 2. Sliding conversation window tokens (last 6 messages)
  const recentMessages = (state.messages || []).slice(-6);
  const historyChars = recentMessages.reduce((sum, msg) => sum + (msg.content || "").length, 0);
  const historyTokens = Math.round(historyChars / 3.6);

  // 3. Injected chunks from latestSources or last assistant message with source_info
  let chunks = state.latestSources || [];
  if (!chunks.length && state.messages && state.messages.length) {
    for (let i = state.messages.length - 1; i >= 0; i--) {
      const msg = state.messages[i];
      if (msg.role === "assistant" && msg.source_info) {
        try {
          const parsed = JSON.parse(msg.source_info);
          if (Array.isArray(parsed) && parsed.length) {
            chunks = parsed;
            break;
          }
        } catch (_) {}
      }
    }
  }

  const chunksChars = chunks.reduce((sum, c) => sum + (c.excerpt || "").length, 0);
  const chunksTokens = Math.round(chunksChars / 3.6);

  const totalTokens = (state.messages && state.messages.length) 
    ? (systemPromptTokens + historyTokens + chunksTokens + 30) 
    : 0;

  const maxTokens = 32768;
  const pct = totalTokens > 0 ? Math.min(100, Math.max(1, Math.round((totalTokens / maxTokens) * 100))) : 0;

  if (tokenCountEl) {
    tokenCountEl.textContent = totalTokens > 0 
      ? `~${totalTokens.toLocaleString()} / ${maxTokens.toLocaleString()} Token (%${pct})`
      : `0 / ${maxTokens.toLocaleString()} Token`;
  }
  if (meterBarEl) meterBarEl.style.width = `${Math.max(totalTokens > 0 ? 2 : 0, pct)}%`;

  if (chunksListEl) {
    if (!chunks.length) {
      chunksListEl.innerHTML = (state.messages && state.messages.length)
        ? `<div class="source-empty"><span><i class="fa-regular fa-lightbulb"></i></span><p>${t("inspector.directContext")}</p></div>`
        : `<div class="source-empty"><span><i class="fa-regular fa-lightbulb"></i></span><p>${t("inspector.noQuestion")}</p></div>`;
    } else {
      chunksListEl.innerHTML = chunks.map((c) => `
        <div class="inspector-chunk-card">
          <header>
            <strong><i class="fa-solid fa-file-pdf"></i> ${escapeHtml(c.source)}</strong>
            <span>${t("inspector.chunk", {index: c.chunk_index, score: Math.round(c.score * 100)})}</span>
          </header>
          <p>${escapeHtml(c.excerpt)}</p>
        </div>
      `).join("");
    }
  }

  if (historyInfoEl) {
    historyInfoEl.textContent = recentMessages.length 
      ? t("inspector.historyMessages", {count: recentMessages.length, tokens: historyTokens})
      : t("inspector.historyDefault");
  }
}

function updateContextInspector(info) {
  if (!info) return;
  const modelNameEl = $("#inspector-model-name");
  const tokenCountEl = $("#inspector-token-count");
  const meterBarEl = $("#context-meter-bar");
  const chunksListEl = $("#inspector-chunks-list");
  const historyInfoEl = $("#inspector-history-info");

  const modelObj = state.models.find(m => m.id === info.model);
  if (modelNameEl) modelNameEl.textContent = modelObj?.name || info.model;
  
  const pct = Math.min(100, Math.round((info.tokens / info.max_tokens) * 100));
  if (tokenCountEl) tokenCountEl.textContent = `~${info.tokens.toLocaleString()} / ${info.max_tokens.toLocaleString()} Token (%${pct})`;
  if (meterBarEl) meterBarEl.style.width = `${Math.max(2, pct)}%`;
  if (chunksListEl) {
    if (!info.chunks || !info.chunks.length) {
      chunksListEl.innerHTML = `<div class="source-empty"><span><i class="fa-regular fa-lightbulb"></i></span><p>${t("inspector.noDirectMatch")}</p></div>`;
    } else {
      chunksListEl.innerHTML = info.chunks.map(c => `
        <div class="inspector-chunk-card">
          <header>
            <strong><i class="fa-solid fa-file-pdf"></i> ${escapeHtml(c.source)}</strong>
            <span>${t("inspector.chunk", {index: c.chunk_index, score: Math.round(c.score * 100)})}</span>
          </header>
          <p>${escapeHtml(c.excerpt)}</p>
        </div>
      `).join("");
    }
  }

  if (historyInfoEl) {
    historyInfoEl.textContent = t("inspector.historyIncluded", {count: info.history_turns});
  }
}

async function sendQuestion(question) {
  if (!question || state.busy) return;
  setBusy(true);
  state.chatAbortController = new AbortController();
  $("#question").value = "";
  $("#question").style.height = "auto";
  appendLiveMessage("user", question);
  const assistant = appendLiveMessage("assistant", t("chat.thinking"), "live-answer");
  assistant.classList.add("loading-message");
  const body = assistant.querySelector(".message-body");
  body.innerHTML = `${t("chat.thinking")}<span class="loading-dots" aria-label="${t("chat.thinking")}"><span>.</span><span>.</span><span>.</span></span>`;
  let answer = "";
  try {
    const response = await fetch("/api/chat", {
      method: "POST", headers: {"Content-Type": "application/json", "Accept-Language": state.language},
      signal: state.chatAbortController.signal,
      body: JSON.stringify({
        project_id: state.projectId,
        conversation_id: state.conversationId,
        question,
        model_alias: state.selectedModel,
        language: state.language,
      }),
    });
    if (!response.ok) throw new Error((await response.json()).detail || t("chat.noResponse"));
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let pending = "";
    while (true) {
      const {value, done} = await reader.read();
      pending += decoder.decode(value || new Uint8Array(), {stream: !done});
      const lines = pending.split("\n");
      pending = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "sources") renderCitations(event.sources);
        if (event.type === "context_info") updateContextInspector(event);
        if (event.type === "token") { answer += event.token; assistant.classList.remove("loading-message"); body.innerHTML = renderMarkdown(answer); }
        if (event.type === "done" && !answer) { answer = event.answer; assistant.classList.remove("loading-message"); body.innerHTML = renderMarkdown(answer); }
        if (event.type === "error") throw new Error(event.message);
        $("#messages").scrollTop = $("#messages").scrollHeight;
      }
      if (done) break;
    }
    assistant.classList.remove("typing");
    const fresh = await api(`/api/workspaces/${state.projectId}?conversation_id=${state.conversationId}`);
    renderWorkspace(fresh, false);
  } catch (error) {
    if (error.name === "AbortError") {
      body.textContent = answer ? `${answer}\n\n${t("chat.stopped")}` : t("chat.stopped");
      assistant.classList.remove("loading-message");
    } else {
      body.textContent = `Hata: ${error.message}`;
    }
    assistant.classList.remove("typing");
    if (error.name !== "AbortError") showToast(error.message, true);
  } finally {
    state.chatAbortController = null;
    setBusy(false);
    $("#question").focus();
  }
}

function stopGeneration() {
  if (!state.busy) return;
  // Tell the backend first so the model stream can stop as well, then close
  // the browser-side response immediately.
  fetch(`/api/chat/${state.conversationId}/stop`, {method: "POST", keepalive: true}).catch(() => {});
  state.chatAbortController?.abort();
}

// Context Menu Helper
function hideContextMenu() {
  const popup = $("#project-menu-popup");
  if (popup) {
    popup.hidden = true;
    popup.classList.add("hidden");
  }
}

function toggleContextMenu(btn) {
  const popup = $("#project-menu-popup");
  if (!popup) return;
  const isHidden = popup.hidden || popup.classList.contains("hidden");
  if (!isHidden) {
    hideContextMenu();
  } else {
    hideModelMenu();
    const rect = btn.getBoundingClientRect();
    popup.style.top = `${rect.bottom + 6}px`;
    popup.style.left = `${Math.max(10, rect.left - 100)}px`;
    popup.hidden = false;
    popup.classList.remove("hidden");
  }
}

// Global Click Handlers
document.addEventListener("click", async (event) => {
  try {
    if (event.target.closest("#send-btn") && state.busy) {
      stopGeneration();
      return;
    }
    // Hide popups on outside click
    if (!event.target.closest("#project-menu-popup") && !event.target.closest("#projects-more-btn")) {
      hideContextMenu();
    }
    if (!event.target.closest("#model-menu-popup") && !event.target.closest("#model-picker-btn")) {
      hideModelMenu();
    }

    // Panel Tab Switching (Belgeler vs Bağlam Penceresi)
    const tabBtn = event.target.closest(".panel-tab-btn");
    if (tabBtn) {
      const targetTab = tabBtn.dataset.tab;
      $$(".panel-tab-btn").forEach((b) => b.classList.toggle("active", b === tabBtn));
      $("#tab-sources").classList.toggle("active", targetTab === "sources");
      $("#tab-inspector").classList.toggle("active", targetTab === "inspector");
      return;
    }

    const suggestion = event.target.closest(".suggestions button");
    if (suggestion) { $("#question").value = suggestion.textContent; $("#question").focus(); return; }

    if (event.target.closest("#quick-new-conv-btn")) {
      await createConversation();
      return;
    }

    // Projects Wrap / Unwrap Toggle
    if (event.target.closest("#projects-toggle")) {
      state.projectsCollapsed = !state.projectsCollapsed;
      const tree = $("#project-tree-container");
      const chevron = $("#projects-chevron");
      tree.classList.toggle("collapsed", state.projectsCollapsed);
      chevron.style.transform = state.projectsCollapsed ? "rotate(-90deg)" : "rotate(0deg)";
      return;
    }

    // Conversations Wrap / Unwrap Toggle
    if (event.target.closest("#conv-toggle")) {
      state.conversationsCollapsed = !state.conversationsCollapsed;
      const tree = $("#conv-tree-container");
      const chevron = $("#conv-chevron");
      tree.classList.toggle("collapsed", state.conversationsCollapsed);
      chevron.style.transform = state.conversationsCollapsed ? "rotate(-90deg)" : "rotate(0deg)";
      return;
    }

    // Projects More Menu (···) Toggle
    const moreBtn = event.target.closest("#projects-more-btn");
    if (moreBtn) {
      event.stopPropagation();
      toggleContextMenu(moreBtn);
      return;
    }

    // Model Selector Toggle
    const modelPickerBtn = event.target.closest("#model-picker-btn");
    if (modelPickerBtn) {
      event.stopPropagation();
      toggleModelMenu(modelPickerBtn);
      return;
    }

    if (event.target.closest("#settings-btn")) {
      await openSettings();
      return;
    }

    if (event.target.closest("#other-models-btn")) {
      hideModelMenu();
      await openSettings("models");
      return;
    }

    const settingsTab = event.target.closest("[data-settings-tab]");
    if (settingsTab) {
      switchSettingsTab(settingsTab.dataset.settingsTab);
      return;
    }

    const catalogDownload = event.target.closest("[data-download-catalog-model]");
    if (catalogDownload) {
      event.stopPropagation();
      await downloadCatalogModel(catalogDownload.dataset.downloadCatalogModel);
      return;
    }

    // Model download / selection
    const downloadModel = event.target.closest("[data-download-model]");
    if (downloadModel) {
      event.stopPropagation();
      await prepareModel(downloadModel.dataset.downloadModel);
      return;
    }

    const modelOption = event.target.closest("[data-model-id]");
    if (modelOption) {
      const selectedId = modelOption.dataset.modelId;
      if (selectedId === state.selectedModel) { hideModelMenu(); return; }
      await prepareModel(selectedId);
      return;
    }

    // Add Project (+) Button on Header
    if (event.target.closest("#add-project-btn") || event.target.closest("#menu-new-project")) {
      hideContextMenu();
      $("#project-dialog").showModal();
      $("#new-project-name").focus();
      return;
    }

    // Manage Projects Button
    if (event.target.closest("#manage-workspaces-btn") || event.target.closest("#menu-manage-projects")) {
      hideContextMenu();
      $("#project-dialog").showModal();
      return;
    }

    // Delete Active Project from Menu
    if (event.target.closest("#menu-delete-active-project")) {
      hideContextMenu();
      if (state.projects.length <= 1) {
        showToast(t("projects.lastCannotDelete"), true);
        return;
      }
      if (confirm(t("projects.deleteConfirm", {name: localizedProjectName(state.projects.find(p => p.id === state.projectId)?.name || "")}))) {
        const data = await api(`/api/projects/${state.projectId}`, {method: "DELETE"});
        renderWorkspace(data);
        showToast(t("projects.deleted"));
      }
      return;
    }

    // Inline Rename Conversation Button (✎)
    const renameConvBtn = event.target.closest("[data-rename-conv]");
    if (renameConvBtn) {
      event.stopPropagation();
      const targetId = Number(renameConvBtn.dataset.renameConv);
      const targetConv = state.conversations.find(c => c.id === targetId);
      const newTitle = prompt(t("chat.renamePrompt"), localizedConversationTitle(targetConv?.title || ""));
      if (newTitle && newTitle.trim()) {
        await api(`/api/conversations/${targetId}/title`, {
          method: "PATCH", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({title: newTitle.trim()})
        }).catch(() => {});
        const fresh = await api(`/api/workspaces/${state.projectId}?conversation_id=${state.conversationId}`);
        renderWorkspace(fresh, false);
        showToast(t("chat.titleUpdated"));
      }
      return;
    }

    // Inline Delete Conversation Button (🗑)
    const deleteConvBtn = event.target.closest("[data-delete-conv]");
    if (deleteConvBtn) {
      event.stopPropagation();
      const targetId = Number(deleteConvBtn.dataset.deleteConv);
      if (confirm(t("chat.deleteConfirm"))) {
        const data = await api(`/api/conversations/${targetId}`, {method: "DELETE"});
        renderWorkspace(data);
        renderCitations([]);
        showToast(t("chat.deleted"));
      }
      return;
    }

    // Top Header Rename Chat
    if (event.target.closest("#rename-chat")) {
      const activeConv = state.conversations.find(c => c.id === state.conversationId);
      const newTitle = prompt(t("chat.renamePrompt"), localizedConversationTitle(activeConv?.title || ""));
      if (newTitle && newTitle.trim()) {
        await api(`/api/conversations/${state.conversationId}/title`, {
          method: "PATCH", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({title: newTitle.trim()})
        }).catch(() => {});
        const fresh = await api(`/api/workspaces/${state.projectId}?conversation_id=${state.conversationId}`);
        renderWorkspace(fresh, false);
      }
      return;
    }

    if (event.target.closest("#delete-chat") && confirm(t("chat.deleteConfirm"))) {
      const data = await api(`/api/conversations/${state.conversationId}`, {method: "DELETE"});
      renderWorkspace(data);
      renderCitations([]);
      showToast(t("chat.deleted"));
      return;
    }

    if (event.target.closest("#add-source") || event.target.closest("[data-upload-trigger]")) {
      $("#file-input").click();
      return;
    }

    const conversation = event.target.closest("[data-conversation]");
    if (conversation) {
      await switchWorkspace(state.projectId, Number(conversation.dataset.conversation));
      return;
    }

    const project = event.target.closest("[data-project]");
    if (project) {
      $("#project-dialog").close();
      await switchWorkspace(Number(project.dataset.project));
      return;
    }

    const deleteDocumentButton = event.target.closest("[data-delete-document]");
    if (deleteDocumentButton && confirm(t("sources.removeConfirm"))) {
      renderWorkspace(await api(`/api/documents/${deleteDocumentButton.dataset.deleteDocument}?project_id=${state.projectId}`, {method: "DELETE"}), false);
      showToast(t("sources.removed"));
      return;
    }

    const deleteProjectButton = event.target.closest("[data-delete-project]");
    if (deleteProjectButton && confirm(t("projects.deleteWorkspaceConfirm"))) {
      const data = await api(`/api/projects/${deleteProjectButton.dataset.deleteProject}`, {method: "DELETE"});
      $("#project-dialog").close();
      renderWorkspace(data);
      showToast(t("projects.workspaceDeleted"));
    }
  } catch (error) { showToast(error.message, true); }
});

$("#create-project").addEventListener("click", async () => {
  const name = $("#new-project-name").value.trim();
  if (!name) { showToast(t("projects.nameRequired"), true); return; }
  try {
    const data = await api("/api/projects", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({name, description: $("#new-project-description").value.trim()}),
    });
    $("#new-project-name").value = "";
    $("#new-project-description").value = "";
    $("#project-dialog").close();
    renderWorkspace(data);
    showToast(t("projects.created", {name}));
  } catch (error) { showToast(error.message, true); }
});

$("#language-select").addEventListener("change", (event) => {
  state.language = event.target.value === "tr" ? "tr" : "en";
  localStorage.setItem("corgue-language", state.language);
  refreshLanguageDependentViews();
});

$("#settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = $("#system-prompt-input").value.trim();
  if (!prompt) { showToast(t("settings.promptRequired"), true); return; }
  try {
    await api("/api/settings/system-prompt", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify({prompt})});
    $("#settings-dialog").close();
    showToast(t("settings.promptSaved"));
  } catch (error) { showToast(error.message, true); }
});

$("#reset-system-prompt").addEventListener("click", async () => {
  try {
    const data = await api("/api/settings/system-prompt", {method: "DELETE"});
    $("#system-prompt-input").value = data.prompt;
    $("#system-prompt-source").textContent = data.source === "environment" ? t("settings.sourceEnvironment") : t("settings.sourceDefault");
    showToast(t("settings.promptReset"));
  } catch (error) { showToast(error.message, true); }
});

$("#source-list").addEventListener("click", () => {});
$(".source-search input").addEventListener("input", (event) => renderSources(event.target.value));
$("#file-input").addEventListener("change", (event) => uploadFiles(event.target.files).catch((error) => showToast(error.message, true)));
$(".upload-card").addEventListener("dragover", (event) => { event.preventDefault(); event.currentTarget.classList.add("dragging"); });
$(".upload-card").addEventListener("dragleave", (event) => event.currentTarget.classList.remove("dragging"));
$(".upload-card").addEventListener("drop", (event) => {
  event.preventDefault(); event.currentTarget.classList.remove("dragging");
  const pdfs = [...event.dataTransfer.files].filter((file) => file.name.toLowerCase().endsWith(".pdf"));
  uploadFiles(pdfs).catch((error) => showToast(error.message, true));
});
$("#question").addEventListener("input", (event) => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 140)}px`;
});
$("#question").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); $("#composer").requestSubmit(); }
});
$("#composer").addEventListener("submit", (event) => { event.preventDefault(); sendQuestion($("#question").value.trim()); });

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    hideContextMenu();
    hideModelMenu();
  }
});

// Bootstrap application
applyLanguage();
api("/api/bootstrap").then((data) => {
  renderWorkspace(data);
  loadModels();
}).catch((error) => {
  showToast(t("chat.serverUnavailable", {message: error.message}), true);
});
