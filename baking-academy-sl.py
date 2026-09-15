import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Load environment variables
load_dotenv()

# 2. UI Layout Configuration
st.set_page_config(page_title="Rise & Bake Academy", page_icon="🥖", layout="wide")

st.title("🥖 Rise & Bake Culinary Academy")
st.caption("AI Kitchen Mentor & Recipe Lab Powered by Gemini 3.6 Flash")

# 3. Secure API Key Retrieval
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ `GEMINI_API_KEY` not detected. Please verify your local `.env` file configuration.")
    st.stop()

# 4. Initialize SDK Client
@st.cache_resource
def get_gemini_client(key):
    return genai.Client(api_key=key)

client = get_gemini_client(api_key)

# ==========================================
# CULINARY TOOLS FOR GENAI (AFC)
# ==========================================
def calculate_dough_hydration(flour_grams: float, water_grams: float) -> str:
    """
    Calculates the exact hydration percentage of a dough recipe based on flour and water weights.
    Use this when a student asks about dough sticky-ness, ratios, or hydration calculation.
    """
    if flour_grams <= 0:
        return "Error: Flour weight must be greater than zero."
    
    hydration = (water_grams / flour_grams) * 100
    
    # Provide culinary context alongside the math
    notes = "Standard hydration (60-65%): Tight, easy to shape.\n"
    if hydration >= 75:
        notes = "High hydration (75%+): Very sticky, open crumb structure typical for Ciabatta or Sourdough."
    elif hydration < 60:
        notes = "Low hydration (Under 60%): Stiff dough, common for Bagels or Pretzels."

    return f"Calculated Hydration: {hydration:.1f}%\nCulinary Classification: {notes}"

def convert_oven_temperature(temp_value: float, unit_from: str) -> str:
    """
    Converts culinary oven baking temperatures between Celsius and Fahrenheit.
    Accepts 'C' or 'F' for unit_from.
    """
    unit_cleaned = unit_from.strip().upper()
    if unit_cleaned == "C":
        converted = (temp_value * 9/5) + 32
        return f"{temp_value}°C converts exactly to {converted:.1f}°F (Standard baking range)."
    elif unit_cleaned == "F":
        converted = (temp_value - 32) * 5/9
        return f"{temp_value}°F converts exactly to {converted:.1f}°C (Standard baking range)."
    else:
        return "Error: Invalid unit. Use 'C' or 'F'."

# ==========================================
# SETUP CULINARY PERSISTENT CONTEXT
# ==========================================
ACADEMY_PROMPT = """
You are 'Chef Pierre', the master pastry chef and head instructor at the Rise & Bake Academy. 
Your tone is encouraging, precise, and passionate about culinary arts. 

Guidelines:
1. Scope: Help students troubleshoot flat bread structure, unactivated yeast, sticky pastry doughs, and recipe adaptations.
2. Math/Conversion: Always use your registered tools (`calculate_dough_hydration`, `convert_oven_temperature`) whenever a student brings up raw weights or asks to translate temperatures. Never guess the numbers.
3. Limits: Politely refuse non-baking requests (e.g., car repairs, coding, politics) by framing it as a distraction from mastering the dough.
"""

# ==========================================
# SIDEBAR SCENARIO INJECTOR
# ==========================================
with st.sidebar:
    st.header("👩‍🍳 Student Scenario Injector")
    st.write("Simulate standard classroom problems instantly:")
    
    scenarios = {
        "🍞 Flat Sourdough Troubleshooting": "Chef Pierre, my sourdough loaf turned out completely flat like a pancake. The crumb is super dense. What went wrong?",
        "⚖️ Hydration Calculator Test": "I am mixing a dough with 500 grams of King Arthur bread flour and 390 grams of lukewarm water. Can you check my hydration percentage?",
        "🔥 European Recipe Temperature": "I am trying to bake a French Brioche recipe that calls for an oven temp of 190 degrees Celsius, but my oven at home only displays Fahrenheit! Help!"
    }
    
    injected_prompt = None
    for label, prompt_text in scenarios.items():
        if st.button(label, use_container_width=True):
            injected_prompt = prompt_text
            
    if st.button("🔄 Reset Academy Session", type="secondary", use_container_width=True):
        del st.session_state.chat_session
        st.rerun()

# Initialize chat session with culinary function registrations
if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            system_instruction=ACADEMY_PROMPT,
            temperature=0.3,
            tools=[calculate_dough_hydration, convert_oven_temperature]
        )
    )

# Render Chat History
chat_container = st.container()
with chat_container:
    for message in st.session_state.chat_session.get_history():
        role = "user" if message.role == "user" else "assistant"
        if message.parts and len(message.parts) > 0:
            text_content = "".join([part.text for part in message.parts if part.text])
            if text_content.strip():
                with st.chat_message(role):
                    st.markdown(text_content)

# Message input pipeline
user_input = st.chat_input("Ask Chef Pierre about your recipe or technique...")
if injected_prompt:
    user_input = injected_prompt

if user_input:
    with chat_container:
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                response_stream = st.session_state.chat_session.send_message_stream(user_input)
                
                for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                        
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                st.error(f"Academy server engine error: {e}")
