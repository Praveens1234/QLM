import { Chart } from '../components/Chart.js';
import { MetricsEngine } from '../core/MetricsEngine.js';

export class ResultsView {
    constructor(containerId) {
        this.containerId = containerId;
        this.chart = null;
        this.allTrades = [];
        this.activeTrades = [];
        this.initialCapital = 10000;

        // Filter State
        this.filters = {
            search: '',
            direction: 'all', // all, long, short
            result: 'all',    // all, win, loss
            days: new Set([0, 1, 2, 3, 4, 5, 6]), // 0=Sun, 1=Mon...
            timeRules: [] // Array of { type: 'allow'|'block', start: 'HH:MM', end: 'HH:MM', id: timestamp }
        };
    }

    render(results) {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Store Initial Data
        this.allTrades = results.trades.map((t, i) => ({ ...t, _id: i })); // Add ID for deletion
        this.initialCapital = results.metrics.initial_capital || 10000;

        // Clear container
        container.innerHTML = '';

        // 1. Render Controls
        const controlsHtml = this.renderControls();
        container.insertAdjacentHTML('beforeend', controlsHtml);

        // 2. Render Metrics Grid Container
        container.insertAdjacentHTML('beforeend', '<div id="metrics-grid-container"></div>');

        // 3. Render Chart Container
        const chartId = 'bt-chart-' + Date.now();
        const chartHtml = `
            <div class="glass-panel rounded-xl overflow-hidden shadow-sm mt-6 p-4">
                <div class="flex justify-between items-center mb-2">
                    <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Equity Curve & Drawdown</h3>
                    <span id="chart-stats" class="text-[10px] text-slate-500 font-mono"></span>
                </div>
                <div id="${chartId}" class="w-full h-[300px]"></div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', chartHtml);

        // 4. Render Ledger Container
        container.insertAdjacentHTML('beforeend', '<div id="ledger-container"></div>');

        // 5. Initialize Chart
        setTimeout(() => {
            this.chart = new Chart(chartId);
            this.chart.init();

            // Initial Update
            this.updateResults();
            this.bindEvents();
        }, 50);
    }

    renderControls() {
        const days = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

        return `
        <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm mb-6">
            <div class="flex flex-col gap-4">
                <!-- Top Row: Standard Filters -->
                <div class="flex flex-wrap gap-4 items-center justify-between">
                    
                    <!-- Search -->
                    <div class="relative group">
                        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <i class="fa-solid fa-search text-slate-500 group-focus-within:text-indigo-400 transition-colors"></i>
                        </div>
                        <input type="text" id="filter-search" 
                            class="bg-slate-900/50 border border-slate-700 text-white text-sm rounded-lg block w-64 pl-10 p-2.5 focus:ring-indigo-500 focus:border-indigo-500 placeholder-slate-600 transition-all shadow-sm" 
                            placeholder="Search symbols, reasons...">
                    </div>

                    <!-- Direction Filter -->
                    <div class="flex bg-slate-900/50 rounded-lg p-1 border border-slate-700">
                        <button class="filter-btn-dir px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-white bg-slate-700 shadow-sm" data-val="all">ALL</button>
                        <button class="filter-btn-dir px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-slate-400" data-val="long">LONG</button>
                        <button class="filter-btn-dir px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-slate-400" data-val="short">SHORT</button>
                    </div>

                    <!-- Result Filter -->
                    <div class="flex bg-slate-900/50 rounded-lg p-1 border border-slate-700">
                        <button class="filter-btn-res px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-white bg-slate-700 shadow-sm" data-val="all">ALL</button>
                        <button class="filter-btn-res px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-slate-400" data-val="win">WIN</button>
                        <button class="filter-btn-res px-3 py-1.5 text-xs font-bold rounded hover:bg-slate-700 transition-all text-slate-400" data-val="loss">LOSS</button>
                    </div>

                    <!-- Day Filter -->
                    <div class="flex items-center gap-1">
                        <span class="text-[10px] text-slate-500 mr-2 uppercase font-bold">Days</span>
                        ${days.map((d, i) => `
                            <button class="filter-day w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold border transition-all
                                ${this.filters.days.has(i) ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' : 'bg-slate-900/50 text-slate-600 border-slate-800 hover:border-slate-700'}"
                                data-day="${i}">${d}</button>
                        `).join('')}
                    </div>
                </div>

                <!-- Bottom Row: Time Filters -->
                <div class="border-t border-slate-800/50 pt-4 flex items-start gap-4">
                    <div class="flex items-center gap-2">
                        <select id="time-rule-type" class="bg-slate-900 border border-slate-700 text-white text-xs rounded p-1.5 focus:ring-indigo-500">
                            <option value="allow">Allow Only</option>
                            <option value="block">Block (No Trade)</option>
                        </select>
                        <input type="time" id="time-rule-start" class="bg-slate-900 border border-slate-700 text-white text-xs rounded p-1.5" value="09:00">
                        <span class="text-slate-500 text-xs">to</span>
                        <input type="time" id="time-rule-end" class="bg-slate-900 border border-slate-700 text-white text-xs rounded p-1.5" value="17:00">
                        <button id="btn-add-time-rule" class="text-xs bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1.5 rounded transition-colors font-bold">
                            <i class="fa-solid fa-plus mr-1"></i> Add Rule
                        </button>
                    </div>
                    
                    <div id="time-rules-list" class="flex flex-wrap gap-2 items-center">
                        <!-- Rules injected here -->
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    bindEvents() {
        // Search
        document.getElementById('filter-search').addEventListener('input', (e) => {
            this.filters.search = e.target.value.toLowerCase();
            this.updateResults();
        });

        // Direction
        document.querySelectorAll('.filter-btn-dir').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn-dir').forEach(b => {
                    b.classList.remove('bg-slate-700', 'text-white', 'shadow-sm');
                    b.classList.add('text-slate-400');
                });
                e.target.classList.remove('text-slate-400');
                e.target.classList.add('bg-slate-700', 'text-white', 'shadow-sm');
                this.filters.direction = e.target.dataset.val;
                this.updateResults();
            });
        });

        // Result
        document.querySelectorAll('.filter-btn-res').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn-res').forEach(b => {
                    b.classList.remove('bg-slate-700', 'text-white', 'shadow-sm');
                    b.classList.add('text-slate-400');
                });
                e.target.classList.remove('text-slate-400');
                e.target.classList.add('bg-slate-700', 'text-white', 'shadow-sm');
                this.filters.result = e.target.dataset.val;
                this.updateResults();
            });
        });

        // Days
        document.querySelectorAll('.filter-day').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const day = parseInt(e.target.dataset.day);
                if (this.filters.days.has(day)) {
                    if (this.filters.days.size > 1) {
                        this.filters.days.delete(day);
                        e.target.className = "filter-day w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold border transition-all bg-slate-900/50 text-slate-600 border-slate-800 hover:border-slate-700";
                    }
                } else {
                    this.filters.days.add(day);
                    e.target.className = "filter-day w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold border transition-all bg-indigo-500/20 text-indigo-400 border-indigo-500/30";
                }
                this.updateResults();
            });
        });

        // Time Rules
        document.getElementById('btn-add-time-rule').addEventListener('click', () => {
            const type = document.getElementById('time-rule-type').value;
            const start = document.getElementById('time-rule-start').value;
            const end = document.getElementById('time-rule-end').value;

            if (!start || !end) return;

            this.filters.timeRules.push({
                id: Date.now(),
                type,
                start,
                end
            });
            this.renderTimeRules();
            this.updateResults();
        });
    }

    renderTimeRules() {
        const container = document.getElementById('time-rules-list');
        if (!container) return;

        container.innerHTML = this.filters.timeRules.map(rule => {
            const colorClass = rule.type === 'allow' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';
            const icon = rule.type === 'allow' ? 'fa-check' : 'fa-ban';
            return `
                <div class="flex items-center gap-2 px-2 py-1 rounded border text-[10px] font-mono uppercase ${colorClass}">
                    <i class="fa-solid ${icon}"></i>
                    <span>${rule.start} - ${rule.end}</span>
                    <button class="hover:text-white transition-colors btn-remove-rule" data-id="${rule.id}">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            `;
        }).join('');

        // Bind Remove
        container.querySelectorAll('.btn-remove-rule').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.dataset.id);
                this.filters.timeRules = this.filters.timeRules.filter(r => r.id !== id);
                this.renderTimeRules();
                this.updateResults();
            });
        });
    }

    updateResults() {
        // 1. Filter Trades
        this.activeTrades = this.allTrades.filter(t => {
            // Search
            const searchMatch = !this.filters.search ||
                t.exit_reason.toLowerCase().includes(this.filters.search) ||
                t.direction.toLowerCase().includes(this.filters.search);

            // Direction
            const dirMatch = this.filters.direction === 'all' || t.direction === this.filters.direction;

            // Result
            const resMatch = this.filters.result === 'all' ||
                (this.filters.result === 'win' && t.pnl > 0) ||
                (this.filters.result === 'loss' && t.pnl <= 0);

            // Day & Time Parsing
            const date = new Date(t.entry_time); // UTC string
            const dayMatch = this.filters.days.has(date.getDay());

            // Time Window Logic
            let timeMatch = true;
            if (this.filters.timeRules.length > 0) {
                // Formatting helper for HH:MM comparison
                // entry_time is "YYYY-MM-DD HH:MM:SS"
                const parts = t.entry_time.split(' ')[1].split(':'); // [HH, MM, SS]
                const tradeMin = parseInt(parts[0]) * 60 + parseInt(parts[1]);

                let explicitlyAllowed = false;
                let explicitlyBlocked = false;
                let hasAllowRules = false;

                for (const rule of this.filters.timeRules) {
                    const [sH, sM] = rule.start.split(':').map(Number);
                    const [eH, eM] = rule.end.split(':').map(Number);
                    const startMin = sH * 60 + sM;
                    const endMin = eH * 60 + eM;

                    const inRange = tradeMin >= startMin && tradeMin <= endMin;

                    if (rule.type === 'block') {
                        if (inRange) {
                            explicitlyBlocked = true;
                            break; // Priority to block
                        }
                    } else if (rule.type === 'allow') {
                        hasAllowRules = true;
                        if (inRange) explicitlyAllowed = true;
                    }
                }

                if (explicitlyBlocked) {
                    timeMatch = false;
                } else if (hasAllowRules && !explicitlyAllowed) {
                    timeMatch = false; // Must match at least one allow rule if enabled
                }
            }

            return searchMatch && dirMatch && resMatch && dayMatch && timeMatch;
        });

        // 2. Calculate Metrics
        const calculation = MetricsEngine.calculate(this.activeTrades, this.initialCapital);

        // 3. Update DOM
        const gridContainer = document.getElementById('metrics-grid-container');
        gridContainer.innerHTML = this.generateMetricsGrid(calculation.metrics);

        const ledgerContainer = document.getElementById('ledger-container');
        ledgerContainer.innerHTML = this.generateLedger(this.activeTrades);

        // Bind Ledger Events
        this.bindLedgerEvents();

        // 4. Update Chart
        if (this.chart) {
            this.chart.addAreaSeries(calculation.equity_curve);
        }
    }

    bindLedgerEvents() {
        document.querySelectorAll('.btn-delete-trade').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.dataset.id);
                this.deleteTrade(id);
            });
        });

        const btnExport = document.getElementById('btn-export-csv');
        if (btnExport) {
            btnExport.addEventListener('click', () => this.exportToCsv(this.activeTrades));
        }
    }

    deleteTrade(id) {
        const index = this.allTrades.findIndex(t => t._id === id);
        if (index !== -1) {
            this.allTrades.splice(index, 1);
            this.updateResults();
            if (window.Toast) window.Toast.success("Trade removed & metrics updated");
        }
    }

    generateMetricsGrid(m) {
        // ... (Same as before, abbreviated for brevity in prompt context but keeping full logic)
        const pnlColor = m.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400';
        const fmt = (val, dec = 2) => val !== undefined && val !== null ? Number(val).toFixed(dec) : '0.00';

        return `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Net Profit</span>
                    <div class="text-xl font-bold ${pnlColor} font-mono tracking-tight">$${fmt(m.net_profit)}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Max Drawdown</span>
                    <div class="text-xl font-bold text-rose-400 font-mono tracking-tight">$${fmt(m.max_drawdown)} <span class="text-sm text-slate-500">(${fmt(m.max_drawdown_pct)}%)</span></div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Max Runup</span>
                    <div class="text-xl font-bold text-emerald-400 font-mono tracking-tight">$${fmt(m.max_runup)}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Profit Factor</span>
                    <div class="text-xl font-bold text-white font-mono tracking-tight">${fmt(m.profit_factor)}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Total Trades</span>
                    <div class="text-xl font-bold text-white font-mono tracking-tight">${m.total_trades}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Win Rate</span>
                    <div class="text-xl font-bold text-white font-mono tracking-tight">${fmt(m.win_rate)}%</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Wins / Losses</span>
                    <div class="text-xl font-bold text-white font-mono tracking-tight">
                        <span class="text-emerald-400">${m.total_wins}</span> / <span class="text-rose-400">${m.total_losses}</span>
                    </div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Long / Short</span>
                    <div class="text-xl font-bold text-white font-mono tracking-tight">
                        <span class="text-indigo-400">${m.total_long}</span> / <span class="text-orange-400">${m.total_short}</span>
                    </div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Avg R-Multiple</span>
                    <div class="text-xl font-bold text-indigo-400 font-mono tracking-tight">${fmt(m.avg_r_multiple)}R</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">SQN</span>
                    <div class="text-xl font-bold text-cyan-400 font-mono tracking-tight">${fmt(m.sqn)}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Expectancy</span>
                    <div class="text-xl font-bold text-emerald-400 font-mono tracking-tight">$${fmt(m.expectancy)}</div>
                 </div>
                 <div class="glass-panel p-4 rounded-xl border border-white/5 bg-slate-800/50 backdrop-blur-sm">
                    <span class="text-[10px] text-slate-400 uppercase tracking-wide font-bold block mb-1">Avg Duration</span>
                    <div class="text-xl font-bold text-slate-300 font-mono tracking-tight">${fmt(m.avg_duration)}m</div>
                 </div>
            </div>`;
    }

    generateLedger(trades) {
        const rows = trades.map(t => {
            const pnlClass = t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
            const dirClass = t.direction === 'long' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';
            const price = (p) => p !== undefined && p !== null ? Number(p).toFixed(2) : '-';

            // Enhanced Time with Day Name
            const dateObj = new Date(t.entry_time);
            const dayName = dateObj.toLocaleDateString(undefined, { weekday: 'short' });
            const timeStr = t.entry_time.split(' ')[1] || '';
            const dateStr = t.entry_time.split(' ')[0] || '';
            const entryDisplay = `<div class="flex flex-col"><span class="text-white">${dateStr} (${dayName})</span><span class="text-[10px] text-slate-500">${timeStr}</span></div>`;

            // Helper for MAE/MFE Display
            const fmtExcursion = (pnl, r, prc, color) => {
                if (pnl === undefined || pnl === null) return '-';
                return `<div class="flex flex-col text-[10px] items-end leading-tight">
                    <span class="${color} font-bold">$${Number(pnl).toFixed(2)} / ${Number(r).toFixed(2)}R</span>
                    <span class="text-slate-500">@ ${Number(prc).toFixed(2)}</span>
                </div>`;
            };

            // Check for new calculated fields from backend
            // Fallback to simpler display if fields missing (e.g. older cache)
            const showMae = t.mae_pnl !== undefined
                ? fmtExcursion(t.mae_pnl, t.mae_r, t.mae_price, 'text-rose-400')
                : `<span class="text-xs text-slate-500">-${price(t.mae)}</span>`;

            const showMfe = t.mfe_pnl !== undefined
                ? fmtExcursion(t.mfe_pnl, t.mfe_r, t.mfe_price, 'text-emerald-400')
                : `<span class="text-xs text-slate-500">+${price(t.mfe)}</span>`;

            return `
            <tr class="hover:bg-white/5 transition-colors border-b border-slate-800 last:border-0 group">
                <td class="px-6 py-3 whitespace-nowrap text-xs">${entryDisplay}</td>
                <td class="px-6 py-3"><span class="px-2 py-0.5 rounded text-[9px] font-bold border uppercase ${dirClass}">${t.direction}</span></td>
                <td class="px-6 py-3 text-right text-white font-mono">${price(t.entry_price)}</td>
                <td class="px-6 py-3 text-right text-slate-500 font-mono text-xs">${price(t.sl)}</td>
                <td class="px-6 py-3 text-right text-slate-500 font-mono text-xs">${price(t.tp)}</td>
                <td class="px-6 py-3 text-right text-white font-mono">${price(t.exit_price)}</td>
                <td class="px-6 py-3 text-right text-slate-500 font-mono text-xs">${t.exit_time}</td>
                <td class="px-6 py-3 text-right font-bold ${pnlClass} font-mono">${price(t.pnl)}</td>
                <td class="px-6 py-3 text-right text-slate-500 font-mono">${showMae}</td>
                <td class="px-6 py-3 text-right text-slate-500 font-mono">${showMfe}</td>
                <td class="px-6 py-3 text-right text-slate-300 font-mono text-xs">${price(t.duration)}m</td>
                <td class="px-6 py-3 text-right text-slate-500 text-[10px] uppercase">${t.exit_reason || '-'}</td>
                <td class="px-6 py-3 text-center">
                    <button class="btn-delete-trade text-slate-600 hover:text-rose-400 transition-colors" data-id="${t._id}" title="Remove Trade">
                        <i class="fa-solid fa-trash text-xs"></i>
                    </button>
                </td>
            </tr>`;
        }).join('');

        return `
            <div class="glass-panel rounded-xl overflow-hidden shadow-sm mt-6">
                 <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
                    <div class="flex items-center gap-4">
                        <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Trade Ledger</h3>
                        <span class="text-[10px] text-slate-600 uppercase font-mono">${trades.length} TRADES</span>
                    </div>
                    <button id="btn-export-csv" class="text-xs bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded transition-colors border border-slate-700 font-medium">
                        <i class="fa-solid fa-download mr-1"></i> Export CSV
                    </button>
                 </div>
                 <div class="overflow-x-auto max-h-[600px]"> <!-- Increased Height -->
                    <table class="w-full text-left text-sm text-slate-400">
                        <thead class="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 sticky top-0 z-10 shadow-sm">
                            <tr>
                                <th class="px-6 py-3 tracking-wider">Entry</th>
                                <th class="px-6 py-3 tracking-wider">Dir</th>
                                <th class="px-6 py-3 tracking-wider text-right">Entry Px</th>
                                <th class="px-6 py-3 tracking-wider text-right">SL</th>
                                <th class="px-6 py-3 tracking-wider text-right">TP</th>
                                <th class="px-6 py-3 tracking-wider text-right">Exit Px</th>
                                <th class="px-6 py-3 tracking-wider text-right">Exit Time</th>
                                <th class="px-6 py-3 tracking-wider text-right">PnL</th>
                                <th class="px-6 py-3 tracking-wider text-right">MAE (Max Loss)</th>
                                <th class="px-6 py-3 tracking-wider text-right">MFE (Max Prof)</th>
                                <th class="px-6 py-3 tracking-wider text-right">Dur</th>
                                <th class="px-6 py-3 tracking-wider text-right">Reason</th>
                                <th class="px-6 py-3 tracking-wider text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody class="font-mono text-xs divide-y divide-slate-800/50">${rows}</tbody>
                    </table>
                 </div>
            </div>`;
    }

    async exportToCsv(trades) {
        // ... (Same export logic, unchanged)
        // Re-implementing to ensure file completeness
        try {
            const btn = document.getElementById('btn-export-csv');
            const originalText = btn.innerHTML;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Exporting...`;
            btn.disabled = true;

            const response = await fetch('/api/backtest/export-csv', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trades: trades,
                    mode: 'capital'
                })
            });

            if (!response.ok) throw new Error("Export failed");

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trades_${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            btn.innerHTML = originalText;
            btn.disabled = false;
        } catch (e) {
            console.error(e);
            if (window.Toast) window.Toast.error("Failed to export CSV");
            const btn = document.getElementById('btn-export-csv');
            if (btn) {
                btn.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Error`;
                setTimeout(() => btn.innerHTML = `<i class="fa-solid fa-download mr-1"></i> Export CSV`, 2000);
                btn.disabled = false;
            }
        }
    }
}
