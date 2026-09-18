import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

import database
from schema import DietPlanResponse

load_dotenv()
if not os.getenv("GEMINI_API_KEY"):
    st.error("Missing GEMINI_API_KEY inside your .env file!")
    st.stop()

database.init_db()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

client = get_gemini_client()
st.set_page_config(page_title="GenAI Diet & Nutrition Companion", page_icon="🥗", layout="wide")

if "diet_messages" not in st.session_state:
    st.session_state.diet_messages = database.load_persisted_chat()
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = database.load_persisted_grocery()

with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_diet = st.selectbox("Dietary Preference:", ["No Restrictions", "Keto", "Vegan", "Vegetarian", "High-Protein", "Low-Carb", "Mediterranean"])
    excluded_ingredients = st.multiselect("Exclude Allergens:", ["Nuts", "Gluten", "Dairy", "Soy", "Shellfish", "Eggs", "Peanuts"])
    target_calories = st.slider("Target Calories:", min_value=1200, max_value=4000, value=2000, step=100)
    
    st.markdown("---")
    st.subheader("🛒 Shopping List")
    if st.session_state.shopping_list:
        for item in st.session_state.shopping_list: st.write(f"⬜ {item}")
        file_content = "\n".join([f"- [ ] {i}" for i in st.session_state.shopping_list])
        st.download_button("📥 Download List", data=file_content, file_name="grocery_list.txt", mime="text/plain", width='stretch')
        if st.button("🗑️ Clear List", width='stretch'):
            database.delete_all_grocery()
            st.session_state.shopping_list = []
            st.rerun()
    else:
        st.info("Shopping list empty.")
        
    st.markdown("---")
    if st.button("🔄 Reset Chat Session", type="secondary", width='stretch'):
        database.clear_entire_session()
        st.session_state.diet_messages = []
        st.session_state.shopping_list = []
        if "diet_chat" in st.session_state: del st.session_state.diet_chat
        st.rerun()

st.title("🥗 Your GenAI Diet & Nutrition Companion")

historical_data = database.fetch_analytics_logs()
if historical_data:
    with st.expander("📈 View Weekly Nutrition Progress & Trend Analysis", expanded=True):
        dates = [row for row in historical_data]
        calories_logged = [row for row in historical_data]
        p_logged = [row for row in historical_data]
        c_logged = [row for row in historical_data]
        f_logged = [row for row in historical_data]
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Tracked Logs", f"{len(dates)} Days")
        m_col2.metric("Avg Calories Logged", f"{int(sum(calories_logged)/len(calories_logged))} kcal")
        m_col3.metric("Peak Energy Intake", f"{max(calories_logged)} kcal")
        
        st.write("#### Energy History (Calories)")
        st.line_chart(dict(zip(dates, calories_logged)))
        st.write("#### Macronutrient Tracking Balance (Grams)")
        st.bar_chart(data={"Protein": p_logged, "Carbohydrates": c_logged, "Fats": f_logged})

if "diet_chat" not in st.session_state:
    history_instances = []
    for msg in st.session_state.diet_messages:
        text_data = json.dumps(msg["content"]) if isinstance(msg["content"], dict) else msg["content"]
        history_instances.append(types.Content(role=msg["role"], parts=[types.Part.from_text(text=text_data)]))
    st.session_state.diet_chat = client.chats.create(model="gemini-2.5-flash", history=history_instances)

