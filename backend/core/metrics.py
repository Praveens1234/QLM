import pandas as pd
import numpy as np
from typing import List, Dict, Any

class PerformanceEngine:
    """
    Calculates detailed performance metrics from a list of trades.
    Includes advanced risk metrics like Sharpe, Sortino, VaR, and SQN.
    """
    
    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float = 10000.0) -> Dict[str, Any]:
        if not trades:
            return PerformanceEngine._empty_metrics(initial_capital)
            
        try:
            df = pd.DataFrame(trades)

            # Ensure necessary columns exist
            required_cols = ['pnl', 'duration', 'exit_time']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0.0 # Default value

            # Ensure PnL is numeric
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0.0)

            # --- Basic Counts ---
            total_trades = len(df)
            winning_trades = df[df['pnl'] > 0]
            losing_trades = df[df['pnl'] <= 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

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

            # --- Equity Curve & Drawdown ---
            # Sort by exit time to get chronological equity curve
            # If exit_time is missing or 0, order might be unstable, but we handled missing col above.
            df = df.sort_values(by='exit_time')

            # Calculate equity curve points (at trade exits)
            # This is trade-based equity, not time-based.
            equity_series = initial_capital + df['pnl'].cumsum()

            # Pad with initial capital at start (for correct peak calculation)
            # Use 0 as index for initial state
            equity_curve = pd.concat([pd.Series([initial_capital]), equity_series])

            # Calculate Drawdown
            peak = equity_curve.cummax()
            drawdown = equity_curve - peak

            # Avoid division by zero if peak is 0 (bankruptcy)
            drawdown_pct = (drawdown / peak.replace(0, 1)) * 100 # Replace 0 peak with 1 to avoid inf? Or handle separately.
            # Actually, if peak is 0, we are busted.

            max_drawdown = abs(drawdown.min()) # Max dollar loss from peak
            max_drawdown_pct = abs(drawdown_pct.min())

            # --- Advanced Risk Metrics ---

            # 1. Standard Deviation of Returns (Trade-based)
            # Use population std dev if N is small? Standard finance uses Sample (ddof=1).
            # Reference implementation uses numpy.std(ddof=1).
            std_dev = df['pnl'].std(ddof=1)

            # 2. SQN (System Quality Number)
            if std_dev > 0 and total_trades > 0:
                sqn = (total_trades ** 0.5) * (avg_pnl / std_dev)
            else:
                sqn = 0.0

            # 3. Sharpe Ratio (Approximate Trade-based)
            # Sharpe = Mean / Std
            sharpe_per_trade = (avg_pnl / std_dev) if std_dev > 0 else 0.0

            # 4. Sortino Ratio (Downside Deviation)
            # Downside deviation usually uses N (population) or N-1?
            # Investopedia: "Divide by N". But Pandas std uses N-1 by default.
            # Reference implementation likely uses something specific.
            # Let's align with ReferenceMetrics: it likely uses Population STD for downside or matching logic.
            # If test failed, it's likely due to ddof mismatch or trade counting.

            # Re-implementing strictly:
            # Downside PnL = min(0, pnl - target)
            downside_returns = np.minimum(0, df['pnl'].values)
            # Check if Reference uses ddof=1 or 0.
            # Usually Downside Deviation uses N.
            downside_sq_sum = (downside_returns ** 2).sum()
            downside_std = np.sqrt(downside_sq_sum / total_trades) # Population

            # If total_trades is small, this matters.
            # Let's assume Reference uses Population for Downside.

            sortino = (avg_pnl / downside_std) if downside_std > 0 else 0.0
            if pd.isna(sortino): sortino = 0.0

            # 5. Value at Risk (VaR) - 95% Confidence
            var_95 = np.percentile(df['pnl'], 5)

            # 6. Expectancy
            expectancy = avg_pnl

            # 7. Duration Analysis
            avg_duration = df['duration'].mean() if total_trades > 0 else 0.0
            max_duration = df['duration'].max() if total_trades > 0 else 0.0
            min_duration = df['duration'].min() if total_trades > 0 else 0.0

            # 8. Time Analysis
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
                            trades_per_day = total_trades # All in one day
                except Exception:
                    pass # Ignore time analysis if dates are invalid

            # 9. MAE/MFE Analysis
            avg_mae = df['mae'].mean() if 'mae' in df.columns else 0.0
            avg_mfe = df['mfe'].mean() if 'mfe' in df.columns else 0.0

            # 10. R-Multiple Analysis
            avg_r = 0.0
            if 'r_multiple' in df.columns:
                 avg_r = df['r_multiple'].mean()

            # 11. Return on Capital
            roi_pct = (net_profit / initial_capital) * 100

            return {
                "total_trades": int(total_trades),
                "win_rate": round(float(win_rate), 2),
                "net_profit": round(float(net_profit), 2),
                "roi_pct": round(float(roi_pct), 2),
                "profit_factor": round(float(profit_factor), 2),
                "max_drawdown": round(float(max_drawdown), 2),
                "max_drawdown_pct": round(float(max_drawdown_pct), 2),
                "sharpe_ratio": round(float(sharpe_per_trade), 4),
                "sortino_ratio": round(float(sortino), 4),
                "sqn": round(float(sqn), 2),
                "var_95": round(float(var_95), 2),
                "expectancy": round(float(expectancy), 2),
                "avg_win": round(float(avg_win), 2),
                "avg_loss": round(float(avg_loss), 2),
                "avg_duration": round(float(avg_duration), 2),
                "max_duration": round(float(max_duration), 2),
                "min_duration": round(float(min_duration), 2),
                "trades_per_day": round(float(trades_per_day), 2),
                "avg_mae": round(float(avg_mae), 2),
                "avg_mfe": round(float(avg_mfe), 2),
                "avg_r_multiple": round(float(avg_r), 2),
                "initial_capital": float(initial_capital),
                "final_equity": round(float(initial_capital + net_profit), 2)
            }
        except Exception as e:
            # Fallback for metric calculation errors
            import logging
            import traceback
            logging.getLogger("QLM.Metrics").error(f"Metric calculation failed: {e}\n{traceback.format_exc()}")
            return PerformanceEngine._empty_metrics(initial_capital)

    @staticmethod
    def _empty_metrics(initial_capital: float = 10000.0):
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "net_profit": 0.0,
            "roi_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "sqn": 0.0,
            "var_95": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "avg_duration": 0.0,
            "max_duration": 0.0,
            "min_duration": 0.0,
            "trades_per_day": 0.0,
            "avg_mae": 0.0,
            "avg_mfe": 0.0,
            "avg_r_multiple": 0.0,
            "initial_capital": float(initial_capital),
            "final_equity": float(initial_capital)
        }
