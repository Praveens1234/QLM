import pandas as pd
import numpy as np
from typing import List, Dict, Any

class PerformanceEngine:
    """
    Calculates performance metrics from a list of trades.
    """
    
    @staticmethod
    def calculate_metrics(trades: List[Dict[str, Any]], initial_capital: float = 10000.0) -> Dict[str, Any]:
        if not trades:
            return PerformanceEngine._empty_metrics(initial_capital)
            
        try:
            df = pd.DataFrame(trades)

            # Ensure PnL is numeric
            df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0.0)
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0.0)

            # Basic Counts
            total_trades = len(df)
            winning_trades = df[df['pnl'] > 0]
            losing_trades = df[df['pnl'] <= 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

            # PnL Metrics
            net_profit = df['pnl'].sum()
            gross_profit = winning_trades['pnl'].sum()
            gross_loss = abs(losing_trades['pnl'].sum())

            profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float('inf')
            if gross_loss == 0 and gross_profit == 0:
                profit_factor = 0.0

            avg_win = winning_trades['pnl'].mean() if win_count > 0 else 0.0
            avg_loss = losing_trades['pnl'].mean() if loss_count > 0 else 0.0

            # Equity Curve & Drawdown
            # Sort by exit time to get chronological equity curve
            df = df.sort_values(by='exit_time')

            # Calculate equity curve
            equity = initial_capital + df['pnl'].cumsum()

            # Pad with initial capital at start for correct DD calculation
            equity_curve = pd.concat([pd.Series([initial_capital]), equity])

            peak = equity_curve.cummax()
            drawdown = equity_curve - peak

            max_drawdown = abs(drawdown.min()) # Max dollar loss from peak

            # Calculate Max DD %
            # Avoid division by zero if peak is 0 (bankruptcy)
            dd_pct = (drawdown / peak) * 100
            # Clean up potential Infs/NaNs
            dd_pct = dd_pct.replace([np.inf, -np.inf], 0).fillna(0)
            max_drawdown_pct = abs(dd_pct.min())

            # Expectancy
            expectancy = net_profit / total_trades if total_trades > 0 else 0.0

            # Avg Duration
            avg_duration = df['duration'].mean() if total_trades > 0 else 0.0

            return {
                "total_trades": int(total_trades),
                "win_rate": round(float(win_rate), 2),
                "net_profit": round(float(net_profit), 2),
                "profit_factor": round(float(profit_factor), 2),
                "max_drawdown": round(float(max_drawdown), 2),
                "max_drawdown_pct": round(float(max_drawdown_pct), 2),
                "expectancy": round(float(expectancy), 2),
                "avg_win": round(float(avg_win), 2),
                "avg_loss": round(float(avg_loss), 2),
                "avg_duration": round(float(avg_duration), 2),
                "initial_capital": float(initial_capital),
                "final_equity": round(float(initial_capital + net_profit), 2)
            }
        except Exception as e:
            # Fallback for metric calculation errors
            import logging
            logging.getLogger("QLM.Metrics").error(f"Metric calculation failed: {e}")
            return PerformanceEngine._empty_metrics(initial_capital)

    @staticmethod
    def _empty_metrics(initial_capital: float = 10000.0):
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "net_profit": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "expectancy": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "avg_duration": 0.0,
            "initial_capital": float(initial_capital),
            "final_equity": float(initial_capital)
        }
