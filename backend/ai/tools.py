import json
import logging
from typing import List, Dict, Any, Optional
from backend.core.strategy import StrategyLoader
from backend.core.store import MetadataStore
from backend.core.engine import BacktestEngine
from backend.ai.analytics import calculate_market_structure, optimize_strategy
import os
import shutil
import pandas as pd

logger = logging.getLogger("QLM.AI.Tools")

class AITools:
    """
    Registry of tools available to the AI Agent.
    """
    def __init__(self):
        self.strategy_loader = StrategyLoader()
        self.metadata_store = MetadataStore()
        
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
            }
        ]

    async def execute(self, tool_name: str, args: Dict) -> Any:
        """
        Execute a tool by name with arguments.
        """
        logger.info(f"Executing tool: {tool_name} with args: {list(args.keys())}")
        
        try:
            if tool_name == "list_datasets":
                return self.metadata_store.list_datasets()
                
            elif tool_name == "list_strategies":
                return self.strategy_loader.list_strategies()
                
            elif tool_name == "get_strategy_code":
                name = args.get("name")
                code = self.strategy_loader.get_strategy_code(name)
                if code:
                    return {"found": True, "code": code}
                return {"found": False, "error": "Strategy not found"}
                
            elif tool_name == "create_strategy":
                name = args.get("name")
                code = args.get("code")
                
                # First validate
                validation = self.strategy_loader.validate_strategy_code(code)
                if not validation.get("valid"):
                    return {"status": "failed", "validation": validation}
                
                # If valid, save
                version = self.strategy_loader.save_strategy(name, code)
                return {"status": "success", "version": version, "message": f"Strategy {name} saved (v{version})."}
            
            elif tool_name == "validate_strategy":
                code = args.get("code")
                return self.strategy_loader.validate_strategy_code(code)
                
            elif tool_name == "run_backtest":
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                
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

                    # Return Summary Metrics
                    return {
                        "status": "success",
                        "metrics": result['metrics'],
                        "trade_count": len(result['trades'])
                    }
                except Exception as e:
                    return {"error": f"Backtest runtime error: {str(e)}"}

            elif tool_name == "get_market_data":
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                datasets = self.metadata_store.list_datasets()
                dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)

                if not dataset:
                    return {"error": "Dataset not found"}

                df = pd.read_parquet(dataset['file_path'])
                head = df.head(10).to_dict(orient='records')
                return {"data": head}

            elif tool_name == "read_file":
                path = args.get("path")
                if ".." in path or path.startswith("/"):
                    return {"error": "Invalid path"}
                if not (path.startswith("strategies/") or path.startswith("logs/")):
                    return {"error": "Access denied. Only strategies/ and logs/ allowed."}
                if not os.path.exists(path):
                    return {"error": "File not found"}
                with open(path, "r") as f:
                    return {"content": f.read()}

            elif tool_name == "write_file":
                path = args.get("path")
                content = args.get("content")
                if ".." in path or path.startswith("/"):
                    return {"error": "Invalid path"}
                if not (path.startswith("strategies/") or path.startswith("logs/")):
                    return {"error": "Access denied. Only strategies/ and logs/ allowed."}
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                return {"status": "success", "message": f"File {path} written."}

            elif tool_name == "delete_entity":
                type_ = args.get("type")
                id_ = args.get("id")
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

            elif tool_name == "analyze_market_structure":
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                datasets = self.metadata_store.list_datasets()
                dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)
                if not dataset:
                    return {"error": "Dataset not found"}
                df = pd.read_parquet(dataset['file_path'])
                return calculate_market_structure(df)

            elif tool_name == "optimize_parameters":
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                param_grid = args.get("param_grid")
                datasets = self.metadata_store.list_datasets()
                dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)
                if not dataset:
                    return {"error": "Dataset not found"}
                return optimize_strategy(strat_name, dataset['id'], param_grid)
            
            else:
                return {"error": f"Tool '{tool_name}' not found."}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Execution failed: {str(e)}"}
