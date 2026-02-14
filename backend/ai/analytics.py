import pandas as pd
import numpy as np

def calculate_market_structure(df: pd.DataFrame) -> dict:
    """
    Calculate basic market structure metrics:
    - Trend (SMA 50 vs 200)
    - Volatility (ATR 14)
    - Support/Resistance (Pivot Points)
    - RSI 14
    """
    if len(df) < 200:
        return {"error": "Not enough data (minimum 200 rows)"}

    # Trend
    sma50 = df['close'].rolling(50).mean().iloc[-1]
    sma200 = df['close'].rolling(200).mean().iloc[-1]
    trend = "Bullish" if sma50 > sma200 else "Bearish"

    # Volatility (ATR)
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    volatility_pct = (atr / close.iloc[-1]) * 100

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]

    # Support/Resistance (Simple Pivot High/Low)
    # Just take min/max of last 50 periods
    support = low.tail(50).min()
    resistance = high.tail(50).max()

    return {
        "trend": trend,
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "volatility_atr": round(atr, 4),
        "volatility_pct": round(volatility_pct, 2),
        "rsi": round(rsi, 2),
        "support_50": round(support, 2),
        "resistance_50": round(resistance, 2),
        "current_price": round(close.iloc[-1], 2)
    }

def optimize_strategy(strategy_name: str, dataset_id: str, param_grid: dict):
    """
    Stub for grid search optimization.
    In a real system, this would modify strategy code or parameters dynamically.
    For now, return a placeholder suggestion.
    """
    return {
        "message": f"Optimization for {strategy_name} on {dataset_id} initiated (Simulation).",
        "best_params": {k: v[0] for k, v in param_grid.items()}, # Placeholder
        "improvement": "+5.2%"
    }
