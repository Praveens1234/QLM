// QLM Frontend Application
const API_BASE = '/api';

// --- Toast Notification System ---
window.showToast = function(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
        error: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
        info: 'bg-slate-800 border-slate-700 text-slate-300',
        warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400'
    };

    const icon = {
        success: '<i class="fa-solid fa-check-circle"></i>',
        error: '<i class="fa-solid fa-circle-exclamation"></i>',
        info: '<i class="fa-solid fa-info-circle"></i>',
        warning: '<i class="fa-solid fa-triangle-exclamation"></i>'
    };

    const toast = document.createElement('div');
    toast.className = `${colors[type]} backdrop-blur-md border p-4 rounded-lg shadow-2xl flex items-start gap-3 transform transition-all duration-300 translate-y-2 opacity-0 pointer-events-auto min-w-[300px] max-w-sm`;
    toast.innerHTML = `
        <div class="text-lg mt-0.5">${icon[type]}</div>
        <div class="font-medium text-sm leading-relaxed break-words">${message}</div>
    `;

    container.appendChild(toast);

    // Animate In
    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    });

    // Auto Dismiss
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
};

// --- Router ---
const router = {
    routes: {
        '': 'page-dashboard',
        '#dashboard': 'page-dashboard',
        '#data': 'page-data',
        '#strategies': 'page-strategies',
        '#backtest': 'page-backtest',
        '#assistant': 'page-assistant',
        '#mcp': 'page-mcp',
        '#settings': 'page-settings'
    },

    init: function() {
        window.addEventListener('hashchange', this.handleRoute.bind(this));
        window.addEventListener('load', this.handleRoute.bind(this));
        this.handleRoute(); // Initial load
    },

    handleRoute: function() {
        const hash = window.location.hash || '';
        const pageId = this.routes[hash] || 'page-dashboard';

        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.classList.add('hidden');
        });

        // Show active page
        const activePage = document.getElementById(pageId);
        if (activePage) {
            activePage.classList.remove('hidden');
        }

        // Update active nav link
        document.querySelectorAll('.nav-item').forEach(link => {
            link.classList.remove('bg-slate-800', 'text-white');
            link.classList.add('text-slate-400');
            const navIdMap = {
                '': 'nav-dashboard',
                '#dashboard': 'nav-dashboard',
                '#data': 'nav-data',
                '#strategies': 'nav-strategies',
                '#backtest': 'nav-backtest',
                '#assistant': 'nav-assistant',
                '#mcp': 'nav-mcp',
                '#settings': 'nav-settings'
            };
            const navId = navIdMap[hash] || 'nav-dashboard';
            if (link.id === navId) {
                link.classList.add('bg-slate-800', 'text-white');
                link.classList.remove('text-slate-400');
            }
        });

        // Page specific logic
        if (pageId === 'page-dashboard') loadDashboard();
        if (pageId === 'page-data') loadData();
        if (pageId === 'page-strategies') loadStrategies();
        if (pageId === 'page-backtest') { loadStrategies(); loadData(); }
        if (pageId === 'page-mcp') initMCP();
        if (pageId === 'page-assistant') initChat();
    },

    navigate: function(hash) {
        window.location.hash = hash;
    }
};

window.router = router;

