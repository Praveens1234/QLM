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
            btn.classList.remove('bg-indigo-600', 'text-white', 'shadow-lg', 'shadow-indigo-500/20');
            btn.classList.add('text-slate-400', 'hover:bg-slate-800', 'hover:text-white');
        });

        const activeBtn = document.getElementById(`nav-${page}`);
        if (activeBtn) {
            activeBtn.classList.remove('text-slate-400', 'hover:bg-slate-800');
            activeBtn.classList.add('bg-indigo-600', 'text-white', 'shadow-lg', 'shadow-indigo-500/20');
        }

        // Close mobile sidebar if open
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        if (!sidebar.classList.contains('-translate-x-full')) {
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

    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
}

// Config
async function saveConfig() {
    const apiKey = document.getElementById('cfg-api-key').value.trim();
    const model = document.getElementById('cfg-model').value.trim();
    const baseUrl = document.getElementById('cfg-base-url').value.trim();

    if (!apiKey) {
        alert("Please enter an API Key.");
        return;
    }

    try {
        const payload = {
            api_key: apiKey,
            model: model,
            base_url: baseUrl
        };

        const res = await fetch(`${API_URL}/ai/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();

        if (res.ok) {
            alert(`Configuration Saved Successfully!`);
        } else {
            console.error("Config Error:", data);
            alert(`Error saving config: ${data.detail}`);
        }
    } catch (e) {
        console.error("Config Network Error:", e);
        alert("Config save failed: " + e.message);
    }
}

async function fetchModels() {
    const apiKey = document.getElementById('cfg-api-key').value.trim();
    const baseUrl = document.getElementById('cfg-base-url').value.trim();

    if (!apiKey) {
        alert("Please enter API Key first.");
        return;
    }

    try {
        await fetch(`${API_URL}/ai/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, base_url: baseUrl, model: "" })
        });

        const res = await fetch(`${API_URL}/ai/models`);
        const data = await res.json();

        if (data.models && data.models.length > 0) {
            const dataList = document.getElementById('model-list');
            dataList.innerHTML = '';
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m;
                dataList.appendChild(opt);
            });
            alert(`Loaded ${data.models.length} models into suggestions.`);
        } else {
            alert("No models found via API. Please enter Model ID manually.");
        }
    } catch (e) {
        alert("Error fetching models: " + e + "\n\nPlease enter Model ID manually.");
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
    socket = new WebSocket(WS_URL);
    socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'progress') {
            updateProgress(msg);
        } else if (msg.type === 'finished') {
            updateProgress(msg);
            renderResults(msg.results);
        }
    };
    socket.onopen = () => console.log("WS Connected");
    socket.onclose = () => setTimeout(initWS, 1000);
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
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                    ${d.timeframe}
                </span>
            </td>
            <td class="px-6 py-4 text-xs text-slate-500 font-mono">
                ${d.start_date.split('T')[0]} <span class="text-slate-600">to</span> ${d.end_date.split('T')[0]}
            </td>
            <td class="px-6 py-4 text-right text-xs text-slate-400 font-mono">${d.row_count.toLocaleString()}</td>
            <td class="px-6 py-4 text-right">
                <button onclick="deleteDataset('${d.id}')" class="text-slate-500 hover:text-rose-500 transition-colors p-1 opacity-0 group-hover:opacity-100">
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
            alert("Uploaded successfully");
            loadDatasets();
        } else {
            const err = await res.json();
            alert("Error: " + err.detail);
        }
    } catch (e) {
        alert("Upload failed: " + e);
    }
}

