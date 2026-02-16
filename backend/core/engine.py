import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
from backend.core.store import MetadataStore
from backend.core.fast_engine import fast_backtest_core
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

    def run(self, dataset_id: str, strategy_name: str, version: int = None, callback=None, parameters: Dict = None) -> Dict[str, Any]:
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
            
            # Inject Parameters if provided
            if parameters:
                strategy_instance.set_parameters(parameters)

            # 3. Execution (Fail-Safe Wrapper)
            try:
                # Use Fast Execution by default if optimization parameters are present, else Standard
                # Or just try fast first? For now, keep standard as default for UI backtests.
                # Actually, optimization calls explicitly need speed.
                # Let's use a heuristic: if callback is None (batch mode), use fast.
                use_fast = (callback is None)
                results = self._execute(df, strategy_instance, callback, use_fast=use_fast)
                status = "success"
                error = None
            except Exception as exec_err:
                logger.error(f"Execution Runtime Error: {exec_err}")
                import traceback
                traceback.print_exc()
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

    def _execute(self, df: pd.DataFrame, strategy: Strategy, callback=None, use_fast=False) -> Dict[str, Any]:
        """
        Event-driven execution loop.
        """
        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 3.1 Define Variables (Vectorized)
        vars_dict = strategy.define_variables(df)
        
        # 3.2 Generate Signals (Vectorized)
        long_signals = strategy.entry_long(df, vars_dict).fillna(False).astype(bool)
        short_signals = strategy.entry_short(df, vars_dict).fillna(False).astype(bool)
        
        # 3.3 Generate Exit Signals (Vectorized) - New Interface
        long_exits = strategy.exit_long_signal(df, vars_dict).fillna(False).astype(bool)
        short_exits = strategy.exit_short_signal(df, vars_dict).fillna(False).astype(bool)
        
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

        # Position Sizing
        pos_sizes = strategy.position_size(df, vars_dict).fillna(1.0).values
        
        # Convert necessary columns to numpy arrays
        opens = df['open'].values.astype(np.float64)
        highs = df['high'].values.astype(np.float64)
        lows = df['low'].values.astype(np.float64)
        closes = df['close'].values.astype(np.float64)
        times = df['dtv'].values.astype(np.int64)
        
        sl_arr = sl_series.fillna(np.nan).values.astype(np.float64)
        tp_arr = tp_series.fillna(np.nan).values.astype(np.float64)
        pos_sizes = pos_sizes.astype(np.float64)

        if use_fast:
             # FAST PATH (Numba)
             trades_arr = fast_backtest_core(
                 times, opens, highs, lows, closes,
                 long_signals.values, short_signals.values,
                 long_exits.values, short_exits.values,
                 sl_arr, tp_arr, pos_sizes
             )

             # Convert Numba results to Dicts
             trades = []
             for row in trades_arr:
                 # row: [entry_time, exit_time, entry_price, exit_price, pnl, direction, exit_reason, size]
                 entry_ts = pd.to_datetime(row[0], unit='ns', utc=True)
                 exit_ts = pd.to_datetime(row[1], unit='ns', utc=True)
                 duration_min = (row[1] - row[0]) / (1e9 * 60)

                 reason_map = {1: "SL Hit", 2: "TP Hit", 3: "Signal", 4: "End"}

                 trades.append({
                     "entry_time": entry_ts.strftime('%Y-%m-%d %H:%M:%S'),
                     "exit_time": exit_ts.strftime('%Y-%m-%d %H:%M:%S'),
                     "entry_price": row[2],
                     "exit_price": row[3],
                     "pnl": row[4],
                     "direction": "long" if row[5] == 1 else "short",
                     "exit_reason": reason_map.get(int(row[6]), "Unknown"),
                     "size": row[7],
                     "duration": round(duration_min, 2)
                 })

        else:
            # SLOW PATH (Python Loop - Legacy & Custom Logic)
            trades = []
            active_trade = None
            
            sig_long = long_signals.values
            sig_short = short_signals.values

            for i in range(n_rows):
                try:
                    current_time = int(times[i])
                    open_p, high_p, low_p, close_p = float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i])
                except (ValueError, TypeError): continue

                if callback and i % (max(1, n_rows // 100)) == 0:
                    progress = (i / n_rows) * 100
                    display_time = pd.to_datetime(current_time, unit='ns', utc=True).strftime('%Y-%m-%d %H:%M:%S')
                    callback(progress, "Running", {"current_time": display_time, "active_trade_count": 1 if active_trade else 0})

                if active_trade:
                    trade_pnl = 0.0
                    exit_price = 0.0
                    exit_reason = ""
                    
                    curr_sl = active_trade.get('sl')
                    curr_tp = active_trade.get('tp')

                    if active_trade['direction'] == 'long':
                        if curr_sl is not None and not np.isnan(curr_sl) and low_p <= curr_sl:
                            exit_price = curr_sl; exit_reason = "SL Hit"
                        elif curr_tp is not None and not np.isnan(curr_tp) and high_p >= curr_tp:
                            exit_price = curr_tp; exit_reason = "TP Hit"
                    elif active_trade['direction'] == 'short':
                        if curr_sl is not None and not np.isnan(curr_sl) and high_p >= curr_sl:
                            exit_price = curr_sl; exit_reason = "SL Hit"
                        elif curr_tp is not None and not np.isnan(curr_tp) and low_p <= curr_tp:
                            exit_price = curr_tp; exit_reason = "TP Hit"

                    if not exit_reason:
                        # Custom Python Logic Check
                        if strategy.exit(df, vars_dict, active_trade):
                             exit_price = close_p; exit_reason = "Signal"
                        # Or Vectorized Check (if strategy overrides standard loop)
                        elif active_trade['direction'] == 'long' and long_exits[i]:
                             exit_price = close_p; exit_reason = "Signal"
                        elif active_trade['direction'] == 'short' and short_exits[i]:
                             exit_price = close_p; exit_reason = "Signal"

                    if exit_reason:
                        trade_size = active_trade.get('size', 1.0)
                        if active_trade['direction'] == 'long':
                            trade_pnl = (exit_price - active_trade['entry_price']) * trade_size
                        else:
                            trade_pnl = (active_trade['entry_price'] - exit_price) * trade_size

                        exit_dt = pd.to_datetime(current_time, unit='ns', utc=True)
                        entry_dt = pd.to_datetime(active_trade['entry_time'], unit='ns', utc=True)

                        active_trade.update({
                            'exit_time': exit_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_time': entry_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'duration': round((current_time - int(entry_dt.value)) / (1e9 * 60), 2),
                            'exit_price': exit_price,
                            'pnl': trade_pnl,
                            'exit_reason': exit_reason
                        })
                        if active_trade['sl'] is not None and np.isnan(active_trade['sl']): active_trade['sl'] = None
                        if active_trade['tp'] is not None and np.isnan(active_trade['tp']): active_trade['tp'] = None

                        trades.append(active_trade)
                        active_trade = None
                        continue

                if not active_trade:
                    if sig_long[i]:
                        active_trade = {
                            "entry_time": current_time, "entry_price": close_p, "direction": "long",
                            "sl": float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None,
                            "tp": float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None,
                            "size": float(pos_sizes[i])
                        }
                    elif sig_short[i]:
                        active_trade = {
                            "entry_time": current_time, "entry_price": close_p, "direction": "short",
                            "sl": float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None,
                            "tp": float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None,
                            "size": float(pos_sizes[i])
                        }
        
        # Calculate Metrics
        metrics = PerformanceEngine.calculate_metrics(trades)
        
        return {
            "metrics": metrics,
            "trades": trades, 
            "chart_data": [] 
        }
