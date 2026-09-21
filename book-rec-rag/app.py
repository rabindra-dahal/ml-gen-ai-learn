"""Main entry platform controller orchestrating the book discovery RAG engine.

Powered by Gemini 3.6 direct chat session memory parameters with interactive reviews.
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
import views

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

utils.init_db()


@st.cache_resource
def get_gemini_client() -> genai.Client:
    """Instantiates and caches official GenAI API network hooks."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(
    page_title="Instant GenAI Book Finder", page_icon="📚", layout="wide"
)


def seed_knowledge_base() -> None:
    """Seeds the RAG vector store with sample reference books if empty."""
    conn = sqlite3.connect(utils.DB_FILE)
    count = conn.cursor().execute(
        "SELECT COUNT(*) FROM book_knowledge_base"
    ).fetchone()[0]
    conn.close()

    if count == 0:
        with st.spinner("Embedding Book Reference Library into RAG store..."):
            books_catalog = [
                {
                    "title": "Project Hail Mary",
                    "author": "Andy Weir",
                    "genre": "Sci-Fi & Fantasy",
                    "summary": "A lone astronaut must save Earth from an extinction-level event by solving complex scientific puzzles.",
                },
                {
                    "title": "Atomic Habits",
                    "author": "James Clear",
                    "genre": "Self-Help & Philosophy",
                    "summary": "A practical guide to breaking bad behaviors and building good habits using tiny, daily atomic increments.",
                },
                {
                    "title": "The Silent Patient",
                    "author": "Alex Michaelides",
                    "genre": "Mystery & Thrillers",
                    "summary": "A psychological thriller about a woman's unexpected act of violence against her husband and the therapist obsessed with uncovering her motive.",
                },
            ]
            for b in books_catalog:
                text_to_embed = f"{b['title']} {b['author']} {b['genre']} {b['summary']}"
                emb_resp = client.models.embed_content(
                    model="gemini-embedding-001", contents=text_to_embed
                )
                if emb_resp.embeddings:
                    utils.save_book_to_knowledge_base(
                        b["title"],
                        b["author"],
                        b["genre"],
                        b["summary"],
                        emb_resp.embeddings.values,
                    )


seed_knowledge_base()

if "book_messages" not in st.session_state:
    st.session_state.book_messages = utils.load_persisted_chat()
if "reading_list" not in st.session_state:
    st.session_state.reading_list = utils.load_persisted_reading_list()

# --- SIDEBAR CONTROL PANEL ---

with st.sidebar:
    st.title("⚙️ Discovery Control Panel")
    selected_genre = st.selectbox(
        "Primary Genre Focus:",
        [
            "All Genres",
            "Sci-Fi & Fantasy",
            "Biographies & Memoirs",
            "Business & Finance",
            "Mystery & Thrillers",
            "Self-Help & Philosophy",
            "Historical Fiction",
        ],
    )
    excluded_tropes = st.multiselect(
        "Pace / Element Exclusions:",
        [
            "Slow Burn",
            "Heavy Gore",
            "Open Endings",
            "Tragic Endings",
            "High Fantasy",
        ],
    )
    target_reading_pace = st.slider(
        "Yearly Reading Goal (Books):", 5, 100, 12, 1
    )

    st.markdown("---")
    st.subheader("📚 Tracked Books & Logs")
    if st.session_state.reading_list:
        for idx, book in enumerate(st.session_state.reading_list):
            title = book["title"]
            stars_preview = "⭐" * book["rating"] if book["rating"] > 0 else "Unrated"

            with st.expander(f"📖 {title} ({stars_preview})", expanded=False):
                new_rating = st.feedback(
                    "stars", key=f"stars_{idx}", default=book["rating"]
                )
                new_review = st.text_area(
                    "My Review Notes:",
                    value=book["review"],
                    key=f"rev_text_{idx}",
                    placeholder="Type your notes here...",
                )

                if (new_rating != book["rating"]) or (new_review != book["review"]):
                    utils.update_book_review(title, new_rating, new_review)
                    st.session_state.reading_list = (
                        utils.load_persisted_reading_list()
                    )
                    st.rerun()

        txt_export = "MY COMPILING READING LOG:\n\n"
        for b in st.session_state.reading_list:
            txt_export += f"- {b['title']}\n  Rating: {'★' * b['rating']}\n  Notes: {b['review']}\n\n"

        st.download_button(
            "📥 Download Tracker Log",
            data=txt_export,
            file_name="reading_history_log.txt",
            mime="text/plain",
            width='stretch',
        )

        if st.button("🗑️ Clear Reading List", width='stretch'):
            utils.delete_all_tracked_books()
            st.session_state.reading_list = []
            st.rerun()
    else:
        st.info("Your list is empty. Click a button under suggestions to add items!")

    st.markdown("---")
    if st.button(
        "🔄 Reset Book Finder Session", type="secondary", width='stretch'
    ):
        utils.clear_entire_session()
        st.session_state.book_messages = []
        st.session_state.reading_list = []
        if "book_chat" in st.session_state:
            del st.session_state.book_chat
        st.rerun()

