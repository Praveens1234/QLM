
import json
import logging
from typing import List, Dict, Any, Optional
from backend.core.strategy import StrategyLoader
from backend.core.store import MetadataStore
from backend.core.engine import BacktestEngine

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
                # Case insensitive match for symbol and timeframe
                dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)
                
                if not dataset:
                    available = [f"{d['symbol']} ({d['timeframe']})" for d in datasets]
                    return {"error": f"Dataset {symbol} {tf} not found. Available: {', '.join(available)}"}
                
                engine = BacktestEngine()
                
                try:
                    # Run backtest (synchronous for now, but in async func)
                    # Note: engine.run reads file, which is blocking, but it's fast enough for local or should be run in executor if needed.
                    result = engine.run(dataset['id'], strat_name)

                    # Return Summary Metrics
                    return {
                        "status": "success",
                        "metrics": result['metrics'],
                        "trade_count": len(result['trades'])
                    }
                except Exception as e:
                    return {"error": f"Backtest runtime error: {str(e)}"}
            
            else:
                return {"error": f"Tool '{tool_name}' not found."}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Execution failed: {str(e)}"}
