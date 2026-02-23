import json
import logging
from typing import List, Dict, Any, Optional
from backend.core.strategy import StrategyLoader
from backend.core.store import MetadataStore
from backend.core.engine import BacktestEngine
from backend.core.data import DataManager
from backend.core.limiter import request_limiter
from backend.core.interceptor import mcp_safe
import os
import shutil
import pandas as pd
import asyncio
import functools
import platform
import psutil
import uuid

logger = logging.getLogger("QLM.MCP.Tools")

class MCPTools:
    """
    Registry of tools available to the MCP Client.
    Includes concurrency limits and smart error handling.
    """
    def __init__(self):
        self.strategy_loader = StrategyLoader()
        self.metadata_store = MetadataStore()
        self.data_manager = DataManager()
        self.logs_dir = "logs"
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        self._ledger_uploads = {}
        
    async def _upload_ledger_to_catbox(self, run_id: str, filepath: str):
        """Asynchronously uploads a file to Catbox.moe using curl."""
        try:
            # Manage dictionary size to prevent memory leak
            if len(self._ledger_uploads) > 50:
                oldest = list(self._ledger_uploads.keys())[0]
                del self._ledger_uploads[oldest]

            self._ledger_uploads[run_id] = {"status": "uploading", "url": None}
            
            # Execute curl
            proc = await asyncio.create_subprocess_exec(
                "curl", "-s", "-F", "reqtype=fileupload", "-F", f"fileToUpload=@{filepath}", "https://catbox.moe/user/api.php",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Set a 30 second timeout for the upload
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            
            if proc.returncode == 0:
                url = stdout.decode().strip()
                if url.startswith("https://"):
                    self._ledger_uploads[run_id] = {"status": "success", "url": url}
                    logger.info(f"Successfully uploaded ledger {run_id} to Catbox: {url}")
                else:
                    self._ledger_uploads[run_id] = {"status": "error", "error": "Invalid response from Catbox"}
                    logger.error(f"Catbox upload failed: invalid response - {url}")
            else:
                err = stderr.decode().strip()
                self._ledger_uploads[run_id] = {"status": "error", "error": err}
                logger.error(f"Catbox upload failed: {err}")
                
        except asyncio.TimeoutError:
            self._ledger_uploads[run_id] = {"status": "error", "error": "Upload timed out after 30 seconds."}
            logger.error(f"Catbox upload timed out for {run_id}")
        except Exception as e:
            self._ledger_uploads[run_id] = {"status": "error", "error": str(e)}
            logger.error(f"Catbox upload error for {run_id}: {e}")

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
                    "name": "get_strategy_coding_guidelines",
                    "description": "Get the comprehensive rules, guidelines, and syntax required to write a valid QLM trading strategy.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_backtest_ledger_url",
                    "description": "Poll the status and retrieve the Catbox.moe URL of a backtest ledger upload.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "run_id": {"type": "string", "description": "The unique run ID returned by run_backtest"}
                        },
                        "required": ["run_id"]
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
                    "name": "get_tools_manifest",
                    "description": "Get detailed documentation for all available tools and QLM introduction.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_dataset_row",
                    "description": "Search for a specific row by index or exact datetime (e.g., '2025-01-01 14:30:00+00:00') and return a window of surrounding rows.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Symbol name (e.g., XAUUSD)"},
                            "timeframe": {"type": "string", "description": "Timeframe (e.g., 1M, 1H)"},
                            "query": {"type": "string", "description": "Row index integer (e.g. '15') or exact datetime string"}
                        },
                        "required": ["symbol", "timeframe", "query"]
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

    async def _run_sync(self, func, *args, timeout: float = 120.0, **kwargs):
        """
        Run a synchronous blocking function in the default executor.
        Enforces a hard timeout to prevent zombie hangs.
        """
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, functools.partial(func, *args, **kwargs)),
            timeout=timeout
        )

    @mcp_safe
    async def execute(self, tool_name: str, args: Dict) -> Any:
        """
        Execute a tool by name with arguments.
        """
        logger.info(f"Executing tool: {tool_name} with args: {list(args.keys())}")
        
        # NOTE: Exceptions are now caught by @mcp_safe
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
            await request_limiter.acquire()
            try:
                strat_name = args.get("strategy_name")
                symbol = args.get("symbol")
                tf = args.get("timeframe")
                run_id = str(uuid.uuid4())
                
                def _run_bt():
                    # Resolve Dataset ID
                    datasets = self.metadata_store.list_datasets()
                    dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)

                    if not dataset:
                        available = [f"{d['symbol']} ({d['timeframe']})" for d in datasets]
                        return {"error": f"Dataset {symbol} {tf} not found. Available: {', '.join(available)}"}

                    engine = BacktestEngine()

                    # Run backtest (Engine now handles basic exceptions, but mcp_safe catches crashes)
                    result = engine.run(dataset['id'], strat_name)

                    if result.get("status") == "failed":
                        return {
                            "status": "failed",
                            "error": result.get("error", "Unknown Backtest Failure")
                        }

                    # Save trades to log file
                    trade_file = f"trades_{run_id}.csv"
                    trade_path = os.path.join(self.logs_dir, trade_file)
                    
                    if result['trades']:
                        pd.DataFrame(result['trades']).to_csv(trade_path, index=False)
                        
                    # Calculate advanced metrics
                    metrics = result.get('metrics', {})
                    if 'Equity Peak' in metrics and 'Return [%]' in metrics:
                         pass # These already come from Engine
                         
                    return {
                        "status": "success",
                        "run_id": run_id,
                        "metrics": metrics,
                        "trade_count": len(result['trades']),
                        "trade_log": trade_path
                    }

                bt_result = await self._run_sync(_run_bt)
                
                if bt_result.get("status") == "success" and bt_result.get("trade_count", 0) > 0:
                    # Spawn the background upload task
                    asyncio.create_task(self._upload_ledger_to_catbox(run_id, bt_result["trade_log"]))
                    bt_result["ledger_upload_status"] = "uploading"
                    bt_result["message"] = f"Trade ledger is uploading. Use get_backtest_ledger_url with run_id '{run_id}' to retrieve the URL."
                    
                return bt_result
            finally:
                request_limiter.release()

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

        elif tool_name == "inspect_dataset_row":
            symbol = args.get("symbol")
            tf = args.get("timeframe")
            query = str(args.get("query", ""))

            def _inspect_data():
                datasets = self.metadata_store.list_datasets()
                dataset = next((d for d in datasets if d['symbol'].lower() == symbol.lower() and d['timeframe'].lower() == tf.lower()), None)

                if not dataset:
                    return {"error": f"Dataset for {symbol} {tf} not found"}

                try:
                    # Look up target index
                    result = self.data_manager.inspect_dataset_row(dataset['file_path'], query)
                    target_idx = result.get('target_index')
                    
                    if target_idx is not None:
                        # Fetch the window of data around that index
                        window = self.data_manager.get_dataset_window(dataset['file_path'], target_idx)
                        return {
                            "status": "success",
                            "target": result,
                            "window": window
                        }
                    else:
                        return {"error": "Row not found matching query"}
                except Exception as ex:
                    return {"error": str(ex)}

            return await self._run_sync(_inspect_data)

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

        elif tool_name == "get_backtest_ledger_url":
            run_id = args.get("run_id")
            if run_id not in self._ledger_uploads:
                return {"error": f"Run ID {run_id} not found. The upload may have expired or the ID is invalid."}
            return self._ledger_uploads[run_id]

        elif tool_name == "get_strategy_coding_guidelines":
            def _guidelines():
                rules_path = os.path.join(os.getcwd(), "backend", "core", "strategy_rules.md")
                if not os.path.exists(rules_path):
                    return {"error": "Strategy rules document not found at " + rules_path}
                with open(rules_path, "r", encoding="utf-8") as f:
                    return {"content": f.read()}
            return await self._run_sync(_guidelines)

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
            # Self-correction: Suggest valid tools
            valid_tools = [d['function']['name'] for d in self.get_definitions()]
            return {
                "error": f"Tool '{tool_name}' not found.",
                "valid_tools": valid_tools,
                "hint": "Please check the tool name and try again."
            }
