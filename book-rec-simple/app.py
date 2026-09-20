"""Main entry platform controller orchestrating the book discovery engine.

Powered by Gemini 3.6 direct chat session memory parameters with interactive reviews.
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
    """Instantiates and caches official GenAI API network hooks."""
    return genai.Client()


client = get_gemini_client()
st.set_page_config(
    page_title="Instant GenAI Book Finder", page_icon="📚", layout="wide"
)

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
    # 📚 UPDATED: SIDEBAR INTERACTIVE STAR-RATING & REVIEW ENGINE
    st.subheader("📚 Tracked Books & Logs")
    if st.session_state.reading_list:
        for idx, book in enumerate(st.session_state.reading_list):
            title = book["title"]
            stars_preview = "⭐" * book["rating"] if book["rating"] > 0 else "Unrated"
            
            # Use separate expanding sections per book row for cleaner visual hierarchy
            with st.expander(f"📖 {title} ({stars_preview})", expanded=False):
                # Interactive native rating metric selection component
                new_rating = st.feedback(
                    "stars", 
                    key=f"stars_{idx}", 
                    value=book["rating"]
                )
                
                # Accompanying reflection message textarea box
                new_review = st.text_area(
                    "My Review Notes:", 
                    value=book["review"], 
                    key=f"rev_text_{idx}",
                    placeholder="Type your notes here..."
                )
                
                # Check for row context property modifications to save records
                if (new_rating != book["rating"]) or (new_review != book["review"]):
                    utils.update_book_review(title, new_rating, new_review)
                    st.session_state.reading_list = utils.load_persisted_reading_list()
                    st.rerun()

        # Compile plain text lines for exporting reviews
        txt_export = "MY COMPILING READING LOG:\n\n"
        for b in st.session_state.reading_list:
            txt_export += f"- {b['title']}\n  Rating: {'★' * b['rating']}\n  Notes: {b['review']}\n\n"
            
        st.download_button(
            "📥 Download Tracker Log",
            data=txt_export,
            file_name="reading_history_log.txt",
            mime="text/plain",
            use_container_width=True,
        )

        if st.button("🗑️ Clear Reading List", use_container_width=True):
            utils.delete_all_tracked_books()
            st.session_state.reading_list = []
            st.rerun()
    else:
        st.info("Your list is empty. Click a button under suggestions to add items!")

    st.markdown("---")
    if st.button(
        "🔄 Reset Book Finder Session", type="destructive", use_container_width=True
    ):
        utils.clear_entire_session()
        st.session_state.book_messages = []
        st.session_state.reading_list = []
        if "book_chat" in st.session_state:
            del st.session_state.book_chat
        st.rerun()

st.title("📚 Your GenAI Literary Companion")
st.caption("Powered by **Gemini 3.6** Direct Chat Session Architecture")

charts.render_analytics_dashboard(utils.fetch_analytics_logs())

if "book_chat" not in st.session_state:
    history_instances = []
    for msg in st.session_state.book_messages:
        history_instances.append(
            types.Content(
                role=msg["role"],
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

if user_input := st.chat_input(
    "Tell me what you last read, your mood, or a topic you want to explore..."
):
    with st.chat_message("user"):
        st.markdown(user_input)
    utils.save_chat_message("user", user_input)
    st.session_state.book_messages.append({"role": "user", "content": user_input})

    sys_ins = (
        "You are an expert literary curator and librarian. Provide an engaging, "
        "highly personalized reading recommendation summary.\n"
        f"Genre Preference: {selected_genre}. Strict element exclusions: "
        f"{', '.join(excluded_tropes)}. Yearly Goal context: {target_reading_pace} books.\n"
        "Format your selections beautifully using markdown. You must start each book recommendation "
        "line with a 3rd-level header exactly matching this format: '### 📖 [Book Title] by [Author]' "
        "so the application can process it. Follow that header with bold keywords for core themes, "
        "bulleted lists for matching reasons, and a quick 1-sentence 'Who this is for' summary box. "
        "Respond immediately with your curated selection based on the conversation."
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
