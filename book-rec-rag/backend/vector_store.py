"""Module provisioning array indexing parameters using high-speed numpy math arrays."""

import json
import numpy as np
from backend.db_core import get_db_connection


def save_book_to_knowledge_base(
    title: str, author: str, genre: str, summary: str, embedding: list[float]
) -> None:
    """Saves a book reference alongside its vector embedding array json block."""
    conn = get_db_connection()
    conn.cursor().execute(
        """INSERT INTO book_knowledge_base (title, author, genre, summary, embedding_json) 
           VALUES (?, ?, ?, ?, ?)""",
        (str(title), author, genre, summary, json.dumps(list(embedding))),
    )
    conn.commit()
    conn.close()


def query_vector_store_rag(query_embedding: list[float], limit: int = 1) -> list[dict]:
    """Fast, numpy-accelerated cosine similarity lookup against database items."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT title, author, genre, summary, embedding_json FROM book_knowledge_base"
    ).fetchall()
    conn.close()

    if not rows or not query_embedding:
        return []

    q_vec = np.array(query_embedding)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []

    results = []
    for title, author, genre, summary, emb_json in rows:
        if not emb_json:
            continue
        b_vec = np.array(json.loads(emb_json))
        b_norm = np.linalg.norm(b_vec)
        if b_norm == 0:
            continue

        similarity = np.dot(q_vec, b_vec) / (q_norm * b_norm)
        results.append(
            (
                similarity,
                {
                    "title": title,
                    "author": author,
                    "genre": genre,
                    "summary": summary,
                },
            )
        )

    # ─── UPDATED: RETURN THE SIMILARITY SCORE BLOCK TOO ───
    results.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "score": item[0],
            "title": item[1]["title"],
            "author": item[1]["author"],
            "genre": item[1]["genre"],
            "summary": item[1]["summary"]
        }
        for item in results[:limit]
    ]
    

# Add Document Fetching & Deletion Actions
def fetch_rag_document_inventory() -> list[dict]:
    """Retrieves all registered custom documents from the RAG knowledge table."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT id, title, author, genre, summary FROM book_knowledge_base ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "title": r[1],
            "author": r[2],
            "genre": r[3],
            "summary": r[4]
        }
        for r in rows
    ]


def delete_single_rag_document(doc_id: int) -> None:
    """Purges a single vector context segment from the knowledge base by its row ID ID."""
    conn = get_db_connection()
    conn.cursor().execute("DELETE FROM book_knowledge_base WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

