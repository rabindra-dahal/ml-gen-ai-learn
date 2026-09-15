import streamlit as st
import os
import sqlite3
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="Multi-Tool AFC Banking Chat", page_icon="🏦", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Database Setup & Tool Functions
DB_FILE = "mock_banking_multi_afc.db"

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
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Netflix', 15.49, '2026-09-01', 'Subscriptions')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Starbucks', 6.75, '2026-09-12', 'Dining')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Amazon Prime', 14.99, '2026-09-14', 'Subscriptions')")
    cursor.execute("INSERT INTO transactions (user_id, merchant, amount, date, category) VALUES ('USR_001', 'Target', 84.20, '2026-09-14', 'Shopping')")
    conn.commit()
    conn.close()

init_mock_db()

# --- SDK BEST PRACTICE: Type hints and clean docstrings generate optimal schemas automatically ---

def query_user_transaction_history(user_id: str) -> str:
    """
    Retrieves the complete recent bank statement and transaction history for a given user ID.
    
    Args:
        user_id: The unique identification token of the customer account, e.g., 'USR_001'.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT merchant, amount, date, category FROM transactions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return json.dumps([dict(row) for row in rows])

def calculate_loan_payment(principal: float, annual_rate: float, term_months: int) -> str:
    """
    Calculates fixed monthly payments, total interest costs, and total repayment amounts for a loan option.
    
    Args:
        principal: The total amount of money borrowed (the loan principal).
        annual_rate: The annual percentage interest rate (APR) as a number (e.g., 5.5 for 5.5%).
        term_months: The total length of the loan amortization term expressed in months.
    """
    monthly_rate = (annual_rate / 100) / 12
    if monthly_rate == 0:
        payment = principal / term_months
    else:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / (((1 + monthly_rate) ** term_months) - 1)
    
    return json.dumps({
        "monthly_payment": round(payment, 2),
        "total_payment": round(payment * term_months, 2),
        "total_interest": round((payment * term_months) - principal, 2)
    })

# 3. Streamlit Chat & Session Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "gemini_chat" not in st.session_state:
    system_instruction = """
    You are a secure, empathetic, and highly accurate AI financial assistant inside a mobile banking app.
    The current active user is 'USR_001'. 
    Use 'query_user_transaction_history' when they ask about their past spending.
    Use 'calculate_loan_payment' if they want to simulate borrowing money or calculating loan options.
    Ground all responses strictly in the data returned by these tools. Do not offer uncertified investment advice.
    """
    
    # FIXED: Simply pass the Python functions directly. 
    # The SDK auto-discovers their names, parameters, descriptions, and registers them as tools.
    banking_tools = [
        query_user_transaction_history,
        calculate_loan_payment
    ]
    
    st.session_state.gemini_chat = client.chats.create(
        model='gemini-3.6-flash',
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=banking_tools,
        )
    )

# 4. UI Layout Components
st.title("🏦 Fixed Multi-Tool Conversational Banking Engine")
st.markdown("Ask about past transactions (e.g., *'What did I spend at Target?'*) or run loan estimates (e.g., *'What would a $10,000 loan cost at 6% interest for 24 months?'*).")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_query := st.chat_input("Ask me anything about your history or custom loan calculations..."):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response_text = ""
        
        try:
            # Multi-turn execution stream runs smoothly with registered Python tool mappings
            response_stream = st.session_state.gemini_chat.send_message_stream(user_query)
            
            for chunk in response_stream:
                if chunk.text:
                    full_response_text += chunk.text
                    placeholder.write(full_response_text)
                    
            st.session_state.messages.append({"role": "assistant", "content": full_response_text})
            
        except Exception as e:
            st.error(f"Error handling multi-tool execution stream: {e}")
