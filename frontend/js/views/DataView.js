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
    }

    async handleUpload() {
        const fileInput = document.getElementById('upload-file');
        const symbolInput = document.getElementById('upload-symbol');
        const tfInput = document.getElementById('upload-tf');

        if (!fileInput.files[0]) {
            if(window.Toast) window.Toast.error("Please select a file");
            return;
        }

        try {
            await dataService.upload(fileInput.files[0], symbolInput.value, tfInput.value);
            if(window.Toast) window.Toast.success("Uploaded successfully");
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
            if(window.Toast) window.Toast.error("Please fill all fields");
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Downloading...`;

        try {
            await dataService.importUrl(url, symbol, timeframe);
            if(window.Toast) window.Toast.success("Imported successfully");
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
        } catch (e) {}
    }
}
