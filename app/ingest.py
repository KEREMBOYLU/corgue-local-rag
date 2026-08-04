import argparse
from pathlib import Path
import sqlite3

from pdf_utils import calculate_file_hash, chunk_text, read_pdf_text, select_pdf_path


DB_PATH = Path("rag.db")
DEFAULT_PROJECT_NAME = "Genel Proje"


def get_db_connection():
    # Multiple FastAPI requests can initialize/read the database concurrently.
    # Wait briefly for the writer instead of immediately surfacing "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def create_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure default project exists
    cursor.execute("SELECT id FROM projects WHERE name = ?", (DEFAULT_PROJECT_NAME,))
    row = cursor.fetchone()
    if row:
        default_project_id = row[0]
    else:
        cursor.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (DEFAULT_PROJECT_NAME, "Varsayılan çalışma alanı"),
        )
        default_project_id = cursor.lastrowid

    # 2. Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT,
            file_hash TEXT,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # Migration: Check if project_id column exists in documents
    cursor.execute("PRAGMA table_info(documents)")
    doc_cols = {r[1] for r in cursor.fetchall()}
    if "project_id" not in doc_cols:
        cursor.execute(
            "ALTER TABLE documents ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE"
        )

    # Assign documents without project_id to the default project
    cursor.execute(
        "UPDATE documents SET project_id = ? WHERE project_id IS NULL",
        (default_project_id,),
    )

    # 3. Create chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

    # Migration for chunks table
    cursor.execute("PRAGMA table_info(chunks)")
    chunk_cols = {r[1] for r in cursor.fetchall()}
    if "document_id" not in chunk_cols:
        cursor.execute(
            "ALTER TABLE chunks ADD COLUMN document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE"
        )
    if "embedding" not in chunk_cols:
        cursor.execute("ALTER TABLE chunks ADD COLUMN embedding TEXT")

    # Migrate legacy chunks without document_id
    cursor.execute("SELECT DISTINCT source FROM chunks WHERE document_id IS NULL")
    legacy_sources = [r[0] for r in cursor.fetchall()]
    for source_name in legacy_sources:
        cursor.execute(
            "SELECT id FROM documents WHERE filename = ? AND project_id = ?",
            (source_name, default_project_id),
        )
        doc_row = cursor.fetchone()
        if doc_row:
            doc_id = doc_row[0]
        else:
            cursor.execute("SELECT COUNT(*) FROM chunks WHERE source = ?", (source_name,))
            count = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO documents (project_id, filename, chunk_count) VALUES (?, ?, ?)",
                (default_project_id, source_name, count),
            )
            doc_id = cursor.lastrowid

        cursor.execute(
            "UPDATE chunks SET document_id = ? WHERE source = ? AND document_id IS NULL",
            (doc_id, source_name),
        )

    # 4. Create conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    # 5. Create messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            source_info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# Project CRUD Operations
# ==========================================

def get_or_create_default_project() -> dict:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, created_at FROM projects ORDER BY id ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "description": row[2], "created_at": row[3]}
    return create_project(DEFAULT_PROJECT_NAME, "Varsayılan çalışma alanı")


def create_project(name: str, description: str = "") -> dict:
    create_database()
    name = (name or "").strip()
    if not name:
        raise ValueError("Proje adı boş olamaz.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        project_id = cursor.lastrowid
        conn.commit()
        return {"id": project_id, "name": name, "description": description}
    except sqlite3.IntegrityError:
        raise ValueError(f"'{name}' isimli bir proje zaten mevcut.")
    finally:
        conn.close()


def list_projects() -> list[dict]:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id, 
            p.name, 
            p.description, 
            p.created_at,
            (SELECT COUNT(*) FROM documents d WHERE d.project_id = p.id) AS doc_count,
            (SELECT COUNT(*) FROM chunks c JOIN documents d ON c.document_id = d.id WHERE d.project_id = p.id) AS chunk_count,
            (SELECT COUNT(*) FROM conversations cv WHERE cv.project_id = p.id) AS conv_count
        FROM projects p
        ORDER BY p.id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "created_at": r[3],
            "doc_count": r[4],
            "chunk_count": r[5],
            "conv_count": r[6],
        }
        for r in rows
    ]


def get_project_by_id(project_id: int) -> dict | None:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, created_at FROM projects WHERE id = ?",
        (project_id,),
    )

    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "description": row[2], "created_at": row[3]}
    return None


