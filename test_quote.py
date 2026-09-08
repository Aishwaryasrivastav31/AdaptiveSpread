# test_quote.py
import requests
import json

print("🚀 Sending RFQ request...")

response = requests.post(
    "http://localhost:8000/api/v1/quote",
    json={"pair": "EUR/USD", "notional": 100000, "tier": "corporate"},
)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print("\n✅ Quote received!")
    print(f"   RFQ ID: {data['rfq_id']}")
    print(f"   Pair: {data['pair']}")
    print(f"   Mid Price: {data['mid_price']:.5f}")
    print(f"   Spread: {data['spread_bps']} bps")
    print(f"   Bid: {data['bid']:.5f}")
    print(f"   Ask: {data['ask']:.5f}")
    print(f"   Volatility: {data['volatility']:.5f}")

    # Ask if want to record outcome
    record = input("\n📝 Record outcome? (y/n): ")
    if record.lower() == "y":
        outcome = requests.post(
            "http://localhost:8000/api/v1/outcome",
            json={"rfq_id": data["rfq_id"], "accepted": True},
        )
        print(f"✅ Outcome recorded! {outcome.json()}")
else:
    print(f"❌ Error: {response.text}")
