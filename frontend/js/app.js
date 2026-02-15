// QLM Frontend Application
const API_BASE = '/api';

// --- Router ---
const router = {
    routes: {
        '': 'page-dashboard',
        '#dashboard': 'page-dashboard',
        '#data': 'page-data',
        '#strategies': 'page-strategies',
        '#backtest': 'page-backtest',
        '#assistant': 'page-assistant', // Changed from #ai
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
        document.querySelectorAll('.nav-item').forEach(link => { // Changed class selector
            link.classList.remove('bg-slate-800', 'text-white');
            link.classList.add('text-slate-400');
            // Logic to match href or id
            // Simple approach: map hash to nav id
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
        if (pageId === 'page-data') loadData();
        if (pageId === 'page-strategies') loadStrategies();
        if (pageId === 'page-backtest') { loadStrategies(); loadData(); } // Populate dropdowns
        if (pageId === 'page-mcp') initMCP();
    },

    navigate: function(hash) {
        window.location.hash = hash;
    }
};

// Expose router to window
window.router = router;

// --- Data Manager ---
async function loadData() {
    try {
        const res = await fetch(`${API_BASE}/data`);
        const data = await res.json();
        const tbody = document.getElementById('data-table-body');
        if(tbody) tbody.innerHTML = '';

        // Populate Backtest Dataset Dropdown
        const btSelect = document.getElementById('bt-dataset');
        if(btSelect) btSelect.innerHTML = '';

        data.forEach(d => {
            if(tbody) {
                const tr = document.createElement('tr');
                tr.className = 'border-b border-slate-800 hover:bg-slate-800/50 transition-colors';
                tr.innerHTML = `
                    <td class="px-6 py-4 text-white font-medium">${d.symbol}</td>
                    <td class="px-6 py-4 text-slate-400">${d.timeframe}</td>
                    <td class="px-6 py-4 text-slate-400">${d.start_date || '-'} to ${d.end_date || '-'}</td>
                    <td class="px-6 py-4 text-right text-slate-400">${d.rows || 0}</td>
                    <td class="px-6 py-4 text-right">
                        <button class="text-rose-400 hover:text-rose-300 transition-colors" onclick="deleteData('${d.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            }

            if(btSelect) {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = `${d.symbol} ${d.timeframe} (${d.rows} rows)`;
                btSelect.appendChild(opt);
            }
        });

        // Update Stats on Dashboard (if element exists)
        const statEl = document.querySelector('[data-stat="datasets"]');
        if(statEl) statEl.textContent = data.length;

    } catch (e) {
        console.error("Load Data Error:", e);
    }
}

async function importFromUrl() {
    const url = document.getElementById('url-input').value;
    const symbol = document.getElementById('url-symbol').value;
    const timeframe = document.getElementById('url-tf').value;

    if (!url || !symbol) return alert("URL and Symbol are required");

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
            alert(`Imported ${result.rows} rows.`);
            loadData();
        } else {
            alert("Error: " + result.detail);
        }
    } catch (e) {
        alert("Import failed: " + e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-cloud-download"></i> Download';
    }
}

function switchImportTab(tab) {
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
window.switchImportTab = switchImportTab;

// --- Strategy Lab ---
async function loadStrategies() {
    try {
        const res = await fetch(`${API_BASE}/strategies`);
        const strategies = await res.json();

        // Update Stats
        const statEl = document.querySelector('[data-stat="strategies"]');
        if(statEl) statEl.textContent = strategies.length;

        // List
        const list = document.getElementById('strategy-list');
        if(list) {
            list.innerHTML = '';
            strategies.forEach(s => {
                const div = document.createElement('div');
                div.className = "px-3 py-2 hover:bg-slate-800 rounded cursor-pointer transition-colors group";
                div.onclick = () => loadStrategyCode(s.name);
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="text-sm font-medium text-slate-300 group-hover:text-white">${s.name}</span>
                        <span class="text-[10px] text-slate-500 font-mono">v${s.latest_version}</span>
                    </div>
                `;
                list.appendChild(div);
            });
        }

        // Populate select in Backtest Runner
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

// --- Backtest Runner ---
async function runBacktest() {
    const strategy = document.getElementById('bt-strategy').value;
    const dataset_id = document.getElementById('bt-dataset').value;

    if (!strategy || !dataset_id) return alert("Please select a strategy and dataset");

    // Status Update
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

             renderResults(result.results);
        } else {
            progressBar.style.width = "100%";
            progressBar.classList.add('bg-rose-500');
            statusText.textContent = "FAILED";
            statusBadge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold border border-rose-500/20";
            statusBadge.textContent = "ERROR";
            alert("Backtest failed: " + (result.detail || "Unknown error"));
        }
    } catch (e) {
        alert("Error running backtest: " + e);
    }
}
window.runBacktest = runBacktest;

window.renderResults = function(results) {
    // Show results section
    const resultsContainer = document.getElementById('bt-results');
    resultsContainer.innerHTML = `
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Net Profit</div>
                <div class="${results.metrics.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'} text-xl font-bold font-mono">$${results.metrics.net_profit.toFixed(2)}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Win Rate</div>
                <div class="text-white text-xl font-bold font-mono">${(results.metrics.win_rate * 100).toFixed(1)}%</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Max Drawdown</div>
                <div class="text-rose-400 text-xl font-bold font-mono">${(results.metrics.max_drawdown * 100).toFixed(1)}%</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <div class="text-slate-500 text-[10px] font-bold uppercase tracking-wide mb-1">Profit Factor</div>
                <div class="text-white text-xl font-bold font-mono">${results.metrics.profit_factor.toFixed(2)}</div>
             </div>
        </div>
        
        <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
             <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Trade List</h3>
            </div>
            <div class="max-h-64 overflow-y-auto">
                 <table class="w-full text-left text-xs font-mono">
                    <thead class="bg-slate-950 text-slate-500 sticky top-0">
                        <tr>
                            <th class="px-4 py-2">Entry Time</th>
                            <th class="px-4 py-2">Dir</th>
                            <th class="px-4 py-2 text-right">Price</th>
                            <th class="px-4 py-2 text-right">Exit</th>
                            <th class="px-4 py-2 text-right">PnL</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 text-slate-400">
                        ${results.trades.map(t => `
                            <tr class="hover:bg-slate-800/50">
                                <td class="px-4 py-2">${t.entry_time}</td>
                                <td class="px-4 py-2 ${t.direction === 'long' ? 'text-emerald-400' : 'text-rose-400'} uppercase font-bold">${t.direction}</td>
                                <td class="px-4 py-2 text-right">${t.entry_price.toFixed(2)}</td>
                                <td class="px-4 py-2 text-right">${t.exit_price.toFixed(2)}</td>
                                <td class="px-4 py-2 text-right ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}">${t.pnl.toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                 </table>
            </div>
        </div>
    `;

    // Chart
    if (results.chart_data && results.chart_data.ohlcv) {
         document.getElementById('bt-charts').classList.remove('hidden');
         renderBacktestCharts(results.chart_data, results.trades);
    }
}


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
        rightPriceScale: {
            borderColor: '#334155',
        },
        timeScale: {
            borderColor: '#334155',
            timeVisible: true,
        },
        width: container.clientWidth,
        height: 500
    };

    mainChart = createChart(container, chartOptions);

    // 1. Candlestick
    candleSeries = mainChart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#f43f5e',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#f43f5e',
    });

    // Sort & Unique
    const sorted = data.ohlcv.sort((a, b) => a.time - b.time);
    const unique = [];
    if (sorted.length > 0) {
        unique.push(sorted[0]);
        for (let i = 1; i < sorted.length; i++) {
            if (sorted[i].time > sorted[i-1].time) {
                unique.push(sorted[i]);
            }
        }
    }
    candleSeries.setData(unique);

    // 2. Markers
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

    // 3. Equity Curve (Overlay on Left Scale)
    equitySeries = mainChart.addLineSeries({
        color: '#fbbf24',
        lineWidth: 2,
        priceScaleId: 'left',
    });

    mainChart.priceScale('left').applyOptions({
        visible: true,
        borderColor: '#334155',
    });

    const equityData = data.equity.sort((a, b) => a.time - b.time);
    // Ensure unique
    const uniqueEquity = [];
    if (equityData.length > 0) {
        uniqueEquity.push(equityData[0]);
        for (let i = 1; i < equityData.length; i++) {
            if (equityData[i].time > equityData[i-1].time) {
                uniqueEquity.push(equityData[i]);
            }
        }
    }
    equitySeries.setData(uniqueEquity);

    mainChart.timeScale().fitContent();

    // Resize Observer
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) { return; }
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

    // Update MCP Endpoint Display dynamically
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

            // Logs
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
    // Poll
    if(!window.mcpInterval) {
        window.mcpInterval = setInterval(updateStatus, 5000);
    }
}

// --- Init ---
router.init();
loadStrategies();
loadData();
