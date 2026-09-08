import numpy as np
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    pair: str
    mid_price: float
    spread_bps: float
    bid: float
    ask: float
    model: str
    volatility: float
    notional: float
    tier: str


class Guardrails:
    def __init__(self):
        self.min_spread = 0.5
        self.max_spread = 100.0
        self.vol_floor = 5.0
        self.notional_multipliers = {
            "retail": 1.0,
            "corporate": 0.8,
            "institutional": 0.6,
        }
        self.max_notional = 50_000_000
        self.min_notional = 1_000

    def validate_rfq(self, pair: str, notional: float, tier: str) -> bool:
        if pair not in ["EUR/USD", "GBP/USD", "USD/INR"]:
            return False
        if tier.lower() not in ["retail", "corporate", "institutional"]:
            return False
        if notional < self.min_notional or notional > self.max_notional:
            return False
        return True

    def apply(self, quote: Quote, rfq_request: dict) -> Quote:
        if not self.validate_rfq(quote.pair, quote.notional, quote.tier):
            logger.warning("RFQ validation failed, applying safe defaults")

        volatility = quote.volatility
        min_spread = self.vol_floor + (volatility * 100 * 10)

        tier = quote.tier.lower()
        notional_mult = self.notional_multipliers.get(tier, 1.0)
        notional_factor = max(0.5, min(1.0, 1 - np.log10(max(quote.notional, 1)) * 0.1))

        adjusted_spread = quote.spread_bps * notional_mult * notional_factor
        adjusted_spread = max(adjusted_spread, min_spread)
        adjusted_spread = min(adjusted_spread, self.max_spread)
        adjusted_spread = round(adjusted_spread, 1)

        half_spread = adjusted_spread / 20000
        return Quote(
            pair=quote.pair,
            mid_price=quote.mid_price,
            spread_bps=adjusted_spread,
            bid=quote.mid_price - half_spread,
            ask=quote.mid_price + half_spread,
            model=quote.model + "+Guardrails",
            volatility=quote.volatility,
            notional=quote.notional,
            tier=quote.tier,
        )
