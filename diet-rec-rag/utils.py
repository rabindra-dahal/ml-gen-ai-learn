"""Utility module providing optimized Pydantic schemas and database actions."""

from datetime import datetime
import json
import sqlite3
import numpy as np
from pydantic import BaseModel, Field

DB_FILE = "nutrition_companion.db"


class MealItem(BaseModel):
    meal_type: str
    recipe_name: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    ingredients: list[str]
    prep_tip: str
    matched_from_db: bool = False


class DietPlanResponse(BaseModel):
    conversational_intro: str
    daily_total_calories: int
    total_protein_g: int
    total_carbs_g: int
    total_fat_g: int
    meals: list[MealItem]


def init_db() -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS grocery_list (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT UNIQUE)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS daily_macro_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS recipe_knowledge_base (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, meal_type TEXT, diet_tag TEXT, calories INTEGER, recipe_json TEXT, embedding_json TEXT)"
    )
    conn.commit()
    conn.close()


def load_persisted_chat() -> list[dict]:
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
            except Exception:
                messages.append({"role": role, "content": content})
        else:
            messages.append({"role": role, "content": content})
    return messages


def save_chat_message(role: str, content_payload: dict | str) -> None:
    conn = sqlite3.connect(DB_FILE)
    s = (
        json.dumps(content_payload)
        if isinstance(content_payload, dict)
        else content_payload
    )
    conn.cursor().execute(
        "INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, s)
    )
    conn.commit()
    conn.close()


def load_persisted_grocery() -> list[str]:
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT item FROM grocery_list").fetchall()
    conn.close()
    return [r[0] for r in rows]


def save_grocery_items(items: list[str]) -> None:
    conn = sqlite3.connect(DB_FILE)
    for i in items:
        conn.cursor().execute(
            "INSERT OR IGNORE INTO grocery_list (item) VALUES (?)",
            (i.strip().capitalize(),),
        )
    conn.commit()
    conn.close()


def delete_all_grocery() -> None:
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()


def log_daily_macros(d: dict) -> None:
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT OR REPLACE INTO daily_macro_logs (log_date, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d"),
            d.get("daily_total_calories", 0),
            d.get("total_protein_g", 0),
            d.get("total_carbs_g", 0),
            d.get("total_fat_g", 0),
        ),
    )
    conn.commit()
    conn.close()


def fetch_analytics_logs() -> list[tuple]:
    return (
        sqlite3.connect(DB_FILE)
        .cursor()
        .execute(
            "SELECT log_date, calories, protein, carbs, fat FROM daily_macro_logs ORDER BY log_date ASC"
        )
        .fetchall()
    )


def clear_entire_session() -> None:
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM chat_history")
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()


def save_recipe_to_vector_store(
    t, m_type, tag, cal, r_dict, emb_vector
) -> None:
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute(
        "INSERT INTO recipe_knowledge_base (title, meal_type, diet_tag, calories, recipe_json, embedding_json) VALUES (?, ?, ?, ?, ?, ?)",
        (t, m_type, tag, cal, json.dumps(r_dict), json.dumps(emb_vector)),
    )
    conn.commit()
    conn.close()


def query_vector_store_rag(query_embedding: list[float], limit: int = 1) -> list[dict]:
    """Optimized database vector mathematical check utilizing vectorized numpy execution."""
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute(
        "SELECT recipe_json, embedding_json FROM recipe_knowledge_base"
    ).fetchall()
    conn.close()
    if not rows:
        return []

    q_vec = np.array(query_embedding)
    q_norm = np.linalg.norm(q_vec)
    if q_norm == 0:
        return []

    res = []
    for r_json, emb_json in rows:
        if not emb_json:
            continue
        r_vec = np.array(json.loads(emb_json))
        r_norm = np.linalg.norm(r_vec)
        if r_norm == 0:
            continue
        # Vectorized optimization
        sim = np.dot(q_vec, r_vec) / (q_norm * r_norm)
        res.append((sim, json.loads(r_json)))

    res.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in res[:limit]]
