# dashboard/streamlit_app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="AdaptiveSpread Dashboard", layout="wide")
st.title("📊 AdaptiveSpread Dashboard")

mode = st.sidebar.radio("Mode", ["REAL-TIME", "SIMULATION"])

st.sidebar.markdown("---")
st.sidebar.subheader("New RFQ")

with st.sidebar.form("rfq_form"):
    pair = st.selectbox("Pair", ["EUR/USD", "GBP/USD", "USD/INR"])
    tier = st.selectbox("Tier", ["retail", "corporate", "institutional"])
    notional = st.number_input("Notional (USD)", min_value=1000, value=100000)
    submitted = st.form_submit_button("Get Quote")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Status", "🟢 Online", "System Ready")
with col2:
    st.metric("Mode", mode, "Active")
with col3:
    st.metric("Data Source", "Live" if mode == "REAL-TIME" else "Synthetic", "OK")

if submitted:
    with st.spinner("Generating quote..."):
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/quote",
                json={"pair": pair, "tier": tier, "notional": notional},
                timeout=10,
            )
            if response.status_code == 200:
                quote = response.json()
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Pair", quote["pair"])
                with c2:
                    st.metric("Spread", f"{quote['spread_bps']} bps")
                with c3:
                    st.metric("Bid", f"{quote['bid']:.5f}")
                with c4:
                    st.metric("Ask", f"{quote['ask']:.5f}")

                if st.button("✅ Accept"):
                    outcome = requests.post(
                        "http://localhost:8000/api/v1/outcome",
                        json={"rfq_id": quote["rfq_id"], "accepted": True},
                    )
                    if outcome.status_code == 200:
                        st.success("Outcome recorded!")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Charts
col1, col2 = st.columns(2)
with col1:
    data = {
        "Spread": [2, 5, 8, 12, 16, 20, 25, 35, 45],
        "Count": np.random.randint(1, 30, 9),
    }
    st.plotly_chart(
        px.bar(pd.DataFrame(data), x="Spread", y="Count", title="Spread Distribution"),
        use_container_width=True,
    )

with col2:
    data = {
        "Pair": ["EUR/USD", "GBP/USD", "USD/INR"],
        "Revenue": np.random.uniform(100, 200, 3),
    }
    st.plotly_chart(
        px.bar(pd.DataFrame(data), x="Pair", y="Revenue", title="Revenue by Pair"),
        use_container_width=True,
    )

st.caption("AdaptiveSpread — Real-time FX Adaptive Pricing System")
