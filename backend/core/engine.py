import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import traceback
from backend.core.data import DataManager
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
from backend.core.store import MetadataStore
from backend.core.fast_engine import run_numba_backtest
from backend.core.system import check_memory
from backend.core.exceptions import QLMSystemError
from backend.core.commission import CommissionModel
from datetime import datetime

logger = logging.getLogger("QLM.Engine")

class BacktestEngine:
    """
    Core Execution Engine.
    Handles data loading, strategy instantiation, and event-driven backtesting.
    Supports both Python loop (Legacy) and Numba JIT (Fast) execution modes.
    Supports dual accounting: Capital (USD) and RRR (R-multiples) modes.
    """
    
    def __init__(self):
        self.data_manager = DataManager()
        self.strategy_loader = StrategyLoader()
        self.commission_model = CommissionModel(type="percent", value=0.0) # Default 0

    def _resolve_risk(self, risk: dict, df, entry_long, entry_short) -> tuple:
        """
        Normalize risk_model output to absolute SL/TP Series.
        Handles both formats:
          - {'sl': Series, 'tp': Series}  (absolute prices)
          - {'stop_loss_dist': scalar/Series, 'take_profit_dist': scalar/Series} (distances)
        Returns (sl_series, tp_series) as pd.Series of floats.
        """
        n = len(df)
        close = df['close']

        # Case 1: Strategy already returns 'sl' and 'tp' as Series
        if 'sl' in risk and risk['sl'] is not None:
            sl_series = risk['sl'] if isinstance(risk['sl'], pd.Series) else pd.Series(risk['sl'], index=df.index)
            tp_series = risk.get('tp')
            if tp_series is not None and not isinstance(tp_series, pd.Series):
                tp_series = pd.Series(tp_series, index=df.index)
            elif tp_series is None:
                tp_series = pd.Series(np.nan, index=df.index)
            return sl_series, tp_series

        # Case 2: Distance-based keys
        sl_dist = risk.get('stop_loss_dist', risk.get('sl_dist', None))
        tp_dist = risk.get('take_profit_dist', risk.get('tp_dist', None))

        if sl_dist is not None or tp_dist is not None:
            # Convert scalar to Series if needed
            if sl_dist is not None and not isinstance(sl_dist, pd.Series):
                sl_dist = pd.Series(float(sl_dist), index=df.index)
            if tp_dist is not None and not isinstance(tp_dist, pd.Series):
                tp_dist = pd.Series(float(tp_dist), index=df.index)

            # Build directional SL/TP: depends on whether entry is long or short
            sl_series = pd.Series(np.nan, index=df.index, dtype=float)
            tp_series = pd.Series(np.nan, index=df.index, dtype=float)

            long_mask = entry_long.fillna(False).astype(bool) if isinstance(entry_long, pd.Series) else pd.Series(entry_long, index=df.index).astype(bool)
            short_mask = entry_short.fillna(False).astype(bool) if isinstance(entry_short, pd.Series) else pd.Series(entry_short, index=df.index).astype(bool)

            if sl_dist is not None:
                sl_series[long_mask] = close[long_mask] - sl_dist[long_mask]
                sl_series[short_mask] = close[short_mask] + sl_dist[short_mask]
            if tp_dist is not None:
                tp_series[long_mask] = close[long_mask] + tp_dist[long_mask]
                tp_series[short_mask] = close[short_mask] - tp_dist[short_mask]

            return sl_series, tp_series

        # Case 3: No risk info at all
        return pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index)

    def set_commission(self, type: str, value: float):
        self.commission_model = CommissionModel(type, value)

    def run(self, dataset_id: str, strategy_name: str, version: int = None,
            callback=None, use_fast: bool = True, parameters: Dict[str, Any] = None,
            mode: str = "capital", initial_capital: float = 10000.0,
            leverage: float = 1.0, position_sizing: str = "fixed",
            fixed_size: float = 1.0, risk_per_trade: float = 0.01) -> Dict[str, Any]:
        """
        Run a backtest for a given dataset and strategy.
        
        Args:
            mode: "capital" (USD PnL) or "rrr" (R-multiple PnL)
            initial_capital: Starting capital in USD (capital mode)
            leverage: Leverage multiplier
            position_sizing: "fixed", "percent_equity", or "strategy_defined"
            fixed_size: Lot size for fixed position_sizing
            risk_per_trade: Fraction of equity risked per trade (percent_equity mode)
        """
        try:
            # 1. System Check
            if not check_memory(required_mb=256):
                raise QLMSystemError("Insufficient memory to run backtest.")

            # 2. Load Dataset
            store = MetadataStore()
            metadata = store.get_dataset(dataset_id)
            if not metadata:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            est_size_mb = (metadata.get('row_count', 0) * 8 * 10) / (1024 * 1024)
            if not check_memory(required_mb=int(est_size_mb * 1.5)):
                raise QLMSystemError(f"Dataset requires approx {int(est_size_mb)}MB RAM, but system is low on memory.")

            df = self.data_manager.load_dataset(metadata['file_path'])
            logger.info(f"Loaded dataset {metadata['symbol']} with {len(df)} rows.")

            # 3. Load Strategy
            if version is None:
                versions = self.strategy_loader._get_versions(strategy_name)
                version = max(versions) if versions else 1
                
            StrategyClass = self.strategy_loader.load_strategy_class(strategy_name, version)
            if not StrategyClass:
                raise ValueError(f"Strategy {strategy_name} v{version} not found")
            
            try:
                if parameters:
                    strategy_instance = StrategyClass(parameters=parameters)
                else:
                    strategy_instance = StrategyClass()
            except TypeError:
                 logger.warning("Strategy __init__ does not accept parameters. Attempting set_parameters...")
                 strategy_instance = StrategyClass()
                 if hasattr(strategy_instance, 'set_parameters') and parameters:
                     strategy_instance.set_parameters(parameters)

            # Build execution config
            exec_config = {
                "mode": mode,
                "initial_capital": initial_capital,
                "leverage": leverage,
                "position_sizing": position_sizing,
                "fixed_size": fixed_size,
                "risk_per_trade": risk_per_trade,
            }
            
            # 4. Execution
            try:
                if use_fast:
                    results = self._execute_fast(df, strategy_instance, callback, exec_config)
                else:
                    results = self._execute_legacy(df, strategy_instance, callback, exec_config)
                status = "success"
                error = None
            except Exception as exec_err:
                logger.error(f"Execution Runtime Error: {exec_err}")
                status = "failed"
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
            results['mode'] = mode
            results['initial_capital'] = initial_capital
            
            return results

        except Exception as e:
            logger.error(f"Backtest Initialization failed: {e}")
            raise e

    def _compute_size_arr(self, df: pd.DataFrame, strategy: Strategy, vars_dict: dict,
                          sl_arr: np.ndarray, exec_config: dict) -> np.ndarray:
        """
        Compute position size array based on sizing mode.
        """
        n_rows = len(df)
        sizing = exec_config.get("position_sizing", "fixed")
        leverage = exec_config.get("leverage", 1.0)
        
        if sizing == "strategy_defined":
            size_arr = strategy.position_size(df, vars_dict).fillna(1.0).values.astype(float)
            size_arr = size_arr * leverage
        elif sizing == "percent_equity":
            # For percent_equity, we compute a uniform size estimate based on initial capital
            # True sequential equity-based sizing is done in trade reconstruction
            capital = exec_config.get("initial_capital", 10000.0)
            risk_frac = exec_config.get("risk_per_trade", 0.01)
            risk_amt = capital * risk_frac
            
            # Estimate size per bar: risk_amount / distance_to_SL
            # If SL is NaN, use 1% of close as fallback risk distance
            closes = df['close'].values
            sl_dist = np.abs(closes - sl_arr)
            sl_dist = np.where(np.isnan(sl_dist) | (sl_dist < 1e-8), closes * 0.01, sl_dist)
            size_arr = (risk_amt / sl_dist) * leverage
        else:
            # Fixed sizing
            fixed = exec_config.get("fixed_size", 1.0)
            size_arr = np.full(n_rows, fixed * leverage, dtype=float)
        
        return size_arr

    def _build_trade_record(self, entry_time_ns, exit_time_ns, entry_price, exit_price,
                            direction_str, size, sl_val, tp_val, mae, mfe,
                            exit_reason, gross_pnl, commission, initial_risk,
                            exec_config) -> dict:
        """
        Build a standardized trade record matching the ledger spec.
        """
        net_pnl = gross_pnl - commission
        
        # R-Multiple (always computed)
        r_multiple = 0.0
        if initial_risk > 0:
            r_multiple = net_pnl / initial_risk

        entry_dt = pd.to_datetime(entry_time_ns, unit='ns', utc=True)
        exit_dt = pd.to_datetime(exit_time_ns, unit='ns', utc=True)
        duration_min = round((exit_time_ns - entry_time_ns) / (1e9 * 60), 2)

        mode = exec_config.get("mode", "capital")

        # In RRR mode, PnL is expressed as R-multiples
        pnl_value = r_multiple if mode == "rrr" else net_pnl

        # Normalize SL/TP: None if NaN
        if sl_val is not None and (isinstance(sl_val, float) and np.isnan(sl_val)):
            sl_val = None
        if tp_val is not None and (isinstance(tp_val, float) and np.isnan(tp_val)):
            tp_val = None

        # Status logic: "SL Hit"/"TP Hit" when SL/TP was set and hit.
        # "Exit" when closed by strategy signal (not SL/TP).
        # Map "Signal" -> "Exit" for user-facing clarity
        status = exit_reason
        if status == "Signal":
            status = "Exit"

        # Calculate MAE/MFE Prices and R-Values
        mae_price = 0.0
        mfe_price = 0.0
        mae_val = float(mae)
        mfe_val = float(mfe)
        entry_px = float(entry_price)

        if direction_str == 'long':
            mae_price = entry_px - mae_val
            mfe_price = entry_px + mfe_val
        else: # short
            mae_price = entry_px + mae_val
            mfe_price = entry_px - mfe_val
            
        # Helper to calculate PnL/R for excursions
        # Note: accurate PnL requires size, which we have.
        trade_size = float(size)
        mae_pnl = -mae_val * trade_size # Always negative logic for Adserse
        mfe_pnl = mfe_val * trade_size  # Always positive for Favorable
        
        # R-Multiple for MAE/MFE
        mae_r = mae_pnl / initial_risk if initial_risk > 0 else 0.0
        mfe_r = mfe_pnl / initial_risk if initial_risk > 0 else 0.0

        return {
            "entry_time": entry_dt.strftime('%Y-%m-%d %H:%M:%S'),
            "exit_time": exit_dt.strftime('%Y-%m-%d %H:%M:%S'),
            "entry_price": round(entry_px, 5),
            "exit_price": round(float(exit_price), 5),
            "direction": direction_str,
            "pnl": round(float(pnl_value), 2),
            "gross_pnl": round(float(gross_pnl), 2),
            "commission": round(float(commission), 2),
            "r_multiple": round(float(r_multiple), 4),
            "sl": round(float(sl_val), 5) if sl_val is not None else None,
            "tp": round(float(tp_val), 5) if tp_val is not None else None,
            "mae": round(mae_val, 2),
            "mfe": round(mfe_val, 2),
            "mae_price": round(mae_price, 5),
            "mfe_price": round(mfe_price, 5),
            "mae_pnl": round(mae_pnl, 2),
            "mfe_pnl": round(mfe_pnl, 2),
            "mae_r": round(mae_r, 2),
            "mfe_r": round(mfe_r, 2),
            "duration": duration_min,
            "exit_reason": status,
            "size": round(trade_size, 4),
            "initial_risk": round(float(initial_risk), 2),
        }

    def _prepare_data_arrays(self, df: pd.DataFrame) -> tuple:
        """
        Pre-calculate numpy arrays for Numba engine to avoid repeated copying in loops.
        Returns: (opens, highs, lows, closes, times)
        """
        opens = df['open'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        closes = df['close'].values.astype(float)
        times = df['dtv'].values.astype(np.int64)
        return (opens, highs, lows, closes, times)

    def _execute_fast(self, df: pd.DataFrame, strategy: Strategy, callback=None,
                      exec_config: dict = None, precalc_arrays: tuple = None) -> Dict[str, Any]:
        """
        High-Performance Numba Execution.
        """
        if exec_config is None:
            exec_config = {"mode": "capital", "initial_capital": 10000.0,
                           "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0}

        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 1. Vectorized Variables
        vars_dict = strategy.define_variables(df)

        # 2. Vectorized Signals
        entry_long_series = strategy.entry_long(df, vars_dict).fillna(False)
        entry_short_series = strategy.entry_short(df, vars_dict).fillna(False)
        entry_long = entry_long_series.values.astype(bool)
        entry_short = entry_short_series.values.astype(bool)

        # Use exit signals directly (base class guarantees existence)
        exit_long = strategy.exit_long_signal(df, vars_dict).fillna(False).values.astype(bool)
        exit_short = strategy.exit_short_signal(df, vars_dict).fillna(False).values.astype(bool)

        # Risk Model — normalize to absolute SL/TP Series
        risk = strategy.risk_model(df, vars_dict)
        sl_series, tp_series = self._resolve_risk(risk, df, entry_long_series, entry_short_series)
        sl_arr = sl_series.fillna(np.nan).values.astype(float)
        tp_arr = tp_series.fillna(np.nan).values.astype(float)

        # Position Size — compute based on sizing mode
        size_arr = self._compute_size_arr(df, strategy, vars_dict, sl_arr, exec_config)

        # Data Arrays (Use pre-calculated if available to save memory/CPU)
        if precalc_arrays:
            opens, highs, lows, closes, times = precalc_arrays
        else:
            opens = df['open'].values.astype(float)
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            closes = df['close'].values.astype(float)
            times = df['dtv'].values.astype(np.int64)

        # Run Numba Loop
        if callback: callback(10, "Running Fast Engine...", {})

        entry_times, exit_times, entry_prices, exit_prices, pnls, reasons, directions, maes, mfes, entry_indices = run_numba_backtest(
            opens, highs, lows, closes, times,
            entry_long, entry_short, exit_long, exit_short,
            sl_arr, tp_arr, size_arr
        )

        if callback: callback(90, "Calculating Metrics...", {})

        # Reconstruct Trades List & Apply Commissions
        reason_map = {1: "SL Hit", 2: "TP Hit", 3: "Signal", 4: "End of Data"}
        trades = []

        for i in range(len(entry_times)):
            entry_px = float(entry_prices[i])
            exit_px = float(exit_prices[i])
            
            # 1. Invalidate Zero Prices
            if entry_px == 0.0 or exit_px == 0.0:
                continue
                
            # 2. Invalidate Weekend Trades
            entry_dt = pd.to_datetime(int(entry_times[i]), unit='ns', utc=True)
            exit_dt = pd.to_datetime(int(exit_times[i]), unit='ns', utc=True)
            if entry_dt.weekday() >= 5 or exit_dt.weekday() >= 5: # 5=Sat, 6=Sun
                continue

            r_code = reasons[i]
            reason_str = reason_map.get(r_code, "Unknown")
            direction_str = "long" if directions[i] == 1 else "short"
            gross_pnl = float(pnls[i])

            # Retrieve Entry Info
            entry_idx = entry_indices[i]
            trade_size = float(size_arr[entry_idx]) if entry_idx < len(size_arr) else 1.0

            trade_obj = {
                "entry_price": entry_px,
                "exit_price": exit_px,
                "size": trade_size
            }

            # Recalculate commission
            comm = CommissionModel.apply_to_trade(trade_obj, self.commission_model)

            # Calculate Risk & R-Multiple
            initial_sl = sl_arr[entry_idx] if entry_idx < len(sl_arr) else np.nan
            initial_risk = 0.0
            if not np.isnan(initial_sl):
                initial_risk = abs(float(entry_prices[i]) - float(initial_sl)) * trade_size

            sl_val = float(sl_arr[entry_idx]) if entry_idx < len(sl_arr) else None
            tp_val = float(tp_arr[entry_idx]) if entry_idx < len(tp_arr) else None

            trade = self._build_trade_record(
                entry_time_ns=int(entry_times[i]),
                exit_time_ns=int(exit_times[i]),
                entry_price=float(entry_prices[i]),
                exit_price=float(exit_prices[i]),
                direction_str=direction_str,
                size=trade_size,
                sl_val=sl_val,
                tp_val=tp_val,
                mae=float(maes[i]),
                mfe=float(mfes[i]),
                exit_reason=reason_str,
                gross_pnl=gross_pnl,
                commission=comm,
                initial_risk=initial_risk,
                exec_config=exec_config,
            )
            trades.append(trade)

        initial_capital = exec_config.get("initial_capital", 10000.0)
        mode = exec_config.get("mode", "capital")
        metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial_capital, mode=mode)

        return {
            "metrics": metrics,
            "trades": trades,
            "chart_data": []
        }

    def _execute_legacy(self, df: pd.DataFrame, strategy: Strategy, callback=None,
                        exec_config: dict = None) -> Dict[str, Any]:
        """
        Original Python Loop Execution (Renamed from _execute).
        """
        if exec_config is None:
            exec_config = {"mode": "capital", "initial_capital": 10000.0,
                           "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0}

        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 1. Variables & Signals
        vars_dict = strategy.define_variables(df)
        long_signals = strategy.entry_long(df, vars_dict).fillna(False).astype(bool)
        short_signals = strategy.entry_short(df, vars_dict).fillna(False).astype(bool)

        risk = strategy.risk_model(df, vars_dict)
        sl_series, tp_series = self._resolve_risk(risk, df, long_signals, short_signals)
        sl_arr = sl_series.fillna(np.nan).values
        tp_arr = tp_series.fillna(np.nan).values

        # Position Size — compute based on sizing mode
        size_arr = self._compute_size_arr(df, strategy, vars_dict, sl_arr, exec_config)

        trades = []
        active_trade = None
        
        opens = df['open'].values
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        times = df['dtv'].values
        sig_long = long_signals.values
        sig_short = short_signals.values
        
        for i in range(n_rows):
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
                exit_price = 0.0
                exit_reason = ""
                
                curr_sl = active_trade.get('_sl')
                curr_tp = active_trade.get('_tp')
                
                # Check Exits
                if active_trade['_direction'] == 'long':
                    if curr_sl is not None and not np.isnan(curr_sl) and low_p <= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    elif curr_tp is not None and not np.isnan(curr_tp) and high_p >= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"
                elif active_trade['_direction'] == 'short':
                    if curr_sl is not None and not np.isnan(curr_sl) and high_p >= curr_sl:
                        exit_price = curr_sl
                        exit_reason = "SL Hit"
                    elif curr_tp is not None and not np.isnan(curr_tp) and low_p <= curr_tp:
                        exit_price = curr_tp
                        exit_reason = "TP Hit"

                if not exit_reason:
                    try:
                        trade_info = {
                            'direction': active_trade['_direction'],
                            'entry_price': active_trade['_entry_price'],
                            'current_idx': i,
                        }
                        should_exit = strategy.exit(df, vars_dict, trade_info)
                        if should_exit:
                            exit_price = close_p
                            exit_reason = "Signal"
                    except Exception as e:
                        logger.warning(f"Strategy exit logic failed at idx {i}: {e}")

                # Track MAE/MFE
                if active_trade['_direction'] == 'long':
                    excursion_up = high_p - active_trade['_entry_price']
                    excursion_down = active_trade['_entry_price'] - low_p
                else:
                    excursion_up = active_trade['_entry_price'] - low_p
                    excursion_down = high_p - active_trade['_entry_price']
                if excursion_up > active_trade['_mfe']:
                    active_trade['_mfe'] = excursion_up
                if excursion_down > active_trade['_mae']:
                    active_trade['_mae'] = excursion_down
                
                if exit_reason:
                    trade_size = active_trade.get('_size', 1.0)
                    if active_trade['_direction'] == 'long':
                        gross_pnl = (exit_price - active_trade['_entry_price']) * trade_size
                    else:
                        gross_pnl = (active_trade['_entry_price'] - exit_price) * trade_size

                    trade_obj = {
                        "entry_price": active_trade['_entry_price'],
                        "exit_price": exit_price,
                        "size": trade_size
                    }
                    
                    # 1. Invalidate Zero Prices
                    if active_trade['_entry_price'] == 0.0 or exit_price == 0.0:
                        active_trade = None
                        continue
                        
                    # 2. Invalidate Weekend Trades
                    entry_dt = pd.to_datetime(int(active_trade['_entry_time_ns']), unit='ns', utc=True)
                    exit_dt = pd.to_datetime(int(current_time), unit='ns', utc=True)
                    if entry_dt.weekday() >= 5 or exit_dt.weekday() >= 5: # 5=Sat, 6=Sun
                        active_trade = None
                        continue

                    comm = CommissionModel.apply_to_trade(trade_obj, self.commission_model)

                    trade = self._build_trade_record(
                        entry_time_ns=active_trade['_entry_time_ns'],
                        exit_time_ns=current_time,
                        entry_price=active_trade['_entry_price'],
                        exit_price=exit_price,
                        direction_str=active_trade['_direction'],
                        size=trade_size,
                        sl_val=curr_sl,
                        tp_val=curr_tp,
                        mae=active_trade['_mae'],
                        mfe=active_trade['_mfe'],
                        exit_reason=exit_reason,
                        gross_pnl=gross_pnl,
                        commission=comm,
                        initial_risk=active_trade['_initial_risk'],
                        exec_config=exec_config,
                    )
                    trades.append(trade)
                    active_trade = None
                    continue 
            
            if not active_trade:
                try:
                    is_long = sig_long[i]
                    is_short = sig_short[i]

                    if is_long or is_short:
                        direction = "long" if is_long else "short"
                        sl_val = float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None
                        tp_val = float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None
                        size_val = float(size_arr[i]) if not np.isnan(size_arr[i]) else 1.0
                        risk_val = abs(close_p - sl_val) * size_val if sl_val is not None else 0.0

                        active_trade = {
                            "_entry_time_ns": current_time,
                            "_entry_price": close_p,
                            "_direction": direction,
                            "_sl": sl_val,
                            "_tp": tp_val,
                            "_size": size_val,
                            "_initial_risk": risk_val,
                            "_mae": 0.0,
                            "_mfe": 0.0,
                        }
                except Exception as e:
                    logger.warning(f"Signal processing failed at idx {i}: {e}")
        
        # Force-close any open trade at end of data
        if active_trade:
            last_close = float(closes[-1])
            last_time = int(times[-1])
            trade_size = active_trade.get('_size', 1.0)
            
            if active_trade['_direction'] == 'long':
                gross_pnl = (last_close - active_trade['_entry_price']) * trade_size
            else:
                gross_pnl = (active_trade['_entry_price'] - last_close) * trade_size

            trade_obj = {
                "entry_price": active_trade['_entry_price'],
                "exit_price": last_close,
                "size": trade_size
            }
            comm = CommissionModel.apply_to_trade(trade_obj, self.commission_model)

            trade = self._build_trade_record(
                entry_time_ns=active_trade['_entry_time_ns'],
                exit_time_ns=last_time,
                entry_price=active_trade['_entry_price'],
                exit_price=last_close,
                direction_str=active_trade['_direction'],
                size=trade_size,
                sl_val=active_trade.get('_sl'),
                tp_val=active_trade.get('_tp'),
                mae=active_trade['_mae'],
                mfe=active_trade['_mfe'],
                exit_reason="End of Data",
                gross_pnl=gross_pnl,
                commission=comm,
                initial_risk=active_trade['_initial_risk'],
                exec_config=exec_config,
            )
            trades.append(trade)

        initial_capital = exec_config.get("initial_capital", 10000.0)
        mode = exec_config.get("mode", "capital")
        metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial_capital, mode=mode)
        
        return {
            "metrics": metrics,
            "trades": trades, 
            "chart_data": [] 
        }