def render_diet_cards(data: dict, turn_index: int):
    st.markdown(f"*{data.get('conversational_intro', 'Here is your plan:')}*")
    p, c, f = data.get('total_protein_g', 0), data.get('total_carbs_g', 0), data.get('total_fat_g', 0)
    
    if p > 0 or c > 0 or f > 0:
        st.markdown("#### 📊 Selected Plan Macronutrient Profile")
        col_p, col_c, col_f = st.columns(3)
        col_p.write(f"🧬 **Protein:** {p}g"); col_p.progress(min(p / 200, 1.0))
        col_c.write(f"🍞 **Carbs:** {c}g"); col_c.progress(min(c / 300, 1.0))
        col_f.write(f"🥑 **Fat:** {f}g"); col_f.progress(min(f / 100, 1.0))
    
    st.metric(label="Calculated Daily Energy Total", value=f"{data.get('daily_total_calories', 0)} kcal")
    
    for idx, meal in enumerate(data.get("meals", [])):
        m_type, r_name, ingredients = meal.get("meal_type", "Meal"), meal.get("recipe_name", "Healthy Dish"), meal.get("ingredients", [])
        with st.container(border=True):
            c1, c2 = st.columns(2) 
            with c1:
                st.subheader(f"🍳 {m_type}: {r_name}")
                st.caption(f"P: {meal.get('protein_g')}g | C: {meal.get('carbs_g')}g | F: {meal.get('fat_g')}g")
            with c2: st.metric(label="Calories", value=f"{meal.get('calories')} kcal")
            st.write("**Ingredients:** " + ", ".join(ingredients))
            st.info(f"💡 **Prep Tip:** {meal.get('prep_tip')}")
            
            btn_key = f"diet_{turn_index}_{idx}_{m_type.lower()}"
            if st.button("➕ Add Ingredients to Grocery List", key=btn_key):
                database.save_grocery_items(ingredients)
                st.session_state.shopping_list = database.load_persisted_grocery()
                st.toast(f"Added {len(ingredients)} items!")
                st.rerun()

for index, message in enumerate(st.session_state.diet_messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user": st.markdown(message["content"])
        else: render_diet_cards(message["content"], turn_index=index)

if user_input := st.chat_input("Request a custom meal plan..."):
    with st.chat_message("user"): st.markdown(user_input)
    database.save_chat_message("user", user_input)
    st.session_state.diet_messages.append({"role": "user", "content": user_input})
    
    diet_rules = f" Adhere strictly to the rules of a '{selected_diet}' diet." if selected_diet != "No Restrictions" else ""
    allergy_rules = f" CRITICAL: Exclude these items: {', '.join(excluded_ingredients)}." if excluded_ingredients else ""
    
    runtime_system_instruction = (
        "You are an expert nutrition companion. Return structured responses balancing flavor and macros."
        f"{diet_rules}{allergy_rules} Aim for a daily total of around {target_calories} calories. "
        "Sum up total protein, carbs, and fats accurately across all generated meals. "
        "You must return the structured payload list exactly according to the schema provided."
    )
    
    model_fallback_pipeline = ("gemini-2.5-flash", "gemini-2.5-pro")
    response_text = None
    
    with st.chat_message("assistant"):
        with st.spinner("Compiling nutrition data..."):
            for target_model in model_fallback_pipeline:
                try:
                    response = st.session_state.diet_chat.send_message(
                        message=user_input, 
                        config=types.GenerateContentConfig(
                            system_instruction=runtime_system_instruction, temperature=0.3,
                            response_mime_type="application/json", response_schema=DietPlanResponse,
                        )
                    )
                    response_text = response.text
                    break
                except Exception as model_error:
                    if "503" in str(model_error) or "UNAVAILABLE" in str(model_error).upper():
                        st.warning(f"⚠️ `{target_model}` is busy. Attempting pipeline fallback...")
                        continue
                    else:
                        st.error(f"Execution Error: {str(model_error)}"); st.stop()
            
            if response_text:
                try:
                    parsed_json = json.loads(response_text)
                    database.log_daily_macros(parsed_json)
                    database.save_chat_message("assistant", parsed_json)
                    current_turn = len(st.session_state.diet_messages)
                    render_diet_cards(parsed_json, turn_index=current_turn)
                    st.session_state.diet_messages.append({"role": "assistant", "content": parsed_json})
                    st.rerun()
                except Exception as e: st.error(f"Error parsing layout: {str(e)}")
            else:
                st.error("❌ Google's API nodes are overloaded. Please try pressing Enter again.")
