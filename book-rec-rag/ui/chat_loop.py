"""Module running live dialogue iteration pipelines with vector matching lookups and live trace logs."""

import json
from google.genai import types
import streamlit as st
from backend import chat_history, tracker_engine, vector_store
import views


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
        chat_history.save_chat_message("user", user_input)
        st.session_state.book_messages.append({"role": "user", "content": user_input})

        # Execute live trace index retrieval calculations
        rag_payload = []
        try:
            emb_resp = client.models.embed_content(model="gemini-embedding-001", contents=user_input)
            tracker_engine.increment_api_counter("Embedding (User Query)")
            q_emb = emb_resp.embeddings[0].values if emb_resp.embeddings else None
            
            if q_emb:
                rag_payload = vector_store.query_vector_store_rag(q_emb, limit=1)
        except Exception:
            rag_payload = []

        # ─── NEW: AUTOMATED KEYWORD HIGHLIGHT CONTAINER ───
        if rag_payload and rag_payload[0]["score"] > 0.4:
            matched_doc = rag_payload[0]
            clean_title = str(matched_doc["title"]).replace("('", "").replace("',)", "")
            
            # Print a neat warning box showing exact matching context logs
            st.info(
                f"🎯 **RAG Match Verified** (Similarity Score: `{matched_doc['score']:.2f}`)\n\n"
                f"Injecting context memory fragment from: **{clean_title}**\n\n"
                f"➔ *\"{matched_doc['summary']}\"*"
            )

        rag_context = json.dumps(rag_payload)
        sys_ins = (
            f"You are an expert literary librarian. Genre Focus: {selected_genre}. Exclude: {', '.join(excluded_tropes)}. Goal: {target_reading_pace} books.\n"
            f"Database reference match context: {rag_context}.\n"
            "Format selections beautifully using markdown. You must start each book recommendation line with a 3rd-level header exactly matching: '### 📖 [Book Title] by [Author]' so the system can parse it. Respond immediately."
        )

        with st.chat_message("assistant"):
            with st.spinner("Curating your reading list..."):
                try:
                    response = st.session_state.book_chat.send_message(message=user_input, config=types.GenerateContentConfig(system_instruction=sys_ins, temperature=0.4))
                    tracker_engine.increment_api_counter("Chat Inference")
                    
                    if not response.text:
                        st.error("⚠️ Connection delay occurred. Please try again.")
                        st.stop()

                    views.render_markdown_response(response.text, t_idx=len(st.session_state.book_messages))
                    chat_history.save_chat_message("assistant", response.text)
                    tracker_engine.log_reading_goal(target_reading_pace)
                    st.session_state.book_messages.append({"role": "assistant", "content": response.text})
                    st.rerun()
                except Exception as err:
                    st.error(f"Chat Session Error: {str(err)}")