async function deleteDataset(id) {
    if (!confirm("Are you sure?")) return;
    await fetch(`${API_URL}/data/${id}`, { method: 'DELETE' });
    loadDatasets();
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
            alert("Error: " + err.detail);
        }
    } catch (e) {
        alert("Delete failed: " + e);
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
        alert("Strategy Saved");
        loadStrategies();
    } else {
        alert("Error saving strategy");
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
            alert(`✅ Valid! \n${result.message}`);
        } else {
            alert(`❌ Invalid! \n${result.error}`);
        }
    } catch (e) {
        alert("Validation request failed: " + e);
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

    document.getElementById('bt-progress-bar').style.width = '0%';
    document.getElementById('bt-status').innerText = "Starting...";

    // Show badge
    const badge = document.getElementById('bt-status-badge');
    badge.classList.remove('hidden');
    badge.innerText = "STARTING";
    badge.className = "bg-amber-500/10 text-amber-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";

    const res = await fetch(`${API_URL}/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, strategy_name: strategyName })
    });

    if (!res.ok) {
        alert("Backtest failed to start");
        document.getElementById('bt-status').innerText = "Failed";
        badge.innerText = "FAILED";
        badge.className = "bg-rose-500/10 text-rose-400 text-[10px] px-2 py-0.5 rounded font-bold uppercase";
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
    }
}

function renderResults(results) {
    const container = document.getElementById('bt-results');
    const m = results.metrics;

    const pnlColor = m.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400';

    container.innerHTML = `
        <!-- Metrics Grid -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Net Profit</span>
                <div class="text-xl font-bold ${pnlColor} mt-1">$${m.net_profit}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Trades</span>
                <div class="text-xl font-bold text-white mt-1">${m.total_trades}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Win Rate</span>
                <div class="text-xl font-bold text-white mt-1">${m.win_rate}%</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Profit Factor</span>
                <div class="text-xl font-bold text-white mt-1">${m.profit_factor}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Max DD</span>
                <div class="text-xl font-bold text-rose-400 mt-1">$${m.max_drawdown}</div>
             </div>
             <div class="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                <span class="text-[10px] text-slate-500 uppercase tracking-wide font-bold">Avg Duration</span>
                <div class="text-xl font-bold text-white mt-1">${m.avg_duration}m</div>
             </div>
        </div>
        
        <!-- Trade Ledger -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
             <div class="px-6 py-4 border-b border-slate-800 bg-slate-900/50">
                <h3 class="text-sm font-semibold text-white">Trade Ledger</h3>
             </div>
             <div class="overflow-x-auto max-h-[400px]">
                <table class="w-full text-left text-sm text-slate-400">
                    <thead class="bg-slate-950 text-xs uppercase font-medium text-slate-500 sticky top-0">
                        <tr>
                            <th class="px-6 py-3">Entry Time (UTC)</th>
                            <th class="px-6 py-3">Dir</th>
                            <th class="px-6 py-3">Size</th>
                            <th class="px-6 py-3 text-right">Entry</th>
                            <th class="px-6 py-3">Exit Time (UTC)</th>
                            <th class="px-6 py-3 text-right">Exit</th>
                            <th class="px-6 py-3 text-right">PnL</th>
                            <th class="px-6 py-3 text-right">Reason</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 font-mono">
                        ${results.trades.map(t => {
                            const pnlClass = t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400';
                            const dirClass = t.direction === 'long' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20';

                            return `
                            <tr class="hover:bg-slate-800/50 transition-colors">
                                <td class="px-6 py-3 text-xs">${t.entry_time}</td>
                                <td class="px-6 py-3">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${dirClass}">${t.direction}</span>
                                </td>
                                <td class="px-6 py-3 text-xs">${t.size ? t.size.toFixed(2) : '1.00'}</td>
                                <td class="px-6 py-3 text-right text-xs text-white">${t.entry_price.toFixed(2)}</td>
                                <td class="px-6 py-3 text-xs">${t.exit_time}</td>
                                <td class="px-6 py-3 text-right text-xs text-white">${t.exit_price.toFixed(2)}</td>
                                <td class="px-6 py-3 text-right font-bold ${pnlClass}">${t.pnl.toFixed(2)}</td>
                                <td class="px-6 py-3 text-right text-xs">${t.exit_reason}</td>
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
        alert("Failed to create session");
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

        const loadingEl = document.getElementById(loadingId);
        if(loadingEl) loadingEl.remove();

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
        ? "bg-indigo-600 text-white chat-bubble-user"
        : (role === 'system' ? "bg-slate-800/50 text-slate-400 text-xs italic text-center w-full bg-transparent" : "bg-slate-800 border border-slate-700 text-slate-200 chat-bubble-ai");

    const innerDiv = document.createElement('div');
    innerDiv.className = `max-w-[85%] p-4 shadow-sm ${bubbleClass}`;

    // Markdown formatting
    let html = text
        .replace(/</g, "&lt;").replace(/>/g, "&gt;") // Escape HTML
        .replace(/```python([\s\S]*?)```/g, '<div class="mt-2 mb-2 bg-slate-950 rounded-lg border border-slate-900 overflow-hidden"><div class="bg-slate-900 px-3 py-1 text-[10px] text-slate-500 font-mono uppercase border-b border-slate-800">Python</div><pre class="p-3 overflow-x-auto text-xs"><code class="language-python">$1</code></pre></div>')
        .replace(/```([\s\S]*?)```/g, '<pre class="bg-slate-950 p-3 rounded-lg text-xs border border-slate-900 overflow-x-auto mt-2 mb-2"><code>$1</code></pre>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
        .replace(/\n/g, '<br>');

    innerDiv.innerHTML = html;
    div.appendChild(innerDiv);

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

// Bind Chat Input
document.getElementById('ai-send-btn').addEventListener('click', sendChatMessage);
document.getElementById('ai-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

// Init
window.onload = () => {
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
