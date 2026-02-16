const API_URL = "/api";
const WS_URL = `ws://${window.location.host}/api/ws`;

// State
let socket;
let datasets = [];
let strategies = [];
let sessions = [];
let currentSessionId = null;
let currentStrategyCode = "";
let editor; // Monaco instance

// Router (Simple hash router)
const router = {
    navigate: (page) => {
        document.querySelectorAll('.page').forEach(el => {
            el.classList.add('hidden');
        });

        const target = document.getElementById(`page-${page}`);
        if(target) {
            target.classList.remove('hidden');
            target.classList.add('animate-fade-in');
        }

        window.location.hash = page;

        // Update Nav Active State
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.remove('bg-indigo-600/10', 'text-indigo-400', 'border-l-2', 'border-indigo-500');
            // Remove icon active color
            const icon = btn.querySelector('i');
            if(icon) {
                icon.classList.remove('text-indigo-400');
                icon.classList.add('text-slate-500');
            }
            btn.classList.add('text-slate-400', 'hover:bg-slate-800');
        });

        const activeBtn = document.getElementById(`nav-${page}`);
        if (activeBtn) {
            activeBtn.classList.remove('text-slate-400', 'hover:bg-slate-800');
            activeBtn.classList.add('bg-indigo-600/10', 'text-indigo-400', 'border-l-2', 'border-indigo-500');
             const icon = activeBtn.querySelector('i');
            if(icon) {
                icon.classList.remove('text-slate-500');
                icon.classList.add('text-indigo-400');
            }
        }

        // Close mobile sidebar if open
        const sidebar = document.getElementById('sidebar');
        if (sidebar && !sidebar.classList.contains('-translate-x-full') && window.innerWidth < 768) {
            toggleSidebar();
        }

        // Page specific loads
        if (page === 'dashboard') updateDashboardStats();
        if (page === 'data') loadDatasets();
        if (page === 'strategies') {
            loadStrategies();
            setTimeout(() => { if (editor) editor.layout(); }, 200);
        }
        if (page === 'backtest') loadBacktestOptions();
        if (page === 'assistant') loadSessions();
        if (page === 'mcp') loadMCPStatus();
    },
    init: () => {
        window.addEventListener('hashchange', () => router.navigate(window.location.hash.substring(1) || 'dashboard'));
        router.navigate(window.location.hash.substring(1) || 'dashboard');
    }
};

// UI Toggles
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (sidebar.classList.contains('-translate-x-full')) {
        // Open
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden', 'opacity-0', 'pointer-events-none');
    } else {
        // Close
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('opacity-0', 'pointer-events-none');
        setTimeout(() => overlay.classList.add('hidden'), 300); // Wait for fade out
    }
}

// AI Settings & Registry
let providers = [];
let activeConfig = {};

async function loadProviders() {
    try {
        const res = await fetch(`${API_URL}/ai/config/providers`);
        providers = await res.json();

        // Render List
        const list = document.getElementById('provider-list');
        list.innerHTML = providers.map(p => `
            <li class="px-6 py-3 flex justify-between items-center">
                <div>
                    <div class="font-medium text-slate-300">${p.name}</div>
                    <div class="text-[10px] text-slate-500 font-mono">${p.base_url}</div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-[10px] ${p.has_key ? 'text-emerald-500' : 'text-rose-500'} bg-slate-800 px-2 py-0.5 rounded">
                        ${p.has_key ? 'KEY SET' : 'NO KEY'}
                    </span>
                    <div class="text-xs text-slate-500">${p.models.length} Models</div>
                </div>
            </li>
        `).join('');

        // Populate Active Dropdown
        const activeSelect = document.getElementById('active-provider');
        activeSelect.innerHTML = `<option value="">Select Provider</option>` +
            providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

        // Load Active Config
        const confRes = await fetch(`${API_URL}/ai/config/active`);
        activeConfig = await confRes.json();

        if (activeConfig.base_url) {
             if(activeConfig.provider_name) {
                 const p = providers.find(x => x.name === activeConfig.provider_name);
                 if(p) {
                     activeSelect.value = p.id;
                     loadProviderModels(p.id, activeConfig.model);
                 }
             }
        }
    } catch (e) { console.error("Error loading providers", e); }
}

