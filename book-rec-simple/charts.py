"""Module handling dashboard metric tracking visualizations."""

import streamlit as st


def render_analytics_dashboard(hist: list[tuple]) -> None:
    """Graphs reading milestone choices cleanly onto line chart plots."""
    if not hist:
        return

    with st.expander("📈 View Reading Goal Commitments", expanded=True):
        dates = [row[0] for row in hist]
        goals_logged = [row[1] for row in hist]

        c1, c2 = st.columns(2)
        c1.metric("Activity Logs", f"{len(dates)} Days Tracked")
        c2.metric(
            "Current Pace Target",
            f"{goals_logged[-1] if goals_logged else 0} Books/Year",
        )

        st.write("#### Historical Yearly Reading Pace Commitment")
        st.line_chart(dict(zip(dates, goals_logged)))
