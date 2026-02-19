from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import os
import importlib.util
import sys
import logging
import ast
from filelock import FileLock
from backend.core.events import event_bus

logger = logging.getLogger("QLM.Strategy")

class Strategy(ABC):
    """
    Abstract Base Class for QLM Strategies.
    """
    def __init__(self, parameters: Dict[str, Any] = None):
        self.parameters = parameters or {}

    def set_parameters(self, params: Dict[str, Any]):
        self.parameters.update(params)

    @abstractmethod
    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]: pass

    @abstractmethod
    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series: pass

    @abstractmethod
    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series: pass

    def exit_long_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized exit signal for Long positions.
        Required for Fast Mode execution.
        Returns a boolean Series where True indicates an exit signal.
        """
        return pd.Series(False, index=df.index)

    def exit_short_signal(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        """
        Vectorized exit signal for Short positions.
        Required for Fast Mode execution.
        Returns a boolean Series where True indicates an exit signal.
        """
        return pd.Series(False, index=df.index)

    @abstractmethod
    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool: pass

    @abstractmethod
    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]: pass

    def position_size(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        return pd.Series(1.0, index=df.index, dtype=float)

class StrategyLoader:
    """
    Handles loading, saving, and versioning of strategies.
    Strategies are stored in `strategies/{name}/v{version}.py`.
    """
    
    def __init__(self, strategy_dir: str = "strategies"):
        self.strategy_dir = strategy_dir
        if not os.path.exists(strategy_dir):
            os.makedirs(strategy_dir)

    def list_strategies(self) -> List[Dict[str, Any]]:
        strategies = []
        if not os.path.exists(self.strategy_dir):
            return []
            
        for name in os.listdir(self.strategy_dir):
            path = os.path.join(self.strategy_dir, name)
            if os.path.isdir(path):
                versions = self._get_versions(name)
                latest = max(versions) if versions else 0

                # Parse metadata from latest version
                metadata = {}
                if latest > 0:
                    code = self.get_strategy_code(name, latest)
                    if code:
                        metadata = self._parse_metadata(code)

                strategies.append({
                    "name": name,
                    "versions": versions,
                    "latest_version": latest,
                    "metadata": metadata
                })
        return strategies

    def _parse_metadata(self, code: str) -> Dict[str, str]:
        """
        Extract metadata from Strategy class docstring.
        Format expected: Key: Value (e.g., Author: John Doe)
        """
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits Strategy
                    is_strategy = False
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'Strategy':
                            is_strategy = True
                            break

                    if is_strategy and ast.get_docstring(node):
                        doc = ast.get_docstring(node)
                        meta = {}
                        for line in doc.split('\n'):
                            if ':' in line:
                                key, val = line.split(':', 1)
                                meta[key.strip().lower()] = val.strip()
                        return meta
            return {}
        except:
            return {}

    def _get_versions(self, name: str) -> List[int]:
        path = os.path.join(self.strategy_dir, name)
        if not os.path.exists(path):
            return []
        
        versions = []
        for f in os.listdir(path):
            if f.startswith("v") and f.endswith(".py"):
                try:
                    v = int(f[1:-3])
                    versions.append(v)
                except ValueError:
                    pass
        return sorted(versions)

    def save_strategy(self, name: str, code: str) -> int:
        """
        Save a new version of the strategy. Returns the new version number.
        Uses FileLock to ensure atomic writes.
        Notifies EventBus.
        """
        # Security Check: Validate imports
        self._validate_code(code)
        
        path = os.path.join(self.strategy_dir, name)
        if not os.path.exists(path):
            os.makedirs(path)
        
        lock_path = os.path.join(path, ".lock")
        lock = FileLock(lock_path, timeout=10)

        with lock:
            versions = self._get_versions(name)
            new_version = (max(versions) if versions else 0) + 1

            filename = f"v{new_version}.py"
            filepath = os.path.join(path, filename)

            with open(filepath, "w") as f:
                f.write(code)

            # Notify
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                uri = f"qlm://strategy/{name}"
                loop.create_task(event_bus.notify_resource_update(uri))
            except:
                pass

            return new_version

    def get_strategy_code(self, name: str, version: int = None) -> Optional[str]:
        if version is None:
            versions = self._get_versions(name)
            if not versions:
                return None
            version = max(versions)
            
        filepath = os.path.join(self.strategy_dir, name, f"v{version}.py")
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r") as f:
            return f.read()

    def load_strategy_class(self, name: str, version: int) -> Optional[type[Strategy]]:
        """
        Load the Strategy class from the file.
        """
        filepath = os.path.join(self.strategy_dir, name, f"v{version}.py")
        if not os.path.exists(filepath):
            return None
            
        # Unique module name to avoid conflicts
        module_name = f"strategies.{name}.v{version}"
        
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Failed to execute strategy module: {e}")
            raise e
            
        # Find class inheriting from Strategy
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Strategy) and attr is not Strategy:
                return attr
                
        return None

    def _validate_code(self, code: str):
        """
        Enhanced AST validation to block dangerous imports and system calls.
        """
        tree = ast.parse(code)

        # Allowed Root Modules
        SAFE_MODULES = {
            'math', 'numpy', 'pandas', 'typing', 'datetime', 'collections',
            'itertools', 'functools', 'random', 'statistics', 'scipy', 'sklearn',
            'talib', 'backend'
        }

        # Blocked sub-modules (even if root is safe)
        BLOCKED_SUBMODULES = {
            'backend.database', 'backend.core.system', 'backend.api'
        }

        # Dangerous Builtins
        DANGEROUS_FUNCTIONS = {
            'exec', 'eval', '__import__', 'open', 'compile', 'globals', 'locals', 'input', 'breakpoint'
        }

        for node in ast.walk(tree):
            # 1. Check Imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Handle Import vs ImportFrom
                if isinstance(node, ast.Import):
                    for n in node.names:
                        mod_name = n.name
                        root_mod = mod_name.split('.')[0]
                        if root_mod not in SAFE_MODULES:
                            raise ValueError(f"Security Violation: Import '{root_mod}' is not allowed.")
                        if any(mod_name.startswith(b) for b in BLOCKED_SUBMODULES):
                            raise ValueError(f"Security Violation: Import '{mod_name}' is restricted.")

                else:
                    # ImportFrom: from module import name
                    if not node.module: continue # Skip relative imports

                    root_mod = node.module.split('.')[0]
                    if root_mod not in SAFE_MODULES:
                        raise ValueError(f"Security Violation: Import '{root_mod}' is not allowed.")

                    if any(node.module.startswith(b) for b in BLOCKED_SUBMODULES):
                        raise ValueError(f"Security Violation: Import '{node.module}' is restricted.")

                    # Check imported names (prevent 'from backend import api')
                    for n in node.names:
                        full_name = f"{node.module}.{n.name}"
                        if any(full_name.startswith(b) for b in BLOCKED_SUBMODULES):
                            raise ValueError(f"Security Violation: Import '{full_name}' is restricted.")

            # 2. Check Function Calls
            elif isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    # Check for subprocess.call, os.system etc if module was somehow aliased
                    # But we block imports so this is secondary defense
                    pass

                if func_name and func_name in DANGEROUS_FUNCTIONS:
                    raise ValueError(f"Security Violation: Function '{func_name}' is not allowed.")

    def validate_strategy_code(self, code: str) -> Dict[str, Any]:
        """
        Validate strategy code for syntax, security, and interface compliance.
        Returns: {"valid": bool, "error": str, "message": str}
        """
        # 1. Syntax & Security Check
        try:
            self._validate_code(code) # this does AST parsing and security checks
        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax Error: {e}"}
        except ValueError as e:
            return {"valid": False, "error": f"Security Violation: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation Error: {e}"}

        # 2. Interface Check (Static Analysis via AST)
        try:
            tree = ast.parse(code)
            
            # Find the class inheriting from Strategy
            strategy_class_node = None
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Check bases
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'Strategy':
                            strategy_class_node = node
                            break
            
            if not strategy_class_node:
                return {"valid": False, "error": "No class inheriting from 'Strategy' found."}
            
            # Check required methods
            required_methods = {
                'define_variables', 
                'entry_long', 
                'entry_short', 
                'exit', 
                'risk_model'
            }
            implemented_methods = set()
            
            for item in strategy_class_node.body:
                if isinstance(item, ast.FunctionDef):
                    implemented_methods.add(item.name)
            
            missing = required_methods - implemented_methods
            if missing:
                return {"valid": False, "error": f"Missing required methods: {', '.join(missing)}"}
            
        except Exception as e:
             return {"valid": False, "error": f"Analysis Error: {e}"}

        # 3. Runtime Simulation
        import uuid
        temp_name = f"temp_validate_{uuid.uuid4().hex}"
        temp_path = os.path.join(self.strategy_dir, f"{temp_name}.py")
        
        try:
            # Write to temp file
            with open(temp_path, "w") as f:
                f.write(code)
                
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(f"strategies.{temp_name}", temp_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"strategies.{temp_name}"] = module
            spec.loader.exec_module(module)
            
            # Find Strategy Class
            strategy_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Strategy) and attr is not Strategy:
                    strategy_cls = attr
                    break
            
            if not strategy_cls:
                 return {"valid": False, "error": "Could not load Strategy class."}

            # Instantiate
            strat_instance = strategy_cls()
            
            # Create Robust Dummy Data
            dates = pd.date_range(start="2023-01-01", periods=20, freq="h")
            
            # Scenario 1: Normal Data
            df_norm = pd.DataFrame({
                "open": [100.0]*20, "high": [105.0]*20, "low": [95.0]*20, "close": [100.0]*20, "volume": [1000.0]*20,
                "datetime": dates, "dtv": dates.astype('int64')
            })

            # Scenario 2: Edge Cases (NaNs, Zeros)
            df_edge = df_norm.copy()
            df_edge.loc[5:10, ['open', 'high', 'low', 'close']] = np.nan
            df_edge.loc[11:15, 'volume'] = 0.0

            for df in [df_norm, df_edge]:
                # Run Methods & Check Returns
                vars_dict = strat_instance.define_variables(df)
                if not isinstance(vars_dict, dict):
                     return {"valid": False, "error": "Runtime Error: define_variables must return a Dict"}

                # Entries
                longs = strat_instance.entry_long(df, vars_dict)
                if not isinstance(longs, pd.Series) or longs.dtype != bool:
                     return {"valid": False, "error": "Runtime Error: entry_long must return a Boolean Series"}

                shorts = strat_instance.entry_short(df, vars_dict)
                if not isinstance(shorts, pd.Series) or shorts.dtype != bool:
                     return {"valid": False, "error": "Runtime Error: entry_short must return a Boolean Series"}

                # Check Vectorized Exits (Fast Mode)
                ex_l = strat_instance.exit_long_signal(df, vars_dict)
                if not isinstance(ex_l, pd.Series) or ex_l.dtype != bool:
                     return {"valid": False, "error": "Runtime Error: exit_long_signal must return a Boolean Series"}

                # Risk
                risk = strat_instance.risk_model(df, vars_dict)
                if not isinstance(risk, dict):
                     return {"valid": False, "error": "Runtime Error: risk_model must return a Dict"}

                # Exit (Simulate an active trade)
                dummy_trade = {
                    "entry_time": dates[0],
                    "entry_price": 100.0,
                    "direction": "long",
                    "sl": 90.0,
                    "tp": 110.0,
                    "current_idx": 5
                }
                try:
                    should_exit = strat_instance.exit(df, vars_dict, dummy_trade)
                    if not isinstance(should_exit, (bool, np.bool_)):
                         return {"valid": False, "error": "Runtime Error: exit must return a boolean"}
                except Exception as e:
                    return {"valid": False, "error": f"Runtime Error in exit(): {str(e)}"}
            
            return {"valid": True, "message": "Strategy Validated & Simulated Successfully (Passed Normal & Edge Cases)."}
            
        except Exception as e:
            return {"valid": False, "error": f"Runtime Error: {str(e)}"}
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if f"strategies.{temp_name}" in sys.modules:
                del sys.modules[f"strategies.{temp_name}"]

    def delete_strategy(self, name: str):
        """
        Delete a strategy and all its versions.
        """
        import shutil
        path = os.path.join(self.strategy_dir, name)
        if os.path.exists(path):
            shutil.rmtree(path)
        else:
            raise FileNotFoundError(f"Strategy {name} not found")