// --- Dashboard ---
async function loadDashboard() {
    // Populate "Recent Activity" with strategies for now
    try {
        const res = await fetch(`${API_BASE}/strategies`);
        const strategies = await res.json();
        const activityContainer = document.getElementById('dashboard-activity');

        if(activityContainer) {
            // Sort by most recent version first? Assuming backend does, but otherwise...
            // Strategies don't have update timestamp yet, so just list them.

            activityContainer.innerHTML = '';
            activityContainer.className = "bg-slate-900/50 border border-slate-800 rounded-xl p-6 min-h-[300px] flex flex-col";
            // Header
            const header = document.createElement('div');
            header.className = "w-full flex justify-between items-center mb-4 border-b border-slate-800 pb-2";
            header.innerHTML = '<h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Recent Strategy Updates</h3>';
            activityContainer.appendChild(header);

            const list = document.createElement('div');
            list.className = "w-full space-y-3";

            strategies.slice(0, 5).forEach(s => {
                const item = document.createElement('div');
                item.className = "flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-800 hover:border-slate-700 transition-colors";
                item.innerHTML = `
                    <div class="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
                        <i class="fa-solid fa-code"></i>
                    </div>
                    <div>
                        <div class="text-sm font-medium text-white">${s.name}</div>
                        <div class="text-[10px] text-slate-500">Version ${s.latest_version}</div>
                    </div>
                    <div class="ml-auto text-[10px] text-slate-500 font-mono">
                        ${new Date().toLocaleDateString()}
                    </div>
                `;
                list.appendChild(item);
            });
            activityContainer.appendChild(list);

            // Add a "System Status" card
            // ...
        }
    } catch(e) {
        console.error("Dashboard Load Error", e);
    }
}

