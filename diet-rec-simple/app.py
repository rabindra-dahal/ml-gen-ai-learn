"""Main Streamlit execution interface driving high-speed streaming pipelines.

Powered natively by Gemini 3.6 direct inference architectures.
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

utils.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates optimized official GenAI client routing connections."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(
    page_title="Instant GenAI Diet Companion", page_icon="🥗", layout="wide"
)

if "diet_messages" not in st.session_state:
    st.session_state.diet_messages = utils.load_persisted_chat()

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
    if st.button("🔄 Reset Session", type="primary", width='stretch'):
        utils.clear_entire_session()
        st.session_state.diet_messages = []
        st.rerun()

st.title("🥗 Your GenAI Diet & Nutrition Companion")
st.caption("Powered by **Gemini 3.6** High-Speed Text Streaming Architecture")

# Render Analytics dashboards instantly out of quick metrics histories
charts.render_analytics_dashboard(utils.fetch_analytics_logs())

# Render Dialogue History turns smoothly using Markdown layouts
for message in st.session_state.diet_messages:
    with st.chat_message(message["role"]):
        views.render_markdown_response(message["content"])

if user_input := st.chat_input("Request a custom meal plan instantly..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    utils.save_chat_message("user", user_input)
    st.session_state.diet_messages.append({"role": "user", "content": user_input})

    # Compile a quick memory context window string tracking the last few entries
    past_history_context = ""
    if len(st.session_state.diet_messages) > 1:
        recent_turns = st.session_state.diet_messages[-3:-1]
        past_history_context = "Recent context:\n" + "\n".join(
            [f"{m['role']}: {m['content']}" for m in recent_turns]
        )

    sys_ins = (
        "You are an expert clinical dietitian. Provide a concise, highly practical daily meal plan.\n"
        f"Diet focus: {selected_diet}. Exclude allergens: {', '.join(excluded_ingredients)}. Target: {target_calories} calories.\n"
        f"{past_history_context}\n"
        "Format the output using clear markdown headers (e.g. ### 🍳 Breakfast), bold metrics for macro totals, "
        "and bulleted shopping sections summarizing required groceries. Respond immediately."
    )

    with st.chat_message("assistant"):
        stream_placeholder = st.empty()
        full_response_text = ""

        try:
            # ─── HIGH-SPEED RAW STREAMING INFERENCE CHANNEL ───
            response_stream = client.models.generate_content_stream(
                model="gemini-3.6-flash",
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=sys_ins,
                    temperature=0.4,
                ),
            )

            # Fire chunks to layout block live as tokens process
            for chunk in response_stream:
                if chunk.text:
                    full_response_text += chunk.text
                    stream_placeholder.markdown(full_response_text + "▌")

            stream_placeholder.markdown(full_response_text)

            # Process asynchronous data sync routines securely without blocking display
            utils.save_chat_message("assistant", full_response_text)
            utils.log_daily_calories(target_calories)
            st.session_state.diet_messages.append(
                {"role": "assistant", "content": full_response_text}
            )
            st.rerun()

        except Exception as err:
            st.error(f"Streaming Engine Error: {str(err)}")