async function addProvider() {
    const name = document.getElementById('new-prov-name').value;
    const url = document.getElementById('new-prov-url').value;
    const key = document.getElementById('new-prov-key').value;

    if(!name || !url || !key) {
        Toast.error("Please fill all fields");
        return;
    }

    try {
        await fetch(`${API_URL}/ai/config/providers`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, base_url: url, api_key: key})
        });

        const provId = name.toLowerCase().replace(/ /g, "_");
        await loadProviders();
        Toast.success("Provider added. Fetching models...");
        await fetchModelsForProvider(provId);
        await loadProviders();

        document.getElementById('new-prov-name').value = "";
        document.getElementById('new-prov-url').value = "";
        document.getElementById('new-prov-key').value = "";

    } catch(e) {
        Toast.error("Error adding provider: " + e);
    }
}

async function fetchModelsForProvider(providerId) {
    try {
        await fetch(`${API_URL}/ai/config/models/${providerId}`);
    } catch (e) {
        console.error("Model fetch failed", e);
    }
}

function loadProviderModels(providerId, selectedModel = null) {
    const provider = providers.find(p => p.id === providerId);
    const modelSelect = document.getElementById('active-model');
    modelSelect.innerHTML = "";

    if (provider && provider.models) {
        modelSelect.innerHTML = provider.models.map(m => `<option value="${m}">${m}</option>`).join('');
        if (selectedModel) modelSelect.value = selectedModel;
    }
}

async function saveActiveConfig() {
    const pid = document.getElementById('active-provider').value;
    const mid = document.getElementById('active-model').value;

    await fetch(`${API_URL}/ai/config/active`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({provider_id: pid, model_id: mid})
    });
    Toast.success("Active Configuration Updated!");
}

// MCP Service Functions
async function loadMCPStatus() {
    try {
        const res = await fetch(`${API_URL}/mcp/status`);
        const data = await res.json();

        const toggle = document.getElementById('mcp-toggle');
        const statusText = document.getElementById('mcp-status-text');
        const statusDetail = document.getElementById('mcp-status-detail');

        toggle.checked = data.is_active;
        statusText.innerText = data.is_active ? "ON" : "OFF";

        if (data.is_active) {
            statusDetail.innerText = "Service Active & Listening";
            statusDetail.className = "text-xs text-emerald-400";
        } else {
            statusDetail.innerText = "Service Offline";
            statusDetail.className = "text-xs text-slate-400";
        }

        const logContainer = document.getElementById('mcp-logs');
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
                        <span class="uppercase ${color}">${log.status}</span>
                    </div>
                    <div class="text-xs text-indigo-300 mb-0.5">${log.action}</div>
                    <div class="text-[10px] text-slate-400 break-all">${log.details}</div>
                </div>`;
            }).join('');
        }

    } catch(e) {
        console.error("MCP Status Error", e);
    }
}

async function toggleMCPService() {
    const toggle = document.getElementById('mcp-toggle');
    const isActive = toggle.checked;

    try {
        await fetch(`${API_URL}/mcp/toggle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({active: isActive})
        });
        loadMCPStatus();
    } catch(e) {
        Toast.error("Failed to toggle service");
        toggle.checked = !isActive;
    }
}

async function updateDashboardStats() {
    try {
        const dRes = await fetch(`${API_URL}/data/`);
        const datasets = await dRes.json();
        const sRes = await fetch(`${API_URL}/strategies/`);
        const strategies = await sRes.json();

        const cards = document.querySelectorAll('.stat-value');
        if (cards.length >= 2) {
            cards[0].innerText = strategies.length;
            cards[1].innerText = datasets.length;
        }
    } catch (e) { console.error("Stats error", e); }
}

// WebSocket
function initWS() {
    // Prevent multiple connections
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

    socket = new WebSocket(WS_URL);

    socket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'progress') {
                updateProgress(msg);
            } else if (msg.type === 'finished') {
                updateProgress(msg);
                renderResults(msg.results);
            } else if (msg.type === 'error') {
                handleWSError(msg);
            } else if (msg.type === 'ai_status') {
                renderAIStatus(msg);
            }
        } catch(e) {
            console.error("WS Parse Error", e);
        }
    };

    socket.onopen = () => {
        console.log("WS Connected");
        // Optional: Send handshake or ID
    };

    socket.onclose = (e) => {
        console.log("WS Disconnected. Reconnecting...", e.reason);
        setTimeout(initWS, 2000);
    };

    socket.onerror = (err) => {
        console.error("WS Error", err);
        socket.close();
    };
}

