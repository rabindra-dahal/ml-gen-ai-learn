import streamlit as st
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="AI Bank Assistant", page_icon="💰", layout="wide")
load_dotenv()

# Instantiate the Gemini Client
@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Please check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Define the Pydantic Schema for Structured JSON Output
class FinancialAssessment(BaseModel):
    can_afford: bool = Field(description="True if the user can safely afford the purchase, False otherwise.")
    reasoning: str = Field(description="A concise, 1-2 sentence empathetic explanation of why, referencing balances or bills.")
    safety_buffer_remaining: float = Field(description="The remaining balance after purchase and upcoming bills are subtracted.")
    alternative_action: str = Field(description="A friendly actionable alternative if they can't afford it, or a saving tip if they can.")

# 3. Streamlit Sidebar: Interactive Mock Core Banking Data
st.sidebar.header("🏦 Core Banking API Simulator")
st.sidebar.markdown("Modify these parameters to simulate real-time API state updates.")

checking_balance = st.sidebar.number_input("Checking Account Balance ($)", value=1200.00, step=50.0)
savings_balance = st.sidebar.number_input("Savings Account Balance ($)", value=5000.00, step=100.0)
weekly_budget = st.sidebar.number_input("Weekly Discretionary Budget ($)", value=200.00, step=10.0)

st.sidebar.subheader("📅 Upcoming Bills (Next 7 Days)")
bill_cc = st.sidebar.number_input("Credit Card Minimum ($)", value=500.00, step=10.0)
bill_rent = st.sidebar.number_input("Rent Allocation ($)", value=400.00, step=50.0)

# Pack context for the RAG engine
mock_banking_context = {
    "checking_balance": checking_balance,
    "savings_balance": savings_balance,
    "upcoming_bills": [
        {"name": "Credit Card Minimum", "amount": bill_cc},
        {"name": "Rent", "amount": bill_rent}
    ],
    "average_weekly_discretionary_spending": weekly_budget
}

# 4. Main App Interface
st.title("💰 AI-Powered Personal Financial Assistant")
st.markdown("Ask the conversational engine questions about your immediate affordability based on your live account health.")

# System Prompt Context
system_instruction = """
You are a secure, empathetic, and highly accurate AI financial assistant inside a mobile banking app.
Analyze the user's query strictly using the provided real-time financial context.
Do not provide investment advice. Remain objective and prioritize the user's financial health.
"""

# Chat Input UI
user_query = st.text_input("Ask your assistant (e.g., 'Can I afford a $300 dinner tonight at a Michelin restaurant?')")

if user_query:
    # Construct Grounded Context Prompt
    user_prompt = f"""
    Context:
    - Checking Account Balance: ${mock_banking_context['checking_balance']}
    - Savings Account Balance: ${mock_banking_context['savings_balance']}
    - Upcoming Bills: {mock_banking_context['upcoming_bills']}
    - Weekly Discretionary Budget: ${mock_banking_context['average_weekly_discretionary_spending']}

    User Query: "{user_query}"
    """

    with st.spinner("Analyzing parameters with Gemini 3.6 Flash..."):
        try:
            # Query the Gemini Model with Strict JSON Outputs
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=FinancialAssessment,
                ),
            )
            
            # 5. Native UI Presentation mapping the Structured Data Output
            # We parse the text safely into an object
            data = FinancialAssessment.model_validate_json(response.text)
            
            st.write("---")
            
            # Dynamically color visual indicator cards based on boolean status
            if data.can_afford:
                st.success("✅ Assessment: Confirmed Affordability")
            else:
                st.error("❌ Assessment: Financial Risk Detected")
            
            # Split details into scannable UI layout components
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Calculated Safety Buffer Remaining", value=f"${data.safety_buffer_remaining:,.2f}")
                st.info(f"**Advisor Reasoning:** {data.reasoning}")
            
            with col2:
                st.warning(f"💡 **Suggested Next Step:** {data.alternative_action}")
                
            with st.expander("🔍 View Raw JSON Payload Returned by Model"):
                st.json(response.text)
                
        except Exception as e:
            st.error(f"Error executing LLM orchestration pipeline: {e}")
