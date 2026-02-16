import asyncio
import pytest
import os
import shutil
import sqlite3
from backend.database import db
from backend.ai.config_manager import AIConfigManager
from backend.ai.memory import JobManager
from backend.ai.store import ChatStore
from backend.core.engine import BacktestEngine
from backend.core.store import MetadataStore
from backend.core.strategy import StrategyLoader

# Setup/Teardown
@pytest.fixture(scope="module")
def setup_db():
    # Use a test DB file
    test_db = "data/test_qlm.db"
    if os.path.exists(test_db):
        os.remove(test_db)

    # Patch Database class to use test_db?
    # Or just instantiate Database with path?
    # backend.database.db is a global instance.
    # We can't easily change it without monkeypatching or re-initializing.
    # But `db.db_path` is public.

    original_path = db.db_path
    db.db_path = test_db
    db._init_schema()

    yield

    # Teardown
    db.db_path = original_path
    if os.path.exists(test_db):
        os.remove(test_db)

def test_config_persistence(setup_db):
    cm = AIConfigManager()
    cm.add_provider("TestProv", "http://test", "sk-123")

    # Read back directly from DB to verify
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers WHERE id='testprov'")
        row = cursor.fetchone()
        assert row is not None
        assert row["base_url"] == "http://test"

def test_job_persistence(setup_db):
    jm = JobManager()
    sid = "session_123"
    jm.start_job(sid, "Win Big")
    jm.update_job(sid, "Step 1 done")

    ctx = jm.get_job_context(sid)
    assert "Win Big" in ctx
    assert "Step 1 done" in ctx

    # Verify DB
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE session_id=?", (sid,))
        row = cursor.fetchone()
        assert row["status"] == "in_progress"

def test_chat_persistence(setup_db):
    cs = ChatStore()
    sid = cs.create_session("My Chat")

    cs.add_message(sid, {"role": "user", "content": "Hello"})
    hist = cs.get_history(sid)

    assert len(hist) == 1
    assert hist[0]["content"] == "Hello"

def test_backtest_fail_safe(setup_db):
    # We need a dummy dataset and strategy
    # 1. Create dummy dataset
    ms = MetadataStore()
    ms.add_dataset({
        "id": "dummy_ds",
        "symbol": "TEST",
        "timeframe": "1H",
        "detected_tf_sec": 3600,
        "start_date": "2023-01-01",
        "end_date": "2023-01-02",
        "row_count": 100,
        "file_path": "data/dummy.parquet", # Doesn't exist, should trigger error in load
        "created_at": "2023-01-01"
    })

    engine = BacktestEngine()

    # Should fail gracefully (return dict with status=failed) not raise
    # Wait, engine.run catches Exception inside execution, but initialization (load dataset) raises?
    # Let's check engine.run code again.
    # It wraps everything in try...except:
    # except Exception as e: logger.error... raise e
    # So initialization errors ARE raised.
    # Execution errors (inside _execute) are caught and return status='failed'.

    # Let's test initialization error
    with pytest.raises(Exception):
        engine.run("dummy_ds", "Strat")

    # Now let's test execution error (e.g. strategy failure)
    # We need a real dataframe to pass init
    # Creating a dummy parquet file
    import pandas as pd
    df = pd.DataFrame({
        "open": [100.0]*10, "high": [105.0]*10, "low": [95.0]*10, "close": [100.0]*10,
        "volume": [1000]*10, "dtv": [1000000000*i for i in range(10)]
    })
    os.makedirs("data", exist_ok=True)
    df.to_parquet("data/dummy.parquet")

    # Create a broken strategy
    sl = StrategyLoader()
    code = """
from backend.core.strategy import Strategy
import pandas as pd
class BrokenStrategy(Strategy):
    def define_variables(self, df): return {}
    def entry_long(self, df, vars): return pd.Series([False]*len(df))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): raise ValueError("Boom")
    def risk_model(self, df, vars): return {}
"""
    sl.save_strategy("BrokenStrat", code)

    # Run
    # This should enter _execute, hit the error in exit(), catch it, log it, and continue?
    # In my code:
    # except Exception as e: logger.warning(...) continue
    # So it should NOT fail the backtest status, just that candle/trade.

    # Let's make it fail in define_variables (which is outside the loop)
    code_fatal = """
from backend.core.strategy import Strategy
import pandas as pd
class FatalStrategy(Strategy):
    def define_variables(self, df): raise ValueError("Fatal Boom")
    def entry_long(self, df, vars): return pd.Series([False]*len(df))
    def entry_short(self, df, vars): return pd.Series([False]*len(df))
    def exit(self, df, vars, trade): return False
    def risk_model(self, df, vars): return {}
"""
    sl.save_strategy("FatalStrat", code_fatal)

    # This should result in status="failed"
    result = engine.run("dummy_ds", "FatalStrat")
    assert result["status"] == "failed"
    assert "Fatal Boom" in result["error"]
