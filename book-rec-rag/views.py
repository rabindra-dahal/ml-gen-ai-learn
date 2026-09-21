"""Module providing presentation layer wrappers for suggestions views."""

import streamlit as st
import utils


def render_markdown_response(content: str, t_idx: int) -> None:
    """Prints pure text book suggestions alongside dynamic action buttons."""
    st.markdown(content)

    lines = content.split("\n")
    book_titles = []
    for line in lines:
        if line.strip().startswith("### 📖"):
            raw_title = (
                line.replace("### 📖", "")
                .replace("**", "")
                .replace("`", "")
                .strip()
            )
            if raw_title:
                book_titles.append(raw_title)

    if book_titles:
        st.caption("✨ **Quick Actions:**")
        cols = st.columns(len(book_titles))
        for idx, title in enumerate(book_titles):
            with cols[idx]:
                btn_key = f"save_{t_idx}_{idx}"
                display_name = (
                    title.split("by")[0].strip() if "by" in title else title
                )
                # FIXED: use_container_width=True replaced with width="stretch"
                if st.button(f"📥 Save: {display_name}", key=btn_key, width="stretch"):
                    utils.save_book_to_list(title)
                    st.session_state.reading_list = (
                        utils.load_persisted_reading_list()
                    )
                    st.toast(f"Saved to your tracker: {display_name}!")
                    st.rerun()
