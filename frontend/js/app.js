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
            el.classList.remove('active');
            el.style.display = 'none'; // Ensure hidden
        });

        const target = document.getElementById(`page-${page}`);
        if(target) {
            target.style.display = 'block';
            setTimeout(() => target.classList.add('active'), 10); // Trigger animation
        }

        window.location.hash = page;

        // Update Nav Active State
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById(`nav-${page}`);
        if (activeBtn) activeBtn.classList.add('active');

        // Close mobile sidebar if open
        const sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('open')) sidebar.classList.remove('open');

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
    sidebar.classList.toggle('open');
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

        const cards = document.querySelectorAll('.stat-card .big-number');
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
    tbody.innerHTML = datasets.map(d => `
        <tr>
            <td>${d.symbol}</td>
            <td>${d.timeframe}</td>
            <td>${d.start_date.split('T')[0]}</td>
            <td>${d.end_date.split('T')[0]}</td>
            <td>${d.row_count}</td>
            <td>
                <button onclick="deleteDataset('${d.id}')" class="icon-btn" style="color:var(--danger-color)"><i class="fa-solid fa-trash"></i></button>
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
    list.innerHTML = strategies.map(s => `
        <li class="session-item" onclick="loadStrategyCode('${s.name}', ${s.latest_version})">
            <span>${s.name} <small>(v${s.latest_version})</small></span>
            <button onclick="deleteStrategy('${s.name}'); event.stopPropagation();" class="icon-btn" style="color:var(--danger-color)">
                <i class="fa-solid fa-trash"></i>
            </button>
        </li>
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

    const res = await fetch(`${API_URL}/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: datasetId, strategy_name: strategyName })
    });

    if (!res.ok) {
        alert("Backtest failed to start");
        document.getElementById('bt-status').innerText = "Failed";
    }
}

function updateProgress(msg) {
    const bar = document.getElementById('bt-progress-bar');
    const status = document.getElementById('bt-status');
    // Check if relevant

    if (msg.type === 'progress') {
        bar.style.width = `${msg.progress}%`;
        status.innerText = `${msg.message} (${msg.progress}%) - ${msg.data.current_time}`;
    } else if (msg.type === 'finished') {
        bar.style.width = '100%';
        status.innerText = "Completed";
    }
}

function renderResults(results) {
    const container = document.getElementById('bt-results');
    const m = results.metrics;

    // Helper for coloring
    const pnlColor = m.net_profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)';

    container.innerHTML = `
        <div class="card no-padding" style="margin-bottom: 2rem;">
            <div class="card-header">
                <h3>Performance Metrics</h3>
            </div>
            <div class="dashboard-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); padding: 1.5rem; gap: 1rem; margin: 0;">
                <div class="metric-item">
                    <small>Net Profit</small>
                    <div class="big-number" style="color:${pnlColor}">${m.net_profit}</div>
                </div>
                <div class="metric-item">
                    <small>Total Trades</small>
                    <div class="big-number">${m.total_trades}</div>
                </div>
                <div class="metric-item">
                    <small>Win Rate</small>
                    <div class="big-number">${m.win_rate}%</div>
                </div>
                <div class="metric-item">
                    <small>Profit Factor</small>
                    <div class="big-number">${m.profit_factor}</div>
                </div>
                <div class="metric-item">
                    <small>Max Drawdown</small>
                    <div class="big-number" style="color:var(--danger-color)">${m.max_drawdown} (${m.max_drawdown_pct}%)</div>
                </div>
                <div class="metric-item">
                    <small>Avg Duration</small>
                    <div class="big-number">${m.avg_duration} m</div>
                </div>
            </div>
        </div>
        
        <div class="card no-padding">
            <div class="card-header">
                <h3>Trade Ledger</h3>
            </div>
            <div style="max-height: 500px; overflow-y: auto;">
                <table class="data-table">
                    <thead style="position: sticky; top: 0; background: var(--card-bg); z-index: 1;">
                        <tr>
                            <th>Entry Time (UTC)</th>
                            <th>Dir</th>
                            <th>Size</th>
                            <th>Entry</th>
                            <th>Exit Time (UTC)</th>
                            <th>Exit</th>
                            <th>PnL</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${results.trades.map(t => {
                            const pnlClass = t.pnl >= 0 ? 'color:var(--success-color)' : 'color:var(--danger-color)';
                            const size = t.size ? t.size.toFixed(2) : '1.00';
                            return `
                            <tr>
                                <td>${t.entry_time}</td>
                                <td><span style="padding:2px 6px; border-radius:4px; font-size:0.8em; background:${t.direction==='long'?'rgba(16, 185, 129, 0.2)':'rgba(239, 68, 68, 0.2)'}; color:${t.direction==='long'?'var(--success-color)':'var(--danger-color)'}">${t.direction.toUpperCase()}</span></td>
                                <td>${size}</td>
                                <td>${t.entry_price.toFixed(2)}</td>
                                <td>${t.exit_time}</td>
                                <td>${t.exit_price.toFixed(2)}</td>
                                <td style="${pnlClass}; font-weight:bold;">${t.pnl.toFixed(2)}</td>
                                <td>${t.exit_reason}</td>
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
    select.innerHTML = `<option value="">-- Load Template --</option>` +
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
        <li class="session-item ${s.id === currentSessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
            <span>${s.title}</span>
            <button onclick="deleteSession('${s.id}'); event.stopPropagation()" class="icon-btn" style="padding:2px"><i class="fa-solid fa-times"></i></button>
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
    container.innerHTML = '<div style="text-align:center; padding:1rem; color:var(--text-secondary)">Loading...</div>';

    try {
        const res = await fetch(`${API_URL}/ai/sessions/${id}/history`);
        const history = await res.json();

        container.innerHTML = '';
        history.forEach(msg => {
            if (msg.role === 'user') appendMessage('user', msg.content);
            if (msg.role === 'assistant') appendMessage('ai', msg.content);
            if (msg.role === 'tool') {
                // Optional: Show tool outputs debug style?
                // For now skip or show as subtle system msg
                // appendMessage('system', `Tool Output: ${msg.name}`);
            }
        });
    } catch (e) {
        container.innerHTML = 'Error loading history.';
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

    if (!currentSessionId) await newSession(); // Auto create if null

    input.value = '';
    appendMessage('user', message);

    const loadingId = appendMessage('ai', '...');

    try {
        const res = await fetch(`${API_URL}/ai/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message, session_id: currentSessionId })
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();
        appendMessage('ai', data.response);

        // Refresh session list (title might update or re-order?)
        // Ideally we update title based on content if needed, but for now just keep simple.
    } catch (e) {
        document.getElementById(loadingId).innerText = "Error: " + e.message;
    }
}

function appendMessage(role, text) {
    const container = document.getElementById('chat-container');
    const div = document.createElement('div');
    const id = 'msg-' + Date.now();
    div.id = id;
    div.className = `chat-message ${role}`;

    // Markdown formatting
    let html = text
        .replace(/</g, "&lt;").replace(/>/g, "&gt;") // Escape HTML
        .replace(/```python([\s\S]*?)```/g, '<pre><code class="language-python">$1</code></pre>')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    div.innerHTML = html;
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
                minimap: { enabled: false }
            });
            // Initial Layout
            setTimeout(() => editor.layout(), 100);
        }
    });
};
