"""Main Streamlit execution interface driving high-speed chat pipelines.

Powered natively by Gemini 3.6 direct chat session inference architectures.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import streamlit as st

import charts
import utils
import views

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

# Initialize localized SQL tracking databases
utils.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates optimized official GenAI client routing connections."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(
    page_title="Instant GenAI Diet Companion", page_icon="🥗", layout="wide"
)

# Hydrate user history data array out of local cache
if "diet_messages" not in st.session_state:
    st.session_state.diet_messages = utils.load_persisted_chat()

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_diet = st.selectbox(
        "Dietary Preference:",
        [
            "No Restrictions",
            "Keto",
            "Vegan",
            "Vegetarian",
            "High-Protein",
            "Low-Carb",
            "Mediterranean",
        ],
    )
    excluded_ingredients = st.multiselect(
        "Exclude Allergens:", ["Nuts", "Gluten", "Dairy", "Soy", "Eggs"]
    )
    target_calories = st.slider("Target Calories:", 1200, 4000, 2000, 100)

    st.markdown("---")
    if st.button("🔄 Reset Session", type="destructive", use_container_width=True):
        utils.clear_entire_session()
        st.session_state.diet_messages = []
        if "diet_chat" in st.session_state:
            del st.session_state.diet_chat
        st.rerun()

st.title("🥗 Your GenAI Diet & Nutrition Companion")
st.caption("Powered by **Gemini 3.6** Direct Chat Session Architecture")

# Render Analytics dashboards instantly out of quick metrics histories
charts.render_analytics_dashboard(utils.fetch_analytics_logs())

# --- INSTANTIATE PERSISTENT CHAT SESSION ---
if "diet_chat" not in st.session_state:
    # Build history context turns array from database records if they exist
    history_instances = []
    for msg in st.session_state.diet_messages:
        history_instances.append(
            types.Content(
                role=msg["role"], 
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    
    # Initialize the ongoing conversation state machine cleanly
    st.session_state.diet_chat = client.chats.create(
        model="gemini-3.6-flash", 
        history=history_instances
    )

# Render Dialogue History turns smoothly using Markdown layouts
for message in st.session_state.diet_messages:
    with st.chat_message(message["role"]):
        views.render_markdown_response(message["content"])

# --- HANDLE CONVERSATIONAL CHAT INPUT LOOP ---
if user_input := st.chat_input("Ask for a meal plan, change an ingredient, or talk to your dietitian..."):
    # 1. Render User Message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    utils.save_chat_message("user", user_input)
    st.session_state.diet_messages.append({"role": "user", "content": user_input})

    # 2. Dynamic Input System Generation Prompts
    sys_ins = (
        "You are an expert clinical dietitian. Provide a concise, highly practical daily meal plan.\n"
        f"Diet focus: {selected_diet}. Exclude allergens: {', '.join(excluded_ingredients)}. Target: {target_calories} calories.\n"
        "Format the output beautifully using clear markdown headers (e.g. ### 🍳 Breakfast), bold metrics for macro totals, "
        "and bulleted shopping sections summarizing required groceries. Respond immediately."
    )

    # 3. Process Chat Session Response
    with st.chat_message("assistant"):
        with st.spinner("Dietitian is typing..."):
            try:
                # ─── HIGH-SPEED MULTI-TURN CHAT CONTEXT CHANNEL ───
                # Uses send_message while dynamically passing system instructions and parameters
                response = st.session_state.diet_chat.send_message(
                    message=user_input,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_ins,
                        temperature=0.4,
                    )
                )

                response_text = response.text
                
                if not response_text or response_text.strip() == "":
                    st.error("⚠️ The generation pipeline returned a blank value. Please re-enter your query.")
                    st.stop()

                # Render the compiled layout text block
                views.render_markdown_response(response_text)

                # Process data sync routines securely without blocking display
                utils.save_chat_message("assistant", response_text)
                utils.log_daily_calories(target_calories)
                st.session_state.diet_messages.append(
                    {"role": "assistant", "content": response_text}
                )
                st.rerun()

            except Exception as err:
                st.error(f"Chat Session Error: {str(err)}")
