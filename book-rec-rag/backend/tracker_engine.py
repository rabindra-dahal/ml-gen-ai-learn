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
    """Fetches all structured book metrics with explicit row tuple unpacking to prevent tuple type mismatches."""
    conn = get_db_connection()
    rows = conn.cursor().execute(
        "SELECT id, book_title, rating, review_notes FROM reading_list ORDER BY id DESC"
    ).fetchall()
    conn.close()
    
    # ─── FIXED: EXPLICITLY UNPACK THE TUPLE FIELDS INSIDE THE COMPREHENSION LOOP ───
    # This separates each index immediately, forcing 'rating' into a clean, standalone integer object.
    return [
        {
            "id": book_id,
            "title": title,
            "rating": rating,
            "review": review
        } 
        for book_id, title, rating, review in rows
    ]

# Add Math Metrics Calculation Hook
def fetch_kpi_summary_metrics() -> dict:
    """Calculates active analytical metrics summary counts across historical reading logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate totals and average star evaluations
    books_data = cursor.execute("SELECT rating FROM reading_list").fetchall()
    total_saved = len(books_data)
    
    rated_books = [r[0] for r in books_data if r[0] > 0]
    avg_rating = sum(rated_books) / len(rated_books) if rated_books else 0.0
    
    conn.close()
    return {
        "total_saved": total_saved,
        "avg_rating": round(avg_rating, 1)
    }


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
