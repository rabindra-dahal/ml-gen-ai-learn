"""Module handling database log rendering and visualization trend lines."""

import streamlit as st


def render_analytics_dashboard(hist: list[tuple]) -> None:
    """Processes historical SQLite database tuples into graphical dashboards."""
    if not hist:
        return

    with st.expander("📈 View Weekly Nutrition Trends", expanded=True):
        dates = [row[0] for row in hist]
        calories_logged = [row[1] for row in hist]
        p_vals = [row[2] for row in hist]
        c_vals = [row[3] for row in hist]
        f_vals = [row[4] for row in hist]

        c1, c2, c3 = st.columns(3)
        c1.metric("Logs Tracker", f"{len(dates)} Days")
        c2.metric(
            "Avg Calories Intake",
            f"{int(sum(calories_logged)/len(calories_logged)) if calories_logged else 0} kcal",
        )
        c3.metric(
            "Peak Intake",
            f"{max(calories_logged) if calories_logged else 0} kcal",
        )

        st.write("#### Caloric Trend Lines")
        st.line_chart(dict(zip(dates, calories_logged)))
        st.write("#### Macronutrient Gram Balances")
        st.bar_chart(data={"Protein": p_vals, "Carbs": c_vals, "Fats": f_vals})
