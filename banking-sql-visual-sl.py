import streamlit as st
import os
import sqlite3
import json
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="Interactive Banking Dashboard", page_icon="🏦", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Database Setup & Core Analytical Engines
DB_FILE = "mock_banking_multi_afc.db"

def init_mock_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, merchant TEXT, amount REAL, date TEXT, category TEXT
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

# =====================================================================
# ENHANCEMENT 1: Decoupled Math Calculation Runtime
# =====================================================================
def run_amortization_schedule(principal: float, annual_rate: float, term_months: int) -> dict:
    """Core mathematical engine capable of running independent of the LLM pipeline."""
    monthly_rate = (annual_rate / 100) / 12
    if monthly_rate == 0:
        payment = principal / term_months
    else:
        payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / (((1 + monthly_rate) ** term_months) - 1)
    
    remaining_balance = principal
    schedule = []
    
    for month in range(1, term_months + 1):
        interest_paid = remaining_balance * monthly_rate
        principal_paid = payment - interest_paid
        remaining_balance -= principal_paid
        if remaining_balance < 0: remaining_balance = 0
        
        schedule.append({
            "Month": month,
            "Principal Paid": round(principal_paid, 2),
            "Interest Paid": round(interest_paid, 2),
            "Remaining Balance": round(remaining_balance, 2)
        })

    return {
        "principal": principal,
        "annual_rate": annual_rate,
        "term_months": term_months,
        "monthly_payment": round(payment, 2),
        "total_payment": round(payment * term_months, 2),
        "total_interest": round((payment * term_months) - principal, 2),
        "schedule": schedule
    }

def calculate_loan_payment(principal: float, annual_rate: float, term_months: int) -> str:
    """Tool target called automatically by Gemini."""
    result_data = run_amortization_schedule(principal, annual_rate, term_months)
    st.session_state.last_calculated_loan = result_data
    return json.dumps(result_data)

def query_user_transaction_history(user_id: str) -> str:
    """Tool target to fetch statements."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT merchant, amount, date, category FROM transactions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return json.dumps([dict(row) for row in rows])

# 3. Session State Initializations
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_calculated_loan" not in st.session_state:
    st.session_state.last_calculated_loan = None

if "gemini_chat" not in st.session_state:
    system_instruction = """
    You are a secure, empathetic, and highly accurate AI financial assistant inside a mobile banking app.
    The current active user is 'USR_001'.
    Use 'query_user_transaction_history' when they ask about their past spending.
    Use 'calculate_loan_payment' if they want to calculate loan options.
    Ground all responses strictly in the data returned by these tools.
    """
    st.session_state.gemini_chat = client.chats.create(
        model='gemini-3.6-flash',
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[query_user_transaction_history, calculate_loan_payment],
        )
    )

# 4. Main App Interface
st.title("🏦 Interactive Hybrid Dashboard & AI Chat")
st.markdown("Use the chat console to structure terms, then use the live controls on the right to perform interactive adjustments.")

layout_chat, layout_visuals = st.columns(2, gap="large")

# --- LEFT COLUMN: Chat Interface ---
with layout_chat:
    st.subheader("💬 Financial Assistant Chat")
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_query := st.chat_input("Calculate a loan for $20,000 at 6% for 24 months..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response_text = ""
            
            try:
                response_stream = st.session_state.gemini_chat.send_message_stream(user_query)
                for chunk in response_stream:
                    if chunk.text:
                        full_response_text += chunk.text
                        placeholder.write(full_response_text)
                        
                st.session_state.messages.append({"role": "assistant", "content": full_response_text})
                st.rerun()
                
            except Exception as e:
                st.error(f"Error handling multi-tool execution stream: {e}")

# --- RIGHT COLUMN: Visual Dashboard & Interactive Sliders ---
with layout_visuals:
    st.subheader("📊 Interactive Loan Overrides & Dashboard")
    
    baseline_loan = st.session_state.last_calculated_loan
    
    if baseline_loan:
        st.markdown("### 🎛️ Real-Time Fine-Tuning Controls")
        st.caption("Adjust these sliders to manually override the parameters computed by the LLM.")
        
        # =====================================================================
        # ENHANCEMENT 2: Context-Seeded Interface Controls (Dynamic UI Seeding)
        # =====================================================================
        tuned_principal = st.slider(
            "Modify Loan Principal ($)", 
            min_value=1000, 
            max_value=100000, 
            value=int(baseline_loan["principal"]), 
            step=500
        )
        
        tuned_term = st.slider(
            "Modify Term Length (Months)", 
            min_value=6, 
            max_value=72, 
            value=int(baseline_loan["term_months"]), 
            step=6
        )
        
        # Instantly compute changes using the decoupled engine
        live_data = run_amortization_schedule(
            principal=float(tuned_principal), 
            annual_rate=baseline_loan["annual_rate"], 
            term_months=int(tuned_term)
        )
        
        # Dynamic Display KPI Metrics
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="Adjusted Monthly Payment", value=f"${live_data['monthly_payment']:,.2f}")
        with m_col2:
            st.metric(label="Adjusted Interest Cost", value=f"${live_data['total_interest']:,.2f}")
        with m_col3:
            st.metric(label="Adjusted Total Out-of-Pocket", value=f"${live_data['total_payment']:,.2f}")
            
        # Visual Charts Re-Rendering
        df = pd.DataFrame(live_data['schedule'])
        st.write("#### 📈 Dynamic Amortization Balance Curve")
        st.area_chart(data=df, x="Month", y="Remaining Balance", color="#FF4B4B",  width='stretch')
        
        st.write("#### 🔄 Principal vs. Interest Mix Over Time")
        st.bar_chart(data=df, x="Month", y=["Principal Paid", "Interest Paid"], color=["#00CC96", "#AB63FA"],width='stretch')
        
        # =====================================================================
        # ENHANCEMENT 3: Bi-Directional State Synchronization ("Sync Back to Chat")
        # =====================================================================
        if tuned_principal != int(baseline_loan["principal"]) or tuned_term != int(baseline_loan["term_months"]):
            st.markdown("---")
            if st.button("🔄 Sync Adjusted Parameters Back to Chat Context", width='stretch'):
                st.session_state.last_calculated_loan = live_data
                
                st.session_state.messages.append({
                    "role": "user", 
                    "content": f"I adjusted my targets on the dashboard sliders to ${tuned_principal:,.2f} over {tuned_term} months."
                })
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Understood. I have updated your context framework. Your adjusted monthly payment is now ${live_data['monthly_payment']:,.2f} with a lifetime interest cost of ${live_data['total_interest']:,.2f}."
                })
                st.rerun()
                
    else:
        st.info("The interactive adjustments control deck and dynamic chart streams will render once a calculation has been triggered through the chat console on the left.")
