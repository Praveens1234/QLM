import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
from backend.core.store import MetadataStore
from datetime import datetime

logger = logging.getLogger("QLM.Engine")

class BacktestEngine:
    """
    Core Execution Engine.
    Handles data loading, strategy instantiation, and event-driven backtesting.
    """
    
    def __init__(self):
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()

    def run(self, dataset_id: str, strategy_name: str, version: int = None, callback=None) -> Dict[str, Any]:
        """
        Run a backtest for a given dataset and strategy.
        Callback signature: func(progress_pct: float, message: str, data: Dict)
        """
        try:
            # 1. Load Dataset
            store = MetadataStore()
            metadata = store.get_dataset(dataset_id)
            if not metadata:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            df = self.data_manager.load_dataset(metadata['file_path'])
            logger.info(f"Loaded dataset {metadata['symbol']} with {len(df)} rows.")

            # 2. Load Strategy
            if version is None:
                # Get latest
                versions = self.strategy_loader._get_versions(strategy_name)
                version = max(versions) if versions else 1
                
            StrategyClass = self.strategy_loader.load_strategy_class(strategy_name, version)
            if not StrategyClass:
                raise ValueError(f"Strategy {strategy_name} v{version} not found")
            
            strategy_instance = StrategyClass()
            
            # 3. Execution (Fail-Safe Wrapper)
            try:
                results = self._execute(df, strategy_instance, callback)
                status = "success"
                error = None
            except Exception as exec_err:
                logger.error(f"Execution Runtime Error: {exec_err}")
                status = "failed"
                error = str(exec_err)
                results = {
                    "metrics": {},
                    "trades": [],
                    "chart_data": []
                }
            
            # 4. Add Metadata
            results['dataset_id'] = dataset_id
            results['strategy'] = strategy_name
            results['version'] = version
            results['symbol'] = metadata['symbol']
            results['status'] = status
            results['error'] = error
            
            return results

        except Exception as e:
            logger.error(f"Backtest Initialization failed: {e}")
            # Return a structured error response instead of raising if possible,
            # but raising lets the API handler catch it too.
            # Ideally, we want the API to return 200 OK with status="failed" or 400 Bad Request?
            # Let's re-raise to let API handle the HTTP response code, but ensure we logged it.
            raise e

    def _execute(self, df: pd.DataFrame, strategy: Strategy, callback=None) -> Dict[str, Any]:
        """
        Event-driven execution loop.
        """
        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 3.1 Define Variables (Vectorized)
        vars_dict = strategy.define_variables(df)
        
        # 3.2 Generate Signals (Vectorized)
        long_signals = strategy.entry_long(df, vars_dict)
        short_signals = strategy.entry_short(df, vars_dict)
        
        # Ensure signals are booleans and handle NaNs (from rolling)
        long_signals = long_signals.fillna(False).astype(bool)
        short_signals = short_signals.fillna(False).astype(bool)
        
        # Risk Model
        risk = strategy.risk_model(df, vars_dict)

        # Create default NaN series
        default_nan_series = pd.Series([np.nan]*n_rows, index=df.index)

        sl_series = risk.get('sl')
        if sl_series is None:
            sl_series = default_nan_series

        tp_series = risk.get('tp')
        if tp_series is None:
            tp_series = default_nan_series

        # Convert to numpy and fillna
        sl_arr = sl_series.fillna(np.nan).values
        tp_arr = tp_series.fillna(np.nan).values
        
        # Position Sizing
        pos_sizes = strategy.position_size(df, vars_dict).fillna(1.0).values

        trades = []
        active_trade = None
        
        # Convert necessary columns to numpy arrays for speed
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        times = df['dtv'].values # int64
        
        # Signals to numpy
        sig_long = long_signals.values
        sig_short = short_signals.values
        
        # Fail-Safe: Check for data integrity
        if np.any(np.isnan(opens)) or np.any(np.isnan(closes)):
             logger.warning("Dataset contains NaNs in OHLC data. Execution may be unreliable.")

        for i in range(n_rows):
            # Current Candle - CAST TO PYTHON TYPES FOR JSON SERIALIZATION
            try:
                current_time = int(times[i])
                open_p, high_p, low_p, close_p = float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i])
            except (ValueError, TypeError):
                # Skip bad rows
                continue

            # Progress Update
            if callback and i % (max(1, n_rows // 100)) == 0:
                progress = (i / n_rows) * 100
                display_time = pd.to_datetime(current_time, unit='ns', utc=True).strftime('%Y-%m-%d %H:%M:%S')
                callback(progress, "Running", {"current_time": display_time, "active_trade_count": 1 if active_trade else 0})
            
            # Check Active Trade Exit
            if active_trade:
                trade_pnl = 0.0
                exit_price = 0.0
                exit_reason = ""
                
                # 1. Check SL/TP (Intrabar approximation)
                curr_sl = active_trade.get('sl')
                curr_tp = active_trade.get('tp')
                
                # Robust Logic: Ensure we compare float to float
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

                # 2. Check Strategy Exit (Signal)
                if not exit_reason:
                    try:
                        trade_info = active_trade.copy()
                        trade_info['current_idx'] = i
                        should_exit = strategy.exit(df, vars_dict, trade_info)

                        if should_exit:
                            exit_price = close_p
                            exit_reason = "Signal"
                    except Exception as e:
                        # Log strategy error but don't crash
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
                    
                    # Clean up numpy types
                    if active_trade['sl'] is not None and np.isnan(active_trade['sl']): active_trade['sl'] = None
                    if active_trade['tp'] is not None and np.isnan(active_trade['tp']): active_trade['tp'] = None
                    
                    trades.append(active_trade)
                    active_trade = None
                    continue 
            
            # Check Entry
            if not active_trade:
                # Use try-except for checking signals to handle potential index errors (though unlikely with range loop)
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
        
        # Calculate Metrics
        metrics = PerformanceEngine.calculate_metrics(trades)
        
        return {
            "metrics": metrics,
            "trades": trades, 
            "chart_data": [] 
        }
