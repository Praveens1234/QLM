import numpy as np
from numba import jit, float64, int64

@jit(nopython=True, cache=True)
def sma_numba(arr: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Simple Moving Average (SMA).
    """
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return out

    # First value
    sum_val = 0.0
    for i in range(period):
        sum_val += arr[i]
    out[period-1] = sum_val / period

    # Rolling window
    for i in range(period, n):
        sum_val += arr[i] - arr[i-period]
        out[i] = sum_val / period

    return out

@jit(nopython=True, cache=True)
def ema_numba(arr: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Exponential Moving Average (EMA).
    """
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return out

    alpha = 2.0 / (period + 1.0)

    # Initialize with SMA for the first valid point
    sum_val = 0.0
    for i in range(period):
        sum_val += arr[i]
    out[period-1] = sum_val / period

    # Calculate EMA
    for i in range(period, n):
        out[i] = (arr[i] - out[i-1]) * alpha + out[i-1]

    return out

@jit(nopython=True, cache=True)
def rsi_numba(arr: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Relative Strength Index (RSI).
    """
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)

    if n < period + 1:
        return out

    # Calculate gains and losses
    deltas = np.diff(arr)

    avg_gain = 0.0
    avg_loss = 0.0

    # First period
    for i in range(period):
        val = deltas[i]
        if val > 0:
            avg_gain += val
        else:
            avg_loss -= val # Make positive

    avg_gain /= period
    avg_loss /= period

    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - (100.0 / (1.0 + rs))

    # Subsequent values (Wilder's Smoothing)
    for i in range(period + 1, n):
        val = deltas[i-1]
        gain = val if val > 0 else 0.0
        loss = -val if val < 0 else 0.0

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - (100.0 / (1.0 + rs))

    return out

@jit(nopython=True, cache=True)
def atr_numba(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """
    Calculate Average True Range (ATR).
    """
    n = len(close)
    out = np.full(n, np.nan, dtype=np.float64)
    tr = np.zeros(n, dtype=np.float64)

    if n < period + 1:
        return out

    # Calculate TR
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, max(hc, lc))

    # Calculate ATR (Wilder's Smoothing)
    sum_tr = 0.0
    for i in range(period):
        sum_tr += tr[i]
    out[period-1] = sum_tr / period

    for i in range(period, n):
        out[i] = (out[i-1] * (period - 1) + tr[i]) / period

    return out

@jit(nopython=True, cache=True)
def rolling_max_numba(arr: np.ndarray, period: int) -> np.ndarray:
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out

    for i in range(period - 1, n):
        max_val = -np.inf
        for j in range(period):
            if arr[i-j] > max_val:
                max_val = arr[i-j]
        out[i] = max_val
    return out

@jit(nopython=True, cache=True)
def rolling_min_numba(arr: np.ndarray, period: int) -> np.ndarray:
    n = len(arr)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out

    for i in range(period - 1, n):
        min_val = np.inf
        for j in range(period):
            if arr[i-j] < min_val:
                min_val = arr[i-j]
        out[i] = min_val
    return out
