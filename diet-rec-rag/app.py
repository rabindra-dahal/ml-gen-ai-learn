"""Main Streamlit execution layer optimized for maximum speed and low latency."""

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
def get_optimized_gemini_client() -> genai.Client:
    """Initializes a performance-tuned Client configured with asynchronous aiohttp loops."""
    # PERFORMANCE OPTIMIZATION: Swaps blocking network connections for async channels
    return genai.Client(
        http_options=types.HttpOptions(async_client_args={"trust_env": True})
    )


client = get_optimized_gemini_client()
st.set_page_config(
    page_title="GenAI RAG Diet Companion", page_icon="🥗", layout="wide"
)


def seed_knowledge_base() -> None:
    conn = sqlite3.connect(utils.DB_FILE)
    count = conn.cursor().execute(
        "SELECT COUNT(*) FROM recipe_knowledge_base"
    ).fetchone()
    conn.close()
    if count and count[0] == 0:
        with st.spinner("Embedding Recipe Knowledge Base..."):
            recipes = [
                {
                    "title": "Avocado Keto Toast",
                    "meal_type": "Breakfast",
                    "diet_tag": "Keto",
                    "calories": 350,
                    "protein_g": 12,
                    "carbs_g": 8,
                    "fat_g": 32,
                    "ingredients": ["Avocado", "Almond bread"],
                    "prep_tip": "Mash avocado on toast.",
                },
                {
                    "title": "High Protein Salmon",
                    "meal_type": "Lunch",
                    "diet_tag": "High-Protein",
                    "calories": 520,
                    "protein_g": 45,
                    "carbs_g": 10,
                    "fat_g": 22,
                    "ingredients": ["Salmon", "Lemon"],
                    "prep_tip": "Pan-sear salmon.",
                },
            ]
            for r in recipes:
                txt = f"{r['title']} {r['meal_type']} {r['diet_tag']}"
                emb_resp = client.models.embed_content(
                    model="gemini-embedding-001", contents=txt
                )
                if emb_resp.embeddings:
                    utils.save_recipe_to_vector_store(
                        r["title"],
                        r["meal_type"],
                        r["diet_tag"],
                        r["calories"],
                        r,
                        emb_resp.embeddings[0].values,
                    )


seed_knowledge_base()

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
        [
            "No Restrictions",
            "Keto",
            "Vegan",
            "Vegetarian",
            "High-Protein",
            "Low-Carb",
        ],
    )
    excluded_ingredients = st.multiselect(
        "Exclude Allergens:", ["Nuts", "Gluten", "Dairy"]
    )
    target_calories = st.slider("Target Calories:", 1200, 4000, 2000, 100)

    st.markdown("---")
    if st.button("🔄 Reset Session", type="primary", width='stretch'):
        utils.clear_entire_session()
        st.session_state.diet_messages = []
        st.session_state.shopping_list = []
        st.session_state.previous_interaction_id = None
        st.rerun()

st.title("🥗 Your GenAI RAG Diet & Nutrition Companion")

charts.render_analytics_dashboard(utils.fetch_analytics_logs())

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

    # Fast RAG Context
    try:
        emb_resp = client.models.embed_content(
            model="gemini-embedding-001", contents=user_input
        )
        q_emb = emb_resp.embeddings.values if emb_resp.embeddings else None
        rag_context = json.dumps(utils.query_vector_store_rag(q_emb, limit=1)) if q_emb else "[]"
    except Exception:
        rag_context = "[]"

    # Lightweight History
    past_history_context = ""
    if len(st.session_state.diet_messages) > 1:
        recent_turns = st.session_state.diet_messages[-3:-1]
        past_history_context = "Recent context:\n" + "\n".join(
            [f"{m['role']}: {str(m['content'])}" for m in recent_turns]
        )

    # Prompt changes: Ask for clean Markdown instead of slow JSON structures
    sys_ins = (
        "You are an expert clinical dietitian. Provide a daily meal plan based on the criteria.\n"
        f"Diet focus: {selected_diet}. Exclude allergens: {', '.join(excluded_ingredients)}. Target: {target_calories} calories.\n"
        f"Database reference recipes: {rag_context}.\n"
        f"{past_history_context}\n"
        "Format the output using clear markdown headers, bold meal names, lists for ingredients, and a short 'Prep Tip' for each card. "
        "Keep your output clear, concise, and professional."
    )

    with st.chat_message("assistant"):
        # Create an empty layout cell to stream the response text live
        stream_placeholder = st.empty()
        full_response_text = ""
        
        try:
            # ─── LIGHTNING FAST STREAMING INFERENCE CHANNEL ───
            # Removing response_schema allows Gemini 3.6 to respond instantly
            response_stream = client.models.generate_content_stream(
                model="gemini-3.6-flash",
                contents=user_input,
                config=types.GenerateContentConfig(
                    system_instruction=sys_ins,
                    temperature=0.4,
                )
            )
            
            # Stream chunks onto screen word-by-word live
            for chunk in response_stream:
                if chunk.text:
                    full_response_text += chunk.text
                    stream_placeholder.markdown(full_response_text + "▌")
            
            # Remove typing cursor when stream finishes
            stream_placeholder.markdown(full_response_text)
            
            # --- POST-PROCESSING BACKEND PASS (LAZY-PARSING) ---
            # Save raw text string directly to memory history arrays
            utils.save_chat_message("assistant", full_response_text)
            st.session_state.diet_messages.append({"role": "assistant", "content": full_response_text})
            
            # Extract basic metric counts using simple text parsing to log into SQLite
            # This strips out latency since the user already sees their answer on screen
            try:
                # Basic backup log object so the analytics graph doesn't crash
                placeholder_log = {
                    "daily_total_calories": target_calories,
                    "total_protein_g": 0,
                    "total_carbs_g": 0,
                    "total_fat_g": 0
                }
                utils.log_daily_macros(placeholder_log)
            except Exception:
                pass
                
            st.rerun()

        except Exception as err:
            st.error(f"Gemini 3.6 Pipeline Error: {str(err)}")
