import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional
from datetime import datetime

from .fractional_diff import fractional_differentiate

logger = logging.getLogger(__name__)


class FeatureEngine:
    def __init__(
        self, volatility_window: int = 24, frac_d: float = 0.5, frac_window: int = 20
    ):
        self.volatility_window = volatility_window
        self.frac_d = frac_d
        self.frac_window = frac_window
        self.price_history = {pair: [] for pair in ["EUR/USD", "GBP/USD", "USD/INR"]}
        self.return_history = {pair: [] for pair in ["EUR/USD", "GBP/USD", "USD/INR"]}

    def update_price(self, pair: str, price: float):
        if pair not in self.price_history:
            return
        self.price_history[pair].append(price)
        if len(self.price_history[pair]) > 100:
            self.price_history[pair] = self.price_history[pair][-100:]
        if len(self.price_history[pair]) >= 2:
            ret = (price - self.price_history[pair][-2]) / self.price_history[pair][-2]
            self.return_history[pair].append(ret)
            if len(self.return_history[pair]) > 100:
                self.return_history[pair] = self.return_history[pair][-100:]

    def get_volatility(self, pair: str) -> float:
        if len(self.return_history[pair]) < self.volatility_window:
            return 0.001
        return np.std(self.return_history[pair][-self.volatility_window :])

    def get_normalized_volatility(self, pair: str) -> float:
        vol = self.get_volatility(pair)
        return np.clip((vol - 0.0005) / (0.01 - 0.0005), 0, 1)

    def get_fractional_feature(self, pair: str) -> float:
        if len(self.price_history[pair]) < self.frac_window:
            return self.price_history[pair][-1] if self.price_history[pair] else 1.0
        series = pd.Series(self.price_history[pair][-self.frac_window :])
        diff, _ = fractional_differentiate(series, self.frac_d, self.frac_window)
        return diff.iloc[-1] if not diff.empty else series.iloc[-1]

    def get_features(self, pair: str, notional: float) -> Dict:
        return {
            "bias": 1.0,
            "volatility": self.get_normalized_volatility(pair),
            "log_notional": np.log(max(notional, 1)),
            "raw_volatility": self.get_volatility(pair),
            "frac_feature": self.get_fractional_feature(pair),
            "current_price": self.price_history[pair][-1]
            if self.price_history[pair]
            else 1.0,
        }

    def get_feature_vector(self, pair: str, notional: float, tier: str) -> np.ndarray:
        features = self.get_features(pair, notional)
        tier_map = {"retail": 0, "corporate": 1, "institutional": 2}
        tier_idx = tier_map.get(tier.lower(), 0)
        tier_onehot = [0, 0, 0]
        tier_onehot[tier_idx] = 1
        pair_map = {"EUR/USD": 0, "GBP/USD": 1, "USD/INR": 2}
        pair_idx = pair_map.get(pair, 0)
        pair_onehot = [0, 0, 0]
        pair_onehot[pair_idx] = 1
        return np.array(
            [
                1.0,
                features["volatility"],
                features["log_notional"],
                *tier_onehot,
                *pair_onehot,
            ]
        )
