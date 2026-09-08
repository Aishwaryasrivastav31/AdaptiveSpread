import numpy as np


def true_accept_prob(
    spread_bps: float, tier: str, notional: float, volatility: float, pair: str
) -> float:
    tier_effects = {"retail": 0.0, "corporate": 0.15, "institutional": 0.30}
    pair_effects = {"EUR/USD": 0.0, "GBP/USD": -0.05, "USD/INR": -0.10}

    z = (
        0.8
        - 0.08 * spread_bps
        + tier_effects.get(tier, 0)
        + pair_effects.get(pair, 0)
        - np.log(max(notional, 1)) * 0.02
        + volatility * 5
    )

    prob = 1 / (1 + np.exp(-z / 2))
    return np.clip(prob + np.random.normal(0, 0.05), 0.01, 0.99)


def simulate_outcome(
    spread_bps: float, tier: str, notional: float, volatility: float, pair: str
) -> bool:
    return np.random.random() < true_accept_prob(
        spread_bps, tier, notional, volatility, pair
    )
