import sqlite3
import json
from datetime import datetime

DB_FILE = "nutrition_companion.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, content TEXT, timestamp TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS grocery_list (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT UNIQUE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS daily_macro_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT UNIQUE, calories INTEGER, protein INTEGER, carbs INTEGER, fat INTEGER, raw_payload TEXT)")
    conn.commit()
    conn.close()

def load_persisted_chat():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT role, content FROM chat_history ORDER BY id ASC").fetchall()
    conn.close()
    messages = []
    for role, content in rows:
        if role == "assistant":
            try: messages.append({"role": role, "content": json.loads(content)})
            except: messages.append({"role": role, "content": content})
        else: messages.append({"role": role, "content": content})
    return messages

def save_chat_message(role, content_payload):
    conn = sqlite3.connect(DB_FILE)
    content_str = json.dumps(content_payload) if isinstance(content_payload, dict) else content_payload
    conn.cursor().execute("INSERT INTO chat_history (role, content, timestamp) VALUES (?, ?, ?)", (role, content_str, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_persisted_grocery():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT item FROM grocery_list").fetchall()
    conn.close()
    return [row for row in rows]

def save_grocery_items(ingredients_list):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for ingredient in ingredients_list:
        cursor.execute("INSERT OR IGNORE INTO grocery_list (item) VALUES (?)", (ingredient.strip().capitalize(),))
    conn.commit()
    conn.close()

def delete_all_grocery():
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()

def log_daily_macros(data_dict):
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("""
        INSERT OR REPLACE INTO daily_macro_logs (log_date, calories, protein, carbs, fat, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d"), data_dict.get('daily_total_calories', 0), data_dict.get('total_protein_g', 0), data_dict.get('total_carbs_g', 0), data_dict.get('total_fat_g', 0), json.dumps(data_dict)))
    conn.commit()
    conn.close()

def fetch_analytics_logs():
    conn = sqlite3.connect(DB_FILE)
    rows = conn.cursor().execute("SELECT log_date, calories, protein, carbs, fat FROM daily_macro_logs ORDER BY log_date ASC").fetchall()
    conn.close()
    return rows

def clear_entire_session():
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM chat_history")
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()
