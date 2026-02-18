import { strategyService } from '../services/StrategyService.js';
import { CodeEditor } from '../components/CodeEditor.js';

export class StrategyView {
    constructor() {
        this.container = document.getElementById('page-strategies');
        this.editor = new CodeEditor('editor-container');
        this.currentStrategyName = "";
        this.bindEvents();
    }

    bindEvents() {
        // Toolbar
        document.querySelector('button[title="New Strategy"]')?.addEventListener('click', () => this.createNew());

        const saveBtn = document.querySelector('button i.fa-save')?.parentElement;
        if(saveBtn) saveBtn.addEventListener('click', () => this.save());

        const validateBtn = document.querySelector('button i.fa-check-double')?.parentElement;
        if(validateBtn) validateBtn.addEventListener('click', () => this.validate());

        const templateSelect = document.getElementById('template-select');
        if(templateSelect) templateSelect.addEventListener('change', () => this.applyTemplate());
    }

    async mount() {
        await this.loadList();
        await this.loadTemplates();
        // Resize editor after view is visible
        setTimeout(() => this.editor.layout(), 100);
    }

    async loadList() {
        try {
            const strategies = await strategyService.list();
            this.renderList(strategies);
        } catch (e) {
            console.error(e);
        }
    }

    renderList(strategies) {
        const list = document.getElementById('strategy-list');
        if (!list) return;

        if (strategies.length === 0) {
            list.innerHTML = `<div class="p-4 text-center text-xs text-slate-500">No strategies yet</div>`;
            return;
        }

        list.innerHTML = strategies.map(s => `
            <div class="group flex items-center justify-between p-2 rounded-lg cursor-pointer hover:bg-white/5 transition-colors border border-transparent hover:border-slate-700 strategy-item" data-name="${s.name}" data-version="${s.latest_version}">
                <div class="flex items-center gap-3 overflow-hidden">
                    <div class="h-8 w-8 rounded bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-xs font-mono font-bold border border-indigo-500/20">PY</div>
                    <div class="overflow-hidden">
                        <h4 class="text-sm font-medium text-slate-200 truncate">${s.name}</h4>
                        <p class="text-[10px] text-slate-500">v${s.latest_version}</p>
                    </div>
                </div>
                <button aria-label="Delete Strategy" class="btn-delete text-slate-600 hover:text-rose-500 p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100" data-name="${s.name}">
                    <i class="fa-solid fa-trash-can text-xs"></i>
                </button>
            </div>
        `).join('');

        // Bind clicks
        list.querySelectorAll('.strategy-item').forEach(el => {
            el.addEventListener('click', () => this.loadCode(el.dataset.name, el.dataset.version));
        });

        list.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteStrategy(btn.dataset.name);
            });
        });
    }

    async loadCode(name, version) {
        try {
            const data = await strategyService.get(name, version);
            this.currentStrategyName = name;
            document.getElementById('strategy-name-input').value = name;
            this.editor.setValue(data.code);
        } catch (e) {}
    }

    createNew() {
        this.currentStrategyName = "";
        document.getElementById('strategy-name-input').value = "";
        this.editor.setValue("# New Strategy\n\nfrom backend.core.strategy import Strategy\n\nclass NewStrategy(Strategy):\n    def define_variables(self, df): return {}\n    def entry_long(self, df, vars): return pd.Series([False]*len(df))\n    def entry_short(self, df, vars): return pd.Series([False]*len(df))\n    def exit_long_signal(self, df, vars): return pd.Series([False]*len(df))\n    def exit_short_signal(self, df, vars): return pd.Series([False]*len(df))\n    def risk_model(self, df, vars): return {}");
    }

    async save() {
        const name = document.getElementById('strategy-name-input').value;
        const code = this.editor.getValue();
        if(!name) {
            if(window.Toast) window.Toast.error("Please enter a strategy name");
            return;
        }

        try {
            await strategyService.save(name, code);
            if(window.Toast) window.Toast.success("Strategy Saved");
            this.loadList();
        } catch (e) {}
    }

    async deleteStrategy(name) {
        if (!confirm(`Delete ${name}?`)) return;
        try {
            await strategyService.delete(name);
            this.loadList();
            if (this.currentStrategyName === name) this.createNew();
        } catch (e) {}
    }

    async validate() {
        const code = this.editor.getValue();
        try {
            const result = await strategyService.validate(code);
            if (result.valid) {
                if(window.Toast) window.Toast.success(`✅ Valid! \n${result.message}`);
            } else {
                if(window.Toast) window.Toast.error(`❌ Invalid! \n${result.error}`);
            }
        } catch (e) {}
    }

    async loadTemplates() {
        try {
            const templates = await strategyService.listTemplates();
            const select = document.getElementById('template-select');
            if (select) {
                select.innerHTML = `<option value="">Load Template...</option>` +
                    templates.map(t => `<option value="${t}">${t.toUpperCase()}</option>`).join('');
            }
        } catch (e) {}
    }

    async applyTemplate() {
        const select = document.getElementById('template-select');
        const name = select.value;
        if (!name) return;

        if (this.editor.getValue().length > 50 && !confirm("Replace current code?")) {
            select.value = "";
            return;
        }

        try {
            const data = await strategyService.getTemplate(name);
            this.editor.setValue(data.code);
            document.getElementById('strategy-name-input').value = `${name.toUpperCase()}_Strategy`;
        } catch (e) {}
    }
}