function handleWSError(msg) {
    Toast.error(msg.message);
    const badge = document.getElementById('bt-status-badge');
    const status = document.getElementById('bt-status');
    const bar = document.getElementById('bt-progress-bar');

    if (badge) {
        badge.innerText = "FAILED";
        badge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    }
    if (status) status.innerText = msg.details || msg.message;
    if (bar) bar.style.width = '100%';
    if (bar) bar.classList.add('bg-rose-500');
}

// Data Functions
async function loadDatasets() {
    const res = await fetch(`${API_URL}/data/`);
    datasets = await res.json();
    renderDatasets();
}

function renderDatasets() {
    const tbody = document.getElementById('data-table-body');
    if (datasets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-4 text-center text-xs text-slate-500 uppercase tracking-wide">No Datasets Found</td></tr>`;
        return;
    }
    tbody.innerHTML = datasets.map(d => `
        <tr class="hover:bg-slate-800/50 transition-colors group">
            <td class="px-6 py-4 font-mono font-medium text-white">${d.symbol}</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                    ${d.timeframe}
                </span>
            </td>
            <td class="px-6 py-4 text-xs text-slate-500 font-mono">
                ${d.start_date.split('T')[0]} <span class="text-slate-600">to</span> ${d.end_date.split('T')[0]}
            </td>
            <td class="px-6 py-4 text-right text-xs text-slate-400 font-mono">${d.row_count.toLocaleString()}</td>
            <td class="px-6 py-4 text-right">
                <button onclick="deleteDataset('${d.id}')" class="text-slate-500 hover:text-rose-500 transition-colors p-1.5 rounded hover:bg-slate-800 opacity-0 group-hover:opacity-100">
                    <i class="fa-solid fa-trash-can"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function uploadDataset() {
    const fileInput = document.getElementById('upload-file');
    const symbolInput = document.getElementById('upload-symbol');
    const tfInput = document.getElementById('upload-tf');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('symbol', symbolInput.value);
    formData.append('timeframe', tfInput.value);

    try {
        const res = await fetch(`${API_URL}/data/upload`, { method: 'POST', body: formData });
        if (res.ok) {
            Toast.success("Uploaded successfully");
            loadDatasets();
        } else {
            const err = await res.json();
            Toast.error("Error: " + err.detail);
        }
    } catch (e) {
        Toast.error("Upload failed: " + e);
    }
}

async function deleteDataset(id) {
    if (!confirm("Are you sure?")) return;
    await fetch(`${API_URL}/data/${id}`, { method: 'DELETE' });
    loadDatasets();
}

// Data Import Tabs
function switchImportTab(tab) {
    const localForm = document.getElementById('import-local');
    const urlForm = document.getElementById('import-url');
    const tabLocal = document.getElementById('tab-local');
    const tabUrl = document.getElementById('tab-url');

    if (tab === 'local') {
        localForm.classList.remove('hidden');
        urlForm.classList.add('hidden');
        tabLocal.className = "text-sm font-semibold text-indigo-400 border-b-2 border-indigo-400 pb-2 transition-colors focus:outline-none";
        tabUrl.className = "text-sm font-semibold text-slate-500 hover:text-slate-300 border-b-2 border-transparent pb-2 transition-colors focus:outline-none";
    } else {
        localForm.classList.add('hidden');
        urlForm.classList.remove('hidden');
        tabUrl.className = "text-sm font-semibold text-emerald-400 border-b-2 border-emerald-400 pb-2 transition-colors focus:outline-none";
        tabLocal.className = "text-sm font-semibold text-slate-500 hover:text-slate-300 border-b-2 border-transparent pb-2 transition-colors focus:outline-none";
    }
}

async function importFromUrl() {
    const url = document.getElementById('url-input').value;
    const symbol = document.getElementById('url-symbol').value;
    const timeframe = document.getElementById('url-tf').value;
    const btn = document.getElementById('btn-import-url');

    if (!url || !symbol || !timeframe) {
        Toast.error("Please fill all fields.");
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Downloading...`;

    try {
        const res = await fetch(`${API_URL}/data/url`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ url, symbol, timeframe })
        });

        if (res.ok) {
            Toast.success("Dataset imported successfully!");
            document.getElementById('url-input').value = "";
            loadDatasets();
        } else {
            const err = await res.json();
            Toast.error("Error: " + err.detail);
        }
    } catch (e) {
        Toast.error("Import failed: " + e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-cloud-download"></i> Download`;
    }
}

