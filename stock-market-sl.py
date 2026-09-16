import streamlit as st
import os
import random
import datetime
import pandas as pd
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="GenAI Stock Market Simulator", page_icon="📈", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Define Strict GenAI Structured Output Schema
class StockAnalysis(BaseModel):
    action: str = Field(description="Must be exactly one of: 'BUY', 'SELL', or 'HOLD'")
    confidence_score: float = Field(description="Confidence score between 0.0 (low) and 1.0 (high)")
    justification: str = Field(description="A sharp 1-2 sentence technical analysis matching price trends and news sentiment.")
    target_price: float = Field(description="Estimated short-term price target based on simulation analysis.")

# 3. Simulated Live Stock Market & News API Engine
def generate_market_data(ticker: str, trend: str):
    """Generates synthetic stock price history and current sentiment payload."""
    now = datetime.datetime.now()
    dates = [now - datetime.timedelta(days=i) for i in range(30)][::-1]
    
    # Set pricing baselines based on selected ticker
    base_price = 220.0 if ticker == "AAPL" else (430.0 if ticker == "MSFT" else 180.0)
    
    prices = []
    current_price = base_price
    
    # Apply synthetic trends
    for _ in range(30):
        change_pct = random.uniform(-0.02, 0.02)
        if trend == "Bullish":
            change_pct += 0.005
        elif trend == "Bearish":
            change_pct -= 0.005
        current_price *= (1 + change_pct)
        prices.append(round(current_price, 2))
        
    # Generate contextual unstructured news feeds
    news_pool = {
        "Bullish": [
            f"{ticker} announces record-breaking Q3 earnings beating Wall Street expectations.",
            f"Next-gen AI integration sparks massive demand upgrade cycles for {ticker}.",
            f"Institutional upgrade: Top firm raises {ticker} outlook to 'Strong Buy'."
        ],
        "Bearish": [
            f"Supply chain bottlenecks threaten holiday shipping windows for {ticker}.",
            f"Antitrust regulators launch broad probe into {ticker}'s market practices.",
            f"Tech sector sell-off drags down market cap leaders including {ticker}."
        ],
        "Flat": [
            f"{ticker} schedules annual developer conference for next month.",
            f"Analysts project neutral growth vectors for {ticker} ahead of product updates.",
            f"Minor executive board shuffling announced by {ticker} corporate relations."
        ]
    }
    
    selected_news = random.sample(news_pool[trend], 2)
    
    df = pd.DataFrame({"Date": dates, "Price": prices})
    return df, selected_news

# 4. Streamlit Dashboard Layout
st.title("📈 GenAI Stock Market Analysis & Trade Simulator")
st.markdown("Simulate how a Generative AI Agent interprets financial variables using **`gemini-3.6-flash`** and structured outputs.")

# Sidebar Configuration Controls
st.sidebar.header("🕹️ Market Simulator Parameters")
selected_ticker = st.sidebar.selectbox("Select Ticker Symbol", ["AAPL (Apple)", "MSFT (Microsoft)", "GOOGL (Alphabet)"])
ticker_clean = selected_ticker.split(" ")[0]

simulated_trend = st.sidebar.radio("Simulate Market Trend Environment", ["Bullish", "Bearish", "Flat"])

# Trigger Data Generation Step
history_df, market_news = generate_market_data(ticker_clean, simulated_trend)
live_price = history_df["Price"].iloc[-1]
previous_price = history_df["Price"].iloc[-2]
price_delta = round(live_price - previous_price, 2)

# Main Dashboard View Grid layout
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.subheader(f"📊 {ticker_clean} Live Asset Chart")
    
    # Live KPI Cards
    kpi1, kpi2 = st.columns(2)
    kpi1.metric(label="Current Spot Value", value=f"\({live_price:,.2f}", delta=f"\){price_delta} (24h)")
    kpi2.metric(label="Simulated Trend Filter", value=simulated_trend)
    
    # Render interactive price timeline
    st.line_chart(data=history_df, x="Date", y="Price", color="#00CC96", use_container_width=True)
    
    st.write("#### 📰 Extracted Real-Time Unstructured News Feed")
    for news in market_news:
        st.info(f"🔹 {news}")

with col2:
    st.subheader("🤖 GenAI Agent Evaluation Module")
    st.markdown("Click below to prompt the AI agent to ingest the live market state and output a validated trading strategy decision matrix.")
    
    if st.button("🚀 Execute GenAI Analysis Engine", use_container_width=True):
        
        # Ground prompt layout with current database parameters (RAG framework)
        system_instruction = """
        You are an elite, highly calculated algorithmic trading assistant. 
        Analyze the stock data, price history trends, and news headlines provided.
        You must compute a deterministic trade assessment payload complying strictly with the requested JSON properties schema.
        """
        
        agent_prompt = f"""
        Asset Ticker: {ticker_clean}
        Current Market Price: \${live_price}
        Recent Price History Matrix (Last 5 Ticks): {history_df['Price'].tail(5).tolist()}
        Live Unstructured News Input Context: {market_news}
        
        Evaluate the indicators above and fill the required schema.
        """
        
        with st.spinner("Analyzing data vector patterns via Gemini 3.6 Flash..."):
            try:
                # Query model utilizing strict schemas
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=agent_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=StockAnalysis,
                    ),
                )
                
                # Parse structured JSON payload tokens safely into Pydantic model
                analysis = StockAnalysis.model_validate_json(response.text)
                
                st.markdown("---")
                st.markdown("### ⚡ AI Agent Decision Matrix")
                
                # Display action indicator badges dynamically based on enum states
                if analysis.action == "BUY":
                    st.success(f"🎯 RECOMMENDED ACTION: {analysis.action}")
                elif analysis.action == "SELL":
                    st.error(f"⚠️ RECOMMENDED ACTION: {analysis.action}")
                else:
                    st.warning(f"⚖️ RECOMMENDED ACTION: {analysis.action}")
                    
                # Technical Assessment Details Display cards
                st.metric(label="Model Evaluation Confidence", value=f"{analysis.confidence_score * 100:.1f}%")
                st.metric(label="AI Projected Target Price", value=f"\${analysis.target_price:,.2f}")
                
                st.info(f"**Agent Rationale:** {analysis.justification}")
                
                with st.expander("🔍 View Raw JSON Audit Payload"):
                    st.json(response.text)
                    
            except Exception as e:
                st.error(f"Error executing AI generation engine block: {e}")
    else:
        st.caption("Awaiting analysis sequence initialization framework. Click the button above to begin.")
