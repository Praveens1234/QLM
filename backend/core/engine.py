import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
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
            from backend.core.store import MetadataStore
            store = MetadataStore()
            metadata = store.get_dataset(dataset_id)
            if not metadata:
                raise ValueError("Dataset not found")
            
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
            
            # 3. Execution
            results = self._execute(df, strategy_instance, callback)
            
            # 4. Add Metadata
            results['dataset_id'] = dataset_id
            results['strategy'] = strategy_name
            results['version'] = version
            results['symbol'] = metadata['symbol']
            
            # 5. Generate CSV (Now that we have the symbol)
            for t in results['trades']:
                t['symbol'] = metadata['symbol']

            results['csv_export'] = PerformanceEngine.generate_metrics_csv(results['trades']) if hasattr(PerformanceEngine, 'generate_metrics_csv') else PerformanceEngine.generate_csv(results['trades'])

            return results

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def _execute(self, df: pd.DataFrame, strategy: Strategy, callback=None) -> Dict[str, Any]:
        """
        Event-driven execution loop.
        """
        n_rows = len(df)

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

        # FIX: Handle cases where 'sl' or 'tp' are None or missing gracefully
        default_nan_series = pd.Series([np.nan]*n_rows, index=df.index)

        sl_series = risk.get('sl')
        if sl_series is None:
            sl_series = default_nan_series

        tp_series = risk.get('tp')
        if tp_series is None:
            tp_series = default_nan_series

        sl_arr = sl_series.fillna(np.nan).values
        tp_arr = tp_series.fillna(np.nan).values
        
        # Position Sizing
        pos_sizes = strategy.position_size(df, vars_dict).fillna(1.0).values

        trades = []
        active_trade = None
        
        # Metrics tracking
        initial_capital = 10000.0
        equity = initial_capital
        equity_curve = [] # List of {time, value}
        
        # Convert necessary columns to numpy arrays for speed
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        times = df['dtv'].values # int64
        
        # Signals to numpy
        sig_long = long_signals.values
        sig_short = short_signals.values
        
        # For OHLCV Chart (Downsampling if huge?)
        # For now, just convert dataframe to list of dicts at the end
        # Or build it here? Actually, standard dataframe to_dict is fast enough unless huge.

        for i in range(n_rows):
            # Current Candle
            current_time_ns = int(times[i])
            # Conversion for JSON (seconds)
            current_time_sec = current_time_ns // 1_000_000_000

            open_p, high_p, low_p, close_p = float(opens[i]), float(highs[i]), float(lows[i]), float(closes[i])
            
            # Progress Update
            if callback and i % (max(1, n_rows // 100)) == 0:
                progress = (i / n_rows) * 100
                display_time = pd.to_datetime(current_time_ns, unit='ns', utc=True).strftime('%Y-%m-%d %H:%M:%S')
                callback(progress, "Running", {"current_time": display_time, "active_trade_count": 1 if active_trade else 0})
            
            # Check Active Trade Exit
            trade_closed_pnl = 0.0

            if active_trade:
                # Update MAE/MFE Tracking
                if active_trade['direction'] == 'long':
                    runup = high_p - active_trade['entry_price']
                    drawdown = active_trade['entry_price'] - low_p
                else: # short
                    runup = active_trade['entry_price'] - low_p
                    drawdown = high_p - active_trade['entry_price']

                # Store absolute values (always positive distance)
                active_trade['max_runup'] = max(active_trade.get('max_runup', 0.0), runup)
                active_trade['max_drawdown_trade'] = max(active_trade.get('max_drawdown_trade', 0.0), drawdown)

                trade_pnl = 0
                exit_price = 0
                exit_reason = ""
                
                # 1. Check SL/TP (Intrabar approximation)
                curr_sl = active_trade.get('sl')
                curr_tp = active_trade.get('tp')
                
                if active_trade['direction'] == 'long':
                    # Check SL (Low <= SL)
                    if curr_sl is not None and not np.isnan(curr_sl) and low_p <= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    # Check TP (High >= TP)
                    elif curr_tp is not None and not np.isnan(curr_tp) and high_p >= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"
                
                elif active_trade['direction'] == 'short':
                    # Check SL (High >= SL)
                    if curr_sl is not None and not np.isnan(curr_sl) and high_p >= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    # Check TP (Low <= TP)
                    elif curr_tp is not None and not np.isnan(curr_tp) and low_p <= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"

                # 2. Check Strategy Exit (Signal)
                if not exit_reason:
                    trade_info = active_trade.copy()
                    trade_info['current_idx'] = i
                    should_exit = strategy.exit(df, vars_dict, trade_info)
                    
                    if should_exit:
                        exit_price = close_p
                        exit_reason = "Signal"
                
                # Check for End of Data
                if not exit_reason and i == n_rows - 1:
                    exit_price = close_p
                    exit_reason = "End of Data"

                if exit_reason:
                    # Calculate Realized PnL
                    trade_size = active_trade.get('size', 1.0)
                    if active_trade['direction'] == 'long':
                        trade_pnl = (exit_price - active_trade['entry_price']) * trade_size
                    else:
                        trade_pnl = (active_trade['entry_price'] - exit_price) * trade_size
                        
                    # Format for Output
                    exit_dt = pd.to_datetime(current_time_ns, unit='ns', utc=True)
                    entry_dt = pd.to_datetime(active_trade['entry_time'], unit='ns', utc=True)
                    
                    active_trade['exit_time'] = exit_dt.strftime('%Y-%m-%d %H:%M:%S')
                    active_trade['entry_time'] = entry_dt.strftime('%Y-%m-%d %H:%M:%S')

                    # Store Unix timestamp for Chart markers
                    active_trade['entry_ts'] = int(entry_dt.timestamp())
                    active_trade['exit_ts'] = int(exit_dt.timestamp())

                    duration_ns = current_time_ns - int(entry_dt.value)
                    duration_min = duration_ns / (1e9 * 60)
                    active_trade['duration'] = round(duration_min, 2)

                    active_trade['exit_price'] = exit_price
                    active_trade['pnl'] = trade_pnl
                    active_trade['exit_reason'] = exit_reason
                    
                    # Determine Status
                    if trade_pnl > 0:
                        active_trade['status'] = "Profitable"
                        if exit_reason == "TP Hit":
                            active_trade['status'] = "TP Hit"
                    elif trade_pnl < 0:
                        active_trade['status'] = "Unprofitable"
                        if exit_reason == "SL Hit":
                            active_trade['status'] = "SL Hit"
                    else:
                        active_trade['status'] = "Breakeven"

                    # Ensure SL/TP are JSON compliant (None instead of NaN)
                    if active_trade['sl'] is not None and np.isnan(active_trade['sl']): active_trade['sl'] = None
                    if active_trade['tp'] is not None and np.isnan(active_trade['tp']): active_trade['tp'] = None
                    
                    trades.append(active_trade)
                    active_trade = None

                    trade_closed_pnl = trade_pnl
            
            # Check Entry
            if not active_trade:
                if sig_long[i]:
                    sl_val = float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None
                    tp_val = float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None

                    # Calculate Initial Risk (R)
                    initial_risk = 0.0
                    if sl_val is not None:
                        initial_risk = abs(close_p - sl_val)

                    active_trade = {
                        "entry_time": current_time_ns,
                        "entry_price": close_p,
                        "direction": "long",
                        "sl": sl_val,
                        "tp": tp_val,
                        "size": float(pos_sizes[i]) if not np.isnan(pos_sizes[i]) else 1.0,
                        "initial_risk": initial_risk,
                        "max_runup": 0.0,
                        "max_drawdown_trade": 0.0
                    }
                elif sig_short[i]:
                    sl_val = float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None
                    tp_val = float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None

                    # Calculate Initial Risk (R)
                    initial_risk = 0.0
                    if sl_val is not None:
                        initial_risk = abs(close_p - sl_val)

                    active_trade = {
                        "entry_time": current_time_ns,
                        "entry_price": close_p,
                        "direction": "short",
                        "sl": sl_val,
                        "tp": tp_val,
                        "size": float(pos_sizes[i]) if not np.isnan(pos_sizes[i]) else 1.0,
                        "initial_risk": initial_risk,
                        "max_runup": 0.0,
                        "max_drawdown_trade": 0.0
                    }

            # Update Equity (Mark to Market + Closed PnL)
            # Simple equity curve: Previous + Closed PnL + Unrealized PnL of active trade
            # Note: accumulating closed PnL is simpler.
            equity += trade_closed_pnl

            current_equity = equity
            if active_trade:
                # Add unrealized PnL
                size = active_trade.get('size', 1.0)
                if active_trade['direction'] == 'long':
                    unrealized = (close_p - active_trade['entry_price']) * size
                else:
                    unrealized = (active_trade['entry_price'] - close_p) * size
                current_equity += unrealized

            equity_curve.append({"time": current_time_sec, "value": current_equity})

        # Calculate Metrics
        metrics = PerformanceEngine.calculate_metrics(trades)
        
        # Prepare Chart Data (Downsample if necessary)
        # Limit OHLCV to e.g. 2000 points? For now, full dataset unless huge.
        ohlcv_data = []
        # Use simple iteration or vectorization to build list of dicts
        # Vectorized approach:
        # chart_df = df[['dtv', 'open', 'high', 'low', 'close']].copy()
        # chart_df['time'] = chart_df['dtv'] // 1_000_000_000
        # ohlcv_data = chart_df[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')

        # Optimization: use numpy directly
        times_sec = times // 1_000_000_000
        ohlcv_data = [
            {"time": int(t), "open": o, "high": h, "low": l, "close": c}
            for t, o, h, l, c in zip(times_sec, opens, highs, lows, closes)
        ]

        return {
            "metrics": metrics,
            "trades": trades, 
            "chart_data": {
                "ohlcv": ohlcv_data,
                "equity": equity_curve
            }
        }
