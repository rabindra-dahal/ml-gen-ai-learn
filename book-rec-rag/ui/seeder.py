"""Module orchestrating first-boot asset initialization pools."""

import streamlit as st
from backend import db_core, tracker_engine, vector_store


def seed_knowledge_base_orchestrator(client) -> None:
    """Seeds the RAG vector store using a single optimized Batch API call."""
    conn = db_core.get_db_connection()
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
            tracker_engine.increment_api_counter("Batch Embedding (Seeding)")
            
            if emb_resp.embeddings:
                for idx, b in enumerate(catalog):
                    vector_store.save_book_to_knowledge_base(
                        b["title"], b["author"], b["genre"], b["summary"], emb_resp.embeddings[idx].values
                    )
        st.rerun()