def delete_project(project_id: int) -> bool:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Prevent deleting if it's the only project
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] <= 1:
        conn.close()
        raise ValueError("Son kalan projeyi silemezsiniz.")

    cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    # Delete chunks for documents of this project
    cursor.execute("""
        DELETE FROM chunks 
        WHERE document_id IN (SELECT id FROM documents WHERE project_id = ?)
    """, (project_id,))

    # Delete messages for conversations of this project
    cursor.execute("""
        DELETE FROM messages 
        WHERE conversation_id IN (SELECT id FROM conversations WHERE project_id = ?)
    """, (project_id,))

    cursor.execute("DELETE FROM conversations WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    conn.commit()
    conn.close()
    return True


# ==========================================
# Document CRUD Operations
# ==========================================

def get_document_by_hash(file_hash: str, project_id: int | None = None) -> dict | None:
    if not file_hash:
        return None
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    if project_id is not None:
        cursor.execute(
            "SELECT id, project_id, filename, filepath, file_hash, chunk_count, created_at FROM documents WHERE file_hash = ? AND project_id = ?",
            (file_hash, project_id),
        )
    else:
        cursor.execute(
            "SELECT id, project_id, filename, filepath, file_hash, chunk_count, created_at FROM documents WHERE file_hash = ?",
            (file_hash,),
        )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "project_id": row[1],
            "filename": row[2],
            "filepath": row[3],
            "file_hash": row[4],
            "chunk_count": row[5],
            "created_at": row[6],
        }
    return None


def list_documents(project_id: int | None = None) -> list[dict]:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    if project_id is not None:
        cursor.execute(
            """
            SELECT d.id, d.project_id, d.filename, d.filepath, d.file_hash, 
                   (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS actual_chunk_count,
                   d.created_at
            FROM documents d
            WHERE d.project_id = ?
            ORDER BY d.id ASC
            """,
            (project_id,),
        )
    else:
        cursor.execute(
            """
            SELECT d.id, d.project_id, d.filename, d.filepath, d.file_hash, 
                   (SELECT COUNT(*) FROM chunks c WHERE c.document_id = d.id) AS actual_chunk_count,
                   d.created_at
            FROM documents d
            ORDER BY d.id ASC
            """
        )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "project_id": row[1],
            "filename": row[2],
            "filepath": row[3],
            "file_hash": row[4],
            "chunk_count": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def save_document_and_chunks(
    filename: str,
    chunks: list[str],
    filepath: str | None = None,
    file_hash: str | None = None,
    project_id: int | None = None,
) -> int:
    create_database()

    if project_id is None:
        default_proj = get_or_create_default_project()
        project_id = default_proj["id"]

    # Check duplicate in same project
    if file_hash:
        existing = get_document_by_hash(file_hash, project_id=project_id)
        if existing:
            raise ValueError(
                f"Bu belge ('{existing['filename']}') bu projede zaten mevcut (ID: {existing['id']})."
            )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO documents (project_id, filename, filepath, file_hash, chunk_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, filename, filepath, file_hash, len(chunks)),
    )
    document_id = cursor.lastrowid

    for index, chunk in enumerate(chunks):
        cursor.execute(
            """
            INSERT INTO chunks (document_id, source, chunk_index, chunk_text)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, filename, index, chunk),
        )

    conn.commit()
    conn.close()
    return document_id


def delete_document(document_id: int) -> bool:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM documents WHERE id = ?", (document_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    conn.commit()
    conn.close()
    return True


# ==========================================
# Conversation & Message CRUD Operations
# ==========================================

def create_conversation(project_id: int, title: str = "Yeni Sohbet") -> dict:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (project_id, title) VALUES (?, ?)",
        (project_id, title),
    )
    conv_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": conv_id, "project_id": project_id, "title": title}


def list_conversations(project_id: int) -> list[dict]:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.id, c.project_id, c.title, c.created_at, c.updated_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS msg_count
        FROM conversations c
        WHERE c.project_id = ?
        ORDER BY c.updated_at DESC, c.id DESC
        """,
        (project_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "project_id": r[1],
            "title": r[2],
            "created_at": r[3],
            "updated_at": r[4],
            "msg_count": r[5],
        }
        for r in rows
    ]


def get_conversation(conv_id: int) -> dict | None:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, project_id, title, created_at, updated_at FROM conversations WHERE id = ?",
        (conv_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "project_id": row[1],
            "title": row[2],
            "created_at": row[3],
            "updated_at": row[4],
        }
    return None


