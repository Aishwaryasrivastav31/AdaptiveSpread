import os
import requests
import pandas as pd
import logging
from typing import Optional, List, Dict
from datetime import datetime
import time

from .base import MarketDataProvider, MarketDataCache

logger = logging.getLogger(__name__)

class TwelveDataProvider(MarketDataProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('TWELVE_DATA_API_KEY')
        if not self.api_key:
            logger.warning("⚠️ No API key found. Using fallback data.")
        
        self.base_url = "https://api.twelvedata.com"
        self.session = requests.Session()
        self.cache = MarketDataCache(ttl_seconds=30)
        self.supported_pairs = ["EUR/USD", "GBP/USD", "USD/INR"]
        self._available = False
        self._using_fallback = False
        
        if self.api_key:
            self._test_connection()
    
    def _test_connection(self):
        try:
            resp = self.session.get(
                f"{self.base_url}/price?symbol=EUR/USD&apikey={self.api_key}",
                timeout=10
            )
            data = resp.json()
            if 'price' in data:
                logger.info("✅ Twelve Data API connection successful!")
                self._available = True
                return True
            else:
                logger.warning(f"⚠️ API test failed: {data}")
                self._using_fallback = True
                return False
        except Exception as e:
            logger.warning(f"⚠️ API test error: {e}")
            self._using_fallback = True
            return False
    
    def get_current_price(self, pair: str) -> float:
        cache_key = f"price_{pair}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached['price']
        
        if self._using_fallback or not self.api_key:
            return self._get_fallback_price(pair)
        
        normalized = pair.replace("/", "")
        try:
            resp = self.session.get(
                f"{self.base_url}/price?symbol={normalized}&apikey={self.api_key}",
                timeout=10
            )
            data = resp.json()
            if 'price' in data:
                price = float(data['price'])
                self.cache.set(cache_key, {'price': price})
                logger.info(f"✅ Live price {pair}: {price:.5f}")
                return price
            else:
                self._using_fallback = True
                return self._get_fallback_price(pair)
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            self._using_fallback = True
            return self._get_fallback_price(pair)
    
    def _get_fallback_price(self, pair: str) -> float:
        fallback = {"EUR/USD": 1.0912, "GBP/USD": 1.2645, "USD/INR": 83.12}
        price = fallback.get(pair, 1.00)
        logger.info(f"Using fallback price {pair}: {price:.5f}")
        return price
    
    def get_latest_quote(self, pair: str) -> Dict:
        cache_key = f"quote_{pair}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        if self._using_fallback or not self.api_key:
            return self._get_fallback_quote(pair)
        
        normalized = pair.replace("/", "")
        try:
            resp = self.session.get(
                f"{self.base_url}/quote?symbol={normalized}&apikey={self.api_key}",
                timeout=10
            )
            data = resp.json()
            if 'bid' in data and 'ask' in data:
                quote = {
                    'bid': float(data['bid']),
                    'ask': float(data['ask']),
                    'mid': (float(data['bid']) + float(data['ask'])) / 2,
                    'timestamp': datetime.now().isoformat()
                }
                self.cache.set(cache_key, quote)
                logger.info(f"✅ Live quote {pair}: bid={quote['bid']:.5f}, ask={quote['ask']:.5f}")
                return quote
            else:
                self._using_fallback = True
                return self._get_fallback_quote(pair)
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            self._using_fallback = True
            return self._get_fallback_quote(pair)
    
    def _get_fallback_quote(self, pair: str) -> Dict:
        price = self._get_fallback_price(pair)
        spread = 0.0001
        return {
            'bid': price - spread,
            'ask': price + spread,
            'mid': price,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_historical_candles(self, pair: str, interval: str = "1min", count: int = 100) -> pd.DataFrame:
        if self._using_fallback or not self.api_key:
            return pd.DataFrame()
        
        normalized = pair.replace("/", "")
        try:
            resp = self.session.get(
                f"{self.base_url}/time_series",
                params={
                    'symbol': normalized,
                    'interval': interval,
                    'outputsize': count,
                    'apikey': self.api_key
                },
                timeout=10
            )
            data = resp.json()
            if 'values' in data:
                df = pd.DataFrame(data['values'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df.set_index('datetime', inplace=True)
                df = df.astype({
                    'open': float, 'high': float, 'low': float,
                    'close': float, 'volume': float
                })
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return pd.DataFrame()
    
    def is_available(self) -> bool:
        return self._available
    
    def get_supported_pairs(self) -> List[str]:
        return self.supported_pairs