import streamlit as st
import os
import uuid
import datetime
import sqlite3
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="AFC Python Chat Bank", page_icon="🏦", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Database Initialization
DB_FILE = "mock_banking_afc.db"

def init_mock_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            merchant TEXT,
            amount REAL,
            date TEXT,
            category TEXT
        )
    """)
    cursor.execute("DELETE FROM transactions")
    # Seed mock history for user USR_001 (Alice Vance)
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Netflix', 15.49, '2026-09-01', 'Subscriptions')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Starbucks', 6.75, '2026-09-12', 'Dining')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Amazon Prime', 14.99, '2026-09-14', 'Subscriptions')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Target', 84.20, '2026-09-14', 'Shopping')")
    conn.commit()
    conn.close()

init_mock_db()

# 3. Python Function Defined as a Gemini Tool
def query_user_transaction_history(user_id: str) -> str:
    """
    Retrieves the complete recent bank statement and transaction history for a given user ID.
    Use this tool whenever the user asks about their recent purchases, spending habits, or transaction records.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT merchant, amount, date, category FROM transactions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = [dict(row) for row in rows]
    return json.dumps(results)

# 4. Streamlit Session State & Chat Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize or grab the persistent SDK Chat instance safely inside session state
if "gemini_chat" not in st.session_state:
    system_instruction = """
    You are a secure, empathetic, and highly accurate AI financial assistant inside a mobile banking app.
    The current active user is 'USR_001'.
    If the user asks questions regarding their recent history, transactions, or merchant spending, use the 'query_user_transaction_history' tool.
    Provide human-like, conversational answers based strictly on the tool's return values.
    """
    
    # Instantiate the multi-turn session with tools attached
    st.session_state.gemini_chat = client.chats.create(
        model='gemini-3.6-flash',
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            # We explicitly declare our local python function as an available tool execution target
            tools=[query_user_transaction_history],
        )
    )

# 5. UI Layout Components
st.title("🏦 Conversational Banking via Chat.send_message_stream")
st.markdown("This setup utilizes **Automatic Function Calling (AFC)** within the recommended chat stream lifecycle to dynamically inspect your transaction history.")

# Display historical turns
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# User prompt ingestion
if user_query := st.chat_input("How many subscriptions did I pay for this month?"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response_text = ""
        
        try:
            # RECOMMENDED PATTERN: Safe automatic loop execution during real-time streaming
            response_stream = st.session_state.gemini_chat.send_message_stream(user_query)
            
            for chunk in response_stream:
                # The SDK intercepts tool calls silently, executes query_user_transaction_history, 
                # submits results to Gemini, and then streams out text here
                if chunk.text:
                    full_response_text += chunk.text
                    placeholder.write(full_response_text)
                    
            st.session_state.messages.append({"role": "assistant", "content": full_response_text})
            
        except Exception as e:
            st.error(f"Error executing chat tool stream pipeline: {e}")