st.title("📚 Your GenAI Literary Companion (with RAG)")
st.caption("Powered by **Gemini 3.6** Direct Chat Session Architecture")

charts.render_analytics_dashboard(utils.fetch_analytics_logs())

if "book_chat" not in st.session_state:
    history_instances = []
    for msg in st.session_state.book_messages:
        api_role = "model" if msg["role"] == "assistant" else msg["role"]
        history_instances.append(
            types.Content(
                role=api_role,
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )
    st.session_state.book_chat = client.chats.create(
        model="gemini-3.6-flash", history=history_instances
    )

for index, message in enumerate(st.session_state.book_messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            views.render_markdown_response(message["content"], t_idx=index)

# --- CONVERSATION LOOP WITH VECTOR RETRIEVAL ---

if user_input := st.chat_input(
    "Tell me what you last read, your mood, or a topic you want to explore..."
):
    with st.chat_message("user"):
        st.markdown(user_input)
    utils.save_chat_message("user", user_input)
    st.session_state.book_messages.append({"role": "user", "content": user_input})

    # 1. RAG Vector Document Fetch Pass (Limited to 1 document to ensure low latency)
    try:
        emb_resp = client.models.embed_content(
            model="gemini-embedding-001", contents=user_input
        )
        q_emb = emb_resp.embeddings.values if emb_resp.embeddings else None
        rag_context = (
            json.dumps(utils.query_vector_store_rag(q_emb, limit=1))
            if q_emb
            else "[]"
        )
    except Exception:
        rag_context = "[]"

    # 2. Inject RAG payload cleanly into System Instructions
    sys_ins = (
        "You are an expert literary curator and librarian. Provide an engaging, "
        "highly personalized reading recommendation summary.\n"
        f"Genre Preference: {selected_genre}. Strict element exclusions: "
        f"{', '.join(excluded_tropes)}. Yearly Goal context: {target_reading_pace} books.\n"
        f"Verified database reference books: {rag_context}.\n"
        "Format your selections beautifully using markdown. You must start each book recommendation "
        "line with a 3rd-level header exactly matching this format: '### 📖 [Book Title] by [Author]' "
        "so the application can process it. Follow that header with bold keywords for core themes, "
        "bulleted lists for matching reasons, and a quick 1-sentence 'Who this is for' summary box. "
        "Prioritize recommending the verified database book if it aligns with the user's request. Respond immediately."
    )

    with st.chat_message("assistant"):
        with st.spinner("Curating your reading list..."):
            try:
                response = st.session_state.book_chat.send_message(
                    message=user_input,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_ins,
                        temperature=0.4,
                    ),
                )
                response_text = response.text

                if not response_text or response_text.strip() == "":
                    st.error("⚠️ The pipeline encountered a connection delay. Please re-type your request.")
                    st.stop()

                current_turn = len(st.session_state.book_messages)
                views.render_markdown_response(response_text, t_idx=current_turn)

                utils.save_chat_message("assistant", response_text)
                utils.log_reading_goal(target_reading_pace)
                st.session_state.book_messages.append(
                    {"role": "assistant", "content": response_text}
                )
                st.rerun()
            except Exception as err:
                st.error(f"Chat Session Error: {str(err)}")
