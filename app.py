import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from datetime import datetime

# --- INSTITUTIONAL CONFIG ---
st.set_page_config(page_title="ALPHA TERMINAL | NIFTY 50", layout="wide")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .stMetric { background: #1a1c23; border-radius: 10px; padding: 15px; border: 1px solid #2e3139; }
    </style>
    """, unsafe_allow_html=True)

class JanesStreetEngine:
    def __init__(self, ticker="^NSEI"):
        self.ticker = ticker
        self.data = yf.Ticker(ticker)

    def get_live_data(self):
        df = self.data.history(period="5d", interval="5m")
        if df.empty: return None
        
        # Updated to use the stable 'ta' library
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        
        high, low, close = df['High'].max(), df['Low'].min(), df['Close'].iloc[-1]
        pivot = (high + low + close) / 3
        r1, s1 = (2 * pivot) - low, (2 * pivot) - high
        return df, pivot, r1, s1

st.title("🏛️ Institutional Market Intelligence Terminal")
st.caption(f"Proprietary Model v4.2 | Live Market Feed | {datetime.now().strftime('%H:%M:%S')}")

engine = JanesStreetEngine()
data_bundle = engine.get_live_data()

if data_bundle is not None:
    df, pivot, r1, s1 = data_bundle
    curr_price, rsi = df['Close'].iloc[-1], df['RSI'].iloc[-1]
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("NIFTY SPOT", f"₹{curr_price:,.2f}", f"{curr_price - df['Open'].iloc[-1]:.2f}")
    with m2: st.metric("RSI (INTENSITY)", f"{rsi:.2f}", "Oversold" if rsi < 30 else "Neutral")
    with m3: st.metric("INSTITUTIONAL PIVOT", f"₹{pivot:,.2f}")
    with m4: st.metric("VOLATILITY (ATR)", f"{df['ATR'].iloc[-1]:.2f}")

    st.markdown("---")
    if curr_price > r1 and rsi > 70:
        st.error("⚠️ ATTENTION: EXTREME OVERBOUGHT. LIQUIDITY SWEEP LIKELY.")
        st.toast("🚨 ALERT: REVERSAL RISK", icon="🚨")
    elif curr_price < s1 and rsi < 30:
        st.success("✅ VERDICT: BULLISH DIVERGENCE. BUY 23500 CALLS.")
        st.toast("🚀 ALERT: BUY SIGNAL", icon="🚀")
    else:
        st.info("📉 BIAS: MARKET CONSOLIDATING AT PIVOT.")

    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"))
    fig.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Market Data API Lag Detected. Refreshing...")
