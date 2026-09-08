import numpy as np
from typing import Dict, List


class SyntheticRFQGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.pairs = ["EUR/USD", "GBP/USD", "USD/INR"]
        self.tiers = ["retail", "corporate", "institutional"]
        self.tier_weights = [0.5, 0.35, 0.15]
        self.notional_ranges = {
            "retail": (1000, 100000),
            "corporate": (50000, 1000000),
            "institutional": (500000, 10000000),
        }

    def generate_rfq(self) -> Dict:
        pair = self.rng.choice(self.pairs)
        tier = self.rng.choice(self.tiers, p=self.tier_weights)
        min_n, max_n = self.notional_ranges[tier]
        notional = np.exp(self.rng.uniform(np.log(min_n), np.log(max_n)))
        notional = max(min_n, min(max_n, notional * (1 + self.rng.normal(0, 0.1))))

        return {"pair": pair, "tier": tier, "notional": round(notional, 2)}

    def generate_batch(self, n: int = 100) -> List[Dict]:
        return [self.generate_rfq() for _ in range(n)]
