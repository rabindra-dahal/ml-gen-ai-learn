"""Module handling card layout container views and UI rendering loops."""

import streamlit as st
import utils


def render_diet_cards(data: dict, t_idx: int) -> None:
    """Renders structured recipe blocks into clean Streamlit layouts."""
    st.markdown(f"*{data.get('conversational_intro', 'Curated schedule:')}*")
    p, c, f = (
        data.get("total_protein_g", 0),
        data.get("total_carbs_g", 0),
        data.get("total_fat_g", 0),
    )

    if p > 0 or c > 0 or f > 0:
        cp, cc, cf = st.columns(3)
        cp.write(f"🧬 **Protein:** {p}g")
        cp.progress(min(p / 200, 1.0))
        cc.write(f"🍞 **Carbs:** {c}g")
        cc.progress(min(c / 300, 1.0))
        cf.write(f"🥑 **Fat:** {f}g")
        cf.progress(min(f / 100, 1.0))
        
    st.metric(
        label="Daily Caloric Target",
        value=f"{data.get('daily_total_calories', 0)} kcal",
    )

    for idx, meal in enumerate(data.get("meals", [])):
        m_type = meal.get("meal_type", "Meal")
        r_name = meal.get("recipe_name", "Dish")
        ing = meal.get("ingredients", [])
        
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                prefix = "📋 [DB Sourced] " if meal.get("matched_from_db") else "🍳 "
                st.subheader(f"{prefix}{m_type}: {r_name}")
                st.caption(
                    f"P: {meal.get('protein_g')}g | C: {meal.get('carbs_g')}g | F: {meal.get('fat_g')}g"
                )
            with col2:
                st.metric("Calories", f"{meal.get('calories')} kcal")
                
            st.write("**Ingredients:** " + ", ".join(ing))
            st.info(f"💡 **Prep Tip:** {meal.get('prep_tip')}")

            if st.button(
                "➕ Add Ingredients", key=f"d_{t_idx}_{idx}_{m_type.lower()}"
            ):
                utils.save_grocery_items(ing)
                st.session_state.shopping_list = utils.load_persisted_grocery()
                st.toast("Ingredients appended!")
                st.rerun()
