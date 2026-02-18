# Metric Standards & Formulas

This document defines the exact formulas used in QLM's `PerformanceEngine` and validated by `ReferenceMetrics`.

## 1. Profit & Loss (PnL)
*   **Net Profit**: $\sum (Trade PnL)$
*   **Gross Profit**: $\sum (Positive Trade PnL)$
*   **Gross Loss**: $\sum |Negative Trade PnL|$

## 2. Ratios
*   **Profit Factor**: $Gross Profit / Gross Loss$. If Loss is 0, returns $\infty$ (if Profit > 0) or 0.
*   **Win Rate**: $(Winning Trades / Total Trades) * 100$.

## 3. Risk Metrics
*   **Max Drawdown**: Maximum peak-to-valley decline in the equity curve.
    *   $Equity_t = Initial Capital + \sum_{i=0}^{t} PnL_i$
    *   $Drawdown_t = Equity_t - \max(Equity_{0...t})$
    *   $Max DD = \min(Drawdown_t)$ (absolute value)
*   **Sharpe Ratio (Trade-based)**:
    *   $\frac{\mu_{returns} - R_f}{\sigma_{returns}}$
    *   Where $\mu$ is mean trade PnL and $\sigma$ is standard deviation (sample, ddof=1).
*   **Sortino Ratio**:
    *   $\frac{\mu_{returns} - Target}{\sigma_{downside}}$
    *   Where $\sigma_{downside} = \sqrt{\frac{1}{N} \sum (\min(0, Return - Target))^2}$

## 4. Other
*   **Expectancy**: $Net Profit / Total Trades$ (Expected value per trade).
