"""Module managing processing streams for text document vector storage maps."""

import os
import streamlit as st
from backend import tracker_engine, vector_store


def process_custom_rag_uploads(client) -> None:
    """Processes any pending text file configurations dropped inside upload hooks."""
    if "pending_rag_uploads" in st.session_state and st.session_state.pending_rag_uploads:
        uploaded_files = st.session_state.pending_rag_uploads
        del st.session_state.pending_rag_uploads 
        
        with st.spinner("Parsing text files and executing vector index injection operations..."):
            for uploaded_file in uploaded_files:
                file_text = uploaded_file.read().decode("utf-8")
                emb_res = client.models.embed_content(model="gemini-embedding-001", contents=file_text)
                tracker_engine.increment_api_counter("Embedding (Custom Document Upload)")
                
                if emb_res.embeddings:
                    # Clean filename array components out to handle doc titles cleanly
                    doc_title = os.path.splitext(uploaded_file.name)
                    vector_store.save_book_to_knowledge_base(
                        title=doc_title,
                        author="Custom Contributor",
                        genre="Uploaded Context Collection",
                        summary=file_text[:200] + "...", 
                        embedding=emb_res.embeddings.values
                    )
            st.toast(f"Successfully indexed {len(uploaded_files)} files into RAG store!")
            st.rerun()


def render_uploader_widget() -> None:
    """Renders the file uploader dropzone control panel."""
    st.markdown("---")
    st.write("### 📤 Custom RAG Knowledge Base Uploader")
    uploaded_files = st.file_uploader(
        "Choose local document text fragments:", 
        type=["txt", "md"], 
        accept_multiple_files=True, 
        key="rag_knowledge_file_uploader"
    )
    if uploaded_files:
        if st.button("🚀 Parse & Index Uploaded Documents", type="primary", width="stretch"):
            st.session_state.pending_rag_uploads = uploaded_files
            st.rerun()
