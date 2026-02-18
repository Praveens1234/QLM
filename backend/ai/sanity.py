import pandas as pd
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.core.exceptions import QLMError

logger = logging.getLogger("QLM.Sanity")

def generate_noise_data(original_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate synthetic OHLC data by shuffling returns.
    Preserves volatility distribution but destroys serial correlation (trend).
    """
    df = original_df.copy()

    # Calculate returns
    returns = df['close'].pct_change().fillna(0).values

    # Shuffle returns
    np.random.shuffle(returns)

    # Reconstruct Price
    start_price = df['close'].iloc[0]
    new_close = start_price * np.cumprod(1 + returns)

    # Reconstruct OHLC structure (approximate)
    # Maintain typical volatility spread
    # high_pct = (high / close) - 1
    # low_pct = (low / close) - 1
    # We can just sample these spreads from original data

    high_ratios = (df['high'] / df['close']).values
    low_ratios = (df['low'] / df['close']).values
    np.random.shuffle(high_ratios)
    np.random.shuffle(low_ratios)

    # Create new DF
    noise_df = pd.DataFrame()
    noise_df['dtv'] = df['dtv'] # Keep timestamps
    noise_df['close'] = new_close
    noise_df['open'] = noise_df['close'].shift(1).fillna(start_price)

    # Ensure High/Low validity
    # High must be >= max(open, close)
    # Low must be <= min(open, close)

    base_high = noise_df[['open', 'close']].max(axis=1)
    base_low = noise_df[['open', 'close']].min(axis=1)

    # Apply randomized spread
    noise_df['high'] = base_high * high_ratios
    noise_df['low'] = base_low * low_ratios

    # Fix inconsistencies (if spread was negative or too small)
    noise_df['high'] = np.maximum(noise_df['high'], base_high)
    noise_df['low'] = np.minimum(noise_df['low'], base_low)

    noise_df['volume'] = df['volume'] # Keep volume or shuffle? Keep for simplicity.

    return noise_df

def run_sanity_check(strategy_name: str, dataset_id: str, n_runs: int = 10) -> Dict[str, Any]:
    """
    Run the strategy on 'n_runs' synthetic noise datasets.
    If the strategy consistently profits on noise, it may be overfitted or logically flawed.
    Expected result for a Trend strategy on Noise: Loss or Breakeven (0 correlation).
    """
    try:
        engine = BacktestEngine()
        store = MetadataStore()
        metadata = store.get_dataset(dataset_id)
        if not metadata:
             raise ValueError(f"Dataset {dataset_id} not found")

        original_df = engine.data_manager.load_dataset(metadata['file_path'])

        # Load Strategy Class
        versions = engine.strategy_loader._get_versions(strategy_name)
        version = max(versions) if versions else 1
        StrategyClass = engine.strategy_loader.load_strategy_class(strategy_name, version)
        if not StrategyClass:
             raise ValueError(f"Strategy {strategy_name} not found")

        # Strategy Instance
        strategy_instance = StrategyClass()

        results = []

        def _run_noise(i):
            noise_df = generate_noise_data(original_df)
            res = engine._execute_fast(noise_df, strategy_instance)
            return res['metrics'].get('net_profit', 0.0)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_run_noise, i) for i in range(n_runs)]
            for future in futures:
                results.append(future.result())

        avg_profit_noise = np.mean(results)
        win_rate_noise = sum(1 for r in results if r > 0) / n_runs * 100

        warning = False
        if avg_profit_noise > 0 and win_rate_noise > 50:
             warning = True
             message = "Warning: Strategy profits on random noise. Likely overfitted or lucky."
        else:
             message = "Pass: Strategy performs poorly on noise (as expected)."

        return {
            "strategy": strategy_name,
            "n_runs": n_runs,
            "avg_profit_on_noise": round(avg_profit_noise, 2),
            "noise_win_rate": round(win_rate_noise, 2),
            "warning": warning,
            "message": message,
            "raw_results": results
        }

    except Exception as e:
        logger.error(f"Sanity Check failed: {e}")
        raise QLMError(f"Sanity Check failed: {str(e)}")
