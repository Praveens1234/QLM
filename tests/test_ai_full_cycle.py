import asyncio
import logging
import os
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
import json

from backend.ai.agent import AIAgent
from backend.core.data import DataManager
from backend.core.store import MetadataStore

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Full_Cycle_Test")

# Constants
TEST_SYMBOL = "AI_TEST_SYMBOL"
TEST_TF = "1H"
STRATEGY_NAME = "AI_Generated_SMA"

# Synthetic Strategy Code
VALID_STRATEGY_CODE = """
from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class AI_Generated_SMA(Strategy):
    def define_variables(self, df: pd.DataFrame) -> dict:
        return {
            'sma_fast': df['close'].rolling(10).mean(),
            'sma_slow': df['close'].rolling(30).mean(),
            'vol': df['close'].rolling(10).std()
        }

    def entry_long(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        return (vars['sma_fast'] > vars['sma_slow']) & (vars['sma_fast'].shift(1) <= vars['sma_slow'].shift(1))

    def entry_short(self, df: pd.DataFrame, vars: dict) -> pd.Series:
        return (vars['sma_fast'] < vars['sma_slow']) & (vars['sma_fast'].shift(1) >= vars['sma_slow'].shift(1))

    def risk_model(self, df: pd.DataFrame, vars: dict) -> dict:
        return {
            'sl': df['close'] - vars['vol'] * 2,
            'tp': df['close'] + vars['vol'] * 4
        }

    def exit(self, df: pd.DataFrame, vars: dict, trade: dict) -> bool:
        return False
"""

async def setup_data():
    """Generates synthetic data and ingests it."""
    logger.info("Step 1: Generating Synthetic Data...")

    dates = pd.date_range(start="2024-01-01", periods=500, freq="h")
    df = pd.DataFrame({
        "datetime": dates,
        "open": np.random.normal(100, 5, 500),
        "high": np.random.normal(105, 5, 500),
        "low": np.random.normal(95, 5, 500),
        "close": np.random.normal(100, 5, 500),
        "volume": np.random.randint(100, 1000, 500)
    })

    # Save to CSV
    csv_path = "temp_ai_test_data.csv"
    df.to_csv(csv_path, index=False)

    # Ingest
    dm = DataManager()
    ms = MetadataStore()

    try:
        metadata = dm.process_upload(csv_path, TEST_SYMBOL, TEST_TF)
        ms.add_dataset(metadata)
        logger.info(f"✅ Data Ingested: {metadata['id']}")
        return metadata['id'], csv_path
    except Exception as e:
        logger.error(f"Data Setup Failed: {e}")
        raise e

async def mock_llm_responses(*args, **kwargs):
    """
    Simulates the LLM's decision process (ReAct).
    Returns different responses based on the conversation history length.
    """
    messages = kwargs.get('messages', [])
    # History includes: System, User (0, 1) -> ToolCall(2) -> ToolRes(3) -> ToolCall(4)...

    # Analyze history depth to decide next step
    # 1. User Ask -> Call create_strategy
    # 2. Tool Executed -> Call validate_strategy
    # 3. Tool Executed -> Call run_backtest
    # 4. Tool Executed -> Final Answer

    tool_messages = [m for m in messages if m.get('role') == 'tool']
    assistant_messages = [m for m in messages if m.get('role') == 'assistant']

    if len(tool_messages) == 0:
        logger.info("🤖 Mock LLM: Deciding to CREATE STRATEGY")
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "I will create a simple SMA strategy for you.",
                    "tool_calls": [{
                        "id": "call_create",
                        "type": "function",
                        "function": {
                            "name": "create_strategy",
                            "arguments": json.dumps({
                                "name": STRATEGY_NAME,
                                "code": VALID_STRATEGY_CODE
                            })
                        }
                    }]
                }
            }]
        }

    elif len(tool_messages) == 1:
        logger.info("🤖 Mock LLM: Deciding to VALIDATE STRATEGY")
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Strategy saved. Now validating.",
                    "tool_calls": [{
                        "id": "call_validate",
                        "type": "function",
                        "function": {
                            "name": "validate_strategy",
                            "arguments": json.dumps({
                                "code": VALID_STRATEGY_CODE
                            })
                        }
                    }]
                }
            }]
        }

    elif len(tool_messages) == 2:
        logger.info("🤖 Mock LLM: Deciding to RUN BACKTEST")
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Validation passed. Running backtest.",
                    "tool_calls": [{
                        "id": "call_backtest",
                        "type": "function",
                        "function": {
                            "name": "run_backtest",
                            "arguments": json.dumps({
                                "strategy_name": STRATEGY_NAME,
                                "symbol": TEST_SYMBOL,
                                "timeframe": TEST_TF
                            })
                        }
                    }]
                }
            }]
        }

    else:
        logger.info("🤖 Mock LLM: FINAL ANSWER")
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "The strategy has been created, validated, and tested successfully. You can view the results in the dashboard."
                }
            }]
        }

async def run_test():
    dataset_id, csv_path = await setup_data()

    logger.info("Step 2: Initializing Agent...")
    agent = AIAgent()

    # Patch the client
    with patch.object(agent.client, 'chat_completion', side_effect=mock_llm_responses):
        logger.info("Step 3: Sending User Prompt...")
        response = await agent.chat("Please create and test an SMA strategy for AI_TEST_SYMBOL.")

        logger.info(f"Step 4: Final Response: {response}")

    # Verification
    logger.info("Step 5: Verifying Artifacts...")

    # 1. Strategy File
    strategy_path = f"strategies/{STRATEGY_NAME}/v1.py"
    if os.path.exists(strategy_path):
        logger.info(f"✅ Strategy File Created: {strategy_path}")
    else:
        logger.error(f"❌ Strategy File Missing: {strategy_path}")

    # 2. History/Jobs
    history = agent.get_history(agent.list_sessions()[0]['id'])

    # Check for specific tool outputs in history
    tools_run = [m['name'] for m in history if m.get('role') == 'tool']
    logger.info(f"Tools Executed: {tools_run}")

    if "create_strategy" in tools_run and "run_backtest" in tools_run:
        logger.info("✅ Full Cycle Tools Executed")
    else:
        logger.error("❌ Missing Tool Executions")

    # Cleanup
    logger.info("Cleanup...")
    if os.path.exists(csv_path):
        os.remove(csv_path)

    # Clean dataset
    ms = MetadataStore()
    ds = ms.get_dataset(dataset_id)
    if ds:
        if os.path.exists(ds['file_path']):
            os.remove(ds['file_path'])
        ms.delete_dataset(dataset_id)

    # Clean strategy
    if os.path.exists(f"strategies/{STRATEGY_NAME}"):
        shutil.rmtree(f"strategies/{STRATEGY_NAME}")

if __name__ == "__main__":
    asyncio.run(run_test())
