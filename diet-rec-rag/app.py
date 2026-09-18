"""Main Streamlit interface coordinating the RAG LLM pipeline.

Uses modular sub-scripts to isolate visualizations and view layers.
"""

import json
import os
import sqlite3
from dotenv import load_dotenv
from google import genai
from google.genai import types
import streamlit as st

import charts
import utils
from utils import DietPlanResponse
import views

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

utils.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates and caches official GenAI client mapping."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(
    page_title="GenAI RAG Diet Companion", page_icon="🥗", layout="wide"
)

if "diet_messages" not in st.session_state:
    st.session_state.diet_messages = utils.load_persisted_chat()
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = utils.load_persisted_grocery()
if "previous_interaction_id" not in st.session_state:
    st.session_state.previous_interaction_id = None

with st.sidebar:
    st.title("⚙️ RAG Control Panel")
    selected_diet = st.selectbox(
        "Dietary Preference:",
        ["No Restrictions", "Keto", "Vegan", "Vegetarian", "High-Protein", "Low-Carb"]
    )
    excluded_ingredients = st.multiselect(
        "Exclude Allergens:", ["Nuts", "Gluten", "Dairy", "Soy", "Eggs"]
    )
    target_calories = st.slider("Target Calories:", 1200, 4000, 2000, 100)

    st.markdown("---")
    st.subheader("🛒 Shopping List")
    if st.session_state.shopping_list:
        for item in st.session_state.shopping_list:
            st.write(f"⬜ {item if isinstance(item, tuple) else item}")
        txt_content = "\n".join(
            [f"- [ ] {i if isinstance(i, tuple) else i}" for i in st.session_state.shopping_list]
        )
        st.download_button(
            "📥 Download List", data=txt_content, file_name="grocery_list.txt", mime="text/plain", width='stretch'
        )
        if st.button("🗑️ Clear List", width='stretch'):
            utils.delete_all_grocery()
            st.session_state.shopping_list = []
            st.rerun()
    else:
        st.info("List empty.")

    st.markdown("---")
    if st.button("🔄 Reset Session", type="primary", width='stretch'):
        utils.clear_entire_session()
        st.session_state.diet_messages = []
        st.session_state.shopping_list = []
        st.session_state.previous_interaction_id = None
        st.rerun()

st.title("🥗 Your GenAI RAG Diet & Nutrition Companion")

# Render Database Dashboards and Logs
charts.render_analytics_dashboard(utils.fetch_analytics_logs())

# Render Conversations
for index, message in enumerate(st.session_state.diet_messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            views.render_diet_cards(message["content"], t_idx=index)

if user_input := st.chat_input("Request a custom meal plan..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    utils.save_chat_message("user", user_input)
    st.session_state.diet_messages.append({"role": "user", "content": user_input})

    try:
        emb_resp = client.models.embed_content(
            model="gemini-embedding-001", contents=f"{user_input} {selected_diet}"
        )
        q_emb = emb_resp.embeddings[0].values if emb_resp.embeddings else None
        rag_context = json.dumps(utils.query_vector_store_rag(q_emb)) if q_emb else "[]"
    except Exception:
        rag_context = "[]"

    sys_ins = (
        "You are an expert nutrition companion. Return structured responses balancing flavor and macros. "
        f"Diet focus: {selected_diet}. Exclude items: {', '.join(excluded_ingredients)}. Target: {target_calories} calories. "
        f"Verified database reference recipes: {rag_context}. If you adapt a recipe from this list, set its "
        "'matched_from_db' property to true. You must return the payload matching the schema format cleanly."
    )

    with st.chat_message("assistant"):
        with st.spinner("Querying Gemini 3.6 Interactions Engine..."):
            try:
                interaction = client.interactions.create(
                    model="gemini-3.6-flash",
                    input=user_input,
                    previous_interaction_id=st.session_state.previous_interaction_id,
                    system_instruction=sys_ins,
                    generation_config={
                        "response_mime_type": "application/json",
                        "response_schema": DietPlanResponse.model_json_schema(),
                    },
                    
                )
                st.session_state.previous_interaction_id = interaction.id
                response_text = interaction.output_text

                if response_text:
                    js = json.loads(response_text)
                    utils.log_daily_macros(js)
                    utils.save_chat_message("assistant", js)
                    views.render_diet_cards(js, t_idx=len(st.session_state.diet_messages))
                    st.session_state.diet_messages.append({"role": "assistant", "content": js})
                    st.rerun()
            except Exception as err:
                st.error(f"Interactions Pipeline Error: {str(err)}")
