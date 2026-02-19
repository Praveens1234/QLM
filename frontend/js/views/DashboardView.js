import { api } from '../core/ApiClient.js';

export class DashboardView {
    constructor() {
        this.container = document.getElementById('page-dashboard');
    }

    async mount() {
        // Logic to run when view is entered
        await this.updateStats();
    }

    async updateStats() {
        try {
            const [datasets, strategies, liveStatus] = await Promise.all([
                api.get('/data/'),
                api.get('/strategies/'),
                api.get('/live/dashboard/live/status')
            ]);

            this.renderStat('strategies', strategies.length);
            this.renderStat('datasets', datasets.length);

            // Render Live Stats
            if (liveStatus && liveStatus.active_orders) {
                this.renderStat('active_orders', liveStatus.active_orders.length);
                this.renderStat('pnl', `$${(liveStatus.total_pnl || 0).toFixed(2)}`);

                // Update specific status indicator
                const indicator = document.getElementById('live-indicator');
                if (indicator) {
                    indicator.className = liveStatus.status === 'online'
                        ? 'h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]'
                        : 'h-2 w-2 rounded-full bg-rose-500';
                }
            }
        } catch (e) {
            console.error("Dashboard update failed", e);
        }
    }

    renderStat(type, value) {
        const els = document.querySelectorAll(`[data-stat="${type}"]`);
        els.forEach(el => {
            el.innerText = value;
            // Pulse animation
            el.classList.add('text-white');
            setTimeout(() => el.classList.remove('text-white'), 500);
        });
    }
}
