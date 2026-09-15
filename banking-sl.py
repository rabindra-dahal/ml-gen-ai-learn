import streamlit as st
import os
import uuid
import datetime
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="Compliance-Ready Bank Assistant", page_icon="💰", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Define the Structured JSON Schema
class FinancialAssessment(BaseModel):
    can_afford: bool = Field(description="True if the user can safely afford the purchase, False otherwise.")
    reasoning: str = Field(description="A concise, 1-2 sentence empathetic explanation of why, referencing balances or bills.")
    safety_buffer_remaining: float = Field(description="The remaining balance after purchase and upcoming bills are subtracted.")
    alternative_action: str = Field(description="A friendly actionable alternative if they can't afford it, or a saving tip if they can.")

# 3. Session State & Compliance Tracking Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Generate or maintain a unique conversation session ID for logging compliance
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# 4. Streamlit Sidebar: Core Banking API Simulator
st.sidebar.header("🏦 Core Banking API Simulator")
checking_balance = st.sidebar.number_input("Checking Account Balance ($)", value=1200.00, step=50.0)
savings_balance = st.sidebar.number_input("Savings Account Balance ($)", value=5000.00, step=100.0)
weekly_budget = st.sidebar.number_input("Weekly Discretionary Budget ($)", value=200.00, step=10.0)

st.sidebar.subheader("📅 Upcoming Bills")
bill_cc = st.sidebar.number_input("Credit Card Minimum ($)", value=500.00, step=10.0)
bill_rent = st.sidebar.number_input("Rent Allocation ($)", value=400.00, step=50.0)

mock_banking_context = {
    "checking_balance": checking_balance,
    "savings_balance": savings_balance,
    "upcoming_bills": [{"name": "Credit Card Minimum", "amount": bill_cc}, {"name": "Rent", "amount": bill_rent}],
    "average_weekly_discretionary_spending": weekly_budget
}

# 5. Compliance & Controls Sidebar Subpanel
st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Compliance & Controls")
st.sidebar.info(f"**Session ID:**\n`{st.session_state.conversation_id}`")

# The Clear History Functional Component
if st.sidebar.button("🗑️ Clear Chat History", use_container_width=True):
    st.session_state.messages = []
    # Regenerate session token on complete user wipe for fresh logging state
    st.session_state.conversation_id = str(uuid.uuid4())
    st.rerun()

# 6. Main UI Canvas
st.title("💰 AI Personal Financial Assistant")

# Render past chat conversation history from session state
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and isinstance(msg["content"], dict):
            data = msg["content"]
            if data.get("can_afford"):
                st.success("✅ Assessment: Confirmed Affordability")
            else:
                st.error("❌ Assessment: Financial Risk Detected")
            st.metric(label="Calculated Safety Buffer Remaining", value=f"${data.get('safety_buffer_remaining'):,.2f}")
            st.info(f"**Advisor Reasoning:** {data.get('reasoning')}")
            st.warning(f"💡 **Suggested Next Step:** {data.get('alternative_action')}")
        else:
            st.write(msg["content"])

# System core layout configurations
system_instruction = """
You are a secure, empathetic, and highly accurate AI financial assistant inside a mobile banking app.
Analyze the user's query strictly using the provided real-time financial context.
Do not provide investment advice. Remain objective and prioritize the user's financial health.
"""

# Accept new user query input
if user_query := st.chat_input("Can I afford a $300 dinner tonight at a Michelin restaurant?"):
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    user_prompt = f"""
    Context:
    - Checking Account Balance: ${mock_banking_context['checking_balance']}
    - Savings Account Balance: ${mock_banking_context['savings_balance']}
    - Upcoming Bills: {mock_banking_context['upcoming_bills']}
    - Weekly Discretionary Budget: ${mock_banking_context['average_weekly_discretionary_spending']}

    User Query: "{user_query}"
    """

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response_text = ""
        
        try:
            response_stream = client.models.generate_content_stream(
                model='gemini-3.6-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=FinancialAssessment,
                ),
            )
            
            for chunk in response_stream:
                full_response_text += chunk.text
                placeholder.code(full_response_text, language="json")
            
            placeholder.empty()
            
            parsed_data = FinancialAssessment.model_validate_json(full_response_text)
            parsed_dict = parsed_data.model_dump()
            
            st.session_state.messages.append({"role": "assistant", "content": parsed_dict})
            
            # --- Enterprise Compliance Logging Simulation ---
            # In production, this dictionary would be pushed to an immutable system (e.g., AWS CloudWatch, Datadog, or an Audit DB)
            log_payload = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "conversation_id": st.session_state.conversation_id,
                "user_prompt": user_query,
                "input_context": mock_banking_context,
                "llm_raw_response": full_response_text
            }
            # For demonstration, we print this directly to the system console logs
            print(f"[AUDIT LOG] {log_payload}")
            # ------------------------------------------------

            if parsed_dict["can_afford"]:
                st.success("✅ Assessment: Confirmed Affordability")
            else:
                st.error("❌ Assessment: Financial Risk Detected")
                
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Calculated Safety Buffer Remaining", value=f"${parsed_dict['safety_buffer_remaining']:,.2f}")
                st.info(f"**Advisor Reasoning:** {parsed_dict['reasoning']}")
            with col2:
                st.warning(f"💡 **Suggested Next Step:** {parsed_dict['alternative_action']}")
                
        except Exception as e:
            st.error(f"Error handling streaming pipeline: {e}")
