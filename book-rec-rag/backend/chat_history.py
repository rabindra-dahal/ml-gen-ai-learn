"""Module provisioning data abstraction adapters to retain chronological dialogue logs."""

from backend.db_core import get_db_connection


def load_persisted_chat() -> list[dict]:
    """Loads text conversation timeline from historical database records."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT role, content FROM chat_history ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]


def save_chat_message(role: str, content: str) -> None:
    """Stores text conversation items directly to storage history logs."""
    conn = get_db_connection()
    conn.cursor().execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)",
        (role, content),
    )
    conn.commit()
    conn.close()