def update_conversation_title(conv_id: int, title: str) -> bool:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, conv_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def delete_conversation(conv_id: int) -> bool:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def save_message(conv_id: int, role: str, content: str, source_info: str = "") -> int:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, role, content, source_info)
        VALUES (?, ?, ?, ?)
        """,
        (conv_id, role, content, source_info),
    )
    msg_id = cursor.lastrowid

    # Update conversation updated_at
    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,),
    )
    conn.commit()
    conn.close()
    return msg_id


def get_conversation_messages(conv_id: int, limit: int | None = None) -> list[dict]:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    if limit:
        cursor.execute(
            """
            SELECT id, conversation_id, role, content, source_info, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (conv_id, limit),
        )
        rows = cursor.fetchall()
        rows.reverse()
    else:
        cursor.execute(
            """
            SELECT id, conversation_id, role, content, source_info, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conv_id,),
        )
        rows = cursor.fetchall()

    conn.close()
    return [
        {
            "id": r[0],
            "conversation_id": r[1],
            "role": r[2],
            "content": r[3],
            "source_info": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]


def clear_conversation_messages(conv_id: int) -> bool:
    create_database()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return True


# ==========================================
# CLI Helper Functions
# ==========================================

def clear_old_chunks():
    """Tüm veritabanını temizler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM chunks")
    cursor.execute("DELETE FROM documents")
    conn.commit()
    conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="PDF belgelerini okuyup chunk'larını yerel RAG veritabanına kaydeder."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="İşlenecek PDF'in yolu. Verilmezse interaktif olarak sorulur.",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Belgenin ekleneceği proje adı.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Koleksiyondaki mevcut projeleri ve belgeleri listeler.",
    )
    parser.add_argument(
        "--delete",
        type=int,
        metavar="DOC_ID",
        help="Koleksiyondan silinecek belgenin ID'si.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Tüm koleksiyonu ve chunk'ları sıfırlar.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    create_database()

    if args.list:
        projects = list_projects()
        print("\n" + "=" * 70)
        print("📁 MEVCUT PROJELER VE ÇALIŞMA ALANLARI")
        print("=" * 70)
        for p in projects:
            print(f"\n📂 Proje: {p['name']} (ID: {p['id']}) - {p['doc_count']} Belge, {p['chunk_count']} Chunk, {p['conv_count']} Sohbet")
            docs = list_documents(project_id=p["id"])
            if docs:
                for doc in docs:
                    print(f"   └── 📄 {doc['filename']} (ID: {doc['id']} · {doc['chunk_count']} chunk)")
            else:
                print("   └── (Henüz belge eklenmemiş)")
        print("\n" + "=" * 70)
        return

    if args.delete is not None:
        success = delete_document(args.delete)
        if success:
            print(f"Belge (ID: {args.delete}) başarıyla silindi.")
        else:
            print(f"Belge bulunamadı: ID {args.delete}")
        return

    if args.clear:
        confirm = input("Tüm belgeleri ve veritabanını temizlemek istediğinize emin misiniz? (e/h): ").strip().lower()
        if confirm == "e":
            clear_old_chunks()
            print("Veritabanı tamamen sıfırlandı.")
        else:
            print("İşlem iptal edildi.")
        return

    # Ingest interactive or argument
    try:
        pdf_path = select_pdf_path(args.pdf)
    except ValueError as error:
        print(error)
        return

    # Select or create project
    if args.project:
        projs = [p for p in list_projects() if p["name"].lower() == args.project.lower()]
        if projs:
            target_proj = projs[0]
        else:
            target_proj = create_project(args.project)
    else:
        target_proj = get_or_create_default_project()

    file_hash = calculate_file_hash(pdf_path)
    existing_doc = get_document_by_hash(file_hash, project_id=target_proj["id"])
    if existing_doc:
        print(f"\n[UYARI] Bu dosya ('{existing_doc['filename']}') zaten '{target_proj['name']}' projesinde mevcut.")
        return

    print(f"PDF okunuyor ({pdf_path.name})...")
    text = read_pdf_text(pdf_path)
    chunks = chunk_text(text)

    doc_id = save_document_and_chunks(
        filename=pdf_path.name,
        chunks=chunks,
        filepath=str(pdf_path),
        file_hash=file_hash,
        project_id=target_proj["id"],
    )

    print("\nIngestion tamamlandı.")
    print(f"Hedef Proje: {target_proj['name']} (ID: {target_proj['id']})")
    print(f"Belge ID: {doc_id} | {pdf_path.name}")
    print(f"Chunk Sayısı: {len(chunks)}")
    print(f"Embedding oluşturmak için Gradio arayüzünü kullanabilir veya `python app/embed_chunks.py` çalıştırabilirsiniz.")


if __name__ == "__main__":
    main()
