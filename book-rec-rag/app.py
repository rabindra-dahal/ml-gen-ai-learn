"""Main layout runner keeping visual footprint tiny and well-distributed."""

import json
import os
import sqlite3
from dotenv import load_dotenv
from google import genai
from google.genai import types
import streamlit as st

import charts
import components
import utils
import views

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

utils.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates official GenAI API network hooks."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(page_title="GenAI Book Finder", page_icon="📚", layout="wide")

def seed_knowledge_base() -> None:
    """Seeds the RAG vector store using a single optimized Batch API call with strict counter logic."""
    conn = sqlite3.connect(utils.DB_FILE)
    count = conn.cursor().execute("SELECT COUNT(*) FROM book_knowledge_base").fetchone()[0]
    conn.close()

    # CRITICAL TRACKING GUARD: Only run if the database knowledge base is totally empty
    if count == 0:
        with st.spinner("Embedding Reference Library in 1 batch call..."):
            catalog = [
                {"title": "Project Hail Mary", "author": "Andy Weir", "genre": "Sci-Fi & Fantasy", "summary": "Astronaut solves complex physics puzzles to save earth."},
                {"title": "Atomic Habits", "author": "James Clear", "genre": "Self-Help & Philosophy", "summary": "Build systems with small atomic iterations."},
                {"title": "The Silent Patient", "author": "Alex Michaelides", "genre": "Mystery & Thrillers", "summary": "Psychological thriller surrounding unexpected domestic violence."}
            ]
            
            texts_to_embed = [f"{b['title']} {b['author']}" for b in catalog]
            
            # Fire the 1 actual API call
            emb_resp = client.models.embed_content(
                model="gemini-embedding-001", 
                contents=texts_to_embed
            )
            
            # Increment your table exactly ONCE for this transaction loop
            utils.increment_api_counter("Batch Embedding (Seeding)")
            
            if emb_resp.embeddings:
                for idx, b in enumerate(catalog):
                    vector_values = emb_resp.embeddings[idx].values
                    utils.save_book_to_knowledge_base(
                        b["title"], b["author"], b["genre"], b["summary"], vector_values
                    )
        
        # Force a programmatic layout clean-slate rerun so your metric reads exactly "1 calls" 
        st.rerun()


seed_knowledge_base()

if "book_messages" not in st.session_state:
    st.session_state.book_messages = utils.load_persisted_chat()
if "reading_list" not in st.session_state:
    st.session_state.reading_list = utils.load_persisted_reading_list()

# --- SIDEBAR: SYSTEM TELEMETRY & CONFIGS ONLY ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.metric(label="🔑 Gemini API Calls", value=f"{utils.get_total_api_calls()} calls")
    st.markdown("---")
    selected_genre = st.selectbox("Primary Genre Focus:", ["All Genres", "Sci-Fi & Fantasy", "Biographies & Memoirs", "Business & Finance", "Mystery & Thrillers", "Self-Help & Philosophy", "Historical Fiction"])
    excluded_tropes = st.multiselect("Pace / Element Exclusions:", ["Slow Burn", "Heavy Gore", "Open Endings", "Tragic Endings", "High Fantasy"])
    target_reading_pace = st.slider("Yearly Reading Goal (Books):", 5, 100, 12, 1)
    st.markdown("---")
    
    if st.button("🚨 Reset Chat Session", type="primary", width="stretch"):
        utils.clear_entire_session()
        st.session_state.book_messages = []
        st.session_state.reading_list = []
        if "book_chat" in st.session_state:
            del st.session_state.book_chat
        st.rerun()

# --- CANVAS DISPLAY WORKSPACES ---
st.title("📚 Your GenAI Literary Companion")
tab_chat, tab_logs = st.tabs(["💬 Dynamic Chat Assistant", "📊 My Reading Logs & Tracker"])

with tab_logs:
    charts.render_analytics_dashboard(utils.fetch_analytics_logs())
    components.render_compact_tracker()

with tab_chat:
    if "book_chat" not in st.session_state:
        history_instances = []
        for msg in st.session_state.book_messages:
            history_instances.append(types.Content(role="model" if msg["role"] == "assistant" else msg["role"], parts=[types.Part.from_text(text=msg["content"])]))
        st.session_state.book_chat = client.chats.create(model="gemini-3.6-flash", history=history_instances)

    for index, message in enumerate(st.session_state.book_messages):
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(message["content"])
            else:
                views.render_markdown_response(message["content"], t_idx=index)

    if user_input := st.chat_input("Tell me what you last read or your mood..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        utils.save_chat_message("user", user_input)
        st.session_state.book_messages.append({"role": "user", "content": user_input})

        try:
            # Single embedding lookup call for the incoming user string text
            emb_resp = client.models.embed_content(model="gemini-embedding-001", contents=user_input)
            utils.increment_api_counter("Embedding (User Query)")
            
            # Map index array values out of the singular item output safely
            q_emb = emb_resp.embeddings[0].values if emb_resp.embeddings else None
            rag_context = json.dumps(utils.query_vector_store_rag(q_emb, limit=1)) if q_emb else "[]"
        except Exception:
            rag_context = "[]"

        sys_ins = (
            f"You are an expert literary librarian. Genre Focus: {selected_genre}. Exclude: {', '.join(excluded_tropes)}. Goal: {target_reading_pace} books.\n"
            f"Database reference match context: {rag_context}.\n"
            "Format selections beautifully using markdown. You must start each book recommendation line with a 3rd-level header exactly matching: '### 📖 [Book Title] by [Author]' so the system can parse it. Respond immediately."
        )

        with st.chat_message("assistant"):
            with st.spinner("Curating your reading list..."):
                try:
                    response = st.session_state.book_chat.send_message(message=user_input, config=types.GenerateContentConfig(system_instruction=sys_ins, temperature=0.4))
                    utils.increment_api_counter("Chat Inference")
                    
                    if not response.text:
                        st.error("⚠️ Connection delay occurred. Please try again.")
                        st.stop()

                    views.render_markdown_response(response.text, t_idx=len(st.session_state.book_messages))
                    utils.save_chat_message("assistant", response.text)
                    utils.log_reading_goal(target_reading_pace)
                    st.session_state.book_messages.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as err:
                    st.error(f"Chat Session Error: {str(err)}")