// --- Data Manager ---
async function loadData() {
    try {
        const res = await fetch(`${API_BASE}/data`);
        const data = await res.json();
        if(!Array.isArray(data)) return; // Handle empty or error gracefully

        const tbody = document.getElementById('data-table-body');
        if(tbody) tbody.innerHTML = '';

        const btSelect = document.getElementById('bt-dataset');
        if(btSelect) btSelect.innerHTML = '';

        data.forEach(d => {
            if(tbody) {
                const tr = document.createElement('tr');
                tr.className = 'border-b border-slate-800 hover:bg-slate-800/50 transition-colors';
                tr.innerHTML = `
                    <td class="px-6 py-4 text-white font-medium">${d.symbol}</td>
                    <td class="px-6 py-4 text-slate-400">${d.timeframe}</td>
                    <td class="px-6 py-4 text-slate-400">${d.start_date ? d.start_date.split('T')[0] : '-'}</td>
                    <td class="px-6 py-4 text-right text-slate-400 font-mono">${d.row_count || 0}</td>
                    <td class="px-6 py-4 text-right">
                        <button class="text-rose-400 hover:text-rose-300 transition-colors p-2 hover:bg-rose-500/10 rounded" onclick="deleteData('${d.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }

            if(btSelect) {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = `${d.symbol} ${d.timeframe} (${d.row_count} rows)`;
                btSelect.appendChild(opt);
            }
        });

        const statEl = document.querySelector('[data-stat="datasets"]');
        if(statEl) statEl.textContent = data.length;

    } catch (e) {
        showToast("Failed to load data: " + e.message, 'error');
    }
}

async function importFromUrl() {
    const url = document.getElementById('url-input').value;
    const symbol = document.getElementById('url-symbol').value;
    const timeframe = document.getElementById('url-tf').value;

    if (!url || !symbol) return showToast("URL and Symbol are required", 'warning');

    const btn = document.getElementById('btn-import-url');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Importing...';

    try {
        const res = await fetch(`${API_BASE}/data/url`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url, symbol, timeframe })
        });

        const result = await res.json();
        if (res.ok) {
            showToast(`Imported ${result.data.row_count} rows successfully`, 'success');
            loadData();
        } else {
            showToast(result.detail, 'error');
        }
    } catch (e) {
        showToast("Import failed: " + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Download';
    }
}

window.deleteData = async function(id) {
    if(!confirm("Are you sure?")) return;
    try {
        const res = await fetch(`${API_BASE}/data/${id}`, { method: 'DELETE' });
        if(res.ok) {
            showToast("Dataset deleted", 'success');
            loadData();
        } else {
            showToast("Delete failed", 'error');
        }
    } catch(e) { showToast(e.message, 'error'); }
};

window.switchImportTab = function(tab) {
    document.getElementById('import-local').classList.add('hidden');
    document.getElementById('import-url').classList.add('hidden');
    document.getElementById('tab-local').className = "text-sm font-semibold text-slate-500 hover:text-slate-300 border-b-2 border-transparent pb-2 transition-colors focus:outline-none";
    document.getElementById('tab-url').className = "text-sm font-semibold text-slate-500 hover:text-slate-300 border-b-2 border-transparent pb-2 transition-colors focus:outline-none";

    if(tab === 'local') {
        document.getElementById('import-local').classList.remove('hidden');
        document.getElementById('tab-local').className = "text-sm font-semibold text-indigo-400 border-b-2 border-indigo-400 pb-2 transition-colors focus:outline-none";
    } else {
        document.getElementById('import-url').classList.remove('hidden');
        document.getElementById('tab-url').className = "text-sm font-semibold text-indigo-400 border-b-2 border-indigo-400 pb-2 transition-colors focus:outline-none";
    }
}

// --- Strategy Lab ---
async function loadStrategies() {
    try {
        const res = await fetch(`${API_BASE}/strategies`);
        const strategies = await res.json();

        const statEl = document.querySelector('[data-stat="strategies"]');
        if(statEl) statEl.textContent = strategies.length;

        const list = document.getElementById('strategy-list');
        if(list) {
            list.innerHTML = '';
            strategies.forEach(s => {
                const div = document.createElement('div');
                div.className = "px-3 py-2 hover:bg-slate-800 rounded cursor-pointer transition-colors group border border-transparent hover:border-slate-700";
                div.onclick = () => loadStrategyCode(s.name); // Need to implement this if editor is real
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="text-sm font-medium text-slate-300 group-hover:text-white">${s.name}</span>
                        <span class="text-[10px] text-slate-500 font-mono">v${s.latest_version}</span>
                    </div>
                `;
                list.appendChild(div);
            });
        }

        const select = document.getElementById('bt-strategy');
        if(select) {
            select.innerHTML = '';
            strategies.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.name;
                opt.textContent = s.name;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Load Strategies Error:", e);
    }
}

window.createNewStrategy = function() {
    const name = prompt("Strategy Name:");
    if(name) {
        // Mock create
        showToast(`Strategy ${name} created (mock)`, 'success');
        loadStrategies();
    }
};

// --- AI Chat ---
let chatInitialized = false;
let currentSessionId = null;
console.log("Showdown available?", typeof showdown);
const mdConverter = typeof showdown !== 'undefined' ? new showdown.Converter({
    tables: true,
    tasklists: true,
    ghCodeBlocks: true,
    openLinksInNewWindow: true
}) : null;

async function initChat() {
    if(chatInitialized) return;
    chatInitialized = true;

    const input = document.getElementById('ai-input');
    const sendBtn = document.getElementById('ai-send-btn');

    sendBtn.onclick = sendMessage;
    input.onkeypress = (e) => { if(e.key === 'Enter') sendMessage(); };

    // Create session
    try {
        const res = await fetch(`${API_BASE}/ai/sessions`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: 'user', model: 'gpt-4o' })
        });
        const data = await res.json();
        currentSessionId = data.session_id;
    } catch(e) {
        showToast("Failed to init AI session", 'error');
    }
}

