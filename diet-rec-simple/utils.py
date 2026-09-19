"""Optimized SQLite data tracking layer for history and analytics logs."""

from datetime import datetime
import sqlite3

DB_FILE = "nutrition_companion.db"


def init_db() -> None:
    """Initializes standard SQLite tables for session logging."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS daily_macro_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, calories INTEGER)"
    )
    conn.commit()
    conn.close()


def load_persisted_chat() -> list[dict]:
    """Loads text conversation timeline from file history."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT role, content FROM chat_history ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]


def save_chat_message(role: str, content: str) -> None:
    """Appends conversation text directly to local history storage."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content)
    )
    conn.commit()
    conn.close()


def log_daily_calories(calories: int) -> None:
    """Saves daily target energy numbers to track progress metrics over time."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT OR REPLACE INTO daily_macro_logs (log_date, calories) VALUES (?, ?)",
        (datetime.now().strftime("%Y-%m-%d"), calories),
    )
    conn.commit()
    conn.close()


def fetch_analytics_logs() -> list[tuple]:
    """Retrieves chronologically sorted daily summary entries."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT log_date, calories FROM daily_macro_logs ORDER BY log_date ASC"
    ).fetchall()
    conn.close()
    return rows


def clear_entire_session() -> None:
    """Clears history structures cleanly."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
