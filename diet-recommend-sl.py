import os
import json
import sqlite3
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load environment variables from .env
load_dotenv()

# Verify API key exists
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Missing GEMINI_API_KEY! Please set it in your .env file.")
    st.stop()

# --- DB PERSISTENCE SYSTEM ---
DB_FILE = "nutrition_companion.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grocery_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_macro_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT UNIQUE,
            calories INTEGER,
            protein INTEGER,
            carbs INTEGER,
            fat INTEGER,
            raw_payload TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_persisted_chat():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC").fetchall()
    conn.close()
    return [{"role": r, "content": json.loads(c) if r == "assistant" else c} for r, c in rows]

def save_chat_message(role, content_payload):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    content_str = json.dumps(content_payload) if isinstance(content_payload, dict) else content_payload
    cursor.execute("INSERT INTO chat_history (role, content, timestamp) VALUES (?, ?, ?)", 
                   (role, content_str, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_persisted_grocery():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT item FROM grocery_list").fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_grocery_items(ingredients_list):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for ingredient in ingredients_list:
        clean_item = ingredient.strip().capitalize()
        cursor.execute("INSERT OR IGNORE INTO grocery_list (item) VALUES (?)", (clean_item,))
    conn.commit()
    conn.close()

def delete_all_grocery():
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM grocery_list")
    conn.commit()
    conn.close()

def log_daily_macros(data_dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT OR REPLACE INTO daily_macro_logs (log_date, calories, protein, carbs, fat, raw_payload)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (today_str, data_dict.get('daily_total_calories', 0), data_dict.get('total_protein_g', 0),
          data_dict.get('total_carbs_g', 0), data_dict.get('total_fat_g', 0), json.dumps(data_dict)))
    conn.commit()
    conn.close()

def fetch_analytics_logs():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT log_date, calories, protein, carbs, fat FROM daily_macro_logs ORDER BY log_date ASC").fetchall()
    conn.close()
    return rows

init_db()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

client = get_gemini_client()

class MealItem(BaseModel):
    meal_type: str = Field(description="Type of meal (e.g., Breakfast, Lunch, Dinner, Snack).")
    recipe_name: str = Field(description="Name of the meal or recipe.")
    calories: int = Field(description="Estimated calories for this meal.")
    protein_g: int = Field(description="Total protein content in grams.")
    carbs_g: int = Field(description="Total carbohydrate content in grams.")
    fat_g: int = Field(description="Total fat content in grams.")
    ingredients: list[str] = Field(description="Raw ingredients needed.")
    prep_tip: str = Field(description="Quick preparation tip.")

class DietPlanResponse(BaseModel):
    conversational_intro: str = Field(description="Encouraging summary statement.")
    daily_total_calories: int = Field(description="Sum of all meals' calories.")
    total_protein_g: int = Field(description="Sum of protein grams.")
    total_carbs_g: int = Field(description="Sum of carbohydrate grams.")
    total_fat_g: int = Field(description="Sum of fat grams.")
    meals: list[MealItem] = Field(description="Set of exactly 3-4 meal recommendations.")

st.set_page_config(page_title="GenAI Diet Companion & Dashboard", page_icon="🥗", layout="wide")

if "diet_messages" not in st.session_state:
    st.session_state.diet_messages = load_persisted_chat()
if "shopping_list" not in st.session_state:
    st.session_state.shopping_list = load_persisted_grocery()

with st.sidebar:
    st.title("⚙️ Control Panel")
    selected_diet = st.selectbox("Dietary Preference Focus:", options=["No Restrictions", "Keto", "Vegan", "Vegetarian", "High-Protein", "Low-Carb", "Mediterranean"])
    excluded_ingredients = st.multiselect("Exclude Ingredients / Allergens:", options=["Nuts", "Gluten", "Dairy", "Soy", "Shellfish", "Eggs", "Peanuts"])
    target_calories = st.slider("Daily Target Calories:", min_value=1200, max_value=4000, value=2000, step=100)
    
    st.markdown("---")
    st.subheader("🛒 Grocery Shopping List")
    if st.session_state.shopping_list:
        for item in st.session_state.shopping_list:
            st.write(f"⬜ {item}")
        file_content = "\n".join([f"- [ ] {i}" for i in st.session_state.shopping_list])
        st.download_button("📥 Download List", data=file_content, file_name="grocery_list.txt", mime="text/plain", width='stretch')
        if st.button("🗑️ Clear Grocery List", width='stretch'):
            delete_all_grocery()
            st.session_state.shopping_list = []
            st.rerun()
    else:
        st.info("Shopping list empty.")
        
    st.markdown("---")
    if st.button("🔄 Reset Chat Session", type="primary", width='stretch'):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history")
        cursor.execute("DELETE FROM grocery_list")
        conn.commit()
        conn.close()
        st.session_state.diet_messages = []
        st.session_state.shopping_list = []
        if "diet_chat" in st.session_state:
            del st.session_state.diet_chat
        st.rerun()

st.title("🥗 Your GenAI Diet & Nutrition Companion")

historical_data = fetch_analytics_logs()
if historical_data:
    with st.expander("📈 View Weekly Nutrition Progress & Trend Analysis", expanded=True):
        dates = [row[0] for row in historical_data]
        calories_logged = [row[1] for row in historical_data]
        p_logged = [row[2] for row in historical_data]
        c_logged = [row[3] for row in historical_data]
        f_logged = [row[4] for row in historical_data]
        
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
    st.session_state.diet_chat = client.chats.create(model="gemini-3.5-flash", history=history_instances)

def render_diet_cards(data: dict, turn_index: int):
    st.markdown(f"*{data.get('conversational_intro', 'Here is your plan:')}*")
    p = data.get('total_protein_g', 0)
    c = data.get('total_carbs_g', 0)
    f = data.get('total_fat_g', 0)
    
    if p > 0 or c > 0 or f > 0:
        st.markdown("#### 📊 Selected Plan Macronutrient Profile")
        col_p, col_c, col_f = st.columns(3)
        col_p.write(f"🧬 **Protein:** {p}g")
        col_p.progress(min(p / 200, 1.0))
        col_c.write(f"🍞 **Carbs:** {c}g")
        col_c.progress(min(c / 300, 1.0))
        col_f.write(f"🥑 **Fat:** {f}g")
        col_f.progress(min(f / 100, 1.0))
    
    st.metric(label="Calculated Daily Energy Total", value=f"{data.get('daily_total_calories', 0)} kcal")
    
    for idx, meal in enumerate(data.get("meals", [])):
        m_type = meal.get("meal_type", "Meal")
        r_name = meal.get("recipe_name", "Healthy Dish")
        ingredients = meal.get("ingredients", [])
        
        with st.container(border=True):
            c1, c2 = st.columns(2) 
            with c1:
                st.subheader(f"🍳 {m_type}: {r_name}")
                st.caption(f"P: {meal.get('protein_g')}g | C: {meal.get('carbs_g')}g | F: {meal.get('fat_g')}g")
            with c2:
                st.metric(label="Calories", value=f"{meal.get('calories')} kcal")
            
            st.write("**Ingredients:** " + ", ".join(ingredients))
            st.info(f"💡 **Prep Tip:** {meal.get('prep_tip')}")
            
            btn_key = f"diet_{turn_index}_{idx}_{m_type.lower()}"
            if st.button("➕ Add Ingredients to Grocery List", key=btn_key):
                save_grocery_items(ingredients)
                st.session_state.shopping_list = load_persisted_grocery()
                st.toast(f"Added {len(ingredients)} items to your shopping list!")
                st.rerun()

for index, message in enumerate(st.session_state.diet_messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_diet_cards(message["content"], turn_index=index)

if user_input := st.chat_input("Request a custom meal plan, or request an ingredient substitution..."):
    with st.chat_message("user"):
        st.markdown(user_input)
    save_chat_message("user", user_input)
    st.session_state.diet_messages.append({"role": "user", "content": user_input})
    
    diet_rules = f" Adhere strictly to the rules of a '{selected_diet}' diet." if selected_diet != "No Restrictions" else ""
    allergy_rules = f" CRITICAL: Exclude these items: {', '.join(excluded_ingredients)}." if excluded_ingredients else ""
    
    runtime_system_instruction = (
        "You are an expert nutrition companion. Return structured responses balancing flavor and macros."
        f"{diet_rules}{allergy_rules} Aim for a daily total of around {target_calories} calories. "
        "Sum up total protein, carbs, and fats accurately across all generated meals. "
        "You must return the structured payload list exactly according to the schema provided."
    )
    
    runtime_config = types.GenerateContentConfig(
        system_instruction=runtime_system_instruction,
        temperature=0.3,
        response_mime_type="application/json",
        response_schema=DietPlanResponse,
    )
    
    with st.chat_message("assistant"):
        with st.spinner("Compiling nutrition data..."):
            try:
                response = st.session_state.diet_chat.send_message(message=user_input, config=runtime_config)
                parsed_json = json.loads(response.text)
                log_daily_macros(parsed_json)
                save_chat_message("assistant", parsed_json)
                current_turn = len(st.session_state.diet_messages)
                render_diet_cards(parsed_json, turn_index=current_turn)
                st.session_state.diet_messages.append({"role": "assistant", "content": parsed_json})
                st.rerun()
            except Exception as e:
                st.error(f"Error compiling layout: {str(e)}")