async function sendMessage() {
    const input = document.getElementById('ai-input');
    const text = input.value.trim();
    if(!text) return;

    input.value = '';
    renderMessage('user', text);

    // Loading State
    const loadingId = 'loading-' + Date.now();
    renderLoading(loadingId);

    try {
        const res = await fetch(`${API_BASE}/ai/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: currentSessionId,
                message: text
            })
        });

        const data = await res.json();
        removeLoading(loadingId);
        renderMessage('assistant', data.response);

    } catch(e) {
        removeLoading(loadingId);
        showToast("AI Error: " + e.message, 'error');
    }
}

function renderMessage(role, content) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    div.className = `flex ${role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`;

    const bubble = document.createElement('div');
    bubble.className = role === 'user'
        ? "max-w-[85%] bg-indigo-600 text-white rounded-2xl rounded-tr-none px-5 py-3 shadow-md"
        : "max-w-[85%] bg-slate-800 border border-slate-700 text-slate-200 rounded-2xl rounded-tl-none px-5 py-4 shadow-md prose prose-invert prose-sm max-w-none";

    if(role === 'assistant') {
        // Parse Markdown
        if(mdConverter) {
            bubble.innerHTML = mdConverter.makeHtml(content);
        } else {
            // Manual Fallback for basic Markdown
            let html = content
                .replace(/</g, '&lt;').replace(/>/g, '&gt;') // Escape HTML
                .replace(/```python([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>')
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/`([^`]+)`/g, '<code class="bg-slate-700 px-1 py-0.5 rounded text-xs">$1</code>')
                .replace(/\n/g, '<br>');
            bubble.innerHTML = html;
        }
        // Highlight Code
        if(typeof hljs !== 'undefined') {
            bubble.querySelectorAll('pre code').forEach((el) => {
                hljs.highlightElement(el);
            });
        }
    } else {
        bubble.textContent = content;
    }

    div.appendChild(bubble);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function renderLoading(id) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    div.id = id;
    div.className = "flex justify-start animate-fade-in";
    div.innerHTML = `
        <div class="bg-slate-800 border border-slate-700 px-4 py-3 rounded-2xl rounded-tl-none shadow-md flex gap-1.5 items-center">
            <div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></div>
            <div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if(el) el.remove();
}

// --- Backtest Runner ---
async function runBacktest() {
    const strategy = document.getElementById('bt-strategy').value;
    const dataset_id = document.getElementById('bt-dataset').value;

    if (!strategy || !dataset_id) return showToast("Please select a strategy and dataset", 'warning');

    const statusBadge = document.getElementById('bt-status-badge');
    const statusText = document.getElementById('bt-status');
    const progressBar = document.getElementById('bt-progress-bar');

    statusBadge.classList.remove('hidden');
    statusText.textContent = "INITIALIZING...";
    progressBar.style.width = "5%";

    try {
        const res = await fetch(`${API_BASE}/backtest/run`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                strategy_name: strategy,
                dataset_id: dataset_id
            })
        });

        const result = await res.json();

        if (res.ok && result.status === 'success') {
             progressBar.style.width = "100%";
             statusText.textContent = "COMPLETED";
             statusBadge.className = "bg-emerald-500/10 text-emerald-400 text-[10px] px-2 py-0.5 rounded font-bold border border-emerald-500/20";
             statusBadge.textContent = "SUCCESS";
             showToast("Backtest completed successfully", 'success');
             renderResults(result.results);
        } else {
            progressBar.style.width = "100%";
            progressBar.classList.add('bg-rose-500');
            statusText.textContent = "FAILED";
            statusBadge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold border border-rose-500/20";
            statusBadge.textContent = "ERROR";
            showToast("Backtest failed: " + (result.detail || "Unknown error"), 'error');
        }
    } catch (e) {
        showToast("Error running backtest: " + e.message, 'error');
    }
}
window.runBacktest = runBacktest;

