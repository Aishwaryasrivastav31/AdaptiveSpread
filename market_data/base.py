from abc import ABC, abstractmethod
from typing import Optional, List, Dict
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    @abstractmethod
    def get_current_price(self, pair: str) -> float:
        pass

    @abstractmethod
    def get_historical_candles(
        self, pair: str, interval: str = "1min", count: int = 100
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_latest_quote(self, pair: str) -> Dict:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_supported_pairs(self) -> List[str]:
        pass


class MarketDataCache:
    def __init__(self, ttl_seconds: int = 30):
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if (datetime.now() - timestamp).seconds < self.ttl:
                return data
        return None

    def set(self, key: str, data: Dict):
        self.cache[key] = (data, datetime.now())
