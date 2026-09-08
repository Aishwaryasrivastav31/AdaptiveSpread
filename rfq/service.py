# rfq/service.py - COMPLETE FIXED VERSION
import logging
import numpy as np
from datetime import datetime

from market_data.twelve_data import TwelveDataProvider
from features.feature_engine import FeatureEngine
from pricing.linucb import LinUCB
from pricing.guardrails import Guardrails, Quote
from storage.database import db

logger = logging.getLogger(__name__)


class RFQService:
    def __init__(self):
        self.market_data = TwelveDataProvider()
        self.feature_engine = FeatureEngine()
        self.guardrails = Guardrails()
        self.spread_arms = [2, 5, 8, 12, 16, 20, 25, 35, 45]

        # ✅ FIXED: d=9
        self.bandit = LinUCB(arms=self.spread_arms, alpha=1.0, d=9)

        # Try to load existing model (if any)
        try:
            self.bandit.load_from_file("model_state.pkl")
        except:
            logger.info("No existing model found, starting fresh")

        self.mode = "SIMULATION"

    def process_rfq(self, request: dict, rfq_id: str):
        pair = request["pair"]
        notional = request["notional"]
        tier = request["tier"]

        quote_data = self.market_data.get_latest_quote(pair)
        mid_price = quote_data["mid"]

        self.feature_engine.update_price(pair, mid_price)
        x = self.feature_engine.get_feature_vector(pair, notional, tier)

        arm_idx, spread_bps = self.bandit.select_arm(x)
        volatility = self.feature_engine.get_volatility(pair)

        quote = Quote(
            pair=pair,
            mid_price=mid_price,
            spread_bps=spread_bps,
            bid=mid_price - spread_bps / 20000,
            ask=mid_price + spread_bps / 20000,
            model="LinUCB",
            volatility=volatility,
            notional=notional,
            tier=tier,
        )

        final_quote = self.guardrails.apply(quote, request)

        # ✅ FIXED: Convert all NumPy types to Python types
        context = {
            "rfq_id": rfq_id,
            "pair": pair,
            "notional": float(notional),
            "tier": tier,
            "arm_idx": int(arm_idx),
            "feature_vector": [float(v) for v in x.tolist()],
            "spread_bps": float(spread_bps),
            "final_spread_bps": float(final_quote.spread_bps),
            "volatility": float(volatility),
            "mid_price": float(mid_price),
            "timestamp": datetime.now().isoformat(),
        }

        db.store_rfq(
            rfq_id,
            request,
            {
                "spread_bps": float(spread_bps),
                "final_spread_bps": float(final_quote.spread_bps),
                "mid_price": float(mid_price),
            },
            context,
        )

        return final_quote, context

    def calculate_reward(self, quoted_spread: float, accepted: bool) -> float:
        if not accepted:
            return 0.0
        spread_norm = min(quoted_spread / 45.0, 1.0)
        reward = 0.1 + 0.8 * (1 / (1 + np.exp(-4 * (spread_norm - 0.4))))
        return float(np.clip(reward, 0, 1))  # ✅ Convert to float

    def update_model(self, context: dict, arm_idx: int, reward: float):
        x = np.array(context["feature_vector"])
        self.bandit.update(arm_idx, x, float(reward))  # ✅ Convert to float
        self.bandit.save_to_file("model_state.pkl")
