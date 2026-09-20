"""Data persistence engine providing SQLite tracking workflows.

Manages conversational message history, reading goals, and a reading tracker.
"""

from datetime import datetime
import sqlite3

DB_FILE = "book_recommender.db"


def init_db() -> None:
    """Initializes schema blueprints for book collection metrics."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chat_history 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS reading_goal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            log_date TEXT UNIQUE, 
            books_target INTEGER
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS reading_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            book_title TEXT UNIQUE
        )"""
    )
    conn.commit()
    conn.close()


def load_persisted_chat() -> list[dict]:
    """Loads text conversation timeline from historical database records."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT role, content FROM chat_history ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]


def save_chat_message(role: str, content: str) -> None:
    """Stores text conversation items directly to storage history logs."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)",
        (role, content),
    )
    conn.commit()
    conn.close()


def log_reading_goal(books_target: int) -> None:
    """Saves user reading targets to compile performance tracking graphs."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        """INSERT OR REPLACE INTO reading_goal_logs (log_date, books_target) 
           VALUES (?, ?)""",
        (datetime.now().strftime("%Y-%m-%d"), books_target),
    )
    conn.commit()
    conn.close()


def fetch_analytics_logs() -> list[tuple]:
    """Retrieves chronologically sorted pace entries for graph generation."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT log_date, books_target FROM reading_goal_logs ORDER BY log_date ASC"
    ).fetchall()
    conn.close()
    return rows


def load_persisted_reading_list() -> list[str]:
    """Fetches all raw book title strings tracked in the database collection."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT book_title FROM reading_list").fetchall()
    conn.close()
    return [row[0] for row in rows]


def save_book_to_list(book_title: str) -> None:
    """Appends a new unique book title string cleanly into SQLite storage."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT OR IGNORE INTO reading_list (book_title) VALUES (?)",
        (book_title.strip(),),
    )
    conn.commit()
    conn.close()


def delete_all_tracked_books() -> None:
    """Clears out all saved items inside the reading list database table."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM reading_list")
    conn.commit()
    conn.close()


def clear_entire_session() -> None:
    """Purges chat dialogue tables and active trackers during master clear actions."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM chat_history")
    conn.cursor().execute("DELETE FROM reading_list")
    conn.commit()
    conn.close()
