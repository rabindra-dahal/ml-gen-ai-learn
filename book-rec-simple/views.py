"""Module providing presentation layer wrappers for suggestions views."""

import streamlit as st
import utils


def render_markdown_response(content: str, t_idx: int) -> None:
    """Prints pure text suggestions alongside dynamic action buttons."""
    # Render the primary text recommendation onto the screen
    st.markdown(content)

    # Automatically parse the response block to locate curated headers
    # e.g., finding lines starting with '### 📖' to create clean action markers
    lines = content.split("\n")
    book_titles = []
    for line in lines:
        if line.strip().startswith("### 📖"):
            # Strip out markdown syntax characters to gather a raw text title
            raw_title = (
                line.replace("### 📖", "")
                .replace("**", "")
                .replace("`", "")
                .strip()
            )
            if raw_title:
                book_titles.append(raw_title)

    # Render actionable buttons if any book patterns were identified
    if book_titles:
        st.caption("✨ **Quick Actions:**")
        # Layout action buttons horizontally beneath the message log canvas
        cols = st.columns(len(book_titles))
        for idx, title in enumerate(book_titles):
            with cols[idx]:
                # Isolate button keys contextually based on turn indicators to prevent widget errors
                btn_key = f"save_{t_idx}_{idx}"
                # Render shorter string previews inside the button face for cleaner UI balance
                display_name = (
                    title.split("by")[0].strip() if "by" in title else title
                )
                if st.button(f"📥 Save: {display_name}", key=btn_key):
                    utils.save_book_to_list(title)
                    st.session_state.reading_list = (
                        utils.load_persisted_reading_list()
                    )
                    st.toast(f"Saved: {display_name}!")
                    st.rerun()
