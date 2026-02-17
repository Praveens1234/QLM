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
            drawdown_pct = (drawdown / peak) * 100

            max_drawdown = abs(drawdown.min()) # Max dollar loss from peak
            max_drawdown_pct = abs(drawdown_pct.min())

            # --- Advanced Risk Metrics ---

            # 1. Standard Deviation of Returns (Trade-based)
            # We assume constant capital for % returns approximation or use dollar PnL std dev
            # SQN uses dollar PnL
            std_dev = df['pnl'].std()

            # 2. SQN (System Quality Number)
            # SQN = sqrt(N) * (Avg PnL / Std Dev)
            if std_dev > 0 and total_trades > 0:
                sqn = (total_trades ** 0.5) * (avg_pnl / std_dev)
            else:
                sqn = 0.0

            # 3. Sharpe Ratio (Approximate Trade-based)
            # Sharpe = (Mean Return / Std Dev) * sqrt(Trades/Year)
            # We don't know trades per year easily without dataset duration.
            # Using simple Sharpe per trade:
            sharpe_per_trade = (avg_pnl / std_dev) if std_dev > 0 else 0.0

            # 4. Sortino Ratio (Downside Deviation)
            downside_returns = df[df['pnl'] < 0]['pnl']
            downside_std = downside_returns.std()
            sortino = (avg_pnl / downside_std) if downside_std > 0 else 0.0
            if pd.isna(sortino): sortino = 0.0

            # 5. Value at Risk (VaR) - 95% Confidence
            # 5th percentile of trade PnL
            var_95 = np.percentile(df['pnl'], 5)

            # 6. Expectancy
            expectancy = avg_pnl

            # 7. Avg Duration
            avg_duration = df['duration'].mean() if total_trades > 0 else 0.0

            # 8. Return on Capital
            roi_pct = (net_profit / initial_capital) * 100

            return {
                "total_trades": int(total_trades),
                "win_rate": round(float(win_rate), 2),
                "net_profit": round(float(net_profit), 2),
                "roi_pct": round(float(roi_pct), 2),
                "profit_factor": round(float(profit_factor), 2),
                "max_drawdown": round(float(max_drawdown), 2),
                "max_drawdown_pct": round(float(max_drawdown_pct), 2),
                "sharpe_ratio": round(float(sharpe_per_trade), 4), # Note: Per trade
                "sortino_ratio": round(float(sortino), 4),
                "sqn": round(float(sqn), 2),
                "var_95": round(float(var_95), 2),
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
            "initial_capital": float(initial_capital),
            "final_equity": float(initial_capital)
        }