window.renderResults = function(results) {
    const resultsContainer = document.getElementById('bt-results');
    const m = results.metrics;

    // Store CSV for download
    window.currentCsvData = results.csv_export;

    resultsContainer.innerHTML = `
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 animate-fade-in">
             <!-- Primary Metrics -->
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Net Profit</div>
                <div class="${m.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'} text-lg font-bold font-mono">$${m.net_profit.toFixed(2)}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Win Rate</div>
                <div class="text-white text-lg font-bold font-mono">${m.win_rate}%</div>
                <div class="text-[9px] text-slate-500 mt-1">L: ${m.win_rate_long}% | S: ${m.win_rate_short}%</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Profit Factor</div>
                <div class="text-white text-lg font-bold font-mono">${m.profit_factor}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Max DD</div>
                <div class="text-rose-400 text-lg font-bold font-mono">${m.max_drawdown_pct}%</div>
                <div class="text-[9px] text-slate-500 mt-1">${m.max_drawdown_r} R</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Total Trades</div>
                <div class="text-white text-lg font-bold font-mono">${m.total_trades}</div>
                <div class="text-[9px] text-slate-500 mt-1">W: ${m.long_wins + m.short_wins} | L: ${m.long_losses + m.short_losses}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Expectancy</div>
                <div class="text-white text-lg font-bold font-mono">${m.expectancy_r} R</div>
                <div class="text-[9px] text-slate-500 mt-1">$${m.expectancy}</div>
             </div>

             <!-- Secondary Metrics Row -->
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Avg PnL (R)</div>
                <div class="${m.avg_r_trade >= 0 ? 'text-emerald-400' : 'text-rose-400'} text-base font-bold font-mono">${m.avg_r_trade} R</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Total R</div>
                <div class="${m.total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'} text-base font-bold font-mono">${m.total_r} R</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Avg Trades/Day</div>
                <div class="text-white text-base font-bold font-mono">${m.avg_trades_day}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Avg Trades/Week</div>
                <div class="text-white text-base font-bold font-mono">${m.avg_trades_week}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Avg Trades/Month</div>
                <div class="text-white text-base font-bold font-mono">${m.avg_trades_month}</div>
             </div>
              <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl col-span-1">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Avg Duration</div>
                <div class="text-white text-base font-bold font-mono">${m.avg_duration}m</div>
             </div>
        </div>
        
        <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm animate-fade-in">
             <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Trade List</h3>
                <button onclick="downloadCSV()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold uppercase px-3 py-1.5 rounded transition-colors flex items-center gap-2">
                    <i class="fa-solid fa-download"></i> Export CSV
                </button>
            </div>
            <div class="max-h-96 overflow-y-auto overflow-x-auto">
                 <table class="w-full text-left text-xs font-mono whitespace-nowrap">
                    <thead class="bg-slate-950 text-slate-500 sticky top-0">
                        <tr>
                            <th class="px-4 py-2">Entry Time</th>
                            <th class="px-4 py-2">Exit Time</th>
                            <th class="px-4 py-2">Dir</th>
                            <th class="px-4 py-2">Status</th>
                            <th class="px-4 py-2 text-right">Entry</th>
                            <th class="px-4 py-2 text-right">Exit</th>
                            <th class="px-4 py-2 text-right">SL</th>
                            <th class="px-4 py-2 text-right">TP</th>
                            <th class="px-4 py-2 text-right">PnL</th>
                            <th class="px-4 py-2 text-right">R</th>
                            <th class="px-4 py-2 text-right">DD</th>
                            <th class="px-4 py-2 text-right">Runup</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 text-slate-400">
                        ${results.trades.map(t => {
                            // Calculate R for display if missing
                            const rVal = (t.initial_risk && t.initial_risk > 0) ? (t.pnl / t.initial_risk).toFixed(2) : '-';
                            const statusColor = t.pnl > 0 ? 'text-emerald-400' : (t.pnl < 0 ? 'text-rose-400' : 'text-slate-400');

                            return `
                            <tr class="hover:bg-slate-800/50">
                                <td class="px-4 py-2">${t.entry_time}</td>
                                <td class="px-4 py-2">${t.exit_time}</td>
                                <td class="px-4 py-2 ${t.direction === 'long' ? 'text-emerald-400' : 'text-rose-400'} uppercase font-bold">${t.direction}</td>
                                <td class="px-4 py-2 ${statusColor}">${t.status || (t.pnl > 0 ? 'Win' : 'Loss')}</td>
                                <td class="px-4 py-2 text-right">${t.entry_price.toFixed(2)}</td>
                                <td class="px-4 py-2 text-right">${t.exit_price.toFixed(2)}</td>
                                <td class="px-4 py-2 text-right text-rose-300">${t.sl ? t.sl.toFixed(2) : '-'}</td>
                                <td class="px-4 py-2 text-right text-emerald-300">${t.tp ? t.tp.toFixed(2) : '-'}</td>
                                <td class="px-4 py-2 text-right ${statusColor}">${t.pnl.toFixed(2)}</td>
                                <td class="px-4 py-2 text-right ${rVal > 0 ? 'text-emerald-400' : (rVal < 0 ? 'text-rose-400' : '')}">${rVal}</td>
                                <td class="px-4 py-2 text-right text-rose-400">${t.max_drawdown_trade ? t.max_drawdown_trade.toFixed(2) : '0.00'}</td>
                                <td class="px-4 py-2 text-right text-emerald-400">${t.max_runup ? t.max_runup.toFixed(2) : '0.00'}</td>
                            </tr>
                        `}).join('')}
                    </tbody>
                 </table>
            </div>
        </div>
    `;

    if (results.chart_data && results.chart_data.ohlcv) {
         document.getElementById('bt-charts').classList.remove('hidden');
         renderBacktestCharts(results.chart_data, results.trades);
    }
}

