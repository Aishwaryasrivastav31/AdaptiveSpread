# test_multiple_rfqs.py
import requests
import random
import time
import json

print("=" * 60)
print("📊 Testing Multiple RFQs")
print("=" * 60)

test_cases = [
    {"pair": "EUR/USD", "notional": 100000, "tier": "retail"},
    {"pair": "GBP/USD", "notional": 250000, "tier": "corporate"},
    {"pair": "USD/INR", "notional": 500000, "tier": "institutional"},
    {"pair": "EUR/USD", "notional": 1000000, "tier": "institutional"},
    {"pair": "GBP/USD", "notional": 50000, "tier": "retail"},
]

print(f"\n🚀 Sending {len(test_cases)} RFQs...\n")

for i, rfq in enumerate(test_cases, 1):
    print(
        f"[{i}/{len(test_cases)}] {rfq['pair']} | {rfq['tier']} | ${rfq['notional']:,}"
    )

    try:
        response = requests.post(
            "http://localhost:8000/api/v1/quote", json=rfq, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Spread: {data['spread_bps']} bps")
            print(f"   Bid: {data['bid']:.5f} | Ask: {data['ask']:.5f}")
            print(f"   RFQ ID: {data['rfq_id'][:8]}...")

            # Random outcome (70% chance of acceptance)
            accepted = random.random() < 0.7
            outcome_response = requests.post(
                "http://localhost:8000/api/v1/outcome",
                json={"rfq_id": data["rfq_id"], "accepted": accepted},
            )

            if outcome_response.status_code == 200:
                outcome_data = outcome_response.json()
                print(
                    f"   📝 {'✅ Accepted' if accepted else '❌ Rejected'} | Reward: {outcome_data['reward']:.3f}"
                )
            else:
                print(f"   ❌ Outcome Error: {outcome_response.status_code}")

        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   {response.text[:100]}...")

    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Is server running? (python app.py)")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")

    time.sleep(0.5)  # Thoda delay
    print()

print("=" * 60)
print("✅ Test Complete!")
print("=" * 60)
