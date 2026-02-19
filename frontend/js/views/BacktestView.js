import { backtestService } from '../services/BacktestService.js';
import { dataService } from '../services/DataService.js';
import { strategyService } from '../services/StrategyService.js';

export class BacktestView {
    constructor() {
        this.container = document.getElementById('page-backtest');
        this.mode = 'backtest';
        this.bindEvents();

        backtestService.onProgress((msg) => this.updateProgress(msg));
        backtestService.onResult((res) => this.renderResults(res));
        backtestService.onError((err) => this.handleError(err));
    }

    bindEvents() {
        const btnBt = document.getElementById('btn-mode-bt');
        const btnOpt = document.getElementById('btn-mode-opt');
        const btnRun = document.getElementById('btn-run-action');

        if (btnBt) btnBt.addEventListener('click', () => this.setMode('backtest'));
        if (btnOpt) btnOpt.addEventListener('click', () => this.setMode('optimization'));
        if (btnRun) btnRun.addEventListener('click', () => this.run());
    }

    async mount() {
        await this.loadOptions();
    }

    setMode(mode) {
        this.mode = mode;
        const btnBt = document.getElementById('btn-mode-bt');
        const btnOpt = document.getElementById('btn-mode-opt');
        const optConfig = document.getElementById('opt-config');
        const actionBtn = document.getElementById('btn-run-action');

        if (mode === 'backtest') {
            btnBt.className = "flex-1 bg-indigo-600 text-white text-xs font-bold py-2 rounded border border-indigo-500 shadow-md transition-all";
            btnOpt.className = "flex-1 bg-slate-800 text-slate-400 hover:text-white text-xs font-bold py-2 rounded border border-slate-700 hover:bg-slate-700 transition-all";
            optConfig.classList.add('hidden');
            actionBtn.innerHTML = `<i class="fa-solid fa-rocket"></i> Run Simulation`;
        } else {
            btnBt.className = "flex-1 bg-slate-800 text-slate-400 hover:text-white text-xs font-bold py-2 rounded border border-slate-700 hover:bg-slate-700 transition-all";
            btnOpt.className = "flex-1 bg-emerald-600 text-white text-xs font-bold py-2 rounded border border-emerald-500 shadow-md transition-all";
            optConfig.classList.remove('hidden');
            actionBtn.innerHTML = `<i class="fa-solid fa-flask"></i> Run Optimization`;
        }
    }

    async loadOptions() {
        try {
            const [datasets, strategies] = await Promise.all([
                dataService.list(),
                strategyService.list()
            ]);

            const dSelect = document.getElementById('bt-dataset');
            const sSelect = document.getElementById('bt-strategy');

            dSelect.innerHTML = datasets.map(d => `<option value="${d.id}">${d.symbol} (${d.timeframe})</option>`).join('');
            sSelect.innerHTML = strategies.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
        } catch (e) { }
    }

    async run() {
        const datasetId = document.getElementById('bt-dataset').value;
        const strategyName = document.getElementById('bt-strategy').value;

        this.resetProgress();

        try {
            if (this.mode === 'backtest') {
                await backtestService.runBacktest(datasetId, strategyName);
            } else {
                const method = document.getElementById('opt-method').value;
                const target = document.getElementById('opt-target').value;

                const badge = document.getElementById('bt-status-badge');
                badge.classList.remove('hidden');
                badge.innerText = method === 'genetic' ? "EVOLVING" : "SEARCHING";
                badge.className = "bg-purple-500/10 text-purple-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase animate-pulse";
                document.getElementById('bt-status').innerText = `Running ${method.toUpperCase()} Optimization...`;

                // Handle async response
                const res = await backtestService.runOptimization({
                    dataset_id: datasetId,
                    strategy_name: strategyName,
                    method: method,
                    target_metric: target
                });

                if (res.status === 'success') {
                    this.renderResults(res.results); // Note: response structure is {status: ..., results: {...}}
                    this.completeProgress("Optimization Finished");
                } else {
                    throw new Error(res.error || "Optimization failed");
                }
            }
        } catch (e) {
            this.handleError({ message: e.message || "Operation Failed" });
        }
    }

    resetProgress() {
        const bar = document.getElementById('bt-progress-bar');
        bar.style.width = '0%';
        bar.classList.remove('bg-rose-500');
        document.getElementById('bt-status').innerText = "Starting...";

        const badge = document.getElementById('bt-status-badge');
        badge.classList.remove('hidden');
        badge.innerText = "STARTING";
        badge.className = "bg-amber-500/10 text-amber-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    }

    updateProgress(msg) {
        const bar = document.getElementById('bt-progress-bar');
        const status = document.getElementById('bt-status');
        const badge = document.getElementById('bt-status-badge');

        bar.style.width = `${msg.progress}%`;
        status.innerText = `${msg.message} - ${msg.data.current_time || ''}`;

        badge.innerText = "RUNNING";
        badge.className = "bg-indigo-500/10 text-indigo-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    }

    completeProgress(msg = "Completed") {
        const bar = document.getElementById('bt-progress-bar');
        bar.style.width = '100%';
        document.getElementById('bt-status').innerText = msg;
        const badge = document.getElementById('bt-status-badge');
        badge.innerText = "COMPLETED";
        badge.className = "bg-emerald-500/10 text-emerald-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    }

    handleError(msg) {
        if (window.Toast) window.Toast.error(msg.message || msg.details || "Error");
        const bar = document.getElementById('bt-progress-bar');
        bar.classList.add('bg-rose-500');
        bar.style.width = '100%';
        document.getElementById('bt-status').innerText = "Failed";

        const badge = document.getElementById('bt-status-badge');
        badge.innerText = "FAILED";
        badge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    }

    renderResults(results) {
        if (results.best_metrics) {
            this._renderOptResults(results);
        } else {
            // Use ResultsView for backtest
            import('./ResultsView.js?v=5').then(({ ResultsView }) => {
                const view = new ResultsView('bt-results');
                view.render(results);
            });
        }
    }

    _renderOptResults(results) {
        const container = document.getElementById('bt-results');
        const best = results.best_metrics;
        const params = results.best_params;

        let paramsHtml = Object.entries(params).map(([k, v]) => `
            <div class="flex justify-between text-xs border-b border-slate-800 pb-1 last:border-0">
                <span class="text-slate-500 font-mono">${k}</span>
                <span class="text-emerald-400 font-bold font-mono">${v}</span>
            </div>
        `).join('');

        container.innerHTML = `
            <div class="glass-panel rounded-xl p-6 shadow-sm mb-6">
                <h3 class="text-sm font-bold text-white mb-4 flex items-center gap-2">
                    <i class="fa-solid fa-trophy text-amber-400"></i> Best Parameters Found
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="bg-slate-950/50 rounded-lg p-4 space-y-2 border border-slate-800">
                        ${paramsHtml}
                    </div>
                    <div class="space-y-4">
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-slate-500 uppercase font-bold">Net Profit</span>
                            <span class="text-lg font-mono font-bold ${best.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}">$${best.net_profit}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-slate-500 uppercase font-bold">Sharpe Ratio</span>
                            <span class="text-lg font-mono font-bold text-indigo-400">${best.sharpe_ratio}</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-slate-500 uppercase font-bold">Win Rate</span>
                            <span class="text-lg font-mono font-bold text-white">${best.win_rate}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}
