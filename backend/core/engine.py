import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import traceback # Added for self-healing
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
from backend.core.store import MetadataStore
from backend.core.fast_engine import run_numba_backtest
from backend.core.system import check_memory
from backend.core.exceptions import SystemError
from datetime import datetime

logger = logging.getLogger("QLM.Engine")

class BacktestEngine:
    """
    Core Execution Engine.
    Handles data loading, strategy instantiation, and event-driven backtesting.
    Supports both Python loop (Legacy) and Numba JIT (Fast) execution modes.
    Includes Memory Checks.
    """
    
    def __init__(self):
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()

    def run(self, dataset_id: str, strategy_name: str, version: int = None, callback=None, use_fast: bool = True, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run a backtest for a given dataset and strategy.
        Callback signature: func(progress_pct: float, message: str, data: Dict)
        """
        try:
            # 1. System Check
            if not check_memory(required_mb=256): # Require at least 256MB free
                raise SystemError("Insufficient memory to run backtest.")

            # 2. Load Dataset
            store = MetadataStore()
            metadata = store.get_dataset(dataset_id)
            if not metadata:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            # Check row count for huge datasets
            est_size_mb = (metadata.get('row_count', 0) * 8 * 10) / (1024 * 1024) # Approx 80 bytes/row
            if not check_memory(required_mb=int(est_size_mb * 1.5)): # 1.5x buffer
                raise SystemError(f"Dataset requires approx {int(est_size_mb)}MB RAM, but system is low on memory.")

            df = self.data_manager.load_dataset(metadata['file_path'])
            logger.info(f"Loaded dataset {metadata['symbol']} with {len(df)} rows.")

            # 3. Load Strategy
            if version is None:
                # Get latest
                versions = self.strategy_loader._get_versions(strategy_name)
                version = max(versions) if versions else 1
                
            StrategyClass = self.strategy_loader.load_strategy_class(strategy_name, version)
            if not StrategyClass:
                raise ValueError(f"Strategy {strategy_name} v{version} not found")
            
            # Instantiate with parameters if provided
            try:
                if parameters:
                    strategy_instance = StrategyClass(parameters=parameters)
                else:
                    strategy_instance = StrategyClass()
            except TypeError:
                 # Fallback for strategies that don't accept parameters in __init__ yet
                 logger.warning("Strategy __init__ does not accept parameters. Attempting set_parameters...")
                 strategy_instance = StrategyClass()
                 if hasattr(strategy_instance, 'set_parameters') and parameters:
                     strategy_instance.set_parameters(parameters)
            
            # 4. Execution (Fail-Safe Wrapper)
            try:
                if use_fast:
                    results = self._execute_fast(df, strategy_instance, callback)
                else:
                    results = self._execute_legacy(df, strategy_instance, callback)
                status = "success"
                error = None
            except Exception as exec_err:
                logger.error(f"Execution Runtime Error: {exec_err}")
                status = "failed"
                # Include traceback for AI Self-Healing
                error = f"{str(exec_err)}\n\nTraceback:\n{traceback.format_exc()}"
                results = {
                    "metrics": {},
                    "trades": [],
                    "chart_data": []
                }
            
            # 5. Add Metadata
            results['dataset_id'] = dataset_id
            results['strategy'] = strategy_name
            results['version'] = version
            results['symbol'] = metadata['symbol']
            results['status'] = status
            results['error'] = error
            results['parameters'] = parameters or {}
            
            return results

        except Exception as e:
            logger.error(f"Backtest Initialization failed: {e}")
            raise e

    def _execute_fast(self, df: pd.DataFrame, strategy: Strategy, callback=None) -> Dict[str, Any]:
        """
        High-Performance Numba Execution.
        """
        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 1. Vectorized Variables
        vars_dict = strategy.define_variables(df)

        # 2. Vectorized Signals
        entry_long = strategy.entry_long(df, vars_dict).fillna(False).values.astype(bool)
        entry_short = strategy.entry_short(df, vars_dict).fillna(False).values.astype(bool)

        # Check if strategy supports vectorized exit signals (New Interface)
        if hasattr(strategy, 'exit_long_signal'):
             exit_long = strategy.exit_long_signal(df, vars_dict).fillna(False).values.astype(bool)
        else:
             exit_long = np.zeros(n_rows, dtype=bool)

        if hasattr(strategy, 'exit_short_signal'):
             exit_short = strategy.exit_short_signal(df, vars_dict).fillna(False).values.astype(bool)
        else:
             exit_short = np.zeros(n_rows, dtype=bool)

        # Risk Model
        risk = strategy.risk_model(df, vars_dict)
        sl_arr = risk.get('sl', pd.Series([np.nan]*n_rows)).fillna(np.nan).values.astype(float)
        tp_arr = risk.get('tp', pd.Series([np.nan]*n_rows)).fillna(np.nan).values.astype(float)

        # Position Size
        size_arr = strategy.position_size(df, vars_dict).fillna(1.0).values.astype(float)

        # Data Arrays
        opens = df['open'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        closes = df['close'].values.astype(float)
        times = df['dtv'].values.astype(np.int64)

        # Run Numba Loop
        if callback: callback(10, "Running Fast Engine...", {})

        # Updated unpacking to include MAE/MFE
        entry_times, exit_times, entry_prices, exit_prices, pnls, reasons, directions, maes, mfes = run_numba_backtest(
            opens, highs, lows, closes, times,
            entry_long, entry_short, exit_long, exit_short,
            sl_arr, tp_arr, size_arr
        )

        if callback: callback(90, "Calculating Metrics...", {})

        # Reconstruct Trades List
        trades = []
        for i in range(len(entry_times)):
            entry_dt = pd.to_datetime(entry_times[i], unit='ns', utc=True)
            exit_dt = pd.to_datetime(exit_times[i], unit='ns', utc=True)

            reason_map = {1: "SL Hit", 2: "TP Hit", 3: "Signal"}
            r_code = reasons[i]
            reason_str = reason_map.get(r_code, "Unknown")

            direction_str = "long" if directions[i] == 1 else "short"

            trades.append({
                "entry_time": entry_dt.strftime('%Y-%m-%d %H:%M:%S'),
                "exit_time": exit_dt.strftime('%Y-%m-%d %H:%M:%S'),
                "entry_price": float(entry_prices[i]),
                "exit_price": float(exit_prices[i]),
                "direction": direction_str,
                "pnl": float(pnls[i]),
                "exit_reason": reason_str,
                "duration": round((exit_times[i] - entry_times[i]) / (1e9 * 60), 2),
                "mae": float(maes[i]),
                "mfe": float(mfes[i])
            })

        metrics = PerformanceEngine.calculate_metrics(trades)

        return {
            "metrics": metrics,
            "trades": trades,
            "chart_data": [] # Can be populated if needed
        }

    def _execute_legacy(self, df: pd.DataFrame, strategy: Strategy, callback=None) -> Dict[str, Any]:
        """
        Original Python Loop Execution (Renamed from _execute).
        Kept for backward compatibility with strategies using complex exit() logic.
        """
        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 3.1 Define Variables (Vectorized)
        vars_dict = strategy.define_variables(df)
        
        # 3.2 Generate Signals (Vectorized)
        long_signals = strategy.entry_long(df, vars_dict)
        short_signals = strategy.entry_short(df, vars_dict)
        
        long_signals = long_signals.fillna(False).astype(bool)
        short_signals = short_signals.fillna(False).astype(bool)
        
        risk = strategy.risk_model(df, vars_dict)
        default_nan_series = pd.Series([np.nan]*n_rows, index=df.index)
        sl_series = risk.get('sl', default_nan_series)
        tp_series = risk.get('tp', default_nan_series)
        sl_arr = sl_series.fillna(np.nan).values
        tp_arr = tp_series.fillna(np.nan).values
        pos_sizes = strategy.position_size(df, vars_dict).fillna(1.0).values

        trades = []
        active_trade = None
        
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        times = df['dtv'].values # int64
        sig_long = long_signals.values
        sig_short = short_signals.values
        
        for i in range(n_rows):
            # ... (Original loop logic) ...
            try:
                current_time = int(times[i])
                open_p, high_p, low_p, close_p = float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i])
            except (ValueError, TypeError):
                continue

            if callback and i % (max(1, n_rows // 100)) == 0:
                progress = (i / n_rows) * 100
                display_time = pd.to_datetime(current_time, unit='ns', utc=True).strftime('%Y-%m-%d %H:%M:%S')
                callback(progress, "Running Legacy", {"current_time": display_time, "active_trade_count": 1 if active_trade else 0})
            
            if active_trade:
                trade_pnl = 0.0
                exit_price = 0.0
                exit_reason = ""
                
                curr_sl = active_trade.get('sl')
                curr_tp = active_trade.get('tp')
                
                if active_trade['direction'] == 'long':
                    if curr_sl is not None and not np.isnan(curr_sl) and low_p <= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    elif curr_tp is not None and not np.isnan(curr_tp) and high_p >= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"
                
                elif active_trade['direction'] == 'short':
                    if curr_sl is not None and not np.isnan(curr_sl) and high_p >= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    elif curr_tp is not None and not np.isnan(curr_tp) and low_p <= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"

                if not exit_reason:
                    try:
                        trade_info = active_trade.copy()
                        trade_info['current_idx'] = i
                        should_exit = strategy.exit(df, vars_dict, trade_info)
                        if should_exit:
                            exit_price = close_p
                            exit_reason = "Signal"
                    except Exception as e:
                        logger.warning(f"Strategy exit logic failed at idx {i}: {e}")
                
                if exit_reason:
                    trade_size = active_trade.get('size', 1.0)
                    if active_trade['direction'] == 'long':
                        trade_pnl = (exit_price - active_trade['entry_price']) * trade_size
                    else:
                        trade_pnl = (active_trade['entry_price'] - exit_price) * trade_size
                        
                    exit_dt = pd.to_datetime(current_time, unit='ns', utc=True)
                    entry_dt = pd.to_datetime(active_trade['entry_time'], unit='ns', utc=True)
                    
                    active_trade['exit_time'] = exit_dt.strftime('%Y-%m-%d %H:%M:%S')
                    active_trade['entry_time'] = entry_dt.strftime('%Y-%m-%d %H:%M:%S')

                    duration_ns = current_time - int(entry_dt.value)
                    duration_min = duration_ns / (1e9 * 60)
                    active_trade['duration'] = round(duration_min, 2)

                    active_trade['exit_price'] = exit_price
                    active_trade['pnl'] = trade_pnl
                    active_trade['exit_reason'] = exit_reason
                    
                    if active_trade['sl'] is not None and np.isnan(active_trade['sl']): active_trade['sl'] = None
                    if active_trade['tp'] is not None and np.isnan(active_trade['tp']): active_trade['tp'] = None
                    
                    trades.append(active_trade)
                    active_trade = None
                    continue 
            
            if not active_trade:
                try:
                    is_long = sig_long[i]
                    is_short = sig_short[i]

                    if is_long:
                        active_trade = {
                            "entry_time": current_time,
                            "entry_price": close_p,
                            "direction": "long",
                            "sl": float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None,
                            "tp": float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None,
                            "size": float(pos_sizes[i]) if not np.isnan(pos_sizes[i]) else 1.0
                        }
                    elif is_short:
                        active_trade = {
                            "entry_time": current_time,
                            "entry_price": close_p,
                            "direction": "short",
                            "sl": float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None,
                            "tp": float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None,
                            "size": float(pos_sizes[i]) if not np.isnan(pos_sizes[i]) else 1.0
                        }
                except Exception as e:
                    logger.warning(f"Signal processing failed at idx {i}: {e}")
        
        metrics = PerformanceEngine.calculate_metrics(trades)
        return {
            "metrics": metrics,
            "trades": trades, 
            "chart_data": [] 
        }
