import numpy as np
import pandas as pd
from typing import Tuple


def frac_diff_weights(d: float, window: int) -> np.ndarray:
    """Calculate weights for fractional differentiation"""
    if d >= 1 or d <= 0:
        raise ValueError("d must be between 0 and 1")
    weights = np.zeros(window)
    weights[0] = 1.0
    for k in range(1, window):
        weights[k] = -weights[k - 1] * (d - k + 1) / k
    return weights


def fractional_differentiate(
    series: pd.Series, d: float = 0.5, window: int = 20
) -> Tuple[pd.Series, pd.Series]:
    """Apply fractional differentiation"""
    if len(series) < window:
        window = len(series) - 1
        if window < 1:
            return series.copy(), np.array([1.0])
    weights = frac_diff_weights(d, window)
    n = len(series)
    diff_series = pd.Series(index=series.index, dtype=float)
    for i in range(window, n):
        window_data = series.iloc[i - window : i].values
        diff_series.iloc[i] = np.dot(weights, window_data)
    for i in range(min(window, n)):
        diff_series.iloc[i] = series.iloc[i]
    return diff_series, pd.Series(weights)
