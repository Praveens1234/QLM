import time
import pandas as pd
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from backend.core.engine import BacktestEngine
from backend.core.data import DataManager
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader
import os
import uuid

# Configure Logging
from backend.utils.logging import configure_logging
configure_logging()
logger = logging.getLogger("QLM.StressTest")

def generate_synthetic_data(rows=100000) -> str:
    """Generate a large Parquet file for testing."""
    logger.info(f"Generating synthetic dataset with {rows} rows...")
    dates = pd.date_range(start="2020-01-01", periods=rows, freq="1min", tz="UTC")

    # Random walk
    returns = np.random.normal(0, 0.001, rows)
    price_path = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        "datetime": dates,
        "dtv": dates.astype(np.int64),
        "open": price_path,
        "high": price_path * 1.001,
        "low": price_path * 0.999,
        "close": price_path,
        "volume": np.random.randint(100, 10000, rows)
    })

    # Save via DataManager manual path (hacky but effective for test)
    dm = DataManager()
    path = os.path.join(dm.data_dir, f"stress_test_{uuid.uuid4()}.parquet")

    # PyArrow Schema
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df)
    pq.write_table(table, path)

    # Register
    store = MetadataStore()
    ds_id = str(uuid.uuid4())
    store.add_dataset({
        "id": ds_id,
        "symbol": "STRESS",
        "timeframe": "1M",
        "detected_tf_sec": 60,
        "start_date": str(dates[0]),
        "end_date": str(dates[-1]),
        "row_count": rows,
        "file_path": path,
        "created_at": str(dates[0])
    })

    return ds_id

def run_stress_test(n_concurrent=20, n_rows=500000):
    ds_id = generate_synthetic_data(n_rows)
    strategy_name = "StressTestStrat" # Assumes v1.py exists from previous step

    logger.info(f"Starting Stress Test: {n_concurrent} concurrent backtests on {n_rows} rows.")

    start_time = time.time()

    def _task(i):
        engine = BacktestEngine()
        try:
            res = engine.run(ds_id, strategy_name, use_fast=True)
            return True
        except Exception as e:
            logger.error(f"Task {i} failed: {e}")
            return False

    with ThreadPoolExecutor(max_workers=n_concurrent) as executor:
        futures = [executor.submit(_task, i) for i in range(n_concurrent)]
        results = [f.result() for f in as_completed(futures)]

    duration = time.time() - start_time
    success_count = sum(results)

    logger.info(f"Stress Test Complete.")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info(f"Throughput: {n_concurrent * n_rows / duration:.0f} rows/sec")
    logger.info(f"Success Rate: {success_count}/{n_concurrent}")

    if success_count == n_concurrent:
        print("✅ STRESS TEST PASSED")
    else:
        print("❌ STRESS TEST FAILED")

if __name__ == "__main__":
    run_stress_test()
