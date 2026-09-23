"""Database core connectivity infrastructure provisioning baseline SQLite initialization tables."""

import sqlite3

DB_FILE = "book_recommender.db"


def get_db_connection() -> sqlite3.Connection:
    """Returns a direct isolated socket handle to the local sqlite binary data asset."""
    return sqlite3.connect(DB_FILE)


def init_db() -> None:
    """Initializes schema blueprints for book collection, reviews, telemetry, and RAG."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chat_history 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS reading_goal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, books_target INTEGER
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS reading_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT, book_title TEXT UNIQUE,
            rating INTEGER DEFAULT 0, review_notes TEXT DEFAULT ''
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS book_knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, author TEXT,
            genre TEXT, summary TEXT, embedding_json TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS api_usage_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT, call_type TEXT, timestamp TEXT
        )"""
    )
    conn.commit()
    conn.close()
