"""UI Module presenting a visual inventory table for modifying indexed RAG vectors."""

import streamlit as st
from backend import vector_store


def render_document_inventory_table() -> None:
    """Displays custom database documents alongside active row deletion actions."""
    st.write("### 🗂️ RAG Document Inventory Inspector")
    st.caption("Inspect and manage custom knowledge records currently loaded inside your SQLite vector index database space.")

    documents = vector_store.fetch_rag_document_inventory()

    if not documents:
        st.info("No customized text files or seed references found inside your active knowledge index table.")
        return

    # Render a structural title boundary card framework grid header split
    for idx, doc in enumerate(documents):
        # Format names cleanly if tuple artifacts exist from file uploader paths
        doc_title = doc["title"].replace("('", "").replace("',)", "") if isinstance(doc["title"], str) else str(doc["title"])
        
        with st.container(border=True):
            col_meta, col_summary, col_action = st.columns([2, 4, 1])
            
            with col_meta:
                st.markdown(f"**📄 {doc_title}**")
                st.caption(f"Category: `{doc['genre']}`")
                
            with col_summary:
                st.write(f"_{doc['summary']}_")
                
            with col_action:
                # Standardized to unique index count keys to maintain modern layouts without clashing grid references
                if st.button("🗑️ Wipe", key=f"btn_wipe_rag_doc_{doc['id']}_{idx}", width="stretch"):
                    vector_store.delete_single_rag_document(doc["id"])
                    st.toast(f"Successfully purged vector item record reference: {doc_title}!")
                    st.rerun()
