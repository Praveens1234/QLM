from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import os
import importlib.util
import sys
import logging
import ast

logger = logging.getLogger("QLM.Strategy")

class Strategy(ABC):
    """
    Abstract Base Class for QLM Strategies.
    All user strategies must inherit from this class.
    """
    
    @abstractmethod
    def define_variables(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Define any mathematical transformations (indicators).
        Returns a dictionary of Series aligned with the dataframe.
        """
        pass

    @abstractmethod
    def entry_long(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        """
        Return a boolean Series for long entry signals.
        """
        pass

    @abstractmethod
    def entry_short(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        """
        Return a boolean Series for short entry signals.
        """
        pass

    @abstractmethod
    def exit(self, df: pd.DataFrame, vars: Dict[str, pd.Series], trade: Dict[str, Any]) -> bool:
        """
        Return True to exit the specific trade, False to hold.
        This is called per-trade per-candle during execution.
        Wait, for vectorization support, passing full series might be better,
        but the prompt says 'Execution is Candle-by-candle'.
        However, the interface 'exit' in prompt returns 'boolean_series or condition'.
        If it returns boolean series, it's vectorized.
        If 'condition', it might be per-candle.
        Let's support returning a Boolean Series for exits for now, as it's cleaner.
        """
        pass

    @abstractmethod
    def risk_model(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """
        Return dictionary with 'sl', 'tp', 'valid' (boolean) Series.
        """
        pass

    def position_size(self, df: pd.DataFrame, vars: Dict[str, pd.Series]) -> pd.Series:
        """
        Return a Series of position sizes.
        Default is 1.0 for all candles.
        """
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
                strategies.append({
                    "name": name,
                    "versions": versions,
                    "latest_version": max(versions) if versions else 0
                })
        return strategies

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
        """
        # Security Check: Validate imports
        self._validate_code(code)
        
        path = os.path.join(self.strategy_dir, name)
        if not os.path.exists(path):
            os.makedirs(path)
            
        versions = self._get_versions(name)
        new_version = (max(versions) if versions else 0) + 1
        
        filename = f"v{new_version}.py"
        filepath = os.path.join(path, filename)
        
        with open(filepath, "w") as f:
            f.write(code)
            
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
        Basic AST validation to block dangerous imports.
        """
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = node.names if isinstance(node, ast.Import) else [node.module]
                for alias in names:
                    mod_name = alias.name if isinstance(node, ast.Import) else alias
                    if mod_name and mod_name.split('.')[0] not in ['math', 'numpy', 'pandas', 'backend', 'typing', 'datetime']:
                        raise ValueError(f"Import '{mod_name}' is not allowed.")
            
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval', '__import__', 'open']:
                        raise ValueError(f"Function '{node.func.id}' is not allowed.")

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
                
            # return {"valid": True, "message": "Strategy is valid."} # Removed to allow Runtime Simulation
            pass
            
        except Exception as e:
             return {"valid": False, "error": f"Analysis Error: {e}"}

        # 3. Runtime Simulation
        import uuid
        import tempfile

        # Use system temp directory to avoid triggering file watchers in project root
        temp_dir = tempfile.gettempdir()
        temp_name = f"temp_validate_{uuid.uuid4().hex}"
        temp_path = os.path.join(temp_dir, f"{temp_name}.py")
        
        try:
            # Write to temp file
            with open(temp_path, "w") as f:
                f.write(code)
                
            # Load module dynamically
            # Need to ensure unique name in sys.modules
            module_name = f"temp_strategies.{temp_name}"

            spec = importlib.util.spec_from_file_location(module_name, temp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            else:
                return {"valid": False, "error": "Failed to create module spec for validation."}
            
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
            
            # Create Dummy Data
            dates = pd.date_range(start="2023-01-01", periods=10, freq="h")
            df = pd.DataFrame({
                "open": [100.0]*10, "high": [105.0]*10, "low": [95.0]*10, "close": [100.0]*10, "volume": [1000.0]*10,
                "datetime": dates,
                "dtv": dates.astype('int64')
            })
            
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
            
            return {"valid": True, "message": "Strategy Validated & Simulated Successfully."}
            
        except Exception as e:
            return {"valid": False, "error": f"Runtime Error: {str(e)}"}
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            if module_name in sys.modules:
                del sys.modules[module_name]

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
