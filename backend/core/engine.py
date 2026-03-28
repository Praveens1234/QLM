"""
QLM Backtest Engine — Core Orchestrator.

Handles data loading, strategy instantiation, pre-backtest sanitisation,
and event-driven backtesting through both a Numba JIT (Fast) path and
a Python loop (Legacy) path.

Supports dual accounting: Capital (USD) and RRR (R-multiples) modes.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import logging
import traceback
from datetime import datetime
from backend.core.data import DataManager, MarketCalendar
from backend.core.strategy import StrategyLoader, Strategy
from backend.core.metrics import PerformanceEngine
from backend.core.store import MetadataStore
from backend.core.fast_engine import run_numba_backtest
from backend.core.system import check_memory
from backend.core.exceptions import QLMSystemError, BacktestError, SanitizationError
from backend.core.commission import CommissionModel

logger = logging.getLogger("QLM.Engine")

# Spike threshold: bars with (high-low)/open > this are flagged
DEFAULT_SPIKE_THRESHOLD = 0.15


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
        self.commission_model = CommissionModel(type="percent", value=0.0)

    def set_commission(self, type: str, value: float):
        self.commission_model = CommissionModel(type, value)

    # ─── Pre-Backtest Sanitisation ──────────────────────────────────────────

    def _sanitize_dataset(self, df: pd.DataFrame,
                          spike_threshold: float = DEFAULT_SPIKE_THRESHOLD,
                          ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Pre-backtest data integrity guard.
        Returns a CLEANED COPY of the DataFrame (original parquet untouched)
        and a report dict with counts of each fix applied.

        Also injects two boolean columns for the engine:
          _spike_bar  — True for bars with unrealistic intra-bar range
          _market_closed — True for bars during market closure (weekend)

        Handles:
        1. NaN in OHLC → drop row
        2. Zero-price rows (O/H/L/C == 0) → drop row
        3. Negative prices → drop row
        4. OHLC logic violations (H < L) → swap H/L, clamp O/C
        5. Stale/frozen bars (O=H=L=C AND volume=0) → drop row
        6. Duplicate timestamps → keep first
        7. Spike detection → flag (don't drop)
        8. Market closure detection → flag
        """
        original_len = len(df)
        report: Dict[str, Any] = {
            "original_rows": original_len,
            "nan_dropped": 0,
            "zero_dropped": 0,
            "negative_dropped": 0,
            "logic_fixed": 0,
            "stale_dropped": 0,
            "duplicate_dropped": 0,
            "spike_bars_flagged": 0,
            "market_closed_flagged": 0,
            "final_rows": 0,
            "total_removed": 0,
        }

        df = df.copy()

        # 1. Drop NaN in OHLC
        nan_mask = df[['open', 'high', 'low', 'close']].isna().any(axis=1)
        nan_count = int(nan_mask.sum())
        if nan_count > 0:
            df = df[~nan_mask]
            report["nan_dropped"] = nan_count
            logger.warning(f"Sanitizer: Dropped {nan_count} rows with NaN OHLC.")

        # 2. Drop zero-price rows
        if len(df) > 0:
            zero_mask = (df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)
            zero_count = int(zero_mask.sum())
            if zero_count > 0:
                df = df[~zero_mask]
                report["zero_dropped"] = zero_count
                logger.warning(f"Sanitizer: Dropped {zero_count} rows with zero prices.")

        # 3. Drop negative prices
        if len(df) > 0:
            neg_mask = (df['open'] < 0) | (df['high'] < 0) | (df['low'] < 0) | (df['close'] < 0)
            neg_count = int(neg_mask.sum())
            if neg_count > 0:
                df = df[~neg_mask]
                report["negative_dropped"] = neg_count
                logger.warning(f"Sanitizer: Dropped {neg_count} rows with negative prices.")

        # 4. Fix OHLC logic (H < L → swap; clamp O/C)
        if len(df) > 0:
            inverted = df['high'] < df['low']
            inv_count = int(inverted.sum())
            if inv_count > 0:
                df.loc[inverted, ['high', 'low']] = df.loc[inverted, ['low', 'high']].values
                report["logic_fixed"] = inv_count
                logger.warning(f"Sanitizer: Fixed {inv_count} rows with inverted High/Low.")
            df['open'] = df['open'].clip(lower=df['low'], upper=df['high'])
            df['close'] = df['close'].clip(lower=df['low'], upper=df['high'])

        # 5. Drop stale/frozen bars (O=H=L=C AND volume=0)
        if len(df) > 0:
            stale_mask = (
                (df['open'] == df['high']) &
                (df['high'] == df['low']) &
                (df['low'] == df['close']) &
                (df['volume'] == 0)
            )
            stale_count = int(stale_mask.sum())
            if stale_count > 0:
                df = df[~stale_mask]
                report["stale_dropped"] = stale_count
                logger.warning(f"Sanitizer: Dropped {stale_count} stale/frozen bars.")

        # 6. Drop duplicate timestamps
        if len(df) > 0 and 'datetime' in df.columns:
            dup_count = int(df.duplicated(subset=['datetime'], keep='first').sum())
            if dup_count > 0:
                df = df.drop_duplicates(subset=['datetime'], keep='first')
                report["duplicate_dropped"] = dup_count
                logger.warning(f"Sanitizer: Dropped {dup_count} duplicate timestamps.")

        # Reset index
        df = df.reset_index(drop=True)

        # 7. Flag spike bars (do NOT drop — engine will skip entries on them)
        if len(df) > 0:
            with np.errstate(divide='ignore', invalid='ignore'):
                bar_range_pct = np.abs(df['high'].values - df['low'].values) / np.where(
                    df['open'].values > 0, df['open'].values, 1.0
                )
            spike_mask = bar_range_pct > spike_threshold
            df['_spike_bar'] = spike_mask
            spike_count = int(spike_mask.sum())
            report["spike_bars_flagged"] = spike_count
            if spike_count > 0:
                logger.warning(f"Sanitizer: Flagged {spike_count} spike bars (range > {spike_threshold*100:.0f}%).")
        else:
            df['_spike_bar'] = np.zeros(0, dtype=bool)

        # 8. Flag market closure bars
        if len(df) > 0 and 'dtv' in df.columns:
            mc_mask = MarketCalendar.build_market_closed_mask(df['dtv'].values)
            df['_market_closed'] = mc_mask
            mc_count = int(mc_mask.sum())
            report["market_closed_flagged"] = mc_count
            if mc_count > 0:
                logger.info(f"Sanitizer: Flagged {mc_count} market-closure bars.")
        else:
            df['_market_closed'] = np.zeros(len(df), dtype=bool)

        report["final_rows"] = len(df)
        report["total_removed"] = original_len - len(df)

        if report["total_removed"] > 0:
            pct = (report["total_removed"] / original_len) * 100
            logger.info(
                f"Sanitizer: Removed {report['total_removed']} of {original_len} rows "
                f"({pct:.2f}%). {len(df)} rows remain."
            )
            if pct > 50:
                raise SanitizationError(
                    f"Dataset critically corrupted: {pct:.1f}% of rows removed. "
                    f"Manual review required before backtesting."
                )
        else:
            logger.info(f"Sanitizer: Dataset clean. All {original_len} rows passed.")

        return df, report

    # ─── Risk Model Resolution ──────────────────────────────────────────────

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

        # Case 1: Absolute
        if 'sl' in risk and risk['sl'] is not None:
            sl = risk['sl'] if isinstance(risk['sl'], pd.Series) else pd.Series(risk['sl'], index=df.index)
            tp = risk.get('tp')
            if tp is not None and not isinstance(tp, pd.Series):
                tp = pd.Series(tp, index=df.index)
            elif tp is None:
                tp = pd.Series(np.nan, index=df.index)
            return sl, tp

        # Case 2: Distance-based
        sl_dist = risk.get('stop_loss_dist', risk.get('sl_dist', None))
        tp_dist = risk.get('take_profit_dist', risk.get('tp_dist', None))

        if sl_dist is not None or tp_dist is not None:
            if sl_dist is not None and not isinstance(sl_dist, pd.Series):
                sl_dist = pd.Series(float(sl_dist), index=df.index)
            if tp_dist is not None and not isinstance(tp_dist, pd.Series):
                tp_dist = pd.Series(float(tp_dist), index=df.index)

            sl_series = pd.Series(np.nan, index=df.index, dtype=float)
            tp_series = pd.Series(np.nan, index=df.index, dtype=float)

            long_mask = (entry_long.fillna(False).astype(bool) if isinstance(entry_long, pd.Series)
                         else pd.Series(entry_long, index=df.index).astype(bool))
            short_mask = (entry_short.fillna(False).astype(bool) if isinstance(entry_short, pd.Series)
                          else pd.Series(entry_short, index=df.index).astype(bool))

            if sl_dist is not None:
                sl_series[long_mask] = close[long_mask] - sl_dist[long_mask]
                sl_series[short_mask] = close[short_mask] + sl_dist[short_mask]
            if tp_dist is not None:
                tp_series[long_mask] = close[long_mask] + tp_dist[long_mask]
                tp_series[short_mask] = close[short_mask] - tp_dist[short_mask]

            return sl_series, tp_series

        # Case 3: No risk
        return pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index)

    # ─── Position Sizing ────────────────────────────────────────────────────

    def _compute_size_arr(self, df: pd.DataFrame, strategy: Strategy, vars_dict: dict,
                          sl_arr: np.ndarray, exec_config: dict) -> np.ndarray:
        """Compute position size array based on sizing mode."""
        n_rows = len(df)
        sizing = exec_config.get("position_sizing", "fixed")
        leverage = exec_config.get("leverage", 1.0)

        if sizing == "strategy_defined":
            raw = strategy.position_size(df, vars_dict)
            size_arr = raw.fillna(1.0).values.astype(float) * leverage
        elif sizing == "percent_equity":
            # Initial estimate — actual equity-based rescaling happens in post-processing
            capital = exec_config.get("initial_capital", 10000.0)
            risk_frac = exec_config.get("risk_per_trade", 0.01)
            risk_amt = capital * risk_frac
            closes = df['close'].values
            sl_dist = np.abs(closes - sl_arr)
            sl_dist = np.where(np.isnan(sl_dist) | (sl_dist < 1e-8), closes * 0.01, sl_dist)
            size_arr = (risk_amt / sl_dist) * leverage
        else:
            fixed = exec_config.get("fixed_size", 1.0)
            size_arr = np.full(n_rows, fixed * leverage, dtype=float)

        return size_arr

    # ─── Slippage & Spread Arrays ───────────────────────────────────────────

    def _compute_slippage_arr(self, n_rows: int, exec_config: dict) -> np.ndarray:
        mode = exec_config.get("slippage_mode", "none")
        value = exec_config.get("slippage_value", 0.0)
        if mode == "fixed":
            return np.full(n_rows, value, dtype=float)
        elif mode == "percent":
            return np.full(n_rows, value / 100.0, dtype=float)
        elif mode == "random":
            return np.random.uniform(0, value, size=n_rows).astype(float)
        return np.zeros(n_rows, dtype=float)

    def _compute_spread_arr(self, n_rows: int, exec_config: dict) -> np.ndarray:
        return np.full(n_rows, exec_config.get("spread_value", 0.0), dtype=float)

    # ─── Trade Record Builder ───────────────────────────────────────────────

    def _build_trade_record(self, entry_time_ns, exit_time_ns, entry_price, exit_price,
                            direction_str, size, sl_val, tp_val, mae, mfe,
                            exit_reason, gross_pnl, commission, initial_risk,
                            exec_config) -> dict:
        """Build a standardized trade record."""
        net_pnl = gross_pnl - commission
        r_multiple = (net_pnl / initial_risk) if initial_risk > 0 else 0.0

        entry_dt = pd.to_datetime(entry_time_ns, unit='ns', utc=True)
        exit_dt = pd.to_datetime(exit_time_ns, unit='ns', utc=True)
        duration_sec = max(0, (exit_time_ns - entry_time_ns) / 1e9)
        duration_min = round(duration_sec / 60.0, 2)

        mode = exec_config.get("mode", "capital")
        pnl_value = r_multiple if mode == "rrr" else net_pnl

        # Normalize NaN SL/TP to None
        if sl_val is not None and isinstance(sl_val, float) and np.isnan(sl_val):
            sl_val = None
        if tp_val is not None and isinstance(tp_val, float) and np.isnan(tp_val):
            tp_val = None

        # Friendly exit status
        status = exit_reason
        if status == "Signal":
            status = "Exit"

        # MAE/MFE
        entry_px = float(entry_price)
        mae_val = float(mae)
        mfe_val = float(mfe)
        trade_size = float(size)

        if direction_str == 'long':
            mae_price = entry_px - mae_val
            mfe_price = entry_px + mfe_val
        else:
            mae_price = entry_px + mae_val
            mfe_price = entry_px - mfe_val

        mae_pnl = -mae_val * trade_size
        mfe_pnl = mfe_val * trade_size
        mae_r = (mae_pnl / initial_risk) if initial_risk > 0 else 0.0
        mfe_r = (mfe_pnl / initial_risk) if initial_risk > 0 else 0.0

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

    # ─── Equity Curve Builder ───────────────────────────────────────────────

    def _build_equity_curve(self, trades: List[dict], initial_capital: float,
                            mode: str) -> List[Dict[str, Any]]:
        """
        Build equity curve data from sorted trade list.
        Returns list of {time, equity, drawdown, drawdown_pct} points.
        """
        if not trades:
            return []

        curve = [{"time": None, "equity": initial_capital, "drawdown": 0.0, "drawdown_pct": 0.0}]
        equity = initial_capital
        peak = initial_capital

        for t in trades:
            pnl = t.get('gross_pnl', 0.0) if mode == "rrr" else t.get('pnl', 0.0)
            equity += pnl
            if equity > peak:
                peak = equity
            dd = equity - peak
            dd_pct = (dd / peak * 100) if peak > 0 else 0.0
            curve.append({
                "time": t.get("exit_time"),
                "equity": round(equity, 2),
                "drawdown": round(dd, 2),
                "drawdown_pct": round(dd_pct, 2),
            })

        return curve

    # ─── Dynamic Equity Rescaling for percent_equity ────────────────────────

    def _rescale_trades_for_equity(self, trades: List[dict], exec_config: dict) -> List[dict]:
        """
        When position_sizing == 'percent_equity', the Numba engine used static
        sizing.  We re-scale each trade's size and PnL to reflect dynamic
        equity-based sizing.

        Mutates trades in-place and returns them.
        """
        if exec_config.get("position_sizing") != "percent_equity":
            return trades
        if not trades:
            return trades

        initial_capital = exec_config.get("initial_capital", 10000.0)
        risk_frac = exec_config.get("risk_per_trade", 0.01)
        leverage = exec_config.get("leverage", 1.0)
        mode = exec_config.get("mode", "capital")

        equity = initial_capital

        for t in trades:
            risk_amt = equity * risk_frac
            initial_risk = t.get("initial_risk", 0.0)

            if initial_risk > 0:
                # Original size was based on initial_capital; rescale to current equity
                original_risk_amt = initial_capital * risk_frac
                scale = risk_amt / original_risk_amt if original_risk_amt > 0 else 1.0
            else:
                scale = 1.0

            # Rescale trade fields
            t["size"] = round(t["size"] * scale, 4)
            t["gross_pnl"] = round(t["gross_pnl"] * scale, 2)
            t["initial_risk"] = round(initial_risk * scale, 2)

            # Recompute commission on rescaled trade
            trade_obj = {"entry_price": t["entry_price"], "exit_price": t["exit_price"], "size": t["size"]}
            comm = CommissionModel.apply_to_trade(trade_obj, self.commission_model)
            t["commission"] = round(comm, 2)

            net_pnl = t["gross_pnl"] - comm
            t["pnl"] = round((net_pnl / t["initial_risk"]) if (mode == "rrr" and t["initial_risk"] > 0)
                             else net_pnl, 2)
            t["r_multiple"] = round((net_pnl / t["initial_risk"]) if t["initial_risk"] > 0 else 0.0, 4)

            # MAE/MFE PnL & R
            t["mae_pnl"] = round(-t["mae"] * t["size"], 2)
            t["mfe_pnl"] = round(t["mfe"] * t["size"], 2)
            t["mae_r"] = round(t["mae_pnl"] / t["initial_risk"], 2) if t["initial_risk"] > 0 else 0.0
            t["mfe_r"] = round(t["mfe_pnl"] / t["initial_risk"], 2) if t["initial_risk"] > 0 else 0.0

            # Update running equity
            equity += t["gross_pnl"] - comm

        return trades

    # ─── Main Orchestrator ──────────────────────────────────────────────────

    def run(self, dataset_id: str, strategy_name: str, version: int = None,
            callback=None, use_fast: bool = True, parameters: Dict[str, Any] = None,
            mode: str = "capital", initial_capital: float = 10000.0,
            leverage: float = 1.0, position_sizing: str = "fixed",
            fixed_size: float = 1.0, risk_per_trade: float = 0.01,
            slippage_mode: str = "none", slippage_value: float = 0.0,
            spread_value: float = 0.0, entry_on_next_bar: bool = False,
            skip_weekend_trades: bool = True) -> Dict[str, Any]:
        """Run a backtest for a given dataset and strategy."""
        try:
            # ── 1. System Check ──
            if not check_memory(required_mb=256):
                raise QLMSystemError("Insufficient memory to run backtest.")

            # ── 2. Load Dataset ──
            store = MetadataStore()
            metadata = store.get_dataset(dataset_id)
            if not metadata:
                raise BacktestError(f"Dataset {dataset_id} not found", phase="load")

            est_size_mb = (metadata.get('row_count', 0) * 8 * 10) / (1024 * 1024)
            if not check_memory(required_mb=int(est_size_mb * 1.5)):
                raise QLMSystemError(
                    f"Dataset needs ~{int(est_size_mb)}MB RAM, system is low on memory."
                )

            df = self.data_manager.load_dataset(metadata['file_path'])
            logger.info(f"Loaded dataset {metadata['symbol']} with {len(df)} rows.")

            # ── 2.5. Pre-Backtest Sanitisation ──
            df, sanitization_report = self._sanitize_dataset(df)
            if len(df) < 10:
                raise SanitizationError(
                    f"Dataset has only {len(df)} rows after sanitisation. Minimum 10 required."
                )

            # ── 3. Load Strategy ──
            if version is None:
                versions = self.strategy_loader._get_versions(strategy_name)
                version = max(versions) if versions else 1

            StrategyClass = self.strategy_loader.load_strategy_class(strategy_name, version)
            if not StrategyClass:
                raise BacktestError(
                    f"Strategy {strategy_name} v{version} not found", phase="load"
                )

            try:
                strategy_instance = StrategyClass(parameters=parameters) if parameters else StrategyClass()
            except TypeError:
                logger.warning("Strategy __init__ does not accept parameters. Trying set_parameters...")
                strategy_instance = StrategyClass()
                if hasattr(strategy_instance, 'set_parameters') and parameters:
                    strategy_instance.set_parameters(parameters)

            # Build execution config
            exec_config = {
                "mode": mode,
                "initial_capital": initial_capital,
                "leverage": max(1.0, leverage),
                "position_sizing": position_sizing,
                "fixed_size": max(0.001, fixed_size),
                "risk_per_trade": max(0.0001, risk_per_trade),
                "slippage_mode": slippage_mode,
                "slippage_value": max(0.0, slippage_value),
                "spread_value": max(0.0, spread_value),
                "entry_on_next_bar": entry_on_next_bar,
                "skip_weekend_trades": skip_weekend_trades,
            }

            # ── 4. Execute ──
            try:
                if use_fast:
                    results = self._execute_fast(df, strategy_instance, callback, exec_config)
                else:
                    results = self._execute_legacy(df, strategy_instance, callback, exec_config)
                status = "success"
                error = None
            except Exception as exec_err:
                logger.error(f"Execution runtime error: {exec_err}")
                logger.error(traceback.format_exc())
                status = "failed"
                error = f"{str(exec_err)}\n\nTraceback:\n{traceback.format_exc()}"
                results = {"metrics": {}, "trades": [], "chart_data": []}

            # ── 5. Post-process: equity rescaling, equity curve ──
            if status == "success":
                results['trades'] = self._rescale_trades_for_equity(results['trades'], exec_config)
                results['chart_data'] = self._build_equity_curve(
                    results['trades'], initial_capital, mode
                )
                # Recompute metrics after rescaling
                results['metrics'] = PerformanceEngine.calculate_metrics(
                    results['trades'], initial_capital=initial_capital, mode=mode
                )

            # ── 6. Attach Metadata ──
            results['dataset_id'] = dataset_id
            results['strategy'] = strategy_name
            results['version'] = version
            results['symbol'] = metadata['symbol']
            results['status'] = status
            results['error'] = error
            results['parameters'] = parameters or {}
            results['mode'] = mode
            results['initial_capital'] = initial_capital
            results['sanitization'] = sanitization_report

            return results

        except (BacktestError, SanitizationError, QLMSystemError):
            raise
        except Exception as e:
            logger.error(f"Backtest initialisation failed: {e}")
            logger.error(traceback.format_exc())
            raise BacktestError(str(e), phase="init")

    # ─── Fast Engine Path ───────────────────────────────────────────────────

    def _execute_fast(self, df: pd.DataFrame, strategy: Strategy, callback=None,
                      exec_config: dict = None, precalc_arrays: tuple = None) -> Dict[str, Any]:
        """High-Performance Numba Execution with Realistic Market Simulation."""
        if exec_config is None:
            exec_config = {
                "mode": "capital", "initial_capital": 10000.0,
                "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
            }

        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # 1. Vectorised Variables & Signals
        vars_dict = strategy.define_variables(df)
        entry_long_series = strategy.entry_long(df, vars_dict).fillna(False)
        entry_short_series = strategy.entry_short(df, vars_dict).fillna(False)
        entry_long = entry_long_series.values.astype(bool)
        entry_short = entry_short_series.values.astype(bool)
        exit_long = strategy.exit_long_signal(df, vars_dict).fillna(False).values.astype(bool)
        exit_short = strategy.exit_short_signal(df, vars_dict).fillna(False).values.astype(bool)

        # 2. Risk Model
        risk = strategy.risk_model(df, vars_dict)
        sl_series, tp_series = self._resolve_risk(risk, df, entry_long_series, entry_short_series)
        sl_arr = sl_series.fillna(np.nan).values.astype(float)
        tp_arr = tp_series.fillna(np.nan).values.astype(float)

        # 3. Position Size
        size_arr = self._compute_size_arr(df, strategy, vars_dict, sl_arr, exec_config)

        # 4. Realism Arrays
        slippage_arr = self._compute_slippage_arr(n_rows, exec_config)
        spread_arr = self._compute_spread_arr(n_rows, exec_config)
        entry_on_next_bar = exec_config.get("entry_on_next_bar", False)

        # 5. Market Closure & Spike Arrays
        if '_market_closed' in df.columns:
            market_closed = df['_market_closed'].values.astype(np.bool_)
        else:
            market_closed = np.zeros(n_rows, dtype=np.bool_)

        if '_spike_bar' in df.columns:
            spike_bars = df['_spike_bar'].values.astype(np.bool_)
        else:
            spike_bars = np.zeros(n_rows, dtype=np.bool_)

        # 6. Data Arrays
        if precalc_arrays:
            opens, highs, lows, closes, times = precalc_arrays
        else:
            opens = df['open'].values.astype(float)
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            closes = df['close'].values.astype(float)
            times = df['dtv'].values.astype(np.int64)

        if callback:
            callback(10, "Running Fast Engine...", {})

        # 7. Run Numba Loop
        (entry_times, exit_times, entry_prices, exit_prices, pnls, reasons,
         directions, maes, mfes, entry_indices) = run_numba_backtest(
            opens, highs, lows, closes, times,
            entry_long, entry_short, exit_long, exit_short,
            sl_arr, tp_arr, size_arr,
            slippage_arr, spread_arr, entry_on_next_bar,
            market_closed, spike_bars,
        )

        if callback:
            callback(90, "Calculating Metrics...", {})

        # 8. Reconstruct Trades & Apply Commissions
        reason_map = {1: "SL Hit", 2: "TP Hit", 3: "Signal", 4: "End of Data"}
        trades = []

        for i in range(len(entry_times)):
            entry_px = float(entry_prices[i])
            exit_px = float(exit_prices[i])

            # Invalidate zero prices
            if entry_px == 0.0 or exit_px == 0.0:
                continue

            # Weekend trade filter (additional safety beyond market_closed array)
            if exec_config.get("skip_weekend_trades", True):
                entry_dt = pd.to_datetime(int(entry_times[i]), unit='ns', utc=True)
                exit_dt = pd.to_datetime(int(exit_times[i]), unit='ns', utc=True)
                if entry_dt.weekday() >= 5 or exit_dt.weekday() >= 5:
                    continue

            r_code = reasons[i]
            reason_str = reason_map.get(int(r_code), "Unknown")
            direction_str = "long" if directions[i] == 1 else "short"
            gross_pnl = float(pnls[i])

            entry_idx = int(entry_indices[i])
            trade_size = float(size_arr[entry_idx]) if entry_idx < len(size_arr) else 1.0

            trade_obj = {"entry_price": entry_px, "exit_price": exit_px, "size": trade_size}
            comm = CommissionModel.apply_to_trade(trade_obj, self.commission_model)

            initial_sl = sl_arr[entry_idx] if entry_idx < len(sl_arr) else np.nan
            initial_risk = abs(entry_px - float(initial_sl)) * trade_size if not np.isnan(initial_sl) else 0.0

            sl_val = float(sl_arr[entry_idx]) if entry_idx < len(sl_arr) else None
            tp_val = float(tp_arr[entry_idx]) if entry_idx < len(tp_arr) else None

            trade = self._build_trade_record(
                entry_time_ns=int(entry_times[i]),
                exit_time_ns=int(exit_times[i]),
                entry_price=entry_px,
                exit_price=exit_px,
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
        mode_val = exec_config.get("mode", "capital")
        metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial_capital, mode=mode_val)

        return {"metrics": metrics, "trades": trades, "chart_data": []}

    # ─── Legacy Engine Path ─────────────────────────────────────────────────

    def _execute_legacy(self, df: pd.DataFrame, strategy: Strategy, callback=None,
                        exec_config: dict = None) -> Dict[str, Any]:
        """
        Python Loop Execution with full parity to Fast Engine.
        Includes: slippage, spread, next-bar entry, gap-through SL/TP,
        SL/TP ambiguity resolution, market-closure skipping, spike bar rejection.
        """
        if exec_config is None:
            exec_config = {
                "mode": "capital", "initial_capital": 10000.0,
                "leverage": 1.0, "position_sizing": "fixed", "fixed_size": 1.0,
            }

        n_rows = len(df)
        if n_rows == 0:
            return {"metrics": {}, "trades": [], "chart_data": []}

        # Variables & Signals
        vars_dict = strategy.define_variables(df)
        long_signals = strategy.entry_long(df, vars_dict).fillna(False).astype(bool)
        short_signals = strategy.entry_short(df, vars_dict).fillna(False).astype(bool)

        risk = strategy.risk_model(df, vars_dict)
        sl_series, tp_series = self._resolve_risk(risk, df, long_signals, short_signals)
        sl_arr = sl_series.fillna(np.nan).values
        tp_arr = tp_series.fillna(np.nan).values

        size_arr = self._compute_size_arr(df, strategy, vars_dict, sl_arr, exec_config)
        slippage_arr = self._compute_slippage_arr(n_rows, exec_config)
        spread_arr = self._compute_spread_arr(n_rows, exec_config)
        entry_on_next_bar = exec_config.get("entry_on_next_bar", False)

        # Market closure & spike arrays
        market_closed = df['_market_closed'].values if '_market_closed' in df.columns else np.zeros(n_rows, dtype=bool)
        spike_bars = df['_spike_bar'].values if '_spike_bar' in df.columns else np.zeros(n_rows, dtype=bool)

        trades = []
        active_trade = None
        pending_entry = None

        opens = df['open'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        closes = df['close'].values.astype(float)
        times = df['dtv'].values.astype(np.int64)
        sig_long = long_signals.values
        sig_short = short_signals.values

        for i in range(n_rows):
            try:
                current_time = int(times[i])
                open_p = float(opens[i])
                high_p = float(highs[i])
                low_p = float(lows[i])
                close_p = float(closes[i])
            except (ValueError, TypeError):
                continue

            is_closed = bool(market_closed[i])
            is_spike = bool(spike_bars[i])

            if callback and i % (max(1, n_rows // 100)) == 0:
                progress = (i / n_rows) * 100
                display_time = pd.to_datetime(current_time, unit='ns', utc=True).strftime('%Y-%m-%d %H:%M:%S')
                callback(progress, "Running Legacy", {"current_time": display_time})

            # ── Handle Pending Entry ──
            if pending_entry is not None and active_trade is None:
                if is_closed or is_spike:
                    pending_entry = None
                else:
                    sig_idx = pending_entry['_signal_idx']
                    slip = float(slippage_arr[sig_idx])
                    half_spread = float(spread_arr[sig_idx]) / 2.0

                    if pending_entry['_direction'] == 'long':
                        entry_px = open_p + slip + half_spread
                    else:
                        entry_px = open_p - slip - half_spread

                    sl_val = float(sl_arr[sig_idx]) if not np.isnan(sl_arr[sig_idx]) else None
                    tp_val = float(tp_arr[sig_idx]) if not np.isnan(tp_arr[sig_idx]) else None
                    size_val = float(size_arr[sig_idx]) if not np.isnan(size_arr[sig_idx]) else 1.0
                    risk_val = abs(entry_px - sl_val) * size_val if sl_val is not None else 0.0

                    active_trade = {
                        "_entry_time_ns": current_time,
                        "_entry_price": entry_px,
                        "_direction": pending_entry['_direction'],
                        "_sl": sl_val, "_tp": tp_val,
                        "_size": size_val, "_initial_risk": risk_val,
                        "_mae": 0.0, "_mfe": 0.0,
                    }
                    pending_entry = None

                    # Entry-bar MAE/MFE
                    if active_trade['_direction'] == 'long':
                        mfe_val = high_p - active_trade['_entry_price']
                        mae_val = active_trade['_entry_price'] - low_p
                    else:
                        mfe_val = active_trade['_entry_price'] - low_p
                        mae_val = high_p - active_trade['_entry_price']
                    if mfe_val > 0 and mfe_val > active_trade['_mfe']:
                        active_trade['_mfe'] = mfe_val
                    if mae_val > 0 and mae_val > active_trade['_mae']:
                        active_trade['_mae'] = mae_val

                    continue  # Don't check exit on entry bar

            # ── Check Exit ──
            if active_trade:
                if is_closed:
                    continue  # Freeze trade during market closure

                exit_price = 0.0
                exit_reason = ""

                curr_sl = active_trade.get('_sl')
                curr_tp = active_trade.get('_tp')

                if active_trade['_direction'] == 'long':
                    # Update MAE/MFE
                    excursion_up = high_p - active_trade['_entry_price']
                    excursion_down = active_trade['_entry_price'] - low_p
                    if excursion_up > active_trade['_mfe']:
                        active_trade['_mfe'] = excursion_up
                    if excursion_down > active_trade['_mae']:
                        active_trade['_mae'] = excursion_down

                    sl_valid = curr_sl is not None and not np.isnan(curr_sl)
                    tp_valid = curr_tp is not None and not np.isnan(curr_tp)
                    sl_hit = sl_valid and low_p <= curr_sl
                    tp_hit = tp_valid and high_p >= curr_tp

                    if sl_hit and tp_hit:
                        # Ambiguity resolution
                        if open_p <= curr_sl:
                            exit_price, exit_reason = open_p, "SL Hit"
                        elif open_p >= curr_tp:
                            exit_price, exit_reason = open_p, "TP Hit"
                        else:
                            exit_price, exit_reason = curr_sl, "SL Hit"
                    elif sl_hit:
                        exit_price = open_p if open_p < curr_sl else curr_sl
                        exit_reason = "SL Hit"
                    elif tp_hit:
                        exit_price = open_p if open_p > curr_tp else curr_tp
                        exit_reason = "TP Hit"

                elif active_trade['_direction'] == 'short':
                    excursion_up = active_trade['_entry_price'] - low_p
                    excursion_down = high_p - active_trade['_entry_price']
                    if excursion_up > active_trade['_mfe']:
                        active_trade['_mfe'] = excursion_up
                    if excursion_down > active_trade['_mae']:
                        active_trade['_mae'] = excursion_down

                    sl_valid = curr_sl is not None and not np.isnan(curr_sl)
                    tp_valid = curr_tp is not None and not np.isnan(curr_tp)
                    sl_hit = sl_valid and high_p >= curr_sl
                    tp_hit = tp_valid and low_p <= curr_tp

                    if sl_hit and tp_hit:
                        if open_p >= curr_sl:
                            exit_price, exit_reason = open_p, "SL Hit"
                        elif open_p <= curr_tp:
                            exit_price, exit_reason = open_p, "TP Hit"
                        else:
                            exit_price, exit_reason = curr_sl, "SL Hit"
                    elif sl_hit:
                        exit_price = open_p if open_p > curr_sl else curr_sl
                        exit_reason = "SL Hit"
                    elif tp_hit:
                        exit_price = open_p if open_p < curr_tp else curr_tp
                        exit_reason = "TP Hit"

                # Signal exit check (if SL/TP didn't trigger)
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

                # Update MAE/MFE with exit excursion
                if exit_reason == "SL Hit":
                    if active_trade['_direction'] == 'long':
                        sl_mae = active_trade['_entry_price'] - exit_price
                        if sl_mae > active_trade['_mae']:
                            active_trade['_mae'] = sl_mae
                    else:
                        sl_mae = exit_price - active_trade['_entry_price']
                        if sl_mae > active_trade['_mae']:
                            active_trade['_mae'] = sl_mae
                elif exit_reason == "TP Hit":
                    if active_trade['_direction'] == 'long':
                        tp_mfe = exit_price - active_trade['_entry_price']
                        if tp_mfe > active_trade['_mfe']:
                            active_trade['_mfe'] = tp_mfe
                    else:
                        tp_mfe = active_trade['_entry_price'] - exit_price
                        if tp_mfe > active_trade['_mfe']:
                            active_trade['_mfe'] = tp_mfe

                if exit_reason:
                    trade_size = active_trade.get('_size', 1.0)

                    # Apply slippage/spread to exit
                    slip = float(slippage_arr[i])
                    half_spread = float(spread_arr[i]) / 2.0
                    if exit_reason == "Signal":
                        if active_trade['_direction'] == 'long':
                            exit_price -= slip + half_spread
                        else:
                            exit_price += slip + half_spread
                    elif exit_reason == "SL Hit":
                        if active_trade['_direction'] == 'long':
                            exit_price -= slip
                        else:
                            exit_price += slip

                    if active_trade['_direction'] == 'long':
                        gross_pnl = (exit_price - active_trade['_entry_price']) * trade_size
                    else:
                        gross_pnl = (active_trade['_entry_price'] - exit_price) * trade_size

                    # Invalidate zero prices
                    if active_trade['_entry_price'] == 0.0 or exit_price == 0.0:
                        active_trade = None
                        continue

                    # Weekend filter
                    if exec_config.get("skip_weekend_trades", True):
                        entry_dt = pd.to_datetime(int(active_trade['_entry_time_ns']), unit='ns', utc=True)
                        exit_dt = pd.to_datetime(int(current_time), unit='ns', utc=True)
                        if entry_dt.weekday() >= 5 or exit_dt.weekday() >= 5:
                            active_trade = None
                            continue

                    trade_obj = {
                        "entry_price": active_trade['_entry_price'],
                        "exit_price": exit_price,
                        "size": trade_size,
                    }
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

            # ── Check Entry ──
            if not active_trade and pending_entry is None:
                if is_closed or is_spike:
                    continue

                try:
                    is_long = sig_long[i]
                    is_short = sig_short[i]

                    if is_long or is_short:
                        direction = "long" if is_long else "short"

                        if entry_on_next_bar:
                            if i + 1 < n_rows:
                                pending_entry = {"_direction": direction, "_signal_idx": i}
                        else:
                            slip = float(slippage_arr[i])
                            half_spread = float(spread_arr[i]) / 2.0
                            if direction == 'long':
                                entry_px = close_p + slip + half_spread
                            else:
                                entry_px = close_p - slip - half_spread

                            sl_val = float(sl_arr[i]) if not np.isnan(sl_arr[i]) else None
                            tp_val = float(tp_arr[i]) if not np.isnan(tp_arr[i]) else None
                            size_val = float(size_arr[i]) if not np.isnan(size_arr[i]) else 1.0
                            risk_val = abs(entry_px - sl_val) * size_val if sl_val is not None else 0.0

                            active_trade = {
                                "_entry_time_ns": current_time,
                                "_entry_price": entry_px,
                                "_direction": direction,
                                "_sl": sl_val, "_tp": tp_val,
                                "_size": size_val, "_initial_risk": risk_val,
                                "_mae": 0.0, "_mfe": 0.0,
                            }
                except Exception as e:
                    logger.warning(f"Signal processing failed at idx {i}: {e}")

        # Force-close any open trade at end of data
        if active_trade:
            last_close = float(closes[-1])
            last_time = int(times[-1])
            trade_size = active_trade.get('_size', 1.0)

            slip = float(slippage_arr[-1])
            half_spread = float(spread_arr[-1]) / 2.0
            if active_trade['_direction'] == 'long':
                last_close = last_close - slip - half_spread
                gross_pnl = (last_close - active_trade['_entry_price']) * trade_size
            else:
                last_close = last_close + slip + half_spread
                gross_pnl = (active_trade['_entry_price'] - last_close) * trade_size

            trade_obj = {
                "entry_price": active_trade['_entry_price'],
                "exit_price": last_close,
                "size": trade_size,
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
        mode_val = exec_config.get("mode", "capital")
        metrics = PerformanceEngine.calculate_metrics(trades, initial_capital=initial_capital, mode=mode_val)

        return {"metrics": metrics, "trades": trades, "chart_data": []}
