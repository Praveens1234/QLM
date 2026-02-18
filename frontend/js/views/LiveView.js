import { tradeService } from '../services/TradeService.js';
import { toast } from '../notifications.js';

export class LiveView {
    constructor() {
        this.container = document.getElementById('page-live');
        this.controlsContainer = document.getElementById('live-controls');
        this.positionsContainer = document.getElementById('live-positions-list');
        this.ordersContainer = document.getElementById('live-orders-list');
    }

    async mount() {
        if (!this.container) {
             this.container = document.getElementById('page-live');
             this.controlsContainer = document.getElementById('live-controls');
             this.positionsContainer = document.getElementById('live-positions-list');
             this.ordersContainer = document.getElementById('live-orders-list');
        }

        await this.refreshStatus();

        // Setup auto-refresh if live
        if (this.interval) clearInterval(this.interval);
        this.interval = setInterval(() => this.refreshStatus(), 2000); // Poll status every 2s
    }

    unmount() {
        if (this.interval) clearInterval(this.interval);
    }

    async refreshStatus() {
        try {
            const status = await tradeService.getStatus();
            this.renderLivePanel(status);
            this.renderPositions(status.positions || []);
            this.renderOrders(status.orders || []);
        } catch (e) {
            console.error("Live view status error", e);
        }
    }

    renderLivePanel(status) {
        if (!this.controlsContainer) return;

        const isRunning = status.running;
        const color = isRunning ? "text-emerald-400" : "text-slate-500";
        const text = isRunning ? "RUNNING" : "STOPPED";
        const btnAction = isRunning ? `onclick="liveView.stop()"` : `onclick="liveView.start()"`;
        const btnText = isRunning ? "Stop Engine" : "Start Live Trading";
        const btnClass = isRunning ? "bg-rose-600 hover:bg-rose-500" : "bg-emerald-600 hover:bg-emerald-500";

        // Mode Selection (disabled if running)
        const modeSelect = isRunning
            ? `<div class="text-xs font-mono text-indigo-400 font-bold bg-indigo-500/10 px-3 py-2 rounded-lg border border-indigo-500/20">${status.mode || 'PAPER'}</div>`
            : `
            <select id="trade-mode" class="bg-slate-950 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 focus:border-indigo-500 outline-none font-mono">
                <option value="PAPER">PAPER TRADING</option>
                <option value="LIVE">LIVE EXCHANGE</option>
            </select>
            `;

        this.controlsContainer.innerHTML = `
            <div class="glass-panel rounded-xl p-6 shadow-sm mb-6 relative overflow-hidden">
                 <div class="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>

                <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4 relative z-10">
                    <h3 class="text-sm font-bold text-white uppercase tracking-wide flex items-center gap-3">
                        <span class="relative flex h-3 w-3">
                          <span class="${isRunning ? 'animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75' : 'hidden'}"></span>
                          <span class="relative inline-flex rounded-full h-3 w-3 ${isRunning ? 'bg-emerald-500' : 'bg-slate-600'}"></span>
                        </span>
                        Engine Status
                    </h3>
                    <div class="flex items-center gap-3">
                         <span class="text-xs font-mono font-bold ${color} bg-slate-950/50 px-2 py-1 rounded border border-slate-800">${text}</span>
                    </div>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6 relative z-10">
                    <div class="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">Active Orders</div>
                        <div class="text-2xl font-mono text-white tracking-tight">${status.orders_count || 0}</div>
                    </div>
                    <div class="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">Open Positions</div>
                        <div class="text-2xl font-mono text-white tracking-tight">${status.positions_count || 0}</div>
                    </div>
                    <div class="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">Total PnL</div>
                        <div class="text-2xl font-mono ${status.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'} tracking-tight">
                            ${status.pnl > 0 ? '+' : ''}${status.pnl || '0.00'}
                        </div>
                    </div>
                    <div class="bg-slate-950/50 rounded-lg p-4 border border-slate-800">
                        <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">Errors</div>
                        <div class="text-2xl font-mono text-rose-400 tracking-tight">${status.error_count || 0}</div>
                    </div>
                </div>

                <div class="flex flex-col md:flex-row justify-end gap-3 border-t border-slate-800 pt-4 relative z-10">
                    ${modeSelect}
                    <button ${btnAction} class="${btnClass} text-white font-bold text-xs uppercase px-6 py-2.5 rounded-lg transition-all shadow-lg flex items-center justify-center gap-2">
                        ${isRunning ? '<i class="fa-solid fa-stop"></i>' : '<i class="fa-solid fa-play"></i>'} ${btnText}
                    </button>
                </div>
            </div>
        `;
    }

