import pytest
import os
import shutil
import asyncio
import pandas as pd
from backend.database import db
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.ai.config_manager import AIConfigManager
from backend.ai.memory import JobManager

@pytest.fixture(scope="module")
def setup_system():
    # Use a fresh test DB
    test_db = "data/integration_test.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    original_path = db.db_path
    db.db_path = test_db
    db._init_schema()

    # Create temp data dir
    data_dir = "tests/data_integration"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)

    # Create temp strategy dir
    strat_dir = "tests/strategies_integration"
    if os.path.exists(strat_dir):
        shutil.rmtree(strat_dir)
    os.makedirs(strat_dir)

    yield {
        "data_dir": data_dir,
        "strat_dir": strat_dir
    }

    # Cleanup
    db.db_path = original_path
    if os.path.exists(test_db):
        os.remove(test_db)
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    if os.path.exists(strat_dir):
        shutil.rmtree(strat_dir)

def test_full_flow(setup_system):
    # 1. Initialize Components with test paths
    dm = DataManager(data_dir=setup_system["data_dir"])
    sl = StrategyLoader(strategy_dir=setup_system["strat_dir"])
    ms = MetadataStore() # uses db
    engine = BacktestEngine()
    engine.data_manager = dm # inject
    engine.strategy_loader = sl # inject

    # 2. Ingest Data
    csv_path = os.path.join(setup_system["data_dir"], "test.csv")
    with open(csv_path, "w") as f:
        f.write("datetime,open,high,low,close,volume\n")
        # Generate 100 candles
        for i in range(100):
            dt = pd.Timestamp("2023-01-01") + pd.Timedelta(hours=i)
            f.write(f"{dt},100,105,95,100,1000\n")

    meta = dm.process_upload(csv_path, "TEST", "1H")
    ms.add_dataset(meta)

    # Verify DB
    ds_list = ms.list_datasets()
    assert len(ds_list) == 1
    assert ds_list[0]['symbol'] == "TEST"

    # 3. Create Strategy
    strat_code = """
from backend.core.strategy import Strategy
import pandas as pd
class MyStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars): return pd.Series([True] + [False]*(len(df)-1))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return True
    def risk_model(self, df, vars): return {}
"""
    sl.save_strategy("MyStrat", strat_code)

    # 4. Run Backtest
    result = engine.run(meta['id'], "MyStrat")
    assert result['status'] == 'success'
    assert result['metrics']['total_trades'] == 1

    # 5. Fail-Safe Check
    broken_code = """
from backend.core.strategy import Strategy
class Broken(Strategy):
    def define_variables(self, df): raise ValueError("Crash")
    def entry_long(self, df, vars): return None
    def entry_short(self, df, vars): return None
    def exit(self, df, vars, trade): return None
    def risk_model(self, df, vars): return None
"""
    sl.save_strategy("BrokenStrat", broken_code)

    fail_result = engine.run(meta['id'], "BrokenStrat")
    assert fail_result['status'] == 'failed'
    assert "Crash" in fail_result['error']

    # 6. Job Persistence Check
    jm = JobManager()
    jm.start_job("session_test", "Audit")
    jm.update_job("session_test", "Done")

    ctx = jm.get_job_context("session_test")
    assert "Audit" in ctx
    assert "Done" in ctx
