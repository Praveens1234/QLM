import { Chart } from '../components/Chart.js';

export class ResultsView {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
    }

    render(results) {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Clear container
        container.innerHTML = '';

        // 1. Render Metrics Grid
        const metricsHtml = this.generateMetricsGrid(results.metrics);
        container.insertAdjacentHTML('beforeend', metricsHtml);

        // 2. Render Chart Container
        const chartId = 'bt-chart-' + Date.now();
        const chartHtml = `
            <div class="glass-panel rounded-xl overflow-hidden shadow-sm mt-6 p-4">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Equity Curve & Drawdown</h3>
                <div id="${chartId}" class="w-full h-[300px]"></div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', chartHtml);

        // 3. Initialize Chart
        // Wait for DOM
        setTimeout(() => {
            this.chart = new Chart(chartId);
            this.chart.init();

            // Transform Equity Data
            if (results.chart_data && results.chart_data.length > 0) {
                // If backend provides chart_data
                // Assuming format: { time: '...', value: ... }
                // For now, we simulate equity from trades if chart_data missing
                const equityData = this.calculateEquityCurve(results.trades, results.metrics.initial_capital);
                this.chart.addAreaSeries(equityData);
            } else if (results.trades) {
                const equityData = this.calculateEquityCurve(results.trades, results.metrics.initial_capital);
                this.chart.addAreaSeries(equityData);
            }
        }, 50);

        // 4. Render Ledger
        const ledgerHtml = this.generateLedger(results.trades);
        container.insertAdjacentHTML('beforeend', ledgerHtml);
    }

    calculateEquityCurve(trades, initialCapital) {
        let equity = initialCapital;
        const data = [];

        // Sort trades by exit time
        const sortedTrades = [...trades].sort((a, b) => new Date(a.exit_time) - new Date(b.exit_time));

        // Initial Point (Start of first trade or slightly before)
        if (sortedTrades.length > 0) {
            data.push({ time: sortedTrades[0].entry_time.split(' ')[0], value: initialCapital });
        }

        sortedTrades.forEach(t => {
            equity += t.pnl;
            // Lightweight charts needs YYYY-MM-DD or timestamp
            data.push({
                time: t.exit_time.split(' ')[0], // Date only for now
                value: equity
            });
        });

        // Deduplicate times (take last value for day)
        const uniqueData = [];
        const seen = new Set();
        for (let i = data.length - 1; i >= 0; i--) {
            if (!seen.has(data[i].time)) {
                seen.add(data[i].time);
                uniqueData.unshift(data[i]);
            }
        }

        return uniqueData;
    }

    generateMetricsGrid(m) {
        const pnlColor = m.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400';
        return `
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Net Profit</span>
                    <div class="text-xl font-bold ${pnlColor} mt-1 font-mono tracking-tight">$${m.net_profit}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Trades</span>
                    <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.total_trades}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Win Rate</span>
                    <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.win_rate}%</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Profit Factor</span>
                    <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.profit_factor}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Max DD</span>
                    <div class="text-xl font-bold text-rose-400 mt-1 font-mono tracking-tight">$${m.max_drawdown}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl shadow-sm">
                    <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Avg R</span>
                    <div class="text-xl font-bold text-indigo-400 mt-1 font-mono tracking-tight">${m.avg_r_multiple || '0.00'}R</div>
                 </div>
            </div>`;
    }

    generateLedger(trades) {
        const rows = trades.map(t => {
            const pnlClass = t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
            const rClass = (t.r_multiple || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400';
            const dirClass = t.direction === 'long' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';

            return `
            <tr class="hover:bg-white/5 transition-colors border-b border-slate-800 last:border-0">
                <td class="px-6 py-3">${t.entry_time}</td>
                <td class="px-6 py-3"><span class="px-2 py-0.5 rounded text-[9px] font-bold border uppercase ${dirClass}">${t.direction}</span></td>
                <td class="px-6 py-3 text-right text-white">${t.entry_price.toFixed(2)}</td>
                <td class="px-6 py-3 text-right text-white">${t.exit_price.toFixed(2)}</td>
                <td class="px-6 py-3 text-right font-bold ${pnlClass}">${t.pnl.toFixed(2)}</td>
                <td class="px-6 py-3 text-right font-bold ${rClass}">${(t.r_multiple || 0).toFixed(2)}R</td>
                <td class="px-6 py-3 text-right text-slate-500">${t.exit_reason}</td>
            </tr>`;
        }).join('');

        return `
            <div class="glass-panel rounded-xl overflow-hidden shadow-sm mt-6">
                 <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Trade Ledger</h3>
                 </div>
                 <div class="overflow-x-auto max-h-[400px]">
                    <table class="w-full text-left text-sm text-slate-400">
                        <thead class="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 sticky top-0">
                            <tr>
                                <th class="px-6 py-3 tracking-wider">Entry</th>
                                <th class="px-6 py-3 tracking-wider">Dir</th>
                                <th class="px-6 py-3 tracking-wider text-right">Entry Px</th>
                                <th class="px-6 py-3 tracking-wider text-right">Exit Px</th>
                                <th class="px-6 py-3 tracking-wider text-right">PnL</th>
                                <th class="px-6 py-3 tracking-wider text-right">R-Mult</th>
                                <th class="px-6 py-3 tracking-wider text-right">Reason</th>
                            </tr>
                        </thead>
                        <tbody class="font-mono text-xs">${rows}</tbody>
                    </table>
                 </div>
            </div>`;
    }
}
