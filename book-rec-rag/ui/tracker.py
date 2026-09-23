"""Module rendering table metrics grids alongside contextual dialog prompt boxes."""

import streamlit as st
from backend import tracker_engine


@st.dialog("📝 Log Book Review Notes")
def show_review_modal(book_data: dict, index: int) -> None:
    """Renders an overlay dialog window for writing book logs without breaking layouts."""
    st.write(f"#### Edit Entry for: {book_data['title']}")
    
    with st.form(key=f"modal_form_instance_id_{index}", border=False):
        # FIXED: Subtract 1 from the stored database rating (1-5) to map back to Streamlit's 0-4 scale
        default_star_index = max(0, book_data["rating"] - 1)
        
        current_stars = st.feedback(
            "stars", 
            key=f"modal_stars_instance_id_{index}", 
            default=default_star_index
        )
        current_text = st.text_area(
            "My Thoughts:", 
            value=book_data["review"], 
            key=f"modal_notes_instance_id_{index}"
        )
        
        if st.form_submit_button("💾 Save Review Metrics", width="stretch"):
            # FIXED: Add 1 to shift Streamlit's 0-4 return value into a human-readable 1-5 score
            actual_score = current_stars + 1 if current_stars is not None else 0
            
            tracker_engine.update_book_review(book_data["title"], actual_score, current_text)
            st.session_state.reading_list = tracker_engine.load_persisted_reading_list()
            st.toast(f"Saved review as {actual_score} stars! ⭐")
            st.rerun()


def render_compact_tracker() -> None:
    """Renders saved book logs inside table grids to maximize space allocation."""
    # ─── NEW: LIVE TELEMETRY KPI SUMMARY CARD BLOCK ───
    metrics = tracker_engine.fetch_kpi_summary_metrics()
    
    st.write("### 📊 My Reading Analytics Dashboard")
    col_kpi1, col_kpi2 = st.columns(2)
    
    with col_kpi1:
        st.metric(
            label="📚 Total Tracked Books", 
            value=f"{metrics['total_saved']} items",
            help="Total number of book recommendations saved directly into your logs database."
        )
    with col_kpi2:
        stars_label = f"⭐ {metrics['avg_rating']}" if metrics['avg_rating'] > 0 else "No ratings"
        st.metric(
            label="📈 Average Library Evaluation", 
            value=stars_label,
            help="The mean score calculated across all rated items inside your list."
        )
    
    st.markdown("---")

    """Renders saved book logs inside table grids to maximize space allocation."""
    st.write("### 📖 My Saved Reading List & Reviews")
    
    if not st.session_state.reading_list:
        st.info("Your list is empty. Click a quick-save button under suggestions to log entries here!")
        return

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
            tracker_engine.delete_all_tracked_books()
            st.session_state.reading_list = []
            st.rerun()
