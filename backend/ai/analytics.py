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

from itertools import product
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
from backend.core.data import DataManager
import logging

logger = logging.getLogger("QLM.Analytics")

def optimize_strategy(strategy_name: str, dataset_id: str, param_grid: dict):
    """
    Perform a Grid Search Optimization for the given strategy and dataset.
    Uses the Fast Backtest Engine (Numba) for performance.
    """
    try:
        # 1. Load Data (Once)
        store = MetadataStore()
        metadata = store.get_dataset(dataset_id)
        if not metadata:
            return {"error": f"Dataset {dataset_id} not found"}

        data_manager = DataManager()
        df = data_manager.load_dataset(metadata['file_path'])

        # 2. Load Strategy Class
        loader = StrategyLoader()
        versions = loader._get_versions(strategy_name)
        if not versions:
            return {"error": f"Strategy {strategy_name} not found"}

        latest_version = max(versions)
        StrategyClass = loader.load_strategy_class(strategy_name, latest_version)

        # 3. Generate Parameter Combinations
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(product(*values))

        logger.info(f"Starting optimization for {strategy_name}: {len(combinations)} combinations.")

        best_result = None
        best_pnl = -float('inf')
        best_params = {}

        results_log = []

        engine = BacktestEngine()

        # 4. Run Grid Search
        for combo in combinations:
            params = dict(zip(keys, combo))

            # Instantiate new strategy for each run to reset state
            strategy = StrategyClass()
            strategy.set_parameters(params)

            try:
                # Use Fast Engine (use_fast=True)
                # Pass callback=None for speed
                res = engine._execute(df, strategy, callback=None, use_fast=True)

                metrics = res['metrics']
                net_profit = metrics.get('net_profit', 0.0)
                trades_count = metrics.get('total_trades', 0)

                # Simple Logic: Maximize Net Profit
                # (Could be Sharpe, etc.)
                if net_profit > best_pnl:
                    best_pnl = net_profit
                    best_params = params
                    best_result = metrics

                results_log.append({
                    "params": params,
                    "metrics": metrics
                })

            except Exception as e:
                logger.warning(f"Optimization run failed for params {params}: {e}")
                continue

        if not best_result:
            return {"error": "Optimization failed to produce any valid results."}

        # Calculate Improvement (stub for baseline comparison)
        # We could run with default params to compare, but for now just return result.

        return {
            "status": "success",
            "strategy": strategy_name,
            "dataset": metadata['symbol'],
            "best_params": best_params,
            "best_metrics": best_result,
            "total_runs": len(combinations),
            "top_results": sorted(results_log, key=lambda x: x['metrics']['net_profit'], reverse=True)[:5]
        }

    except Exception as e:
        logger.error(f"Optimization Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
