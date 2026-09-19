"""Module handling historical message displays on screen canvas."""

import streamlit as st


def render_markdown_response(content: str) -> None:
    """Renders plain text markdown content strings natively to chat frames."""
    st.markdown(content)
