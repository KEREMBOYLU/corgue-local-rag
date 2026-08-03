# Local RAG Assistant

A local, script-based retrieval-augmented generation (RAG) prototype built with Python, Microsoft Foundry Local, SQLite, and PDF documents. It extracts and chunks a PDF, generates local embeddings, retrieves relevant chunks with cosine similarity, and sends the retrieved context to a local chat model.

The current project is intended as a learning prototype. It runs inference locally through Foundry Local and does not implement a web interface or hosted service.

## How the RAG pipeline works

1. `app/ingest.py` reads a PDF with `pypdf` and splits the extracted text into overlapping character-based chunks.
2. The chunks are stored in a local SQLite database (`rag.db`).
3. `app/embed_chunks.py` uses the Foundry Local `qwen3-embedding-0.6b` model to generate an embedding for each chunk. Embeddings are serialized as JSON in SQLite.
4. `app/retrieve.py`, `app/rag_chat.py`, and `app/rag_cli.py` embed a question and rank stored chunks using cosine similarity calculated with NumPy.
5. The RAG scripts place the best matching chunk in the prompt for the Foundry Local `qwen2.5-1.5b` chat model, which streams an answer to the terminal.

The current retrieval implementation loads all embedded chunks into memory and performs a linear similarity scan. It is suitable for a small local corpus, not a large production index.

## Models and local storage

- **Embedding model:** `qwen3-embedding-0.6b`
- **Chat model:** `qwen2.5-1.5b`
- **Chat smoke-test model:** `qwen2.5-0.5b` in the root `app.py`
- **Database:** SQLite (`rag.db`)

The scripts initialize `FoundryLocalManager`, prepare execution providers, and download/load the required model on first use. Foundry Local manages downloaded model/runtime artifacts separately from the application source. Repository rules also exclude common local model and cache artifacts if they are created inside the project.

## Requirements

- Python 3.11 or newer
- A platform supported by Microsoft Foundry Local
- Enough local storage and memory for the selected models

The original development environment used Python 3.11. The pinned `foundry-local-sdk` and NumPy versions in `requirements.txt` require Python 3.11 or newer.

## Installation

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Run all commands below from the repository root because the current scripts use relative paths for the PDF and database.

## Add a source document

PDF source material is intentionally not tracked. Place a PDF that you own or have permission to use at:

```text
data/documents/data_types.pdf
```

The filename is currently hard-coded in `app/ingest.py`, `app/read_pdf.py`, and `app/chunk_pdf.py`. Rename your document to `data_types.pdf` or update those constants locally. Do not publish private, copyrighted, or course material without permission.

## Ingest the PDF

```bash
python app/ingest.py
```

This creates `rag.db`, clears existing rows from the `chunks` table, and inserts chunks from the configured PDF. The current ingestion workflow handles one configured PDF at a time.

Optional inspection scripts show extracted text or example chunks without writing to the database:

```bash
python app/read_pdf.py
python app/chunk_pdf.py
```

## Generate embeddings

After ingestion, generate and store embeddings for chunks that do not already have one:

```bash
python app/embed_chunks.py
```

The first run may take longer while Foundry Local prepares its execution providers and downloads the embedding model.

## Run retrieval

Run the retrieval demonstration with its current built-in query:

```bash
python app/retrieve.py
```

It prints the three chunks with the highest cosine-similarity scores. The query is currently defined in `app/retrieve.py`.

## Run a single RAG question

Run the end-to-end RAG demonstration with its built-in question:

```bash
python app/rag_chat.py
```

This retrieves one chunk, builds a context-only prompt, and streams the local chat model's response.

## Run the interactive RAG CLI

```bash
python app/rag_cli.py
```

Enter questions at the `Soru:` prompt. Enter `exit`, `quit`, or `q` to unload the models and stop the program.

## Additional diagnostic scripts

- `app.py` verifies basic streaming chat completion with a small Foundry Local model and a fixed example prompt.
- `app/test_embedding.py` verifies embedding generation and prints embedding metadata.
- `app/inspect_foundry.py` prints selected Foundry Local manager, catalog, and model methods for SDK exploration.

These scripts are retained because they are useful during development, but they are diagnostics rather than automated tests.

## Project structure

```text
local-rag-assistant/
├── app.py                         # Foundry Local chat smoke test
├── app/
│   ├── chunk_pdf.py               # PDF chunking diagnostic
│   ├── embed_chunks.py            # Generate and store chunk embeddings
│   ├── ingest.py                  # Extract, chunk, and store the configured PDF
│   ├── inspect_foundry.py         # Foundry Local SDK inspection utility
│   ├── rag_chat.py                # Single-question end-to-end RAG demo
│   ├── rag_cli.py                 # Interactive RAG command-line application
│   ├── read_pdf.py                # PDF extraction diagnostic
│   ├── retrieve.py                # Cosine-similarity retrieval demo
│   └── test_embedding.py          # Embedding smoke test
├── data/
│   └── documents/
│       └── .gitkeep               # Placeholder; local PDFs are ignored
├── .gitignore
├── README.md
└── requirements.txt
```

Generated and machine-local files such as `.venv/`, `rag.db`, PDFs, Python caches, secrets, and model caches are excluded from version control.

## Current status and limitations

- Functional prototype composed of standalone scripts.
- PDF path, demonstration questions, model aliases, chunk size, overlap, and retrieval count are constants in the scripts rather than CLI options.
- Ingestion replaces all existing chunks and currently targets one PDF.
- Chunking uses character boundaries and may split sentences or page markers.
- Embeddings are stored as JSON text, and retrieval performs an in-memory linear scan.
- Retrieval currently supplies one top-ranked chunk to the chat model in the RAG flows.
- There is no automated test suite, package entry point, configuration file, conversation memory, or citation validation.
