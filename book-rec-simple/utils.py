"""Data persistence engine providing SQLite tracking workflows.

Manages conversational message history, reading goals, and book reviews.
"""

from datetime import datetime
import sqlite3

DB_FILE = "book_recommender.db"


def init_db() -> None:
    """Initializes schema blueprints for book collection and reviews."""
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
    # UPDATED: Altered to track granular rating states and text reviews natively
    c.execute(
        """CREATE TABLE IF NOT EXISTS reading_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            book_title TEXT UNIQUE,
            rating INTEGER DEFAULT 0,
            review_notes TEXT DEFAULT ''
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


def load_persisted_reading_list() -> list[dict]:
    """Fetches all structured book metrics including active ratings and reviews."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT book_title, rating, review_notes FROM reading_list ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [
        {"title": row[0], "rating": row[1], "review": row[2]} for row in rows
    ]


def save_book_to_list(book_title: str) -> None:
    """Appends a new unique book title string cleanly into SQLite storage."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT OR IGNORE INTO reading_list (book_title) VALUES (?)",
        (book_title.strip(),),
    )
    conn.commit()
    conn.close()


def update_book_review(book_title: str, rating: int, review_notes: str) -> None:
    """Updates the explicit star evaluation scores and review strings."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "UPDATE reading_list SET rating = ?, review_notes = ? WHERE book_title = ?",
        (rating, review_notes, book_title),
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
