"""Main layout runner keeping visual footprint tiny and well-distributed."""

import os
from dotenv import load_dotenv
from google import genai
import streamlit as st

import charts
from backend import db_core, tracker_engine
from ui import seeder, uploader, tracker, chat_loop, inventory, db_inspector 

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

# Initialize database schema tables cleanly on app start
db_core.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates official GenAI API network hooks."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(page_title="GenAI Book Finder", page_icon="📚", layout="wide")

# Boot initial batch seeding routine map
seeder.seed_knowledge_base_orchestrator(client)

if "book_messages" not in st.session_state:
    from backend import chat_history
    st.session_state.book_messages = chat_history.load_persisted_chat()
if "reading_list" not in st.session_state:
    st.session_state.reading_list = tracker_engine.load_persisted_reading_list()

# --- SIDEBAR: SYSTEM CONFIGURATIONS ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.metric(label="🔑 Gemini API Calls", value=f"{tracker_engine.get_total_api_calls()} calls")
    st.markdown("---")
    selected_genre = st.selectbox("Primary Genre Focus:", ["All Genres", "Sci-Fi & Fantasy", "Biographies & Memoirs", "Business & Finance", "Mystery & Thrillers", "Self-Help & Philosophy", "Historical Fiction"])
    excluded_tropes = st.multiselect("Pace / Element Exclusions:", ["Slow Burn", "Heavy Gore", "Open Endings", "Tragic Endings", "High Fantasy"])
    target_reading_pace = st.slider("Yearly Reading Goal (Books):", 5, 100, 12, 1)
    st.markdown("---")
    
    if st.button("🚨 Reset Chat Session", type="primary", width="stretch"):
        tracker_engine.clear_entire_session()
        st.session_state.book_messages = []
        st.session_state.reading_list = []
        if "book_chat" in st.session_state:
            del st.session_state.book_chat
        st.rerun()

# --- CANVAS DISPLAY WORKSPACES ---
tab_chat, tab_logs = st.tabs(["💬 Dynamic Chat Assistant", "📊 My Reading Logs & Tracker"])

with tab_logs:
    uploader.process_custom_rag_uploads(client)
    # ─── UPDATED: PASS ACTIVE SIDEBAR PARAMETERS TO CHARTS & TRACKERS ───
    metrics = tracker_engine.fetch_kpi_summary_metrics()
    charts.render_analytics_dashboard(
            analytics_logs=tracker_engine.fetch_analytics_logs(),
            target_goal=target_reading_pace,
            completed_count=metrics['completed_reviews']
        )
    tracker.render_compact_tracker(target_goal=target_reading_pace)
    uploader.render_uploader_widget()
    # ─── INJECT THE RUNNER BLOCK DIRECTLY HERE ───
    inventory.render_document_inventory_table()
    # ─── INJECT THE TABLE INSPECTOR VIEW HERE ───
    db_inspector.render_database_tables_inspector()

with tab_chat:
    chat_loop.render_chat_interaction_loop(
        client=client,
        selected_genre=selected_genre,
        excluded_tropes=excluded_tropes,
        target_reading_pace=target_reading_pace
    )
