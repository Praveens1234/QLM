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
            return PerformanceEngine._empty_metrics()
            
        df_trades = pd.DataFrame(trades)
        
        # Basic Counts
        total_trades = len(df_trades)
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
        
        # PnL Metrics
        net_profit = df_trades['pnl'].sum()
        gross_profit = winning_trades['pnl'].sum()
        gross_loss = abs(losing_trades['pnl'].sum())
        
        profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        avg_profit = winning_trades['pnl'].mean() if win_count > 0 else 0
        avg_loss = losing_trades['pnl'].mean() if loss_count > 0 else 0
        
        # Drawdown
        # We need an equity curve to calculate DD accurately
        # Assuming fixed capital allocation or compound?
        # Let's assume simple accumulation for now to get equity curve
        df_trades = df_trades.sort_values(by='exit_time')
        equity_curve = initial_capital + df_trades['pnl'].cumsum()
        
        # Peak equity
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak)
        max_drawdown = drawdown.min() # This is a dollar amount
        max_drawdown_pct = (drawdown / peak).min() * 100 if not peak.empty else 0

        # Expectancy
        expectancy = net_profit / total_trades if total_trades > 0 else 0
        
        # Avg Duration
        avg_duration = df_trades['duration'].mean() if total_trades > 0 else 0
        
        return {
            "total_trades": int(total_trades),
            "win_rate": round(float(win_rate), 2),
            "net_profit": round(float(net_profit), 2),
            "profit_factor": round(float(profit_factor), 2),
            "max_drawdown": round(float(max_drawdown), 2),
            "max_drawdown_pct": round(float(max_drawdown_pct), 2),
            "expectancy": round(float(expectancy), 2),
            "avg_win": round(float(avg_profit), 2),
            "avg_loss": round(float(avg_loss), 2),
            "avg_duration": round(float(avg_duration), 2),
            "initial_capital": float(initial_capital),
            "final_equity": round(float(initial_capital + net_profit), 2)
        }

    @staticmethod
    def _empty_metrics():
        return {
            "total_trades": 0,
            "win_rate": 0,
            "net_profit": 0,
            "profit_factor": 0,
            "max_drawdown": 0,
            "expectancy": 0
        }
