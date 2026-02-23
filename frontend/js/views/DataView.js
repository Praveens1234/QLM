import { dataService } from '../services/DataService.js';

export class DataView {
    constructor() {
        this.container = document.getElementById('page-data');
        this.bindEvents();
    }

    bindEvents() {
        // Tab Switching
        const tabLocal = document.getElementById('tab-local');
        const tabUrl = document.getElementById('tab-url');
        if (tabLocal) tabLocal.addEventListener('click', () => this.switchTab('local'));
        if (tabUrl) tabUrl.addEventListener('click', () => this.switchTab('url'));

        // Upload
        const btnUpload = document.querySelector('#import-local button');
        if (btnUpload) btnUpload.addEventListener('click', () => this.handleUpload());

        // URL Import
        const btnUrl = document.getElementById('btn-import-url');
        if (btnUrl) btnUrl.addEventListener('click', () => this.handleUrlImport());

        // Refresh
        const btnRefresh = document.querySelector('#page-data .fa-refresh')?.parentElement;
        if (btnRefresh) btnRefresh.addEventListener('click', () => this.loadDatasets());

        // Discrepancy Modal Close
        document.getElementById('btn-close-discrepancy').addEventListener('click', () => {
            document.getElementById('modal-discrepancy').classList.add('hidden');
            this.currentDatasetId = null;
        });
    }