window.downloadCSV = function() {
    if (!window.currentCsvData) return showToast("No CSV data available", 'warning');

    const blob = new Blob([window.currentCsvData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', 'backtest_ledger.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
};


// --- Charting ---
let mainChart = null;
let candleSeries = null;
let equitySeries = null;

window.renderBacktestCharts = function(data, trades) {
    const container = document.getElementById('chart-container');
    container.innerHTML = '';

    if (mainChart) {
        mainChart.remove();
        mainChart = null;
    }

    const { createChart } = LightweightCharts;

    const chartOptions = {
        layout: {
            textColor: '#94a3b8',
            background: { type: 'solid', color: '#0f172a' },
        },
        grid: {
            vertLines: { color: '#1e293b' },
            horzLines: { color: '#1e293b' },
        },
        rightPriceScale: { borderColor: '#334155' },
        timeScale: { borderColor: '#334155', timeVisible: true },
        width: container.clientWidth,
        height: 500
    };

    mainChart = createChart(container, chartOptions);

    candleSeries = mainChart.addCandlestickSeries({
        upColor: '#10b981', downColor: '#f43f5e',
        borderVisible: false, wickUpColor: '#10b981', wickDownColor: '#f43f5e',
    });

    const sorted = data.ohlcv.sort((a, b) => a.time - b.time);
    const unique = [];
    if (sorted.length > 0) {
        unique.push(sorted[0]);
        for (let i = 1; i < sorted.length; i++) {
            if (sorted[i].time > sorted[i-1].time) unique.push(sorted[i]);
        }
    }
    candleSeries.setData(unique);

    const markers = [];
    trades.forEach(t => {
        markers.push({
            time: t.entry_ts,
            position: t.direction === 'long' ? 'belowBar' : 'aboveBar',
            color: t.direction === 'long' ? '#6366f1' : '#f59e0b',
            shape: t.direction === 'long' ? 'arrowUp' : 'arrowDown',
            text: 'Entry'
        });
        markers.push({
            time: t.exit_ts,
            position: t.direction === 'long' ? 'aboveBar' : 'belowBar',
            color: '#94a3b8',
            shape: 'circle',
            text: `Exit ${t.pnl > 0 ? '+' : ''}${t.pnl.toFixed(0)}`
        });
    });
    markers.sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(markers);

    equitySeries = mainChart.addLineSeries({
        color: '#fbbf24', lineWidth: 2, priceScaleId: 'left',
    });

    mainChart.priceScale('left').applyOptions({ visible: true, borderColor: '#334155' });

    const equityData = data.equity.sort((a, b) => a.time - b.time);
    const uniqueEquity = [];
    if (equityData.length > 0) {
        uniqueEquity.push(equityData[0]);
        for (let i = 1; i < equityData.length; i++) {
            if (equityData[i].time > equityData[i-1].time) uniqueEquity.push(equityData[i]);
        }
    }
    equitySeries.setData(uniqueEquity);
    mainChart.timeScale().fitContent();

    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) return;
        const newRect = entries[0].contentRect;
        mainChart.applyOptions({ width: newRect.width, height: newRect.height });
    }).observe(container);
};

