"""UI Rendering and component orchestration layer to prevent visual layout overflow errors."""

import streamlit as st
import utils


@st.dialog("📝 Log Book Review Notes")
def show_review_modal(book_data: dict, index: int) -> None:
    """Renders an overlay dialog window for writing book logs without breaking layouts."""
    st.write(f"#### Edit Entry for: {book_data['title']}")
    
    with st.form(key=f"modal_form_{index}", border=False):
        current_stars = st.feedback(
            "stars", key=f"modal_stars_{index}", default=book_data["rating"]
        )
        current_text = st.text_area(
            "My Thoughts & Key Takeaways:",
            value=book_data["review"],
            key=f"modal_notes_{index}"
        )
        
        if st.form_submit_button("💾 Save Review Metrics", use_container_width=True):
            utils.update_book_review(book_data["title"], current_stars, current_text)
            st.session_state.reading_list = utils.load_persisted_reading_list()
            st.toast("Review modifications applied successfully!")
            st.rerun()


def render_compact_tracker() -> None:
    """Renders saved book logs inside table grids to maximize space allocation."""
    st.write("### 📖 My Saved Reading List & Reviews")
    
    if not st.session_state.reading_list:
        st.info("Your list is empty. Click a quick-save button under suggestions to log entries here!")
        return

    # Render actionable controls cleanly across a horizontal grid
    c_list, c_acts = st.columns([3, 1])
    
    with c_list:
        for idx, book in enumerate(st.session_state.reading_list):
            stars_preview = "⭐" * book["rating"] if book["rating"] > 0 else "Unrated"
            
            # Combine expanding rows with a direct button to keep the panel tiny
            col_lbl, col_btn = st.columns([4, 1])
            col_lbl.write(f"**{book['title']}** — {stars_preview}")
            
            if col_btn.button("✏️ Edit Review", key=st.feedback(key=f"edt_{idx}")):
                show_review_modal(book, idx)
                
    with c_acts:
        txt_export = "MY READING TRACKER LOGS:\n\n"
        for b in st.session_state.reading_list:
            txt_export += f"- {b['title']}\n  Rating: {'★' * b['rating']}\n  Notes: {b['review']}\n\n"

        st.download_button(
            "📥 Export Logs Text",
            data=txt_export,
            file_name="reading_history_log.txt",
            mime="text/plain",
            use_container_width=True,
        )

        if st.button("🗑️ Wipe All Logs", use_container_width=True, type="secondary"):
            utils.delete_all_tracked_books()
            st.session_state.reading_list = []
            st.rerun()
