import pandas as pd
import numpy as np

class ReferenceMetrics:
    """
    Textbook implementation of performance metrics for verification.
    Sources: Investopedia, standard quant finance textbooks.
    """

    @staticmethod
    def net_profit(pnls: list) -> float:
        return sum(pnls)

    @staticmethod
    def win_rate(pnls: list) -> float:
        if not pnls: return 0.0
        wins = sum(1 for p in pnls if p > 0)
        return (wins / len(pnls)) * 100

    @staticmethod
    def profit_factor(pnls: list) -> float:
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p <= 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @staticmethod
    def max_drawdown(pnls: list, initial_capital: float = 10000.0) -> float:
        equity = [initial_capital]
        for p in pnls:
            equity.append(equity[-1] + p)

        equity_series = pd.Series(equity)
        peak = equity_series.cummax()
        drawdown = equity_series - peak
        return abs(drawdown.min())

    @staticmethod
    def sharpe_ratio(pnls: list, risk_free_rate_per_period: float = 0.0) -> float:
        """
        Simple trade-based Sharpe.
        (Mean Return - Risk Free) / StdDev Return
        """
        if len(pnls) < 2: return 0.0
        returns = np.array(pnls)
        std = np.std(returns, ddof=1) # Sample std dev
        if std == 0: return 0.0
        return (np.mean(returns) - risk_free_rate_per_period) / std

    @staticmethod
    def sortino_ratio(pnls: list, target_return: float = 0.0) -> float:
        if not pnls: return 0.0
        returns = np.array(pnls)

        # Correct logic: Downside Deviation uses N_total
        # Count positive returns as 0 deviation
        downside_diffs = np.minimum(0, returns - target_return)
        downside_sq_sum = np.sum(downside_diffs ** 2)
        downside_std = np.sqrt(downside_sq_sum / len(pnls))

        if downside_std == 0: return 0.0
        return (np.mean(returns) - target_return) / downside_std
