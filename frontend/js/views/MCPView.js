import { api } from '../core/ApiClient.js';

export class MCPView {
    constructor() {
        this.container = document.getElementById('page-mcp');
        this.bindEvents();
    }

    bindEvents() {
        const toggle = document.getElementById('mcp-toggle');
        if (toggle) toggle.addEventListener('change', () => this.toggleService());

        const refreshBtn = document.querySelector('#page-mcp .fa-refresh')?.parentElement;
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadStatus());
    }

    async mount() {
        await this.loadStatus();
    }

    async loadStatus() {
        try {
            const data = await api.get('/mcp/status');
            this.renderStatus(data);
        } catch (e) {
            console.error(e);
        }
    }

    renderStatus(data) {
        const toggle = document.getElementById('mcp-toggle');
        const statusText = document.getElementById('mcp-status-text');
        const statusDetail = document.getElementById('mcp-status-detail');

        if (toggle) toggle.checked = data.is_active;
        if (statusText) statusText.innerText = data.is_active ? "ON" : "OFF";

        if (statusDetail) {
            if (data.is_active) {
                statusDetail.innerText = "Service Active & Listening";
                statusDetail.className = "text-xs text-emerald-400";
            } else {
                statusDetail.innerText = "Service Offline";
                statusDetail.className = "text-xs text-slate-400";
            }
        }

        const logContainer = document.getElementById('mcp-logs');
        if (logContainer) {
            if (data.logs.length === 0) {
                logContainer.innerHTML = '<div class="text-slate-500 italic">No activity recorded.</div>';
            } else {
                logContainer.innerHTML = data.logs.map(log => {
                    let color = "text-slate-300";
                    if(log.status === 'error') color = "text-rose-400";
                    if(log.status === 'crash') color = "text-rose-600 font-bold";

                    return `
                    <div class="border-b border-slate-900/50 pb-2 mb-2 last:border-0 font-mono">
                        <div class="flex justify-between text-[10px] text-slate-500 mb-1">
                            <span>${log.timestamp}</span>
                            <span class="uppercase ${color}">${log.status || 'INFO'}</span>
                        </div>
                        <div class="text-xs text-indigo-300 mb-0.5">${log.action}</div>
                        <div class="text-[10px] text-slate-400 break-all">${typeof log.details === 'object' ? JSON.stringify(log.details) : log.details}</div>
                    </div>`;
                }).join('');
                // Scroll to bottom
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        }
    }

    async toggleService() {
        const toggle = document.getElementById('mcp-toggle');
        const isActive = toggle.checked;

        try {
            await api.post('/mcp/toggle', { active: isActive });
            await this.loadStatus();
        } catch(e) {
            if(window.Toast) window.Toast.error("Failed to toggle service");
            toggle.checked = !isActive;
        }
    }
}
