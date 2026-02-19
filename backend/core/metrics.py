import pandas as pd
import numpy as np
from typing import List, Dict, Any

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

            # Ensure necessary columns exist
            for col in ['pnl', 'duration', 'exit_time', 'direction', 'r_multiple', 'mae', 'mfe']:
                if col not in df.columns:
                    df[col] = 0.0

            # Ensure PnL is numeric
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0.0)
            df['r_multiple'] = pd.to_numeric(df['r_multiple'], errors='coerce').fillna(0.0)
            df['mae'] = pd.to_numeric(df['mae'], errors='coerce').fillna(0.0)
            df['mfe'] = pd.to_numeric(df['mfe'], errors='coerce').fillna(0.0)

            # For RRR mode metrics, we might need gross_pnl for equity calculations
            if 'gross_pnl' in df.columns:
                df['gross_pnl'] = pd.to_numeric(df['gross_pnl'], errors='coerce').fillna(0.0)
            else:
                df['gross_pnl'] = df['pnl']

            # --- Basic Counts ---
            total_trades = len(df)
            winning_trades = df[df['pnl'] > 0]
            losing_trades = df[df['pnl'] <= 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

            # Direction Counts
            total_long = int((df['direction'] == 'long').sum())
            total_short = int((df['direction'] == 'short').sum())
            total_wins = win_count
            total_losses = loss_count

            # --- PnL Metrics ---
            net_profit = df['pnl'].sum()
            gross_profit = winning_trades['pnl'].sum()
            gross_loss = abs(losing_trades['pnl'].sum())

            profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float('inf')
            if gross_loss == 0 and gross_profit == 0:
                profit_factor = 0.0

            avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0.0
            avg_loss = losing_trades['pnl'].mean() if loss_count > 0 else 0.0
            avg_pnl = df['pnl'].mean()

            # --- Equity Curve & Drawdown / Runup ---
            df = df.sort_values(by='exit_time')

            # Use gross_pnl for equity curve in both modes (equity is always USD)
            equity_pnl = df['gross_pnl'] if mode == "rrr" else df['pnl']
            equity_series = initial_capital + equity_pnl.cumsum()
            equity_curve = pd.concat([pd.Series([initial_capital]), equity_series])

            # Drawdown
            peak = equity_curve.cummax()
            drawdown = equity_curve - peak
            max_drawdown = abs(drawdown.min())
            drawdown_pct = (drawdown / peak.replace(0, 1)) * 100
            max_drawdown_pct = abs(drawdown_pct.min())

            # Max Runup (max equity peak above initial capital)
            max_runup = equity_curve.max() - initial_capital
            if max_runup < 0:
                max_runup = 0.0

            # --- Advanced Risk Metrics ---

            # Standard Deviation of Returns (Trade-based)
            std_dev = df['pnl'].std(ddof=1)

            # SQN (System Quality Number)
            if std_dev > 0 and total_trades > 0:
                sqn = (total_trades ** 0.5) * (avg_pnl / std_dev)
            else:
                sqn = 0.0

            # Sharpe Ratio (Approximate Trade-based)
            sharpe_per_trade = (avg_pnl / std_dev) if std_dev > 0 else 0.0

            # Sortino Ratio (Downside Deviation)
            target_return = 0.0
            downside_sq_sum = (np.minimum(0, df['pnl'] - target_return) ** 2).sum()
            downside_std = np.sqrt(downside_sq_sum / total_trades) if total_trades > 0 else 0.0
            sortino = (avg_pnl / downside_std) if downside_std > 0 else 0.0
            if pd.isna(sortino): sortino = 0.0

            # Value at Risk (VaR) - 95% Confidence
            var_95 = np.percentile(df['pnl'], 5)

            # Expectancy
            expectancy = avg_pnl

            # Duration Analysis
            avg_duration = df['duration'].mean() if total_trades > 0 else 0.0
            max_duration = df['duration'].max() if total_trades > 0 else 0.0
            min_duration = df['duration'].min() if total_trades > 0 else 0.0

            # Time Analysis
            trades_per_day = 0.0
            if total_trades > 0:
                try:
                    start_time = pd.to_datetime(df['exit_time'], errors='coerce').min()
                    end_time = pd.to_datetime(df['exit_time'], errors='coerce').max()
                    if pd.notna(start_time) and pd.notna(end_time):
                        delta_days = (end_time - start_time).days
                        if delta_days > 0:
                            trades_per_day = total_trades / delta_days
                        else:
                            trades_per_day = total_trades
                except Exception:
                    pass

            # MAE/MFE Analysis
            avg_mae = df['mae'].mean() if 'mae' in df.columns else 0.0
            avg_mfe = df['mfe'].mean() if 'mfe' in df.columns else 0.0

            # R-Multiple Analysis
            avg_r = df['r_multiple'].mean() if 'r_multiple' in df.columns else 0.0

            # Return on Capital
            roi_pct = (net_profit / initial_capital) * 100 if mode == "capital" else 0.0

            # Unit label
            unit = "USD" if mode == "capital" else "R"

            return {
                "mode": mode,
                "unit": unit,
                "total_trades": int(total_trades),
                "total_long": total_long,
                "total_short": total_short,
                "total_wins": int(total_wins),
                "total_losses": int(total_losses),
                "win_rate": round(float(win_rate), 2),
                "net_profit": round(float(net_profit), 2),
                "roi_pct": round(float(roi_pct), 2),
                "profit_factor": round(float(profit_factor), 2),
                "max_drawdown": round(float(max_drawdown), 2),
                "max_drawdown_pct": round(float(max_drawdown_pct), 2),
                "max_runup": round(float(max_runup), 2),
                "expectancy": round(float(expectancy), 2),
                "avg_win": round(float(avg_win), 2),
                "avg_loss": round(float(avg_loss), 2),
                "avg_r_multiple": round(float(avg_r), 4),
                "sharpe_ratio": round(float(sharpe_per_trade), 4),
                "sortino_ratio": round(float(sortino), 4),
                "sqn": round(float(sqn), 2),
                "var_95": round(float(var_95), 2),
                "avg_duration": round(float(avg_duration), 2),
                "max_duration": round(float(max_duration), 2),
                "min_duration": round(float(min_duration), 2),
                "trades_per_day": round(float(trades_per_day), 2),
                "avg_mae": round(float(avg_mae), 2),
                "avg_mfe": round(float(avg_mfe), 2),
                "initial_capital": float(initial_capital),
                "final_equity": round(float(initial_capital + net_profit), 2) if mode == "capital" else round(float(initial_capital), 2),
            }
        except Exception as e:
            import logging
            import traceback
            logging.getLogger("QLM.Metrics").error(f"Metric calculation failed: {e}\n{traceback.format_exc()}")
            return PerformanceEngine._empty_metrics(initial_capital, mode)

    @staticmethod
    def _empty_metrics(initial_capital: float = 10000.0, mode: str = "capital"):
        unit = "USD" if mode == "capital" else "R"
        return {
            "mode": mode,
            "unit": unit,
            "total_trades": 0,
            "total_long": 0,
            "total_short": 0,
            "total_wins": 0,
            "total_losses": 0,
            "win_rate": 0.0,
            "net_profit": 0.0,
            "roi_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "max_runup": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "avg_r_multiple": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "sqn": 0.0,
            "var_95": 0.0,
            "avg_duration": 0.0,
            "max_duration": 0.0,
            "min_duration": 0.0,
            "trades_per_day": 0.0,
            "avg_mae": 0.0,
            "avg_mfe": 0.0,
            "initial_capital": float(initial_capital),
            "final_equity": float(initial_capital),
        }
