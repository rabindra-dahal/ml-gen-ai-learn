"""Utility module providing Pydantic schemas and SQLite database operations.

Includes vector similarity capabilities for a RAG-driven diet application.
"""

from datetime import datetime
import json
import sqlite3
import numpy as np
from pydantic import BaseModel, Field

DB_FILE = "nutrition_companion.db"


# --- PYDANTIC SCHEMAS ---


class MealItem(BaseModel):
    """Pydantic model representing a structured individual meal card."""

    meal_type: str = Field(
        description="Type of meal (e.g., Breakfast, Lunch, Dinner, Snack)."
    )
    recipe_name: str = Field(description="Name of the meal or recipe.")
    calories: int = Field(description="Estimated calories.")
    protein_g: int = Field(description="Protein in grams.")
    carbs_g: int = Field(description="Carbohydrates in grams.")
    fat_g: int = Field(description="Fat in grams.")
    ingredients: list[str] = Field(description="List of ingredients.")
    prep_tip: str = Field(description="1-sentence prep tip.")
    matched_from_db: bool = Field(
        default=False,
        description="True if recipe is from the provided database context.",
    )


class DietPlanResponse(BaseModel):
    """Pydantic model forcing Gemini to return a structured daily plan response."""

    conversational_intro: str = Field(description="Summary statement.")
    daily_total_calories: int = Field(description="Total daily calories.")
    total_protein_g: int = Field(description="Total protein grams.")
    total_carbs_g: int = Field(description="Total carbohydrate grams.")
    total_fat_g: int = Field(description="Total fat grams.")
    meals: list[MealItem] = Field(
        description="Array of 3-4 meal recommendations."
    )


# --- DB METHODS ---


def init_db() -> None:
    """Initializes SQLite database schemas for history, lists, and logging."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS chat_history 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS grocery_list 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT UNIQUE)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS daily_macro_logs 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, 
                   calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS recipe_knowledge_base 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, meal_type TEXT, 
                   diet_tag TEXT, calories INTEGER, recipe_json TEXT, embedding_json TEXT)"""
    )
    conn.commit()
    conn.close()


def load_persisted_chat() -> list[dict]:
    """Loads chat timeline entries from the SQLite chat historical ledger."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT role, content FROM chat_history ORDER BY id ASC"
    ).fetchall()
    conn.close()

    messages = []
    for role, content in rows:
        if role == "assistant":
            try:
                messages.append({"role": role, "content": json.loads(content)})
            except (json.JSONDecodeError, TypeError):
                messages.append({"role": role, "content": content})
        else:
            messages.append({"role": role, "content": content})
    return messages


def save_chat_message(role: str, content_payload: dict | str) -> None:
    """Stores user queries or assistant dictionary responses to file history."""
    conn = sqlite3.connect(DB_FILE)
    serialized = (
        json.dumps(content_payload)
        if isinstance(content_payload, dict)
        else content_payload
    )
    conn.cursor().execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)",
        (role, serialized),
    )
    conn.commit()
    conn.close()


def load_persisted_grocery() -> list[str]:
    """Fetches all unique items saved in the grocery database storage list."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT item FROM grocery_list").fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_grocery_items(items: list[str]) -> None:
    """Appends array of ingredient text snippets cleanly into local SQLite storage."""
    conn = sqlite3.connect(DB_FILE)
    for item in items:
        conn.cursor().execute(
            "INSERT OR IGNORE INTO grocery_list (item) VALUES (?)",
            (item.strip().capitalize(),),
        )
    conn.commit()
    conn.close()


def delete_all_grocery() -> None:
    """Clears out all recorded grocery lines within the database layout."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()


def log_daily_macros(data_dict: dict) -> None:
    """Saves daily intake targets for tracking and dashboard compilation."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        """INSERT OR REPLACE INTO daily_macro_logs 
           (log_date, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)""",
        (
            datetime.now().strftime("%Y-%m-%d"),
            data_dict.get("daily_total_calories", 0),
            data_dict.get("total_protein_g", 0),
            data_dict.get("total_carbs_g", 0),
            data_dict.get("total_fat_g", 0),
        ),
    )
    conn.commit()
    conn.close()


def fetch_analytics_logs() -> list[tuple]:
    """Retrieves chronologically sorted daily summary records for analytics graphing."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT log_date, calories, protein, carbs, fat FROM daily_macro_logs ORDER BY log_date ASC"
    ).fetchall()
    conn.close()
    return rows


def clear_entire_session() -> None:
    """Purges active user conversational records and shopping list contents completely."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM chat_history")
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()


def save_recipe_to_vector_store(
    title: str,
    meal_type: str,
    diet_tag: str,
    calories: int,
    recipe_dict: dict,
    embedding_vector: list[float],
) -> None:
    """Indexes factual reference recipes beside vector embedding array data points."""
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        """INSERT INTO recipe_knowledge_base 
           (title, meal_type, diet_tag, calories, recipe_json, embedding_json) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            title,
            meal_type,
            diet_tag,
            calories,
            json.dumps(recipe_dict),
            json.dumps(embedding_vector),
        ),
    )
    conn.commit()
    conn.close()


def query_vector_store_rag(
    query_embedding: list[float], limit: int = 2
) -> list[dict]:
    """Performs in-memory cosine similarity metrics to locate match context."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT recipe_json, embedding_json FROM recipe_knowledge_base"
    ).fetchall()
    conn.close()

    if not rows:
        return []

    results = []
    q_vec = np.array(query_embedding)
    q_norm = np.linalg.norm(q_vec)

    for r_json, emb_json in rows:
        if not r_json or not emb_json:
            continue
        r_vec = np.array(json.loads(emb_json))
        r_norm = np.linalg.norm(r_vec)

        if q_norm == 0 or r_norm == 0:
            continue

        # Cosine Similarity Calculation
        similarity = np.dot(q_vec, r_vec) / (q_norm * r_norm)
        results.append((similarity, json.loads(r_json)))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:limit]]
