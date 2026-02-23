import { dataService } from '../services/DataService.js';

export class InspectorView {
    constructor() {
        this.container = document.getElementById('page-inspector');
        this.datasetSelect = document.getElementById('page-inspector-dataset');
        this.searchTypeRowBtn = document.getElementById('search-type-row');
        this.searchTypeTimeBtn = document.getElementById('search-type-time');
        this.inputLabel = document.getElementById('inspector-input-label');
        this.inputField = document.getElementById('page-inspector-input');
        this.form = document.getElementById('inspector-form');
        this.resultsContainer = document.getElementById('inspector-results-container');
        this.tableWrapper = document.getElementById('inspector-table-wrapper');
        this.btnInspect = document.getElementById('btn-run-page-inspect');
        this.currentSearchType = 'row'; // 'row' or 'time'

        this.bindEvents();
    }

    bindEvents() {
        if (!this.container) return;

        this.searchTypeRowBtn.addEventListener('click', () => {
            this.setSearchType('row');
        });

        this.searchTypeTimeBtn.addEventListener('click', () => {
            this.setSearchType('time');
        });

        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleInspect();
        });
    }

    setSearchType(type) {
        this.currentSearchType = type;
        if (type === 'row') {
            this.searchTypeRowBtn.className = "flex-1 text-sm font-medium px-4 h-full rounded-md bg-indigo-600 text-white transition-all shadow-sm";
            this.searchTypeTimeBtn.className = "flex-1 text-sm font-medium px-4 h-full rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all";
            this.inputLabel.innerHTML = '<i class="fa-solid fa-hashtag mr-1"></i> Row Number';
            this.inputField.placeholder = "e.g. 1500";
            this.inputField.type = "number";
        } else {
            this.searchTypeTimeBtn.className = "flex-1 text-sm font-medium px-4 h-full rounded-md bg-indigo-600 text-white transition-all shadow-sm";
            this.searchTypeRowBtn.className = "flex-1 text-sm font-medium px-4 h-full rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all";
            this.inputLabel.innerHTML = '<i class="fa-regular fa-clock mr-1"></i> Datetime';
            this.inputField.placeholder = "e.g. 2025-01-01 15:30:00";
            this.inputField.type = "text";
        }
    }

    async mount() {
        if (!this.container) return;
        try {
            const datasets = await dataService.list();
            this.populateDatasets(datasets);
        } catch (e) {
            console.error("Failed to load datasets for inspector", e);
        }
    }

    populateDatasets(datasets) {
        const currentVal = this.datasetSelect.value;
        this.datasetSelect.innerHTML = `<option value="" disabled ${!currentVal ? 'selected' : ''}>Select Dataset...</option>` +
            datasets.map(d => `<option value="${d.id}">${d.symbol} (${d.timeframe})</option>`).join('');

        if (currentVal && datasets.some(d => d.id === currentVal)) {
            this.datasetSelect.value = currentVal;
        }
    }

    async handleInspect() {
        const datasetId = this.datasetSelect.value;
        const query = this.inputField.value.trim();

        if (!datasetId) {
            if (window.Toast) window.Toast.warning("Please select a dataset.");
            return;
        }
        if (!query) {
            if (window.Toast) window.Toast.warning(`Please enter a valid ${this.currentSearchType === 'row' ? 'row number' : 'datetime'}.`);
            return;
        }

        this.btnInspect.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
        this.btnInspect.disabled = true;

        try {
            // First look up the row index if necessary, or just rely on backend parsing
            const res = await dataService.inspectRow(datasetId, query);

            if (res.target_index !== undefined) {
                if (window.Toast) window.Toast.success(`Found target at Row index ${res.target_index}`);

                // Now fetch the surrounding window
                const windowRes = await dataService.getWindow(datasetId, res.target_index);
                this.renderResults(datasetId, res.target_index, windowRes.data || []);
            }
        } catch (e) {
            if (window.Toast) window.Toast.error("Inspect Failed: " + (e.response?.data?.detail || e.message));
        } finally {
            this.btnInspect.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> Inspect`;
            this.btnInspect.disabled = false;
        }
    }

    renderResults(datasetId, targetIndex, dataRows) {
        this.resultsContainer.classList.remove('hidden');

        if (!dataRows || dataRows.length === 0) {
            this.tableWrapper.innerHTML = `<div class="p-8 text-center text-slate-400">No data window could be loaded.</div>`;
            return;
        }

        const tableHTML = `
            <table class="w-full text-left border-collapse">
                <thead class="bg-slate-800/50 text-[10px] uppercase tracking-wider text-slate-400 sticky top-0">
                    <tr>
                        <th class="px-3 py-2 font-medium">Time (UTC)</th>
                        <th class="px-3 py-2 font-medium">Open</th>
                        <th class="px-3 py-2 font-medium">High</th>
                        <th class="px-3 py-2 font-medium">Low</th>
                        <th class="px-3 py-2 font-medium">Close</th>
                        <th class="px-3 py-2 font-medium">Volume</th>
                        <th class="px-3 py-2 font-medium text-center w-24">Actions</th>
                    </tr>
                </thead>
                <tbody class="text-xs font-mono divide-y divide-slate-800/50">
                    ${dataRows.map(row => {
            const isTarget = row.index === targetIndex;
            const rowClass = isTarget ? 'bg-indigo-500/10' : 'hover:bg-slate-800/30';
            const inputClass = "w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all text-right";

            let extraActions = isTarget ?
                `<button class="btn-delete-row px-2 py-1 bg-rose-500/20 text-rose-400 hover:bg-rose-500 hover:text-white rounded text-[10px] font-bold uppercase transition-colors ml-1" title="Delete Row"><i class="fa-solid fa-trash"></i></button>` : '';

            return `
                        <tr class="${rowClass} transition-colors group" data-row-index="${row.index}">
                            <td class="px-3 py-2 text-left text-slate-400">
                                ${isTarget ? '<i class="fa-solid fa-arrow-right text-indigo-400 mr-2"></i>' : ''}
                                ${row.datetime.replace('T', ' ')}
                            </td>
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
        }).join('')}
                </tbody>
            </table>
        `;

        this.tableWrapper.innerHTML = tableHTML;

        // Bind saves
        this.tableWrapper.querySelectorAll('.btn-save-row').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tr = e.currentTarget.closest('tr');
                this.saveRowEdit(datasetId, tr);
            });
        });

        // Bind deletes
        this.tableWrapper.querySelectorAll('.btn-delete-row').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                if (!confirm("Delete this row entirely from the dataset?")) return;
                const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                try {
                    await dataService.deleteRow(datasetId, index);
                    if (window.Toast) window.Toast.success("Row deleted permanently.");
                    // Re-run inspection to refresh the view
                    this.handleInspect();
                } catch (err) {
                    if (window.Toast) window.Toast.error("Delete failed: " + err.message);
                }
            });
        });
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
            if (window.Toast) window.Toast.success("Row updated");
        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to update row: " + e.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
}