    switchTab(tab) {
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

    async mount() {
        await this.loadDatasets();
    }

    async loadDatasets() {
        try {
            const datasets = await dataService.list();
            this.renderTable(datasets);
        } catch (e) {
            console.error("Failed to load datasets", e);
        }
    }

    renderTable(datasets) {
        const tbody = document.getElementById('data-table-body');
        if (!datasets || datasets.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-xs text-slate-500 uppercase tracking-wide">No Datasets Found</td></tr>`;
            return;
        }
        tbody.innerHTML = datasets.map(d => `
            <tr class="hover:bg-white/5 transition-colors group border-b border-slate-800 last:border-0">
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
                    <button aria-label="Discrepancies" data-id="${d.id}" class="btn-discrepancy text-slate-500 hover:text-indigo-400 transition-colors p-1.5 rounded hover:bg-slate-800 opacity-0 group-hover:opacity-100 mr-2" title="Find Discrepancies">
                        <i class="fa-solid fa-magnifying-glass-chart"></i>
                    </button>
                    <button aria-label="Delete Dataset" data-id="${d.id}" class="btn-delete text-slate-500 hover:text-rose-500 transition-colors p-1.5 rounded hover:bg-slate-800 opacity-0 group-hover:opacity-100">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </td>
            </tr>
        `).join('');

        // Bind delete buttons
        tbody.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.id;
                this.handleDelete(id);
            });
        });

        // Bind discrepancy buttons
        tbody.querySelectorAll('.btn-discrepancy').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.id;
                this.openDiscrepancyModal(id);
            });
        });
    }

    async handleUpload() {
        const fileInput = document.getElementById('upload-file');
        const symbolInput = document.getElementById('upload-symbol');
        const tfInput = document.getElementById('upload-tf');

        if (!fileInput.files[0]) {
            if (window.Toast) window.Toast.error("Please select a file");
            return;
        }

        try {
            await dataService.upload(fileInput.files[0], symbolInput.value, tfInput.value);
            if (window.Toast) window.Toast.success("Uploaded successfully");
            this.loadDatasets();
        } catch (e) {
            // Handled by ApiClient or Service
        }
    }

    async handleUrlImport() {
        const url = document.getElementById('url-input').value;
        const symbol = document.getElementById('url-symbol').value;
        const timeframe = document.getElementById('url-tf').value;
        const btn = document.getElementById('btn-import-url');

        if (!url || !symbol || !timeframe) {
            if (window.Toast) window.Toast.error("Please fill all fields");
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Downloading...`;

        try {
            await dataService.importUrl(url, symbol, timeframe);
            if (window.Toast) window.Toast.success("Imported successfully");
            this.loadDatasets();
            document.getElementById('url-input').value = "";
        } catch (e) {
            // Handled
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-cloud-download"></i> Download`;
        }
    }

    async handleDelete(id) {
        if (!confirm("Are you sure you want to delete this dataset?")) return;
        try {
            await dataService.delete(id);
            this.loadDatasets();
        } catch (e) { }
    }

    async openDiscrepancyModal(datasetId) {
        this.currentDatasetId = datasetId;
        const modal = document.getElementById('modal-discrepancy');
        const loading = document.getElementById('discrepancy-loading');
        const listBody = document.getElementById('discrepancy-list-body');
        const detailView = document.getElementById('discrepancy-detail-view');
        const countSpan = document.getElementById('discrepancy-count');

        modal.classList.remove('hidden');
        loading.classList.remove('hidden');
        detailView.classList.add('hidden');
        listBody.innerHTML = '';

        try {
            const res = await dataService.getDiscrepancies(datasetId);
            const discrepancies = res.discrepancies || [];
            this.currentDiscrepancies = discrepancies; // Save for export

            countSpan.textContent = `${discrepancies.length} found`;

            // Bind Exports
            const btnExportTxt = document.getElementById('btn-export-txt');
            const btnExportJson = document.getElementById('btn-export-json');
            if (btnExportTxt) btnExportTxt.onclick = () => this.exportDiscrepancies('txt');
            if (btnExportJson) btnExportJson.onclick = () => this.exportDiscrepancies('json');

            if (discrepancies.length === 0) {
                listBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-xs text-slate-500 uppercase">No discrepancies detected</td></tr>`;
            } else {
                listBody.innerHTML = discrepancies.map(d => `
                    <tr class="hover:bg-slate-800/30 transition-colors">
                        <td class="px-4 py-3 font-mono text-xs text-slate-300 gap-2">${d.timestamp.replace('T', ' ')}</td>
                        <td class="px-4 py-3">
                            <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border ${d.type === 'ZERO_VALUE' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}">
                                ${d.type}
                            </span>
                        </td>
                        <td class="px-4 py-3 text-xs text-slate-400 truncate max-w-xs" title="${d.details}">${d.details}</td>
                        <td class="px-4 py-3 text-right">
                            <button class="btn-view-context px-2 py-1 bg-indigo-500 hover:bg-indigo-400 text-white rounded text-[10px] font-bold uppercase transition-colors" data-index="${d.index}">Inspect</button>
                        </td>
                    </tr>
                `).join('');

                listBody.querySelectorAll('.btn-view-context').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const index = parseInt(e.currentTarget.dataset.index);
                        const type = e.currentTarget.closest('tr').querySelector('span').textContent.trim();
                        this.openContextWindow(datasetId, index, type);
                    });
                });
            }
        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to scan dataset: " + e.message);
            listBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-xs text-rose-500 uppercase">Scan Failed</td></tr>`;
        } finally {
            loading.classList.add('hidden');
        }
    }

    exportDiscrepancies(format) {
        if (!this.currentDiscrepancies || this.currentDiscrepancies.length === 0) {
            if (window.Toast) window.Toast.error("No discrepancies to export.");
            return;
        }

        if (format === 'json') {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(this.currentDiscrepancies, null, 2));
            const dl = document.createElement('a');
            dl.setAttribute("href", dataStr);
            dl.setAttribute("download", `discrepancies_${this.currentDatasetId}.json`);
            document.body.appendChild(dl);
            dl.click();
            dl.remove();
            if (window.Toast) window.Toast.success("Downloaded JSON");
        } else if (format === 'txt') {
            const lines = this.currentDiscrepancies.map(d => `[${d.timestamp}] ${d.type} (Idx: ${d.index}) - ${d.details}`);
            const txt = lines.join('\\n');
            navigator.clipboard.writeText(txt).then(() => {
                if (window.Toast) window.Toast.success("Copied to clipboard as TXT");
            }).catch(err => {
                if (window.Toast) window.Toast.error("Failed to copy");
            });
        }
    }

    async openContextWindow(datasetId, index, discrepancyType = "") {
        const detailView = document.getElementById('discrepancy-detail-view');
        const windowLoading = document.getElementById('window-loading');
        const windowBody = document.getElementById('discrepancy-window-body');

        detailView.classList.remove('hidden');
        windowLoading.classList.remove('hidden');
        detailView.scrollIntoView({ behavior: 'smooth', block: 'end' });

        try {
            const res = await dataService.getWindow(datasetId, index);
            const data = res.data || [];

            windowBody.innerHTML = data.map(row => {
                const isTarget = row.index === index;
                const rowClass = isTarget ? 'bg-amber-500/5' : 'hover:bg-slate-800/30';
                const inputClass = "w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all text-right";

                let extraActions = '';
                if (isTarget) {
                    extraActions += `<button class="btn-delete-row px-2 py-1 bg-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-white rounded text-[10px] font-bold uppercase transition-colors ml-1" title="Delete Row"><i class="fa-solid fa-trash"></i></button>`;

                    if (discrepancyType === 'TIME_GAP') {
                        extraActions += `<button class="btn-interp-row px-2 py-1 bg-blue-500/20 text-blue-400 hover:bg-blue-500 hover:text-white rounded text-[10px] font-bold uppercase transition-colors ml-1" title="Auto-Interpolate Gap"><i class="fa-solid fa-wand-magic-sparkles"></i></button>`;
                    } else if (discrepancyType === 'LOGIC_ERROR') {
                        extraActions += `<button class="btn-autofix-row px-2 py-1 bg-fuchsia-500/20 text-fuchsia-400 hover:bg-fuchsia-500 hover:text-white rounded text-[10px] font-bold uppercase transition-colors ml-1" title="Auto-Fix Logic"><i class="fa-solid fa-wrench"></i></button>`;
                    }
                }

                return `
                    <tr class="${rowClass} transition-colors group" data-row-index="${row.index}">
                        <td class="px-3 py-2 text-left text-slate-400">${row.datetime.replace('T', ' ')}</td>
                        <td class="px-3 py-2"><input type="number" step="any" class="${inputClass}" data-field="open" value="${row.open}"></td>
                        <td class="px-3 py-2"><input type="number" step="any" class="${inputClass}" data-field="high" value="${row.high}"></td>
                        <td class="px-3 py-2"><input type="number" step="any" class="${inputClass}" data-field="low" value="${row.low}"></td>
                        <td class="px-3 py-2"><input type="number" step="any" class="${inputClass}" data-field="close" value="${row.close}"></td>
                        <td class="px-3 py-2 border-r border-slate-800"><input type="number" step="any" class="${inputClass}" data-field="volume" value="${row.volume}"></td>
                        <td class="px-2 py-2 text-center whitespace-nowrap">
                            <button class="btn-save-row px-2 py-1 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-white rounded text-[10px] font-bold uppercase transition-colors opacity-0 group-hover:opacity-100" title="Save Modifications">Save</button>
                            ${extraActions}
                        </td>
                    </tr>
                `;
            }).join('');

            windowBody.querySelectorAll('.btn-save-row').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tr = e.currentTarget.closest('tr');
                    this.saveRowEdit(datasetId, tr);
                });
            });

            windowBody.querySelectorAll('.btn-delete-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm("Delete this row entirely from the Parquet dataset?")) return;
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        await dataService.deleteRow(datasetId, index);
                        if (window.Toast) window.Toast.success("Row deleted permanently.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Delete failed: " + err.message);
                    }
                });
            });

            windowBody.querySelectorAll('.btn-interp-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm("Auto-interpolate missing bars into this gap? This will modify the sequence bounds.")) return;
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        const r = await dataService.interpolateGap(datasetId, index);
                        if (window.Toast) window.Toast.success(r.message || "Gap filled.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Interp failed: " + err.message);
                    }
                });
            });

            windowBody.querySelectorAll('.btn-autofix-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        await dataService.autofixRow(datasetId, index);
                        if (window.Toast) window.Toast.success("Logic inverted automatically.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Autofix failed: " + err.message);
                    }
                });
            });

            if (window.Toast && discrepancyType) {
                window.Toast.info(`Inspecting ${discrepancyType} at row ${index}`);
            }

        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to load context: " + e.message);
            detailView.classList.add('hidden');
        } finally {
            windowLoading.classList.add('hidden');
        }
    }

    async saveRowEdit(datasetId, tr) {
        const index = parseInt(tr.dataset.rowIndex);
        const btn = tr.querySelector('.btn-save-row');

        const updates = {
            open: parseFloat(tr.querySelector('[data-field="open"]').value),
            high: parseFloat(tr.querySelector('[data-field="high"]').value),
            low: parseFloat(tr.querySelector('[data-field="low"]').value),
            close: parseFloat(tr.querySelector('[data-field="close"]').value),
            volume: parseFloat(tr.querySelector('[data-field="volume"]').value)
        };

        const originalText = btn.innerHTML;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
        btn.disabled = true;

        try {
            await dataService.updateRow(datasetId, index, updates);
            if (window.Toast) window.Toast.success(`Row ${index} successfully updated in Parquet file`);
            this.openDiscrepancyModal(datasetId);
        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to update row: " + e.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}