    renderPositions(positions) {
        if (!this.positionsContainer) return;

        if (positions.length === 0) {
            this.positionsContainer.innerHTML = `
                <div class="flex h-full items-center justify-center text-slate-600">
                    <div class="text-center">
                        <i class="fa-solid fa-layer-group text-3xl mb-3 opacity-20"></i>
                        <p class="text-xs">No active positions</p>
                    </div>
                </div>`;
            return;
        }

        const rows = positions.map(p => {
            const pnlColor = p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
            const pnlSign = p.unrealized_pnl > 0 ? '+' : '';
            return `
                <tr class="hover:bg-slate-800/50 transition-colors">
                    <td class="px-6 py-4 whitespace-nowrap text-white font-bold">${p.symbol}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-slate-300 font-mono">${p.quantity}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-slate-400 font-mono">${p.entry_price.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-slate-300 font-mono">${p.current_price.toFixed(2)}</td>
                    <td class="px-6 py-4 whitespace-nowrap font-mono font-bold ${pnlColor} text-right">
                        ${pnlSign}${p.unrealized_pnl.toFixed(2)}
                    </td>
                </tr>
            `;
        }).join('');

        this.positionsContainer.innerHTML = `
            <table class="w-full text-left text-xs">
                <thead class="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 sticky top-0 z-10">
                    <tr>
                        <th class="px-6 py-3 tracking-wider">Symbol</th>
                        <th class="px-6 py-3 tracking-wider">Size</th>
                        <th class="px-6 py-3 tracking-wider">Entry</th>
                        <th class="px-6 py-3 tracking-wider">Current</th>
                        <th class="px-6 py-3 tracking-wider text-right">PnL</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800 font-mono">
                    ${rows}
                </tbody>
            </table>
        `;
    }

    renderOrders(orders) {
        if (!this.ordersContainer) return;

        if (orders.length === 0) {
            this.ordersContainer.innerHTML = `
                <div class="flex h-full items-center justify-center text-slate-600">
                    <div class="text-center">
                        <i class="fa-solid fa-list-check text-3xl mb-3 opacity-20"></i>
                        <p class="text-xs">No open orders</p>
                    </div>
                </div>`;
            return;
        }

        const rows = orders.map(o => {
            const sideColor = o.side === 'BUY' ? 'text-emerald-400' : 'text-rose-400';
            return `
                <tr class="hover:bg-slate-800/50 transition-colors">
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-500">${new Date(o.created_at).toLocaleTimeString()}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-white font-bold">${o.symbol}</td>
                    <td class="px-6 py-4 whitespace-nowrap font-bold ${sideColor}">${o.side}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-slate-300 font-mono">${o.quantity}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-slate-400 font-mono">${o.price ? o.price.toFixed(2) : 'MKT'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">${o.status}</span>
                    </td>
                </tr>
            `;
        }).join('');

        this.ordersContainer.innerHTML = `
            <table class="w-full text-left text-xs">
                <thead class="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 sticky top-0 z-10">
                    <tr>
                        <th class="px-6 py-3 tracking-wider">Time</th>
                        <th class="px-6 py-3 tracking-wider">Symbol</th>
                        <th class="px-6 py-3 tracking-wider">Side</th>
                        <th class="px-6 py-3 tracking-wider">Qty</th>
                        <th class="px-6 py-3 tracking-wider">Price</th>
                        <th class="px-6 py-3 tracking-wider text-right">Status</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-800 font-mono">
                    ${rows}
                </tbody>
            </table>
        `;
    }

    async start() {
        const modeEl = document.getElementById('trade-mode');
        const mode = modeEl ? modeEl.value : 'PAPER';

        try {
            await tradeService.start(mode);
            toast.success(`Engine started in ${mode} mode`);
            await this.refreshStatus();
        } catch (e) {
            toast.error(e.message);
        }
    }

    async stop() {
        if (!confirm("Stop trading engine? This will cancel active orders.")) return;
        try {
            await tradeService.stop();
            toast.success("Engine stopped");
            await this.refreshStatus();
        } catch (e) {
            toast.error(e.message);
        }
    }
}

export const liveView = new LiveView();
window.liveView = liveView;
