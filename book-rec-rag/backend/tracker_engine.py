"""Module tracking metrics, goals updates, user evaluations, and API counters."""

from datetime import datetime
from backend.db_core import get_db_connection


def increment_api_counter(call_type: str) -> None:
    """Logs an API key event to the telemetry table."""
    conn = get_db_connection()
    conn.cursor().execute(
        "INSERT INTO api_usage_telemetry (call_type, timestamp) VALUES (?, ?)",
        (call_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_total_api_calls() -> int:
    """Returns the total number of recorded Gemini API calls."""
    conn = get_db_connection()
    res = conn.cursor().execute("SELECT COUNT(*) FROM api_usage_telemetry").fetchone()
    conn.close()
    return res[0] if res else 0


def log_reading_goal(books_target: int) -> None:
    """Saves user reading targets to compile performance tracking graphs."""
    conn = get_db_connection()
    conn.cursor().execute(
        """INSERT OR REPLACE INTO reading_goal_logs (log_date, books_target) 
           VALUES (?, ?)""",
        (datetime.now().strftime("%Y-%m-%d"), books_target),
    )
    conn.commit()
    conn.close()


def fetch_analytics_logs() -> list[tuple]:
    """Retrieves chronologically sorted pace entries for graph generation."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT log_date, books_target FROM reading_goal_logs ORDER BY log_date ASC"
    ).fetchall()
    conn.close()
    return rows


def load_persisted_reading_list() -> list[dict]:
    """Fetches all structured book metrics with proper column mapping and row IDs."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT id, book_title, rating, review_notes FROM reading_list ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "rating": row[2], "review": row[3]} for row in rows]


def save_book_to_list(book_title: str) -> None:
    """Appends a new unique book title string cleanly into SQLite storage."""
    conn = get_db_connection()
    conn.cursor().execute(
        "INSERT OR IGNORE INTO reading_list (book_title) VALUES (?)",
        (book_title.strip(),),
    )
    conn.commit()
    conn.close()


def update_book_review(book_title: str, rating: int, review_notes: str) -> None:
    """Updates the explicit star evaluation scores and review strings."""
    conn = get_db_connection()
    conn.cursor().execute(
        "UPDATE reading_list SET rating = ?, review_notes = ? WHERE book_title = ?",
        (rating, review_notes, book_title),
    )
    conn.commit()
    conn.close()


def delete_all_tracked_books() -> None:
    """Clears out all saved items inside the reading list database table."""
    conn = get_db_connection()
    conn.cursor().execute("DELETE FROM reading_list")
    conn.commit()
    conn.close()


def clear_entire_session() -> None:
    """Purges chat dialogue tables, telemetry, and active trackers during resets."""
    conn = get_db_connection()
    conn.cursor().execute("DELETE FROM chat_history")
    conn.cursor().execute("DELETE FROM reading_list")
    conn.cursor().execute("DELETE FROM api_usage_telemetry")
    conn.commit()
    conn.close()
