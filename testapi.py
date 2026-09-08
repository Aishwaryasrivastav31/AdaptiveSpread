import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()


def test_api():
    """Test Twelve Data API connection"""
    api_key = os.getenv("TWELVE_DATA_API_KEY")

    if not api_key:
        print("❌ No API key found!")
        print("📝 Steps:")
        print("1. Get free API key from https://twelvedata.com")
        print("2. Add to .env: TWELVE_DATA_API_KEY=your_key")
        return False

    print(f"✅ API key: {api_key[:8]}...")

    # Test price
    print("\n📊 Testing price fetch...")
    resp = requests.get(
        f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={api_key}", timeout=10
    )
    data = resp.json()

    if "price" in data:
        price = float(data["price"])
        print(f"✅ EUR/USD: {price:.5f}")
        print("\n✅ API is WORKING! Live data available.")
        return True
    else:
        print(f"❌ Error: {data}")
        return False


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