// --- MCP Service ---
async function initMCP() {
    const statusEl = document.getElementById('mcp-status-detail');
    const logsEl = document.getElementById('mcp-logs');
    const toggleCheckbox = document.getElementById('mcp-toggle');
    const statusText = document.getElementById('mcp-status-text');

    if(!statusEl) return;

    const endpointInput = document.getElementById('mcp-endpoint');
    if(endpointInput) {
        endpointInput.value = `${window.location.protocol}//${window.location.host}/api/mcp/sse`;
    }

    async function updateStatus() {
        try {
            const res = await fetch(`${API_BASE}/mcp/status`);
            const data = await res.json();

            toggleCheckbox.checked = data.is_active;

            if (data.is_active) {
                statusEl.textContent = "Service is Online";
                statusEl.className = "text-xs text-emerald-400";
                statusText.textContent = "ON";
                statusText.className = "ml-3 text-sm font-medium text-emerald-400";
            } else {
                statusEl.textContent = "Service is Offline";
                statusEl.className = "text-xs text-rose-400";
                statusText.textContent = "OFF";
                statusText.className = "ml-3 text-sm font-medium text-slate-300";
            }

            if(logsEl) {
                logsEl.innerHTML = '';
                if(data.logs.length === 0) {
                     logsEl.innerHTML = '<div class="text-slate-500 italic">No activity recorded.</div>';
                } else {
                    data.logs.forEach(log => {
                        const div = document.createElement('div');
                        div.className = "border-b border-slate-800 pb-2 last:border-0";
                        const color = log.status === 'error' ? 'text-rose-400' : (log.status === 'crash' ? 'text-rose-600' : 'text-emerald-400');
                        div.innerHTML = `
                            <span class="text-slate-500 mr-2">[${new Date(log.timestamp).toLocaleTimeString()}]</span>
                            <span class="${color} font-bold mr-2">${log.action}</span>
                            <span class="text-slate-400">${log.details}</span>
                        `;
                        logsEl.appendChild(div);
                    });
                }
            }
        } catch (e) {
            console.error("MCP Status Error:", e);
        }
    }

    window.toggleMCPService = async () => {
        const isActive = toggleCheckbox.checked;
        await fetch(`${API_BASE}/mcp/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ active: isActive })
        });
        updateStatus();
    };

    updateStatus();
    if(!window.mcpInterval) {
        window.mcpInterval = setInterval(updateStatus, 5000);
    }
}

// --- Settings ---
async function loadSettings() {
    try {
        const [activeRes, providersRes] = await Promise.all([
            fetch(`${API_BASE}/ai/config/active`),
            fetch(`${API_BASE}/ai/config/providers`)
        ]);

        const activeConfig = await activeRes.json();
        const providers = await providersRes.json();

        // Populate Providers List
        const list = document.getElementById('provider-list');
        if (list) {
            list.innerHTML = '';
            providers.forEach(p => {
                const div = document.createElement('div');
                div.className = "px-6 py-4 flex justify-between items-center";
                div.innerHTML = `
                    <div>
                        <div class="font-medium text-white text-sm">${p.name}</div>
                        <div class="text-[10px] text-slate-500 font-mono mt-0.5">${p.base_url}</div>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="text-[10px] px-2 py-0.5 rounded ${p.has_key ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'} border ${p.has_key ? 'border-emerald-500/20' : 'border-rose-500/20'} font-bold uppercase">
                            ${p.has_key ? 'Configured' : 'No Key'}
                        </span>
                        <div class="text-[10px] text-slate-500">${p.models.length} Models</div>
                    </div>
                `;
                list.appendChild(div);
            });
        }

        // Populate Active Provider Select
        const providerSelect = document.getElementById('active-provider');
        if (providerSelect) {
            providerSelect.innerHTML = '<option value="">Select Provider...</option>';
            providers.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                if (p.name === activeConfig.provider_name || p.id === activeConfig.provider_id) { // Backend needs to send ID ideally
                     // Since activeConfig returns provider_name, we match name or id logic if needed.
                     // The backend get_active_config() returns provider_name.
                     // We should ideally return provider_id too.
                     // But for now, we can match logic or update backend.
                     // Assuming 'id' matches logic if available.
                }
                providerSelect.appendChild(opt);
            });

            // Hack to select active based on name comparison if ID missing
            // But let's rely on finding it.
            for (let i=0; i<providerSelect.options.length; i++) {
                if (providerSelect.options[i].text === activeConfig.provider_name) {
                    providerSelect.selectedIndex = i;
                    break;
                }
            }

            if (providerSelect.value) {
                await loadProviderModels(providerSelect.value, activeConfig.model);
            }
        }

    } catch (e) {
        console.error("Settings Load Error", e);
    }
}

window.loadProviderModels = async function(providerId, activeModelId = null) {
    const modelSelect = document.getElementById('active-model');
    if (!modelSelect || !providerId) return;

    modelSelect.innerHTML = '<option>Loading...</option>';
    modelSelect.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/ai/config/models/${providerId}`);
        const data = await res.json();

        modelSelect.innerHTML = '';
        data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            modelSelect.appendChild(opt);
        });

        if (activeModelId) {
            modelSelect.value = activeModelId;
        }

    } catch (e) {
        showToast("Failed to load models: " + e.message, 'error');
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
    } finally {
        modelSelect.disabled = false;
    }
};

