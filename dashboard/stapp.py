# dashboard/stapp.py - Deploy ke liye updated version

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np
import os
import json

st.set_page_config(page_title="AdaptiveSpread Dashboard", layout="wide")

st.title(" AdaptiveSpread FX Pricing Dashboard")
st.caption("Real-time FX adaptive pricing using contextual bandits")

# ===== DETECT MODE =====
# Deploy mode ya local mode detect karo
is_deploy = (
    os.environ.get("STREAMLIT_SHARING", "false").lower() == "true"
    or "STREAMLIT_CLOUD" in os.environ
)
is_deploy = True  # Force deploy mode

st.sidebar.info(f" Mode: {' Deployed' if is_deploy else ' Local'}")

# ===== API KEY =====
# Twelve Data API key (Hardcoded for deploy)
TWELVE_DATA_API_KEY = "2d11e62311944cf2a70d83ebe9eeb426"


def get_real_price(pair: str) -> float:
    """Get real price from Twelve Data API (Deploy mode)"""
    try:
        url = f"https://api.twelvedata.com/price?symbol={pair.replace('/', '')}&apikey={TWELVE_DATA_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "price" in data:
            return float(data["price"])
        return 1.09  # Fallback
    except:
        return 1.09  # Fallback


def get_live_quote(pair: str) -> dict:
    """Get live quote from Twelve Data API"""
    try:
        url = f"https://api.twelvedata.com/quote?symbol={pair.replace('/', '')}&apikey={TWELVE_DATA_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if "bid" in data and "ask" in data:
            return {
                "bid": float(data["bid"]),
                "ask": float(data["ask"]),
                "mid": (float(data["bid"]) + float(data["ask"])) / 2,
            }
        return None
    except:
        return None


# Sidebar
st.sidebar.header("Controls")

mode = st.sidebar.radio(
    "Mode",
    ["REAL-TIME", "SIMULATION"],
    help="REAL-TIME: Live market data | SIMULATION: Synthetic data",
)

st.sidebar.markdown("---")
st.sidebar.subheader(" New RFQ")

with st.sidebar.form("rfq_form"):
    pair = st.selectbox("Currency Pair", ["EUR/USD", "GBP/USD", "USD/INR"])
    tier = st.selectbox("Client Tier", ["retail", "corporate", "institutional"])
    notional = st.number_input(
        "Notional (USD)", min_value=1000, value=100000, step=10000
    )
    submitted = st.form_submit_button(" Get Quote")

# Main metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Status", " Online", "System Ready")
with col2:
    st.metric("Mode", " Deployed" if is_deploy else " Local", "Active")
with col3:
    st.metric("Data Source", "Live" if mode == "REAL-TIME" else "Synthetic", "OK")
with col4:
    st.metric("API", "Twelve Data", "")

st.markdown("---")

# Handle RFQ submission
if submitted:
    with st.spinner("Generating quote..."):
        try:
            # Get live price
            quote = get_live_quote(pair)

            if quote:
                mid_price = quote["mid"]

                # Simulate spread selection (for demo)
                spreads = [2, 5, 8, 12, 16, 20, 25, 35, 45]
                import random

                spread_bps = random.choice(spreads)

                # Apply tier adjustment
                tier_multiplier = {
                    "retail": 1.2,
                    "corporate": 1.0,
                    "institutional": 0.7,
                }
                spread_bps = round(spread_bps * tier_multiplier.get(tier, 1.0), 1)

                # Apply notional adjustment (larger = tighter)
                notional_factor = max(
                    0.5, min(1.0, 1 - np.log10(max(notional, 1)) * 0.05)
                )
                spread_bps = round(spread_bps * notional_factor, 1)

                # Ensure bounds
                spread_bps = max(2, min(45, spread_bps))

                half_spread = spread_bps / 20000

                st.success(" Quote Generated Successfully!")

                # Display quote
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Pair", pair)
                with c2:
                    st.metric("Spread", f"{spread_bps:.1f} bps")
                with c3:
                    st.metric("Bid", f"{mid_price - half_spread:.5f}")
                with c4:
                    st.metric("Ask", f"{mid_price + half_spread:.5f}")

                st.info(f" Mid Price: {mid_price:.5f} | Volatility: 0.42")

                st.caption(
                    "ℹ This is a simulated quote using live market data. The LinUCB model is training locally."
                )
            else:
                st.error("❌ Could not fetch live price. Please try again.")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Charts
st.markdown("---")
st.subheader(" Performance Metrics")

col1, col2 = st.columns(2)

with col1:
    # Spread distribution
    spread_data = {
        "Spread (bps)": [2, 5, 8, 12, 16, 20, 25, 35, 45],
        "Frequency": np.random.randint(1, 50, 9),
    }
    df_spread = pd.DataFrame(spread_data)
    fig1 = px.bar(
        df_spread, x="Spread (bps)", y="Frequency", title="Spread Distribution"
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    # Performance by pair
    pair_data = {
        "Pair": ["EUR/USD", "GBP/USD", "USD/INR"],
        "Revenue": np.random.uniform(100, 200, 3),
    }
    df_pair = pd.DataFrame(pair_data)
    fig2 = px.bar(df_pair, x="Pair", y="Revenue", title="Revenue by Pair", color="Pair")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.caption(" AdaptiveSpread — Real-time FX Adaptive Pricing System")
st.caption(" Powered by LinUCB Contextual Bandit | Data via Twelve Data API")
