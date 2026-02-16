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
            
        df = pd.DataFrame(trades)
        
        # --- Basic Counts ---
        total_trades = len(df)
        winning_trades = df[df['pnl'] > 0]
        losing_trades = df[df['pnl'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0
        
        # --- Long/Short Breakdown ---
        long_trades = df[df['direction'] == 'long']
        short_trades = df[df['direction'] == 'short']

        total_long = len(long_trades)
        total_short = len(short_trades)

        long_wins = len(long_trades[long_trades['pnl'] > 0])
        long_losses = len(long_trades[long_trades['pnl'] <= 0])
        short_wins = len(short_trades[short_trades['pnl'] > 0])
        short_losses = len(short_trades[short_trades['pnl'] <= 0])

        win_rate_long = (long_wins / total_long * 100) if total_long > 0 else 0.0
        win_rate_short = (short_wins / total_short * 100) if total_short > 0 else 0.0

        # --- PnL Metrics ---
        net_profit = df['pnl'].sum()
        gross_profit = winning_trades['pnl'].sum()
        gross_loss = abs(losing_trades['pnl'].sum())
        
        profit_factor = (gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        avg_profit = winning_trades['pnl'].mean() if win_count > 0 else 0.0
        avg_loss = losing_trades['pnl'].mean() if loss_count > 0 else 0.0
        
        # --- R-Multiples ---
        # If initial_risk is 0 or None, we can't calculate R for that trade.
        # We'll treat R as NaN for those trades or 0?
        # Typically R = PnL / Initial_Risk

        def calculate_r(row):
            risk = row.get('initial_risk', 0)
            if risk and risk > 0:
                return row['pnl'] / risk
            return 0.0 # Or np.nan

        df['R'] = df.apply(calculate_r, axis=1)

        total_r = df['R'].sum()
        avg_r_trade = df['R'].mean() if total_trades > 0 else 0.0
        avg_r_win = df[df['pnl'] > 0]['R'].mean() if win_count > 0 else 0.0
        avg_r_loss = df[df['pnl'] <= 0]['R'].mean() if loss_count > 0 else 0.0

        # --- Drawdown & Equity ---
        df = df.sort_values(by='exit_time')
        equity_curve = initial_capital + df['pnl'].cumsum()
        
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak)
        max_drawdown = abs(drawdown.min())
        max_drawdown_pct = abs((drawdown / peak).min() * 100) if not peak.empty else 0.0

        # Drawdown in R (Simulated cumulative R drawdown)
        r_curve = df['R'].cumsum()
        r_peak = r_curve.cummax()
        r_drawdown = r_curve - r_peak
        max_drawdown_r = abs(r_drawdown.min())

        # --- Expectancy ---
        # Expectancy = (Win % * Avg Win) - (Loss % * Avg Loss)
        # Or simply Net Profit / Total Trades
        expectancy = net_profit / total_trades if total_trades > 0 else 0.0
        expectancy_r = total_r / total_trades if total_trades > 0 else 0.0

        # --- Time Based Metrics ---
        # Convert entry_time to datetime if it's string
        df['entry_dt'] = pd.to_datetime(df['entry_time'])
        
        if not df.empty:
            duration_days = (df['entry_dt'].max() - df['entry_dt'].min()).days
            duration_days = max(1, duration_days) # Avoid div by zero

            avg_trades_day = total_trades / duration_days
            avg_trades_week = avg_trades_day * 7
            avg_trades_month = avg_trades_day * 30
        else:
            avg_trades_day = 0.0
            avg_trades_week = 0.0
            avg_trades_month = 0.0

        avg_duration = df['duration'].mean() if total_trades > 0 else 0.0
        
        return {
            "total_trades": int(total_trades),
            "win_rate": round(float(win_rate), 2),
            "win_rate_long": round(float(win_rate_long), 2),
            "win_rate_short": round(float(win_rate_short), 2),

            "total_long": int(total_long),
            "total_short": int(total_short),
            "long_wins": int(long_wins),
            "long_losses": int(long_losses),
            "short_wins": int(short_wins),
            "short_losses": int(short_losses),

            "net_profit": round(float(net_profit), 2),
            "profit_factor": round(float(profit_factor), 2),
            "expectancy": round(float(expectancy), 2),
            "expectancy_r": round(float(expectancy_r), 2),

            "max_drawdown": round(float(max_drawdown), 2),
            "max_drawdown_pct": round(float(max_drawdown_pct), 2),
            "max_drawdown_r": round(float(max_drawdown_r), 2),

            "total_r": round(float(total_r), 2),
            "avg_r_trade": round(float(avg_r_trade), 2),

            "avg_win": round(float(avg_profit), 2),
            "avg_loss": round(float(avg_loss), 2),
            "avg_duration": round(float(avg_duration), 2),

            "avg_trades_day": round(float(avg_trades_day), 2),
            "avg_trades_week": round(float(avg_trades_week), 2),
            "avg_trades_month": round(float(avg_trades_month), 2),

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
            "expectancy": 0,
            "win_rate_long": 0, "win_rate_short": 0,
            "total_long": 0, "total_short": 0,
            "long_wins": 0, "long_losses": 0,
            "short_wins": 0, "short_losses": 0,
            "expectancy_r": 0, "max_drawdown_r": 0, "total_r": 0,
            "avg_r_trade": 0,
            "avg_trades_day": 0, "avg_trades_week": 0, "avg_trades_month": 0
        }

    @staticmethod
    def generate_csv(trades: List[Dict[str, Any]]) -> str:
        """
        Generates a CSV string from the trade list.
        """
        if not trades:
            return ""

        import io
        import csv

        output = io.StringIO()
        # Define fields based on updated trade structure
        fieldnames = [
            "entry_time", "exit_time", "symbol", "direction", "status",
            "entry_price", "exit_price", "size", "pnl", "R",
            "initial_risk", "sl", "tp", "exit_reason",
            "max_runup", "max_drawdown_trade", "duration"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for trade in trades:
            # Calculate R if not present (it was calculated in calculate_metrics dataframe but maybe not in trade dict)
            # We should probably update the trade dicts with R during metrics calculation or do it here.
            # Doing it here for safety.
            row = trade.copy()
            risk = row.get('initial_risk', 0)
            if risk and risk > 0:
                row['R'] = row.get('pnl', 0) / risk
            else:
                row['R'] = 0.0

            writer.writerow(row)

        return output.getvalue()
