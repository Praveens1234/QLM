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
            const [datasets, strategies] = await Promise.all([
                api.get('/data/'),
                api.get('/strategies/')
            ]);

            this.renderStat('strategies', strategies.length);
            this.renderStat('datasets', datasets.length);
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
