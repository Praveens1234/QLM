import json
import logging
from typing import List, Dict, Any, Optional
from backend.core.strategy import StrategyLoader
from backend.core.store import MetadataStore
from backend.core.engine import BacktestEngine
from backend.core.data import DataManager
from backend.ai.analytics import calculate_market_structure, optimize_strategy
from backend.ai.config_manager import AIConfigManager
import os
import shutil
import pandas as pd
import asyncio
import functools
import platform
import psutil

logger = logging.getLogger("QLM.AI.Tools")

class AITools:
    """
    Registry of tools available to the AI Agent and MCP.
    """
    def __init__(self):
        self.strategy_loader = StrategyLoader()
        self.metadata_store = MetadataStore()
        self.data_manager = DataManager()
        self.config_manager = AIConfigManager()
        
    def get_definitions(self) -> List[Dict]:
        """
        Return the list of tool definitions in OpenAI format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_datasets",
                    "description": "List all available datasets (symbols and timeframes).",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_strategies",
                    "description": "List all available trading strategies.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_strategy_code",
                    "description": "Get the Python code of a specific strategy.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the strategy"},
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_strategy",
                    "description": "Create or update a trading strategy. Returns the validity of the code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Name of the strategy"},
                            "code": {"type": "string", "description": "Complete Python code for the strategy. Must include define_variables, entry_long, entry_short, risk_model, exit, and optionally position_size."}
                        },
                        "required": ["name", "code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_strategy",
                    "description": "Validate a trading strategy code without saving it.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Complete Python code for the strategy"}
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_backtest",
                    "description": "Run a backtest for a specific strategy and dataset.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {"type": "string", "description": "Name of the strategy"},
                            "symbol": {"type": "string", "description": "Symbol to test (e.g. XAUUSD)"},
                            "timeframe": {"type": "string", "description": "Timeframe (e.g. 1H)"}
                        },
                        "required": ["strategy_name", "symbol", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_market_data",
                    "description": "Fetch first 10 rows of a dataset for analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Symbol"},
                            "timeframe": {"type": "string", "description": "Timeframe"}
                        },
                        "required": ["symbol", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "import_dataset_from_url",
                    "description": "Import a dataset from a URL (CSV or ZIP).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Direct download URL"},
                            "symbol": {"type": "string", "description": "Symbol"},
                            "timeframe": {"type": "string", "description": "Timeframe"}
                        },
                        "required": ["url", "symbol", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read content of a file in strategies or logs directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path (e.g., strategies/MyStrat/v1.py)"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file in strategies or logs directory. Use with caution.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path"},
                            "content": {"type": "string", "description": "Content to write"}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_entity",
                    "description": "Delete a strategy or dataset.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["strategy", "dataset"]},
                            "id": {"type": "string", "description": "Name for strategy, ID for dataset"}
                        },
                        "required": ["type", "id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_market_structure",
                    "description": "Analyze market structure metrics (trend, volatility, support/resistance) for a dataset.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Symbol"},
                            "timeframe": {"type": "string", "description": "Timeframe"}
                        },
                        "required": ["symbol", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_parameters",
                    "description": "Run a parameter optimization (simulation) for a strategy.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {"type": "string", "description": "Name of the strategy"},
                            "symbol": {"type": "string", "description": "Symbol"},
                            "timeframe": {"type": "string", "description": "Timeframe"},
                            "param_grid": {"type": "object", "description": "Dict of parameters to optimize (e.g., {'window': [10, 20]})"}
                        },
                        "required": ["strategy_name", "symbol", "timeframe", "param_grid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "Get server health, version, and resource usage.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_ai_config",
                    "description": "Update AI provider configuration.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "provider_id": {"type": "string", "description": "Provider ID (e.g., 'openai')"},
                            "model_id": {"type": "string", "description": "Model ID (e.g., 'gpt-4')"}
                        },
                        "required": ["provider_id", "model_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tools_manifest",
                    "description": "Get detailed documentation for all available tools and QLM introduction.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    def _validate_path(self, path: str, allowed_roots: List[str] = ["strategies", "logs"]) -> str:
        """
        Validate that the path is within the allowed directories to prevent path traversal.
        """
        # Normalize and resolve absolute path
        abs_path = os.path.abspath(path)
        cwd = os.getcwd()

        valid = False
        for root in allowed_roots:
            abs_root = os.path.abspath(os.path.join(cwd, root))
            # Check if abs_path starts with abs_root
            if os.path.commonpath([abs_path, abs_root]) == abs_root:
                valid = True
                break

        if not valid:
            raise ValueError(f"Access denied: {path} is outside allowed directories ({', '.join(allowed_roots)}).")
        return abs_path

    async def _run_sync(self, func, *args, **kwargs):
        """
        Run a synchronous blocking function in the default executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))

    async def execute(self, tool_name: str, args: Dict) -> Any:
        """
        Execute a tool by name with arguments.
        """
        logger.info(f"Executing tool: {tool_name} with args: {list(args.keys())}")
        
        try:
            if tool_name == "list_datasets":
                return await self._run_sync(self.metadata_store.list_datasets)
                
            elif tool_name == "list_strategies":
                return await self._run_sync(self.strategy_loader.list_strategies)
                
            elif tool_name == "get_strategy_code":
                name = args.get("name")
                def _get():
                    code = self.strategy_loader.get_strategy_code(name)
                    if code:
                        return {"found": True, "code": code}
                    return {"found": False, "error": "Strategy not found"}
                return await self._run_sync(_get)
                
            elif tool_name == "create_strategy":
                name = args.get("name")
                code = args.get("code")
                
                def _create():
                    # First validate
                    validation = self.strategy_loader.validate_strategy_code(code)
                    if not validation.get("valid"):
                        return {"status": "failed", "validation": validation}

                    # If valid, save
                    version = self.strategy_loader.save_strategy(name, code)
                    return {"status": "success", "version": version, "message": f"Strategy {name} saved (v{version})."}
                
                return await self._run_sync(_create)
            
            elif tool_name == "validate_strategy":
                code = args.get("code")
                return await self._run_sync(self.strategy_loader.validate_strategy_code, code)
                
            elif tool_name == "run_backtest":
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                
                def _run_bt():
                    # Resolve Dataset ID
                    datasets = self.metadata_store.list_datasets()
                    dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)

                    if not dataset:
                        available = [f"{d['symbol']} ({d['timeframe']})" for d in datasets]
                        return {"error": f"Dataset {symbol} {tf} not found. Available: {', '.join(available)}"}

                    engine = BacktestEngine()

                    try:
                        # Run backtest
                        result = engine.run(dataset['id'], strat_name)

                        if result.get("status") == "failed":
                             return {
                                 "status": "failed",
                                 "error": result.get("error", "Unknown Backtest Failure")
                             }

                        # Return Summary Metrics
                        return {
                            "status": "success",
                            "metrics": result['metrics'],
                            "trade_count": len(result['trades'])
                        }
                    except Exception as e:
                        return {"error": f"Backtest runtime error: {str(e)}"}

                return await self._run_sync(_run_bt)

            elif tool_name == "get_market_data":
                symbol = args.get("symbol")
                tf = args.get("timeframe")

                def _get_data():
                    datasets = self.metadata_store.list_datasets()
                    dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)

                    if not dataset:
                        return {"error": "Dataset not found"}

                    df = pd.read_parquet(dataset['file_path'])
                    head = df.head(10).to_dict(orient='records')
                    return {"data": head}

                return await self._run_sync(_get_data)

            elif tool_name == "import_dataset_from_url":
                url = args.get("url")
                symbol = args.get("symbol")
                timeframe = args.get("timeframe")

                def _import():
                    metadata = self.data_manager.process_url(url, symbol, timeframe)
                    self.metadata_store.add_dataset(metadata)
                    return {"status": "success", "id": metadata['id'], "rows": metadata['row_count']}

                return await self._run_sync(_import)

            elif tool_name == "read_file":
                path = args.get("path")

                def _read():
                    try:
                        abs_path = self._validate_path(path)
                        if not os.path.exists(abs_path):
                            return {"error": "File not found"}
                        with open(abs_path, "r") as f:
                            return {"content": f.read()}
                    except ValueError as ve:
                         return {"error": str(ve)}

                return await self._run_sync(_read)

            elif tool_name == "write_file":
                path = args.get("path")
                content = args.get("content")

                def _write():
                    try:
                        abs_path = self._validate_path(path)
                        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                        with open(abs_path, "w") as f:
                            f.write(content)
                        return {"status": "success", "message": f"File {path} written."}
                    except ValueError as ve:
                         return {"error": str(ve)}

                return await self._run_sync(_write)

            elif tool_name == "delete_entity":
                type_ = args.get("type")
                id_ = args.get("id")

                def _delete():
                    if type_ == "strategy":
                        try:
                            self.strategy_loader.delete_strategy(id_)
                            return {"status": "success", "message": f"Strategy {id_} deleted."}
                        except Exception as e:
                             return {"error": str(e)}
                    elif type_ == "dataset":
                        try:
                            self.metadata_store.delete_dataset(id_)
                            return {"status": "success", "message": f"Dataset {id_} deleted."}
                        except Exception as e:
                             return {"error": str(e)}

                return await self._run_sync(_delete)

            elif tool_name == "analyze_market_structure":
                symbol = args.get("symbol")
                tf = args.get("timeframe")

                def _analyze():
                    datasets = self.metadata_store.list_datasets()
                    dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)
                    if not dataset:
                        return {"error": "Dataset not found"}
                    df = pd.read_parquet(dataset['file_path'])
                    return calculate_market_structure(df)

                return await self._run_sync(_analyze)

            elif tool_name == "optimize_parameters":
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                param_grid = args.get("param_grid")

                def _optimize():
                    datasets = self.metadata_store.list_datasets()
                    dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)
                    if not dataset:
                        return {"error": "Dataset not found"}
                    return optimize_strategy(strat_name, dataset['id'], param_grid)

                return await self._run_sync(_optimize)

            elif tool_name == "get_system_status":
                def _status():
                    return {
                        "status": "online",
                        "system": "QLM",
                        "version": "2.0.0",
                        "os": platform.system(),
                        "cpu_percent": psutil.cpu_percent(),
                        "memory_percent": psutil.virtual_memory().percent,
                    }
                return await self._run_sync(_status)

            elif tool_name == "update_ai_config":
                pid = args.get("provider_id")
                mid = args.get("model_id")
                def _update():
                    self.config_manager.set_active(pid, mid)
                    return {"status": "success", "message": f"Active AI set to {mid} via {pid}"}
                return await self._run_sync(_update)

            elif tool_name == "get_tools_manifest":
                def _manifest():
                    intro = """# QLM (QuantLogic Framework)
QLM is an institutional-grade algorithmic trading platform designed for quantitative researchers. It provides a robust event-driven backtester, market data management, and an AI agent for strategy development.

## Available Tools
"""
                    tools_doc = ""
                    for d in self.get_definitions():
                        fn = d['function']
                        name = fn['name']
                        desc = fn['description']
                        params = json.dumps(fn['parameters'], indent=2)
                        tools_doc += f"\n### `{name}`\n{desc}\n**Parameters**:\n```json\n{params}\n```\n"

                    return intro + tools_doc

                return await self._run_sync(_manifest)
            
            else:
                return {"error": f"Tool '{tool_name}' not found."}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Execution failed: {str(e)}"}