// Strategy Functions
async function loadStrategies() {
    const res = await fetch(`${API_URL}/strategies/`);
    strategies = await res.json();
    const list = document.getElementById('strategy-list');

    if (strategies.length === 0) {
        list.innerHTML = `<div class="p-4 text-center text-xs text-slate-500">No strategies yet</div>`;
        return;
    }

    list.innerHTML = strategies.map(s => `
        <div class="group flex items-center justify-between p-2 rounded-lg cursor-pointer hover:bg-slate-800 transition-colors border border-transparent hover:border-slate-700" onclick="loadStrategyCode('${s.name}', ${s.latest_version})">
            <div class="flex items-center gap-3 overflow-hidden">
                <div class="h-8 w-8 rounded bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-xs font-mono font-bold border border-indigo-500/20">PY</div>
                <div class="overflow-hidden">
                    <h4 class="text-sm font-medium text-slate-200 truncate">${s.name}</h4>
                    <p class="text-[10px] text-slate-500">v${s.latest_version}</p>
                </div>
            </div>
            <button onclick="deleteStrategy('${s.name}'); event.stopPropagation();" class="text-slate-600 hover:text-rose-500 p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100">
                <i class="fa-solid fa-trash-can text-xs"></i>
            </button>
        </div>
    `).join('');
}

function createNewStrategy() {
    currentStrategyCode = "";
    document.getElementById('strategy-name-input').value = "";
    if (editor) editor.setValue("# New Strategy\n\nfrom backend.core.strategy import Strategy\n\nclass NewStrategy(Strategy):\n    pass");
}

async function deleteStrategy(name) {
    if (!confirm(`Are you sure you want to delete strategy '${name}'? This action cannot be undone.`)) return;

    try {
        const res = await fetch(`${API_URL}/strategies/${name}`, { method: 'DELETE' });
        if (res.ok) {
            loadStrategies();
            if (document.getElementById('strategy-name-input').value === name) {
                createNewStrategy();
            }
        } else {
            const err = await res.json();
            Toast.error("Error: " + err.detail);
        }
    } catch (e) {
        Toast.error("Delete failed: " + e);
    }
}

async function loadStrategyCode(name, version) {
    const res = await fetch(`${API_URL}/strategies/${name}/${version}`);
    const data = await res.json();
    currentStrategyCode = data.code;
    document.getElementById('strategy-name-input').value = name;
    if (editor) editor.setValue(data.code);
}

async function saveStrategy() {
    const name = document.getElementById('strategy-name-input').value;
    const code = editor ? editor.getValue() : document.getElementById('strategy-editor-fallback').value;

    const res = await fetch(`${API_URL}/strategies/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, code })
    });

    if (res.ok) {
        Toast.success("Strategy Saved");
        loadStrategies();
    } else {
        Toast.error("Error saving strategy");
    }
}

async function validateStrategy() {
    const code = editor ? editor.getValue() : document.getElementById('strategy-editor-fallback').value;

    try {
        const res = await fetch(`${API_URL}/strategies/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: "temp", code })
        });

        const result = await res.json();

        if (result.valid) {
            Toast.success(`✅ Valid! \n${result.message}`);
        } else {
            Toast.error(`❌ Invalid! \n${result.error}`);
        }
    } catch (e) {
        Toast.error("Validation request failed: " + e);
    }
}

// Backtest Functions
function loadBacktestOptions() {
    const dSelect = document.getElementById('bt-dataset');
    const sSelect = document.getElementById('bt-strategy');

    dSelect.innerHTML = datasets.map(d => `<option value="${d.id}">${d.symbol} (${d.timeframe})</option>`).join('');
    sSelect.innerHTML = strategies.map(s => `<option value="${s.name}">${s.name}</option>`).join('');
}

