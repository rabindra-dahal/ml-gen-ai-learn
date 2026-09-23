"""UI Module presenting a granular raw table viewer for inspecting all SQLite storage layers."""

import streamlit as st
import pandas as pd
from backend import db_core


def render_database_tables_inspector() -> None:
    """Renders dataframes representing all underlying system database tables."""
    st.markdown("---")
    st.write("### 🔍 System Database Table Inspector")
    st.caption("Inspect raw relational row metrics across all schema storage arrays inside `book_recommender.db`.")

    # 1. Fetch available table schema names from SQLite internal master ledger
    conn = db_core.get_db_connection()
    cursor = conn.cursor()
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()
    
    if not tables:
        conn.close()
        st.info("No active user tables located inside database.")
        return

    table_names = [t[0] for t in tables]
    
    # 2. Render dropdown select box mapping individual table variants
    selected_table = st.selectbox(
        "Select Database Table to Inspect:",
        options=table_names,
        key="db_inspector_table_select_dropdown"
    )

    if selected_table:
        try:
            # Fetch all rows from the selected table
            data_rows = cursor.execute(f"SELECT * FROM {selected_table}").fetchall()
            
            # Fetch table column headers explicitly to map cleanly to a pandas DataFrame
            column_headers = [description[0] for description in cursor.description]
            
            if not data_rows:
                st.info(f"Table `{selected_table}` is currently empty (0 rows initialized).")
            else:
                # ─── FIXED: CONVERT TO PANDAS DATAFRAME FIRST TO ENSURE PERFECT COLUMN ALIGNMENT ───
                df = pd.DataFrame(data_rows, columns=column_headers)
                
                # Build an interactive data table representation frame
                st.dataframe(
                    df,
                    use_container_width=True,
                    key=f"dataframe_render_instance_{selected_table}"
                )
                st.caption(f"Total Record Footprint Count: `{len(data_rows)} rows` managed in `{selected_table}`.")
        except Exception as err:
            st.error(f"Failed to read raw relational rows: {str(err)}")
            
    conn.close()
