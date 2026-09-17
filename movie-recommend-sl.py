import os
import json
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

# --- CACHE THE CLIENT TO PREVENT RE-RUN CLOSURE ---
@st.cache_resource
def get_gemini_client():
    """Initializes and caches the Gemini client so it survives Streamlit reruns."""
    return genai.Client()

client = get_gemini_client()

# --- DEFINING THE STRUCTURED OUTPUT SCHEMA ---
class MovieItem(BaseModel):
    title: str = Field(description="The exact title of the movie.")
    year: int = Field(description="The 4-digit release year of the movie.")
    genre: str = Field(description="The primary genre(s) associated with this movie.")
    match_score: int = Field(description="A matching percentage (0 to 100) indicating how well this matches the user prompt.")
    description: str = Field(description="A brief 1-sentence synopsis of the plot.")
    reason: str = Field(description="A 1-sentence personalization explaining exactly why this fits the user's current request.")

class MovieRecommendationList(BaseModel):
    conversational_intro: str = Field(description="A brief, friendly response introducing the movie selections.")
    recommendations: list[MovieItem] = Field(description="A precise list containing exactly 3 recommended movies.")

# --- Page Configurations ---
st.set_page_config(page_title="GenAI Movie Buddy", page_icon="🍿", layout="centered")

# --- Initialize Session States ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []

# --- Watchlist Management Functions ---
def add_to_watchlist(movie_title, movie_year):
    movie_entry = f"🎬 {movie_title} ({movie_year})"
    if movie_entry not in st.session_state.watchlist:
        st.session_state.watchlist.append(movie_entry)

def clear_watchlist():
    st.session_state.watchlist = []

# --- Sidebar Configuration Panels ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    
    genres = ["All Genres", "Action", "Comedy", "Drama", "Sci-Fi", "Horror", "Thriller", "Romance", "Documentary", "Animation"]
    selected_genre = st.selectbox(
        "Preferred Genre Focus:", 
        options=genres, 
        index=0,
        help="Gently nudges the model to prioritize or stay within this genre category."
    )
    
    temperature = st.slider(
        "Creativity (Temperature):", 
        min_value=0.0, 
        max_value=2.0, 
        value=0.7, 
        step=0.1,
        help="Lower values are predictable. Higher values give obscure suggestions."
    )
    
    st.markdown("---")
    
    # Render Watchlist UI Section
    st.subheader("📝 Your Watchlist")
    if st.session_state.watchlist:
        for item in st.session_state.watchlist:
            st.write(item)
        if st.button("🗑️ Clear Watchlist", type="secondary", use_container_width=True):
            clear_watchlist()
            st.rerun()
    else:
        st.info("Your watchlist is currently empty. Click 'Save to Watchlist' on any recommendation card.")
        
    st.markdown("---")
    
    if st.button("🔄 Reset Conversation", type="secondary", use_container_width=True):
        if "messages" in st.session_state:
            del st.session_state.messages
        if "gemini_chat" in st.session_state:
            del st.session_state.gemini_chat
        clear_watchlist()
        st.rerun()

# --- Main Interface ---
st.title("🍿 Your GenAI Movie Buddy")
st.write("Chat with Gemini 3.5 to get structured, card-based recommendations tailored to your style!")

# Maintain a persistent Gemini SDK Chat Session
if "gemini_chat" not in st.session_state:
    st.session_state.gemini_chat = client.chats.create(model="gemini-3.5-flash")

# --- Helper to Display Movies as Graphical Cards ---
def render_movie_cards(data: dict, turn_index: int):
    """Safely renders custom layout blocks using pre-parsed dictionary data."""
    st.markdown(f"*{data.get('conversational_intro', 'Here are your top choices:')}*")
    
    for idx, movie in enumerate(data.get("recommendations", [])):
        title = movie.get("title")
        year = movie.get("year")
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"🎬 {title} ({year})")
                st.caption(f"🎭 **Genre:** {movie.get('genre')}")
            with col2:
                st.metric(label="Match Score", value=f"{movie.get('match_score')}%")
            
            st.write(f"**Synopsis:** {movie.get('description')}")
            st.info(f"💡 {movie.get('reason')}")
            
            # Form clean unique key names for widgets
            btn_key = f"watch_{turn_index}_{idx}_{str(year)}"
            
            st.button(
                "➕ Save to Watchlist", 
                key=btn_key, 
                on_click=add_to_watchlist, 
                args=(title, year),
                use_container_width=True
            )

# --- Display Existing Chat History ---
for index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
        else:
            render_movie_cards(message["content"], turn_index=index)

# --- Handle User Input ---
if user_input := st.chat_input("What kind of movie are you in the mood for?"):
    
    # 1. Render User Message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. Build the dynamic runtime generation config
    genre_instruction = f" Focus primarily on the '{selected_genre}' genre unless the user specifies otherwise." if selected_genre != "All Genres" else ""
    
    runtime_system_instruction = (
        "You are an expert movie recommendation companion. Help the user discover "
        f"movies based on their explicit or implicit preferences.{genre_instruction} "
        "You must return the structured movie data list exactly according to the schema provided. "
        "Always provide exactly 3 items in the recommendations list."
    )
    
    runtime_config = types.GenerateContentConfig(
        system_instruction=runtime_system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=MovieRecommendationList,
    )
    
    # 3. Process Structured Response
    with st.chat_message("assistant"):
        with st.spinner("Curating your custom movie selection..."):
            try:
                response = st.session_state.gemini_chat.send_message(
                    message=user_input, 
                    config=runtime_config
                )
                
                # Parse JSON immediately on the response thread to catch errors early
                parsed_json = json.loads(response.text)
                current_turn = len(st.session_state.messages)
                
                # Render the parsed card layout
                render_movie_cards(parsed_json, turn_index=current_turn)
                
                # Save the parsed DICTIONARY instead of a raw text string into history
                st.session_state.messages.append({"role": "assistant", "content": parsed_json})
                
                st.rerun()
                
            except Exception as e:
                st.error(f"An error occurred while compiling your recommendations: {str(e)}")
