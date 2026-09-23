"""UI Rendering and component orchestration layer to prevent visual layout overflow errors."""

import json
import os
import sqlite3
from google.genai import types
import streamlit as st
import utils
import views


def seed_knowledge_base_orchestrator(client) -> None:
    """Seeds the RAG vector store using a single optimized Batch API call."""
    conn = sqlite3.connect(utils.DB_FILE)
    count = conn.cursor().execute("SELECT COUNT(*) FROM book_knowledge_base").fetchone()
    conn.close()

    if count == 0:
        with st.spinner("Embedding Reference Library in 1 batch call..."):
            catalog = [
                {"title": "Project Hail Mary", "author": "Andy Weir", "genre": "Sci-Fi & Fantasy", "summary": "Astronaut solves complex physics puzzles to save earth."},
                {"title": "Atomic Habits", "author": "James Clear", "genre": "Self-Help & Philosophy", "summary": "Build systems with small atomic iterations."},
                {"title": "The Silent Patient", "author": "Alex Michaelides", "genre": "Mystery & Thrillers", "summary": "Psychological thriller surrounding unexpected domestic violence."}
            ]
            
            texts_to_embed = [f"{b['title']} {b['author']}" for b in catalog]
            emb_resp = client.models.embed_content(
                model="gemini-embedding-001", 
                contents=texts_to_embed
            )
            utils.increment_api_counter("Batch Embedding (Seeding)")
            
            if emb_resp.embeddings:
                for idx, b in enumerate(catalog):
                    utils.save_book_to_knowledge_base(
                        b["title"], b["author"], b["genre"], b["summary"], emb_resp.embeddings[idx].values
                    )
        st.rerun()


def process_custom_rag_uploads(client) -> None:
    """Processes any pending text file configurations dropped inside upload hooks."""
    if "pending_rag_uploads" in st.session_state and st.session_state.pending_rag_uploads:
        uploaded_files = st.session_state.pending_rag_uploads
        del st.session_state.pending_rag_uploads 
        
        with st.spinner("Parsing text files and executing vector index injection operations..."):
            for uploaded_file in uploaded_files:
                file_text = uploaded_file.read().decode("utf-8")
                emb_res = client.models.embed_content(model="gemini-embedding-001", contents=file_text)
                utils.increment_api_counter("Embedding (Custom Document Upload)")
                
                if emb_res.embeddings:
                    doc_title = os.path.splitext(uploaded_file.name)[0]
                    utils.save_book_to_knowledge_base(
                        title=doc_title,
                        author="Custom Contributor",
                        genre="Uploaded Context Collection",
                        summary=file_text[:200] + "...", 
                        embedding=emb_res.embeddings[0].values
                    )
            st.toast(f"Successfully indexed {len(uploaded_files)} files into RAG store!")
            st.rerun()


@st.dialog("📝 Log Book Review Notes")
def show_review_modal(book_data: dict, index: int) -> None:
    """Renders an overlay dialog window for writing book logs without breaking layouts."""
    st.write(f"#### Edit Entry for: {book_data['title']}")
    
    with st.form(key=f"modal_form_instance_id_{index}", border=False):
        current_stars = st.feedback("stars", key=f"modal_stars_instance_id_{index}", default=book_data["rating"])
        current_text = st.text_area("My Thoughts:", value=book_data["review"], key=f"modal_notes_instance_id_{index}")
        
        if st.form_submit_button("💾 Save Review Metrics", width="stretch"):
            utils.update_book_review(book_data["title"], current_stars, current_text)
            st.session_state.reading_list = utils.load_persisted_reading_list()
            st.toast("Review modifications applied successfully!")
            st.rerun()


def render_compact_tracker() -> None:
    """Renders saved book logs inside table grids to maximize space allocation."""
    st.write("### 📖 My Saved Reading List & Reviews")
    
    if not st.session_state.reading_list:
        st.info("Your list is empty. Click a quick-save button under suggestions to log entries here!")
    else:
        c_list, c_acts = st.columns(2)
        with c_list:
            for idx, book in enumerate(st.session_state.reading_list):
                stars_preview = "⭐" * book["rating"] if book["rating"] > 0 else "Unrated"
                col_lbl, col_btn = st.columns(2)
                with col_lbl:
                    st.write(f"**{book['title']}** — {stars_preview}")
                with col_btn:
                    if st.button("✏️ Edit", key=f"btn_edit_action_id_{idx}", width="stretch"):
                        show_review_modal(book, idx)
                    
        with c_acts:
            txt_export = "MY READING TRACKER LOGS:\n\n"
            for b in st.session_state.reading_list:
                txt_export += f"- {b['title']}\n  Rating: {'★' * b['rating']}\n  Notes: {b['review']}\n\n"

            st.download_button("📥 Export Logs Text", data=txt_export, file_name="reading_history_log.txt", mime="text/plain", width="stretch", key="download_log_tracker_btn_fixed")
            if st.button("🗑️ Wipe All Logs", width="stretch", key="clear_all_logs_btn_fixed"):
                utils.delete_all_tracked_books()
                st.session_state.reading_list = []
                st.rerun()

    st.markdown("---")
    st.write("### 📤 Custom RAG Knowledge Base Uploader")
    uploaded_files = st.file_uploader("Choose local document text fragments:", type=["txt", "md"], accept_multiple_files=True, key="rag_knowledge_file_uploader")
    if uploaded_files:
        if st.button("🚀 Parse & Index Uploaded Documents", type="primary", width="stretch"):
            st.session_state.pending_rag_uploads = uploaded_files
            st.rerun()


def render_chat_interaction_loop(client, selected_genre: str, excluded_tropes: list, target_reading_pace: int) -> None:
    """Orchestrates live conversation thread renders paired with vector augmented retrievals."""
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
            emb_resp = client.models.embed_content(model="gemini-embedding-001", contents=user_input)
            utils.increment_api_counter("Embedding (User Query)")
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
