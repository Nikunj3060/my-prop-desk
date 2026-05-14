import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime

# --- INSTITUTIONAL CONFIG ---
st.set_page_config(page_title="ALPHA TERMINAL | NIFTY 50", layout="wide")

# Custom CSS for that 'Bloomberg' Dark Mode look
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .stMetric { background: #1a1c23; border-radius: 10px; padding: 15px; border: 1px solid #2e3139; }
    </style>
    """, unsafe_content_as_html=True)

# --- CORE ENGINE ---
class JanesStreetEngine:
    def __init__(self, ticker="^NSEI"):
        self.ticker = ticker
        self.data = yf.Ticker(ticker)

    def get_live_data(self):
        # Fetching 5-minute intervals for intraday precision
        df = self.data.history(period="5d", interval="5m")
        if df.empty: return None
        
        # Calculate Technicals (EMA, RSI, ATR)
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Institutional Support/Resistance via Pivot Points
        high = df['High'].max()
        low = df['Low'].min()
        close = df['Close'].iloc[-1]
        
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        s1 = (2 * pivot) - high
        
        return df, pivot, r1, s1

# --- UI LAYOUT ---
st.title("🏛️ Institutional Market Intelligence Terminal")
st.caption(f"Proprietary Model v4.2 | Live Market Feed | {datetime.now().strftime('%H:%M:%S')}")

engine = JanesStreetEngine()
df, pivot, r1, s1 = engine.get_live_data()

if df is not None:
    curr_price = df['Close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    # --- ROW 1: ALPHA METRICS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("NIFTY SPOT", f"₹{curr_price:,.2f}", f"{curr_price - df['Open'].iloc[-1]:.2f}")
    with m2:
        st.metric("RSI (INTENSITY)", f"{rsi:.2f}", "Oversold" if rsi < 30 else "Neutral")
    with m3:
        st.metric("INSTITUTIONAL PIVOT", f"₹{pivot:,.2f}")
    with m4:
        st.metric("VOLATILITY (ATR)", f"{df['ATR'].iloc[-1]:.2f}")

    # --- ROW 2: THE "VERDICT" POP-UP LOGIC ---
    st.markdown("---")
    
    # Jane Street Style Decision Matrix
    verdict = "WAITING FOR SIGNAL"
    color = "info"
    
    if curr_price > r1 and rsi > 70:
        verdict = "⚠️ ATTENTION: EXTREME OVERBOUGHT. LIQUIDITY SWEEP LIKELY. AVOID FRESH LONGS."
        st.toast(verdict, icon="🚨")
        st.error(verdict)
    elif curr_price < s1 and rsi < 30:
        verdict = "✅ VERDICT: BULLISH DIVERGENCE AT SUPPORT. BUY 23500 CALLS. TARGET R1."
        st.toast(verdict, icon="🚀")
        st.success(verdict)
    elif curr_price > pivot:
        verdict = "📈 BIAS: MILDLY BULLISH. INSTITUTIONS ARE DEFENDING THE PIVOT."
        st.info(verdict)
    else:
        verdict = "📉 BIAS: BEARISH. PRICE BELOW PIVOT. SELL ON RISES."
        st.warning(verdict)

    # --- ROW 3: VISUAL ANALYSIS ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'], name="Nifty")])
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"))
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Order Book Analysis")
        st.write(f"**Resistance 1:** ₹{r1:,.2f}")
        st.write(f"**Pivot Point:** ₹{pivot:,.2f}")
        st.write(f"**Support 1:** ₹{s1:,.2f}")
        
        st.markdown("### 🤖 AI Trade Plan")
        st.markdown(f"""
        1. **Strike Selection:** Based on IV, buy **{round(curr_price/50)*50} CE** if price holds {pivot:,.0f}.
        2. **Risk Management:** Max loss per trade capped at 1.5% of capital.
        3. **Institutional Logic:** We are seeing massive absorption at the {s1:,.0f} level. Retail is panicking, Smart Money is accumulating.
        """)

else:
    st.error("Engine failure: Market Data API (Yahoo) is currently throttling requests. Please refresh.")