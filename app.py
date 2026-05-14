import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
from scipy.stats import norm
from datetime import datetime
import time

# --- INSTITUTIONAL CONFIG ---
st.set_page_config(page_title="QUANT DESK | NIFTY 50", layout="wide")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .stMetric { background: #1a1c23; border-radius: 10px; padding: 15px; border: 1px solid #2e3139; }
    </style>
    """, unsafe_allow_html=True)

class QuantOptionsEngine:
    def __init__(self, ticker="^NSEI"):
        self.ticker_sym = ticker
        self.data = yf.Ticker(ticker)
        self.risk_free_rate = 0.07 # 7% India Risk-Free Rate Proxy

    # Black-Scholes Pricing Model
    def black_scholes(self, S, K, T, r, sigma, option_type='call'):
        if T <= 0 or sigma <= 0: return 0.0
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if option_type == 'call':
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    def get_full_analysis(self):
        # 1. Get Spot & Technicals
        df = self.data.history(period="5d", interval="5m")
        if df.empty: return None
        
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        spot_price = df['Close'].iloc[-1]
        
        high, low = df['High'].max(), df['Low'].min()
        pivot = (high + low + spot_price) / 3
        r1, s1 = (2 * pivot) - low, (2 * pivot) - high

        # 2. Options Data & Arbitrage Logic
        options_data = {"support": 0, "resistance": 0, "arbitrage": "None Detected", "atm_iv": 0.15}
        
        try:
            expirations = self.data.options
            if expirations:
                # Get closest expiry
                expiry_date = expirations[0]
                chain = self.data.option_chain(expiry_date)
                calls, puts = chain.calls, chain.puts
                
                # Support & Resistance based on absolute Highest OI
                options_data['resistance'] = calls.loc[calls['openInterest'].idxmax()]['strike']
                options_data['support'] = puts.loc[puts['openInterest'].idxmax()]['strike']
                
                # Time to expiry in years
                T = (datetime.strptime(expiry_date, "%Y-%m-%d") - datetime.now()).days / 365.0
                if T <= 0: T = 0.001
                
                # Find ATM Strike for Arbitrage Check
                atm_strike = min(calls['strike'], key=lambda x: abs(x - spot_price))
                atm_call = calls[calls['strike'] == atm_strike].iloc[0]
                atm_put = puts[puts['strike'] == atm_strike].iloc[0]
                
                options_data['atm_iv'] = (atm_call['impliedVolatility'] + atm_put['impliedVolatility']) / 2
                
                # Calculate Theoretical Values
                theo_call = self.black_scholes(spot_price, atm_strike, T, self.risk_free_rate, atm_call['impliedVolatility'], 'call')
                theo_put = self.black_scholes(spot_price, atm_strike, T, self.risk_free_rate, atm_put['impliedVolatility'], 'put')
                
                # Put-Call Parity Arbitrage Check: C - P = S - K*e^(-rt)
                fwd_price = atm_strike * np.exp(-self.risk_free_rate * T)
                synthetic_fwd = atm_call['lastPrice'] - atm_put['lastPrice']
                discrepancy = (spot_price - fwd_price) - synthetic_fwd
                
                if abs(discrepancy) > 20: # 20 point threshold for slippage/fees
                    options_data['arbitrage'] = f"YES - Mispricing of ₹{abs(discrepancy):.2f} at {atm_strike} Strike"
                    
                options_data['theo_call'] = theo_call
                options_data['theo_put'] = theo_put
                options_data['atm_strike'] = atm_strike
                options_data['call_last'] = atm_call['lastPrice']
                options_data['put_last'] = atm_put['lastPrice']
                
        except Exception as e:
            options_data['error'] = "Live Options Data Unavailable from Yahoo."

        return df, pivot, r1, s1, spot_price, options_data

# --- UI EXECUTION ---
st.title("🏛️ Quantitative Prop Desk | Derivatives & Flow")
st.caption(f"Engine v5.0 | Live Feed | {datetime.now().strftime('%H:%M:%S')}")

engine = QuantOptionsEngine()
with st.spinner("Calculating Greeks and Institutional Flow..."):
    data_bundle = engine.get_full_analysis()

if data_bundle:
    df, pivot, r1, s1, spot_price, opt = data_bundle
    rsi = df['RSI'].iloc[-1]
    
    # --- ROW 1: CORE MARKET ---
    st.subheader("Market Microstructure")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("NIFTY SPOT", f"₹{spot_price:,.2f}")
    with m2: st.metric("INSTITUTIONAL PIVOT", f"₹{pivot:,.2f}")
    with m3: st.metric("OI RESISTANCE (Call Wall)", f"₹{opt.get('resistance', 'N/A')}")
    with m4: st.metric("OI SUPPORT (Put Wall)", f"₹{opt.get('support', 'N/A')}")

    # --- ROW 2: OPTIONS THEORETICAL MISPRICING ---
    st.markdown("---")
    st.subheader("Black-Scholes Mispricing & Arbitrage Scanner")
    if 'error' not in opt and 'atm_strike' in opt:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"**ATM Strike Selected:** {opt['atm_strike']} CE")
            st.write(f"Live Premium: ₹{opt['call_last']:.2f}")
            st.write(f"Theoretical Premium: ₹{opt['theo_call']:.2f}")
            call_diff = opt['call_last'] - opt['theo_call']
            st.caption(f"Diff: {'Overvalued' if call_diff > 0 else 'Undervalued'} by ₹{abs(call_diff):.2f}")
            
        with c2:
            st.warning(f"**ATM Strike Selected:** {opt['atm_strike']} PE")
            st.write(f"Live Premium: ₹{opt['put_last']:.2f}")
            st.write(f"Theoretical Premium: ₹{opt['theo_put']:.2f}")
            put_diff = opt['put_last'] - opt['theo_put']
            st.caption(f"Diff: {'Overvalued' if put_diff > 0 else 'Undervalued'} by ₹{abs(put_diff):.2f}")

        with c3:
            st.error(f"**Arbitrage Opportunity (Put-Call Parity):**")
            st.write(f"**{opt['arbitrage']}**")
            st.caption("Note: Live arbitrage checks require zero-latency feeds. Yahoo data may reflect stale spreads.")
    else:
        st.error("Options chain data currently throttled by exchange feed.")

    # --- ROW 3: AI VERDICT ---
    st.markdown("---")
    if spot_price > opt.get('resistance', r1) and rsi > 70:
        st.error("⚠️ VERDICT: PRICE AT OI RESISTANCE. HEAVY CALL WRITERS TRAPPED. PREPARE FOR GAMMA SQUEEZE.")
    elif spot_price < opt.get('support', s1) and rsi < 30:
        st.success(f"✅ VERDICT: PRICE AT OI SUPPORT. PUT WRITERS DEFENDING. BUY {opt.get('support')} CALLS.")
    else:
        st.info("📉 VERDICT: MARKET IN PREMIUM DECAY (THETA) ZONE. BEST PLAY IS SHORT STRANGLES OUTSIDE OI WALLS.")

    # --- ROW 4: CHART ---
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_20'], line=dict(color='orange', width=1), name="EMA 20"))
    if opt.get('support') > 0:
        fig.add_hline(y=opt['support'], line_dash="dash", line_color="green", annotation_text="Put Wall")
    if opt.get('resistance') > 0:
        fig.add_hline(y=opt['resistance'], line_dash="dash", line_color="red", annotation_text="Call Wall")
    
    fig.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Market Data API Lag Detected. Refreshing...")

# --- AUTO REFRESH PROTOCOL ---
st.caption("⏳ Desk auto-refreshing in 60 seconds to prevent API throttling...")
time.sleep(60)
st.rerun()
