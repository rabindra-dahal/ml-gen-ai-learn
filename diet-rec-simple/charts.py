"""Module handling quick historical calorie trend line visualizations."""

import streamlit as st


def render_analytics_dashboard(hist: list[tuple]) -> None:
    """Graphs daily caloric intake timelines securely."""
    if not hist:
        return

    with st.expander("📈 View Weekly Nutrition Trends", expanded=True):
        dates = [row[0] for row in hist]
        calories_logged = [row[1] for row in hist]

        c1, c2 = st.columns(2)
        c1.metric("Logs Tracker", f"{len(dates)} Days")
        c2.metric(
            "Avg Calories Intake",
            f"{int(sum(calories_logged)/len(calories_logged)) if calories_logged else 0} kcal",
        )

        st.write("#### Energy History (Calories Logged Over Time)")
        st.line_chart(dict(zip(dates, calories_logged)))
