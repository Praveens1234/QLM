"""
QLM Performance Metrics Engine.

Calculates detailed performance metrics from a list of trades.
Supports dual-mode: Capital (USD) and RRR (R-multiples).
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger("QLM.Metrics")


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Safe division — returns `default` if divisor is zero, NaN, or inf."""
    if b == 0.0 or np.isnan(b) or np.isinf(b):
        return default
    result = a / b
    if np.isnan(result) or np.isinf(result):
        return default
    return result


class PerformanceEngine:
    """
    Calculates detailed performance metrics from a list of trades.
    Supports dual-mode: Capital (USD) and RRR (R-multiples).
    """

    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float = 10000.0,
                          mode: str = "capital") -> Dict[str, Any]:
        if not trades:
            return PerformanceEngine._empty_metrics(initial_capital, mode)

        try:
            df = pd.DataFrame(trades)

            # Ensure necessary columns
            for col in ['pnl', 'duration', 'exit_time', 'direction', 'r_multiple', 'mae', 'mfe']:
                if col not in df.columns:
                    df[col] = 0.0

            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0.0)
            df['r_multiple'] = pd.to_numeric(df['r_multiple'], errors='coerce').fillna(0.0)
            df['mae'] = pd.to_numeric(df['mae'], errors='coerce').fillna(0.0)
            df['mfe'] = pd.to_numeric(df['mfe'], errors='coerce').fillna(0.0)

            if 'gross_pnl' in df.columns:
                df['gross_pnl'] = pd.to_numeric(df['gross_pnl'], errors='coerce').fillna(0.0)
            else:
                df['gross_pnl'] = df['pnl']

            # ── Basic Counts ──
            total_trades = len(df)
            winning = df[df['pnl'] > 0]
            losing = df[df['pnl'] < 0]       # Fixed: pnl < 0 (not <=)
            scratch = df[df['pnl'] == 0]

            win_count = len(winning)
            loss_count = len(losing)
            scratch_count = len(scratch)
            win_rate = _safe_div(win_count, total_trades) * 100

            total_long = int((df['direction'] == 'long').sum())
            total_short = int((df['direction'] == 'short').sum())

            # ── PnL Metrics ──
            net_profit = float(df['pnl'].sum())
            gross_profit = float(winning['pnl'].sum())
            gross_loss = abs(float(losing['pnl'].sum()))

            profit_factor = _safe_div(gross_profit, gross_loss)
            if gross_loss == 0 and gross_profit > 0:
                profit_factor = 9999.99  # Capped — no losses
            avg_win = float(winning['pnl'].mean()) if win_count > 0 else 0.0
            avg_loss = float(losing['pnl'].mean()) if loss_count > 0 else 0.0
            avg_pnl = float(df['pnl'].mean())

            # ── Equity Curve & Drawdown ──
            df = df.sort_values(by='exit_time')
            equity_pnl = df['gross_pnl'] if mode == "rrr" else df['pnl']
            equity_series = initial_capital + equity_pnl.cumsum()
            equity_curve = pd.concat([pd.Series([initial_capital]), equity_series])

            peak = equity_curve.cummax()
            drawdown = equity_curve - peak
            max_drawdown = abs(float(drawdown.min()))
            drawdown_pct = (drawdown / peak.replace(0, 1)) * 100
            max_drawdown_pct = abs(float(drawdown_pct.min()))

            max_runup = float(equity_curve.max() - initial_capital)
            if max_runup < 0:
                max_runup = 0.0

            final_equity = float(equity_series.iloc[-1]) if len(equity_series) > 0 else initial_capital

            # ── Time Analysis ──
            trades_per_day = 0.0
            trading_days = 1
            try:
                exit_times = pd.to_datetime(df['exit_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                start_time = exit_times.min()
                end_time = exit_times.max()
                if pd.notna(start_time) and pd.notna(end_time):
                    delta_days = max(1, (end_time - start_time).days)
                    trading_days = delta_days
                    trades_per_day = _safe_div(total_trades, delta_days)
            except Exception:
                pass

            # ── Risk Metrics ──
            std_dev = float(df['pnl'].std(ddof=1)) if total_trades > 1 else 0.0

            # SQN (System Quality Number)
            sqn = _safe_div((total_trades ** 0.5) * avg_pnl, std_dev) if std_dev > 0 else 0.0

            # Sharpe Ratio — annualised (assume ~252 trading days)
            sharpe_per_trade = _safe_div(avg_pnl, std_dev)
            # Estimate annualised: Sharpe_annual = Sharpe_per_trade * sqrt(trades_per_year)
            est_trades_per_year = trades_per_day * 252 if trades_per_day > 0 else total_trades
            sharpe_annual = sharpe_per_trade * (est_trades_per_year ** 0.5) if est_trades_per_year > 0 else 0.0

            # Sortino Ratio — annualised
            downside_returns = np.minimum(0, df['pnl'].values)
            downside_sq_sum = float((downside_returns ** 2).sum())
            downside_std = (downside_sq_sum / total_trades) ** 0.5 if total_trades > 0 else 0.0
            sortino_per_trade = _safe_div(avg_pnl, downside_std)
            sortino_annual = sortino_per_trade * (est_trades_per_year ** 0.5) if est_trades_per_year > 0 else 0.0

            # VaR (95%)
            var_95 = float(np.percentile(df['pnl'], 5)) if total_trades > 0 else 0.0

            # Expectancy
            expectancy = avg_pnl

            # Duration
            avg_duration = float(df['duration'].mean()) if total_trades > 0 else 0.0
            max_duration = float(df['duration'].max()) if total_trades > 0 else 0.0
            min_duration = float(df['duration'].min()) if total_trades > 0 else 0.0

            # MAE/MFE
            avg_mae = float(df['mae'].mean())
            avg_mfe = float(df['mfe'].mean())

            # R-Multiple
            avg_r = float(df['r_multiple'].mean())

            # Max Consecutive Wins / Losses
            max_consec_wins = 0
            max_consec_losses = 0
            streak = 0
            for pnl_val in df['pnl'].values:
                if pnl_val > 0:
                    streak = streak + 1 if streak > 0 else 1
                    max_consec_wins = max(max_consec_wins, streak)
                elif pnl_val < 0:
                    streak = streak - 1 if streak < 0 else -1
                    max_consec_losses = max(max_consec_losses, abs(streak))
                else:
                    streak = 0  # Scratch resets streak

            # Calmar Ratio
            calmar_ratio = 0.0
            if max_drawdown > 0 and trading_days > 0:
                years = max(trading_days / 365.25, 1 / 365.25)
                annualized_return = net_profit / years
                calmar_ratio = _safe_div(annualized_return, max_drawdown)

            # CAGR
            cagr = 0.0
            if mode == "capital" and final_equity > 0 and initial_capital > 0 and trading_days > 30:
                years = trading_days / 365.25
                if years > 0:
                    cagr = ((final_equity / initial_capital) ** _safe_div(1.0, years, 1.0) - 1) * 100

            # ROI
            roi_pct = _safe_div(net_profit, initial_capital) * 100 if mode == "capital" else 0.0

            unit = "USD" if mode == "capital" else "R"

            return {
                "mode": mode,
                "unit": unit,
                "total_trades": int(total_trades),
                "total_long": total_long,
                "total_short": total_short,
                "total_wins": int(win_count),
                "total_losses": int(loss_count),
                "win_rate": round(win_rate, 2),
                "net_profit": round(net_profit, 2),
                "roi_pct": round(roi_pct, 2),
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(max_drawdown, 2),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "max_runup": round(max_runup, 2),
                "expectancy": round(expectancy, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "avg_r_multiple": round(avg_r, 4),
                "sharpe_ratio": round(sharpe_annual, 4),
                "sortino_ratio": round(sortino_annual, 4),
                "sqn": round(sqn, 2),
                "var_95": round(var_95, 2),
                "cagr": round(cagr, 2),
                "avg_duration": round(avg_duration, 2),
                "max_duration": round(max_duration, 2),
                "min_duration": round(min_duration, 2),
                "trades_per_day": round(trades_per_day, 2),
                "avg_mae": round(avg_mae, 2),
                "avg_mfe": round(avg_mfe, 2),
                "max_consecutive_wins": int(max_consec_wins),
                "max_consecutive_losses": int(max_consec_losses),
                "calmar_ratio": round(calmar_ratio, 4),
                "initial_capital": float(initial_capital),
                "final_equity": round(final_equity, 2) if mode == "capital" else round(float(initial_capital), 2),
            }
        except Exception as e:
            import traceback
            logger.error(f"Metric calculation failed: {e}\n{traceback.format_exc()}")
            return PerformanceEngine._empty_metrics(initial_capital, mode)

    @staticmethod
    def _empty_metrics(initial_capital: float = 10000.0, mode: str = "capital"):
        unit = "USD" if mode == "capital" else "R"
        return {
            "mode": mode, "unit": unit,
            "total_trades": 0, "total_long": 0, "total_short": 0,
            "total_wins": 0, "total_losses": 0,
            "win_rate": 0.0, "net_profit": 0.0, "roi_pct": 0.0,
            "profit_factor": 0.0, "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
            "max_runup": 0.0, "expectancy": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0,
            "avg_r_multiple": 0.0, "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
            "sqn": 0.0, "var_95": 0.0, "cagr": 0.0,
            "avg_duration": 0.0, "max_duration": 0.0, "min_duration": 0.0,
            "trades_per_day": 0.0, "avg_mae": 0.0, "avg_mfe": 0.0,
            "max_consecutive_wins": 0, "max_consecutive_losses": 0,
            "calmar_ratio": 0.0,
            "initial_capital": float(initial_capital),
            "final_equity": float(initial_capital),
        }
