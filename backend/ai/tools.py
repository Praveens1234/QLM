
import json
import logging
from typing import List, Dict, Any, Optional
from backend.core.strategy import StrategyLoader
from backend.core.data import DataManager
# We might need to import the Engine, but running backtest might be complex if it's long running.
# For now, let's implement strategy management tools first.

logger = logging.getLogger("QLM.AI.Tools")

class AITools:
    """
    Registry of tools available to the AI Agent.
    """
    def __init__(self):
        self.strategy_loader = StrategyLoader()
        self.data_manager = DataManager()
        
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
                            "code": {"type": "string", "description": "Complete Python code for the strategy"}
                        },
                        "required": ["name", "code"]
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
                            "timeframe": {"type": "string", "description": "Timeframe (e.g. 1H)"},
                            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD), optional"},
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD), optional"}
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
        logger.info(f"Executing tool: {tool_name} with args: {args.keys()}")
        
        try:
            if tool_name == "list_datasets":
                return self.data_manager.list_datasets()
                
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
                from backend.core.engine import BacktestEngine
                from backend.core.metrics import MetricEngine
                import pandas as pd
                
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                
                # Load Strategy
                strat_class = self.strategy_loader.load_strategy_class(strat_name, version=args.get("version", 0))
                # For simplicity, if version is 0 (default in load_strategy_class logic?) or logic handles it.
                # Actually StrategyLoader.load_strategy_class takes version. 
                # If version is 0 or None, we need to find latest.
                # Let's check StrategyLoader.load_strategy_class signature.
                # It takes (name, version).
                # Wait, if version is missing, we should look it up.
                # But to keep it simple, let's assume latest if not provided.
                if not strat_class:
                     # Try to find latest version
                     versions = self.strategy_loader._get_versions(strat_name)
                     if not versions:
                         return {"error": f"Strategy {strat_name} not found"}
                     strat_class = self.strategy_loader.load_strategy_class(strat_name, versions[-1])
                
                if not strat_class:
                    return {"error": f"Could not load strategy class for {strat_name}"}

                # Load Data
                # DataManager.load_dataset(symbol, timeframe) returns df
                df = self.data_manager.load_dataset(symbol, tf)
                if df is None:
                    return {"error": f"Dataset {symbol} {tf} not found"}
                
                # Filter by date if provided
                if args.get("start_date"):
                    df = df[df['datetime'] >= args.get("start_date")]
                if args.get("end_date"):
                    df = df[df['datetime'] <= args.get("end_date")]
                    
                if df.empty:
                    return {"error": "Dataset is empty after filtering"}

                # Run Backtest
                engine = BacktestEngine()
                strategy = strat_class()
                
                # We need a progress callback? For AI tool, probably not needed or just log.
                trade_log = engine.run(df, strategy)
                
                # Calculate Metrics
                metrics_engine = MetricEngine()
                report = metrics_engine.calculate(trade_log)
                
                # Return Summary
                return {
                    "status": "success",
                    "metrics": {
                        "net_profit": report.get("net_profit", 0),
                        "win_rate": report.get("win_rate", 0),
                        "sharpe_ratio": report.get("sharpe_ratio", 0),
                        "total_trades": report.get("total_trades", 0),
                        "max_drawdown": report.get("max_drawdown_pct", 0)
                    },
                    "trade_count": len(trade_log)
                }
            
            else:
                return {"error": f"Tool '{tool_name}' not found."}
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": f"Execution failed: {str(e)}"}
