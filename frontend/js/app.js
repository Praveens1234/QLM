const API_URL = "/api";
const WS_URL = `ws://${window.location.host}/api/ws`;

// State
let socket;
let datasets = [];
let strategies = [];
let currentStrategyCode = "";
let editor; // Monaco instance

// Router (Simple hash router)
const router = {
    navigate: (page) => {
        document.querySelectorAll('.page').forEach(el => el.style.display = 'none');
        document.getElementById(`page-${page}`).style.display = 'block';
        window.location.hash = page;

        // Update Nav Active State
        document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById(`nav-${page}`);
        if (activeBtn) activeBtn.classList.add('active');

        if (page === 'dashboard') updateDashboardStats();
        if (page === 'data') loadDatasets();
        if (page === 'strategies') {
            loadStrategies();
            setTimeout(() => { if (editor) editor.layout(); }, 100);
        }
        if (page === 'backtest') loadBacktestOptions();
    },
    init: () => {
        window.addEventListener('hashchange', () => router.navigate(window.location.hash.substring(1) || 'dashboard'));
        router.navigate(window.location.hash.substring(1) || 'dashboard');
    }
};

async function updateDashboardStats() {
    // Simple verification stats - in real app would fetch from API
    // We can infer some from loaded data if we have it, or fetch it.
    // Let's just fetch counts to be accurate.
    try {
        const dRes = await fetch(`${API_URL}/data/`);
        const datasets = await dRes.json();
        const sRes = await fetch(`${API_URL}/strategies/`);
        const strategies = await sRes.json();

        // Update DOM if elements exist (they should in new layout)
        const cards = document.querySelectorAll('.stat-card .big-number');
        if (cards.length >= 2) {
            cards[0].innerText = strategies.length; // Active Strategies
            cards[1].innerText = datasets.length;   // Datasets
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
            <td>${d.start_date}</td>
            <td>${d.end_date}</td>
            <td>${d.row_count}</td>
            <td>
                <button onclick="deleteDataset('${d.id}')">Delete</button>
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
        <li class="strategy-item" style="display:flex; justify-content:space-between; align-items:center;">
            <span onclick="loadStrategyCode('${s.name}', ${s.latest_version})" style="flex:1; cursor:pointer;">
                ${s.name} (v${s.latest_version})
            </span>
            <button onclick="deleteStrategy('${s.name}')" class="icon-btn" title="Delete Strategy" style="color:var(--danger-color); padding: 0.2rem 0.5rem;">
                <i class="fa-solid fa-trash"></i>
            </button>
        </li>
    `).join('');
}

async function deleteStrategy(name) {
    if (!confirm(`Are you sure you want to delete strategy '${name}'? This action cannot be undone.`)) return;

    try {
        const res = await fetch(`${API_URL}/strategies/${name}`, { method: 'DELETE' });
        if (res.ok) {
            alert(`Strategy '${name}' deleted successfully.`);
            loadStrategies();
            // Clear editor if deleted strategy was open
            if (document.getElementById('strategy-name-input').value === name) {
                currentStrategyCode = "";
                document.getElementById('strategy-name-input').value = "";
                if (editor) editor.setValue("# Select a strategy or create one");
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
    if (msg.dataset_id !== document.getElementById('bt-dataset').value) return; // simple check

    const bar = document.getElementById('bt-progress-bar');
    const status = document.getElementById('bt-status');

    if (msg.type === 'progress') {
        bar.style.width = `${msg.progress}%`;
        status.innerText = `${msg.message} (${msg.progress}%) - Time: ${msg.data.current_time}`;
    } else if (msg.type === 'finished') {
        bar.style.width = '100%';
        status.innerText = "Completed";
    }
}

function renderResults(results) {
    const container = document.getElementById('bt-results');
    const m = results.metrics;
    container.innerHTML = `
        <div class="card no-padding" style="margin-bottom: 2rem;">
            <div class="card-header">
                <h3>Performance Metrics</h3>
            </div>
            <div class="dashboard-grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); padding: 1.5rem; gap: 1rem; margin: 0;">
                <div class="metric-item">
                    <small>Net Profit</small>
                    <div class="big-number" style="color:${m.net_profit >= 0 ? 'var(--success-color)' : 'var(--danger-color)'}">${m.net_profit}</div>
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
                            <th>Entry</th>
                            <th>SL</th>
                            <th>TP</th>
                            <th>Exit Time (UTC)</th>
                            <th>Exit</th>
                            <th>PnL</th>
                            <th>Duration</th>
                            <th>Status/Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${results.trades.map(t => {
        const pnlClass = t.pnl >= 0 ? 'pnl-green' : 'pnl-red';
        const pnlFormatted = t.pnl.toFixed(2);
        const slDisplay = t.sl ? t.sl.toFixed(2) : '-';
        const tpDisplay = t.tp ? t.tp.toFixed(2) : '-';

        return `
                            <tr>
                                <td>${t.entry_time}</td>
                                <td><span class="badge ${t.direction}">${t.direction.toUpperCase()}</span></td>
                                <td>${t.entry_price.toFixed(2)}</td>
                                <td style="color:var(--danger-color); opacity:0.8;">${slDisplay}</td>
                                <td style="color:var(--success-color); opacity:0.8;">${tpDisplay}</td>
                                <td>${t.exit_time}</td>
                                <td>${t.exit_price.toFixed(2)}</td>
                                <td class="${pnlClass}">
                                    <b>${t.pnl > 0 ? '+' : ''}${pnlFormatted}</b>
                                </td>
                                <td>${t.duration} m</td>
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

    // Rename class to avoid conflict? Or user does it.
    // For now just load it.
    if (editor) editor.setValue(data.code);
    else document.getElementById('strategy-editor-fallback').value = data.code;

    // Auto-fill name
    document.getElementById('strategy-name-input').value = `${name.toUpperCase()}_Strategy`;
}

// Init
window.onload = () => {
    initWS();
    router.init();
    loadTemplates(); // Load templates on startup

    // Init Monaco (Lazy load if possible, or assume loaded script)
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
    require(['vs/editor/editor.main'], function () {
        editor = monaco.editor.create(document.getElementById('editor-container'), {
            value: "# Select a strategy or create one",
            language: 'python',
            theme: 'vs-dark'
        });
    });
};