window.saveActiveConfig = async function() {
    const providerId = document.getElementById('active-provider').value;
    const modelId = document.getElementById('active-model').value;

    if (!providerId || !modelId) return showToast("Select a provider and model", 'warning');

    try {
        const res = await fetch(`${API_BASE}/ai/config/active`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ provider_id: providerId, model_id: modelId })
        });

        if (res.ok) {
            showToast("AI Configuration Updated", 'success');
        } else {
            showToast("Failed to update config", 'error');
        }
    } catch (e) {
        showToast("Error: " + e.message, 'error');
    }
};

window.addProvider = async function() {
    const name = document.getElementById('new-prov-name').value;
    const url = document.getElementById('new-prov-url').value;
    const key = document.getElementById('new-prov-key').value;

    if (!name || !url || !key) return showToast("All fields required", 'warning');

    try {
        const res = await fetch(`${API_BASE}/ai/config/providers`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name, base_url: url, api_key: key })
        });

        if (res.ok) {
            showToast("Provider Added", 'success');
            document.getElementById('new-prov-name').value = '';
            document.getElementById('new-prov-url').value = '';
            document.getElementById('new-prov-key').value = '';
            loadSettings();
        } else {
            showToast("Failed to add provider", 'error');
        }
    } catch (e) {
        showToast("Error: " + e.message, 'error');
    }
};

// --- Init ---
router.init();
loadStrategies();
loadData();
// Hook loadSettings into router or call if on settings page
if (window.location.hash === '#settings') loadSettings();
// Also hook router handleRoute to call it when navigating
const originalHandle = router.handleRoute;
router.handleRoute = function() {
    originalHandle.apply(this);
    if (window.location.hash === '#settings') loadSettings();
};