async function runBacktest() {
    const datasetId = document.getElementById('bt-dataset').value;
    const strategyName = document.getElementById('bt-strategy').value;

    const bar = document.getElementById('bt-progress-bar');
    bar.style.width = '0%';
    bar.classList.remove('bg-rose-500'); // Reset color if failed previously

    document.getElementById('bt-status').innerText = "Starting...";

    const badge = document.getElementById('bt-status-badge');
    badge.classList.remove('hidden');
    badge.innerText = "STARTING";
    badge.className = "bg-amber-500/10 text-amber-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";

    try {
        const res = await fetch(`${API_URL}/backtest/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_id: datasetId, strategy_name: strategyName })
        });

        const data = await res.json();

        if (!res.ok || data.status === "failed") {
            const msg = data.error || data.detail || "Backtest failed to start";
            Toast.error(msg);
            document.getElementById('bt-status').innerText = "Failed";
            badge.innerText = "FAILED";
            badge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
            bar.classList.add('bg-rose-500');
            bar.style.width = '100%';
        }
    } catch(e) {
        Toast.error("Request Error: " + e);
    }
}

function updateProgress(msg) {
    const bar = document.getElementById('bt-progress-bar');
    const status = document.getElementById('bt-status');
    const badge = document.getElementById('bt-status-badge');

    if (msg.type === 'progress') {
        bar.style.width = `${msg.progress}%`;
        status.innerText = `${msg.message} - ${msg.data.current_time}`;

        badge.innerText = "RUNNING";
        badge.className = "bg-indigo-500/10 text-indigo-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";

    } else if (msg.type === 'finished') {
        bar.style.width = '100%';
        status.innerText = "Completed";
        badge.innerText = "COMPLETED";
        badge.className = "bg-emerald-500/10 text-emerald-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
    } else if (msg.type === 'ai_status') {
        renderAIStatus(msg);
    }
}

function renderAIStatus(msg) {
    if (msg.session_id !== currentSessionId) return;

    const container = document.getElementById('chat-container');
    let statusEl = document.getElementById('ai-status-indicator');

    if (!statusEl) {
        const div = document.createElement('div');
        div.id = 'ai-status-indicator';
        div.className = "flex w-full mb-4 justify-start";
        div.innerHTML = `
            <div class="max-w-[85%] p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 text-xs flex items-center gap-3 animate-pulse">
                <i class="fa-solid fa-circle-notch fa-spin text-indigo-500"></i>
                <div class="flex flex-col">
                    <span class="font-bold uppercase tracking-wide text-[10px] text-indigo-400" id="ai-status-step">Thinking</span>
                    <span id="ai-status-detail">Processing...</span>
                </div>
            </div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        statusEl = div;
    }

    document.getElementById('ai-status-step').innerText = msg.step;
    document.getElementById('ai-status-detail').innerText = msg.detail;
}

function renderResults(results) {
    const container = document.getElementById('bt-results');
    const m = results.metrics;

    const pnlColor = m.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400';

    container.innerHTML = `
        <!-- Metrics Grid -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Net Profit</span>
                <div class="text-xl font-bold ${pnlColor} mt-1 font-mono tracking-tight">$${m.net_profit}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Trades</span>
                <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.total_trades}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Win Rate</span>
                <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.win_rate}%</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Profit Factor</span>
                <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.profit_factor}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Max DD</span>
                <div class="text-xl font-bold text-rose-400 mt-1 font-mono tracking-tight">$${m.max_drawdown}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-sm">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Avg Duration</span>
                <div class="text-xl font-bold text-white mt-1 font-mono tracking-tight">${m.avg_duration}m</div>
             </div>
        </div>
        
        <!-- Trade Ledger -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
             <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wide">Trade Ledger</h3>
             </div>
             <div class="overflow-x-auto max-h-[400px]">
                <table class="w-full text-left text-sm text-slate-400">
                    <thead class="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 sticky top-0">
                        <tr>
                            <th class="px-6 py-3 tracking-wider">Entry Time (UTC)</th>
                            <th class="px-6 py-3 tracking-wider">Dir</th>
                            <th class="px-6 py-3 tracking-wider">Size</th>
                            <th class="px-6 py-3 tracking-wider text-right">Entry</th>
                            <th class="px-6 py-3 tracking-wider">Exit Time (UTC)</th>
                            <th class="px-6 py-3 tracking-wider text-right">Exit</th>
                            <th class="px-6 py-3 tracking-wider text-right">PnL</th>
                            <th class="px-6 py-3 tracking-wider text-right">Reason</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 font-mono text-xs">
                        ${results.trades.map(t => {
                            const pnlClass = t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
                            const dirClass = t.direction === 'long' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';

                            return `
                            <tr class="hover:bg-slate-800/50 transition-colors">
                                <td class="px-6 py-3">${t.entry_time}</td>
                                <td class="px-6 py-3">
                                    <span class="px-2 py-0.5 rounded text-[9px] font-bold border uppercase ${dirClass}">${t.direction}</span>
                                </td>
                                <td class="px-6 py-3">${t.size ? t.size.toFixed(2) : '1.00'}</td>
                                <td class="px-6 py-3 text-right text-white">${t.entry_price.toFixed(2)}</td>
                                <td class="px-6 py-3">${t.exit_time}</td>
                                <td class="px-6 py-3 text-right text-white">${t.exit_price.toFixed(2)}</td>
                                <td class="px-6 py-3 text-right font-bold ${pnlClass}">${t.pnl.toFixed(2)}</td>
                                <td class="px-6 py-3 text-right text-slate-500">${t.exit_reason}</td>
                            </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
             </div>
        </div>
    `;
}

// Template Functions
async function loadTemplates() {
    const res = await fetch(`${API_URL}/strategies/templates/list`);
    const templates = await res.json();
    const select = document.getElementById('template-select');
    select.innerHTML = `<option value="">Load Template...</option>` +
        templates.map(t => `<option value="${t}">${t.toUpperCase()}</option>`).join('');
}

async function applyTemplate() {
    const name = document.getElementById('template-select').value;
    if (!name) return;

    if (editor && editor.getValue().length > 50 && !confirm("Replace current code with template?")) return;

    const res = await fetch(`${API_URL}/strategies/templates/${name}`);
    const data = await res.json();

    if (editor) editor.setValue(data.code);
    else document.getElementById('strategy-editor-fallback').value = data.code;

    document.getElementById('strategy-name-input').value = `${name.toUpperCase()}_Strategy`;
}

// AI Assistant Logic (Persistent Sessions)
async function loadSessions() {
    try {
        const res = await fetch(`${API_URL}/ai/sessions`);
        sessions = await res.json();
        renderSessions();

        // Load first session if exists and none selected
        if (!currentSessionId && sessions.length > 0) {
            loadSession(sessions[0].id);
        } else if (currentSessionId) {
             // ensure active class
             renderSessions();
        }
    } catch (e) {
        console.error("Failed to load sessions", e);
    }
}

function renderSessions() {
    const list = document.getElementById('session-list');
    list.innerHTML = sessions.map(s => `
        <li class="flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors text-sm ${s.id === currentSessionId ? 'bg-indigo-600/10 text-indigo-400 font-medium' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'}" onclick="loadSession('${s.id}')">
            <span class="truncate pr-2">${s.title}</span>
            <button onclick="deleteSession('${s.id}'); event.stopPropagation()" class="text-slate-600 hover:text-rose-500 p-1 rounded opacity-60 hover:opacity-100">
                <i class="fa-solid fa-times text-xs"></i>
            </button>
        </li>
    `).join('');
}

async function newSession() {
    const title = prompt("Session Title:", "New Analysis");
    if (!title) return;

    try {
        const res = await fetch(`${API_URL}/ai/sessions`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title})
        });
        const session = await res.json();
        currentSessionId = session.id;
        sessions.unshift(session);
        renderSessions();
        document.getElementById('chat-container').innerHTML = '';
        appendMessage('system', "Started new session. How can I help?");
    } catch (e) {
        Toast.error("Failed to create session");
    }
}

async function loadSession(id) {
    currentSessionId = id;
    renderSessions();
    const container = document.getElementById('chat-container');
    container.innerHTML = '<div class="text-center p-4 text-xs text-slate-500 animate-pulse">Loading History...</div>';

    try {
        const res = await fetch(`${API_URL}/ai/sessions/${id}/history`);
        const history = await res.json();

        container.innerHTML = '';
        if(history.length === 0) {
             appendMessage('system', "Started new session. How can I help?");
        }

        history.forEach(msg => {
            if (msg.role === 'user') appendMessage('user', msg.content);
            if (msg.role === 'assistant') appendMessage('ai', msg.content);
            if (msg.role === 'tool') {
                // Optional: Show tool outputs debug style?
            }
        });
    } catch (e) {
        container.innerHTML = '<div class="text-center p-4 text-xs text-rose-500">Error loading history.</div>';
    }
}

async function deleteSession(id) {
    if (!confirm("Delete this chat?")) return;
    await fetch(`${API_URL}/ai/sessions/${id}`, { method: 'DELETE' });
    if (currentSessionId === id) {
        currentSessionId = null;
        document.getElementById('chat-container').innerHTML = '';
    }
    loadSessions();
}

async function sendChatMessage() {
    const input = document.getElementById('ai-input');
    const message = input.value.trim();
    if (!message) return;

    if (!currentSessionId) await newSession();

    input.value = '';
    appendMessage('user', message);

    const loadingId = appendMessage('ai', '<span class="animate-pulse">Thinking...</span>');

    try {
        const res = await fetch(`${API_URL}/ai/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message, session_id: currentSessionId })
        });
        const data = await res.json();

        // Remove simple loading indicator if present
        const loadingEl = document.getElementById(loadingId);
        if(loadingEl) loadingEl.remove();

        // Remove detailed status indicator if present
        const statusEl = document.getElementById('ai-status-indicator');
        if(statusEl) statusEl.remove();

        appendMessage('ai', data.response);

    } catch (e) {
        const loadingEl = document.getElementById(loadingId);
        if(loadingEl) loadingEl.innerHTML = `<span class="text-rose-400">Error: ${e.message}</span>`;
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;

    // Style based on role
    div.className = "flex w-full mb-4 " + (role === 'user' ? "justify-end" : "justify-start");

    const bubbleClass = role === 'user'
        ? "chat-bubble-user text-white"
        : (role === 'system' ? "bg-slate-800/50 text-slate-400 text-xs italic text-center w-full bg-transparent" : "chat-bubble-ai text-slate-200");

    const innerDiv = document.createElement('div');
    innerDiv.className = `max-w-[85%] p-4 shadow-sm ${bubbleClass}`;

    // Markdown formatting
    let html = text
        .replace(/</g, "&lt;").replace(/>/g, "&gt;") // Escape HTML
        .replace(/```python([\s\S]*?)```/g, (match, code) => {
            return `<div class="mt-2 mb-2 bg-slate-950 rounded-lg border border-slate-900 overflow-hidden group relative">
                <div class="bg-slate-900 px-3 py-1 text-[10px] text-slate-500 font-mono uppercase border-b border-slate-800 flex justify-between items-center">
                    <span>Python</span>
                    <button onclick="applyCodeToEditor(this)" data-code="${encodeURIComponent(code)}" class="text-indigo-400 hover:text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                        <i class="fa-solid fa-arrow-right-to-bracket"></i> Apply
                    </button>
                </div>
                <pre class="p-3 overflow-x-auto text-xs"><code class="language-python">${code}</code></pre>
            </div>`;
        })
        .replace(/```([\s\S]*?)```/g, '<pre class="bg-slate-950 p-3 rounded-lg text-xs border border-slate-900 overflow-x-auto mt-2 mb-2"><code>$1</code></pre>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
        .replace(/\n/g, '<br>');

    innerDiv.innerHTML = html;
    div.appendChild(innerDiv);

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function applyCodeToEditor(btn) {
    const code = decodeURIComponent(btn.getAttribute('data-code'));
    if(editor) {
        editor.setValue(code);
        router.navigate('strategies');
        Toast.success("Code applied to editor!");
    }
}

// Bind Chat Input
document.getElementById('ai-send-btn').addEventListener('click', sendChatMessage);
document.getElementById('ai-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

// Init
window.onload = () => {
    // Init Toast
    if(window.Toast) Toast.init();

    initWS();
    router.init();
    loadTemplates();

    // Load config
    fetch(`${API_URL}/ai/config`)
        .then(res => res.json())
        .then(config => {
            if (config.api_key) document.getElementById('cfg-api-key').value = config.api_key;
            if (config.base_url) document.getElementById('cfg-base-url').value = config.base_url;
            if (config.model) document.getElementById('cfg-model').value = config.model;
        })
        .catch(e => console.error("Failed to load config", e));

    // Init Monaco
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
        const container = document.getElementById('editor-container');
        if (container) {
            editor = monaco.editor.create(container, {
                value: "# Select a strategy or create one",
                language: 'python',
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: false },
                padding: { top: 16, bottom: 16 },
                fontSize: 13,
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace"
            });
            // Initial Layout
            setTimeout(() => editor.layout(), 100);
        }
    });
};
