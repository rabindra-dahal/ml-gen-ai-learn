import streamlit as st
import os
import random
import datetime
import sqlite3
import pandas as pd
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. Page Configuration & Environment Setup
st.set_page_config(page_title="GenAI Trading Terminal", page_icon="📈", layout="wide")
load_dotenv()

@st.cache_resource
def get_gemini_client():
    return genai.Client()

try:
    client = get_gemini_client()
except Exception as e:
    st.error("Failed to initialize Gemini Client. Check your GEMINI_API_KEY in the .env file.")
    st.stop()

# 2. Database Initialization (Portfolio & Ledger Layer)
DB_FILE = "trading_simulator.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            ticker TEXT PRIMARY KEY,
            shares REAL,
            avg_cost REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ticker TEXT,
            action TEXT,
            shares REAL,
            price REAL,
            total_value REAL
        )
    """)
    cursor.execute("SELECT shares FROM portfolio WHERE ticker = 'CASH'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO portfolio VALUES ('CASH', 100000.00, 1.0)")
    conn.commit()
    conn.close()

init_db()

def get_portfolio():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM portfolio", conn)
    conn.close()
    return df

def execute_trade(ticker: str, action: str, shares: float, price: float):
    if shares <= 0: return False
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT shares FROM portfolio WHERE ticker = 'CASH'")
    cash = cursor.fetchone()[0]
    total_cost = shares * price
    
    cursor.execute("SELECT shares, avg_cost FROM portfolio WHERE ticker = ?", (ticker,))
    asset = cursor.fetchone()
    current_shares = asset[0] if asset else 0.0
    current_avg_cost = asset[1] if asset else 0.0
    
    timestamp = datetime.datetime.now().isoformat()
    
    if action == "BUY":
        if cash < total_cost:
            conn.close()
            return False
        cursor.execute("UPDATE portfolio SET shares = shares - ? WHERE ticker = 'CASH'", (total_cost,))
        new_shares = current_shares + shares
        new_avg_cost = ((current_shares * current_avg_cost) + total_cost) / new_shares
        cursor.execute("INSERT OR REPLACE INTO portfolio VALUES (?, ?, ?)", (ticker, new_shares, new_avg_cost))
        
    elif action == "SELL":
        if current_shares < shares:
            conn.close()
            return False
        cursor.execute("UPDATE portfolio SET shares = shares + ? WHERE ticker = 'CASH'", (total_cost,))
        new_shares = current_shares - shares
        if new_shares == 0:
            cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
        else:
            cursor.execute("INSERT OR REPLACE INTO portfolio VALUES (?, ?, ?)", (ticker, new_shares, current_avg_cost))
            
    cursor.execute("INSERT INTO transaction_ledger (timestamp, ticker, action, shares, price, total_value) VALUES (?, ?, ?, ?, ?, ?)",
                   (timestamp, ticker, action, shares, price, total_cost))
    conn.commit()
    conn.close()
    return True

# 3. Pydantic Structured Output Schema
class AutomatedTradeDecision(BaseModel):
    action: str = Field(description="Must be exactly one of: 'BUY', 'SELL', or 'HOLD'")
    confidence_score: float = Field(description="Confidence scale metrics from 0.0 to 1.0")
    shares_to_transact: float = Field(description="Recommended quantity of shares to trade (0 if action is HOLD). Max 10 per turn.")
    justification: str = Field(description="Technical rationale referencing price vectors, news parameters, SMA, and RSI indicator states.")

# 4. Math Engine: Advanced Technical Indicators Generator
def generate_market_data_with_indicators(ticker: str, trend: str):
    now = datetime.datetime.now()
    dates = [now - datetime.timedelta(days=i) for i in range(40)][::-1]
    base_price = 220.0 if ticker == "AAPL" else (430.0 if ticker == "MSFT" else 180.0)
    
    prices = []
    current_price = base_price
    for _ in range(40):
        change_pct = random.uniform(-0.02, 0.02)
        if trend == "Bullish": change_pct += 0.006
        elif trend == "Bearish": change_pct -= 0.006
        current_price *= (1 + change_pct)
        prices.append(round(current_price, 2))
        
    df = pd.DataFrame({"Date": dates, "Price": prices})
    df["5_Day_SMA"] = df["Price"].rolling(window=5).mean().round(2)
    
    delta = df["Price"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI_14"] = (100 - (100 / (1 + rs))).round(2)
    
    news_pool = {
        "Bullish": [f"Institutional whales aggressively accumulating {ticker} block shares.", f"Next-gen compute upgrades position {ticker} to dominate enterprise market segments."],
        "Bearish": [f"Macro tightening yields broad resistance across tech giants like {ticker}.", f"Supply disruptions limit structural growth horizons for {ticker} products."],
        "Flat": [f"{ticker} operations align perfectly with current baseline guidance.", f"Market analysts expect standard range-bound oscillation loops for {ticker} this week."]
    }
    
    return df.dropna().tail(30).reset_index(drop=True), random.sample(news_pool[trend], 2)

# 5. Dashboard Grid UI Layout Architecture
st.title("📈 Enterprise GenAI Algorithmic Trading Terminal")
st.markdown("This dashboard integrates live technical metrics and a secure SQLite asset ledger to simulate AI broker workflows.")

col_market, col_portfolio = st.columns(2, gap="large")

st.sidebar.header("🕹️ Controls Interface")
ticker_choice = st.sidebar.selectbox("Target Security Asset", ["AAPL", "MSFT", "GOOGL"])
market_environment = st.sidebar.radio("Simulated Trend Engine", ["Bullish", "Bearish", "Flat"])

history_df, news_feed = generate_market_data_with_indicators(ticker_choice, market_environment)
current_spot_price = history_df["Price"].iloc[-1]
current_sma = history_df["5_Day_SMA"].iloc[-1]
current_rsi = history_df["RSI_14"].iloc[-1]

with col_market:
    st.subheader(f"📊 Market Analytics Matrix: {ticker_choice}")
    
    k1, k2, k3 = st.columns(3)
    k1.metric(label="Live Spot Price", value=f"${current_spot_price:,.2f}")
    k2.metric(label="5-Day SMA Indicator", value=f"${current_sma:,.2f}", delta=round(current_spot_price - current_sma, 2))
    k3.metric(label="Relative Strength Index (RSI-14)", value=str(current_rsi), 
              delta="Oversold (<30)" if current_rsi < 30 else ("Overbought (>70)" if current_rsi > 70 else "Neutral"))
    
    st.markdown("#### 🔄 Stock Price & 5-Day SMA Convergence Chart")
    st.line_chart(data=history_df, x="Date", y=["Price", "5_Day_SMA"], color=["#00CC96", "#AB63FA"], width='stretch')
    
    st.write("#### 📰 Captured Sentiment Context Input Streams")
    for item in news_feed:
        st.info(f"📰 {item}")

with col_portfolio:
    st.subheader("💼 Active Simulated Vault Portfolio Ledger")
    
    portfolio_df = get_portfolio()
    cash_balance = portfolio_df[portfolio_df["ticker"] == "CASH"]["shares"].values[0]
    
    st.metric(label="Simulated Cash Liquid Runway Balance", value=f"${cash_balance:,.2f}")
    st.markdown("##### Current Holdings Assets Allocation Ledger Table")
    st.dataframe(portfolio_df[portfolio_df["ticker"] != "CASH"], width='stretch', hide_index=True)
    
    st.markdown("---")
    st.subheader("🤖 GenAI Fund Broker Execution Desk")
    st.caption("Prompt the autonomous system framework to review metrics logs and execute asset database modifications.")
    
    if st.button("⚡ Run Autonomous Strategy Loop Lifecycle", width='stretch'):
        system_instruction = """
        You are an institutional algorithmic execution agent. Your objective is to run portfolio optimizations.
        Analyze numerical indicators (SMA variations and RSI oscillators) alongside structural textual news vectors.
        Output your transaction commands inside the strictly required JSON response schemas.
        """
        
        agent_prompt = f"""
        Asset Ticker Identity: {ticker_choice}
        Current Spot Market Value: ${current_spot_price}
        Calculated 5-Day Simple Moving Average (SMA): ${current_sma}
        Calculated Relative Strength Index (RSI-14): {current_rsi}
        Live Contextual Headlines: {news_feed}
        Available Investment Liquidity: ${cash_balance}
        
        Evaluate the data criteria above and provide your decision.
        """
        
        with st.spinner("Executing model verification loops..."):
            try:
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=agent_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=AutomatedTradeDecision,
                    )
                )
                
                decision = AutomatedTradeDecision.model_validate_json(response.text)
                
                st.markdown("#### ⚡ Broker Response Matrix Logs")
                if decision.action == "BUY":
                    st.success(f"🚀 Execution Command Issued: {decision.action} {decision.shares_to_transact} shares.")
                elif decision.action == "SELL":
                    st.error(f"⚠️ Execution Command Issued: {decision.action} {decision.shares_to_transact} shares.")
                else:
                    st.warning(f"⚖️ Execution Command Issued: {decision.action} (No transactions logged).")
                    
                st.info(f"**Execution Agent Reasoning Narrative:** {decision.justification}")
                
                if decision.action in ["BUY", "SELL"] and decision.shares_to_transact > 0:
                    trade_success = execute_trade(ticker_choice, decision.action, decision.shares_to_transact, current_spot_price)
                    if trade_success:
                        st.toast(f"Database write completed successfully! Logged {decision.action} to storage ledger.", icon="💾")
                        st.rerun()
                    else:
                        st.error("Trade transaction blocked by Database constraint rules.")
                        
            except Exception as e:
                st.error(f"Error executing AI trading loop: {e}")
                
    with st.expander("📜 View Audit Trails Transaction Logs Ledger"):
        conn = sqlite3.connect(DB_FILE)
        ledger_df = pd.read_sql_query("SELECT * FROM transaction_ledger ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(ledger_df, width='stretch', hide_index=True)
