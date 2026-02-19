export class MetricsEngine {
    static calculate(trades, initialCapital = 10000) {
        if (!trades || trades.length === 0) {
            return this.getEmptyMetrics(initialCapital);
        }

        let equity = initialCapital;
        let maxEquity = initialCapital;
        let minEquity = initialCapital;
        let maxDrawdown = 0;
        let maxRunup = 0;

        let grossProfit = 0;
        let grossLoss = 0;
        let wins = 0;
        let losses = 0;
        let longCount = 0;
        let shortCount = 0;

        const pnls = [];
        const rMultiples = [];
        const durations = [];

        // Time-based sort for Equity Curve
        // Assuming trades are already sorted by Exit Time, but safe to resort?
        // Actually, backend sends them sorted by entry, but usually equity is by exit.
        // Let's sort copy by exit time for accurate curve
        const sortedTrades = [...trades].sort((a, b) => new Date(a.exit_time) - new Date(b.exit_time));

        const equityCurve = [{ time: sortedTrades[0].entry_time.split(' ')[0], value: initialCapital }];

        for (const t of sortedTrades) {
            const pnl = Number(t.pnl);
            equity += pnl;

            // Drawdown / Runup
            if (equity > maxEquity) maxEquity = equity;
            const dd = maxEquity - equity;
            if (dd > maxDrawdown) maxDrawdown = dd;

            if (equity < minEquity) minEquity = equity;
            const runup = equity - minEquity; // This is a simplified runup (max rally from low)
            // Or max runup from *initial*? 
            // Backend definition: "Runup is the max equity reached *after* a new low?" 
            // Let's use simple Peak - Valley approach or copy backend?

            // Backend uses: equity_curve.max() - initial_capital (Total Runup)
            // But usually Runup is "Max Excursion Favorable". 
            // Let's stick to (Equity - Initial) if > 0? No.
            // Let's us backend logic: max_runup = max_equity - initial (if positive)
            // Actually, backend: max_runup = equity_curve.max() - initial_capital

            // Stats
            if (pnl > 0) {
                grossProfit += pnl;
                wins++;
            } else {
                grossLoss += Math.abs(pnl);
                losses++;
            }

            if (t.direction === 'long') longCount++;
            else shortCount++;

            pnls.push(pnl);
            if (t.r_multiple) rMultiples.push(Number(t.r_multiple));
            if (t.duration) durations.push(Number(t.duration));

            // equity curve point
            equityCurve.push({
                time: t.exit_time.split(' ')[0],
                value: Number(equity.toFixed(2))
            });
        }

        // Deduplicate Equity Curve (keep last per day)
        const uniqueCurve = [];
        const seen = new Set();
        for (let i = equityCurve.length - 1; i >= 0; i--) {
            const pt = equityCurve[i];
            if (!seen.has(pt.time)) {
                seen.add(pt.time);
                uniqueCurve.unshift(pt);
            }
        }

        // Aggregate Metrics
        const totalTrades = trades.length;
        const netProfit = equity - initialCapital;
        const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
        const profitFactor = grossLoss === 0 ? (grossProfit > 0 ? 100 : 0) : grossProfit / grossLoss;

        const avgWin = wins > 0 ? grossProfit / wins : 0;
        const avgLoss = losses > 0 ? grossLoss / losses : 0;

        const avgPnl = pnls.reduce((a, b) => a + b, 0) / totalTrades;
        // Std Dev of PnL for SQN
        const variance = pnls.reduce((a, b) => a + Math.pow(b - avgPnl, 2), 0) / totalTrades;
        const stdDev = Math.sqrt(variance);
        const sqn = stdDev > 0 ? (Math.sqrt(totalTrades) * avgPnl) / stdDev : 0;

        const expectancy = (avgWin * (winRate / 100)) - (avgLoss * (1 - winRate / 100));

        const avgR = rMultiples.length > 0 ? rMultiples.reduce((a, b) => a + b, 0) / rMultiples.length : 0;
        const avgDur = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

        const maxDrawdownPct = maxEquity > 0 ? (maxDrawdown / maxEquity) * 100 : 0;
        const totalRunup = maxEquity - initialCapital; // Simple "Max Profit" definition

        return {
            metrics: {
                net_profit: netProfit,
                total_trades: totalTrades,
                win_rate: winRate,
                profit_factor: profitFactor,
                max_drawdown: maxDrawdown,
                max_drawdown_pct: maxDrawdownPct,
                max_runup: totalRunup,
                total_wins: wins,
                total_losses: losses,
                total_long: longCount,
                total_short: shortCount,
                avg_r_multiple: avgR,
                sqn: sqn,
                expectancy: expectancy,
                avg_duration: avgDur,
                initial_capital: initialCapital
            },
            equity_curve: uniqueCurve
        };
    }

    static getEmptyMetrics(initialCapital) {
        return {
            metrics: {
                net_profit: 0,
                total_trades: 0,
                win_rate: 0,
                profit_factor: 0,
                max_drawdown: 0,
                max_drawdown_pct: 0,
                max_runup: 0,
                total_wins: 0,
                total_losses: 0,
                total_long: 0,
                total_short: 0,
                avg_r_multiple: 0,
                sqn: 0,
                expectancy: 0,
                avg_duration: 0,
                initial_capital: initialCapital
            },
            equity_curve: []
        };
    }
}
