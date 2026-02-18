import { aiService } from '../services/AIService.js';
import { toast } from '../notifications.js';

export class SettingsView {
    constructor() {
        this.container = document.getElementById('page-settings');
        this.bindEvents();
    }

    bindEvents() {
        const btnApply = document.querySelector('#page-settings button[onclick="saveActiveConfig()"]');
        // Removing onclick from HTML logic later, assuming bind here
        // If I haven't removed onclick in HTML yet, I'll do it in next step.
        // For now I'll select by button text or class
        const applyBtn = this.container.querySelector('button.bg-indigo-600');
        if (applyBtn) applyBtn.addEventListener('click', () => this.saveActiveConfig());

        const addBtn = this.container.querySelector('button.bg-emerald-600');
        if (addBtn) addBtn.addEventListener('click', () => this.addProvider());

        const providerSelect = document.getElementById('active-provider');
        if (providerSelect) providerSelect.addEventListener('change', (e) => this.loadProviderModels(e.target.value));
    }

    async mount() {
        await this.loadProviders();
    }

    async loadProviders() {
        try {
            const providers = await aiService.getProviders();
            this.renderProviderList(providers);
            this.populateSelects(providers);

            const active = await aiService.getActiveConfig();
            this.setActiveState(active, providers);
        } catch (e) {
            console.error(e);
        }
    }

    renderProviderList(providers) {
        const list = document.getElementById('provider-list');
        if (!list) return;

        list.innerHTML = providers.map(p => `
            <li class="px-6 py-3 flex justify-between items-center hover:bg-slate-800/30 transition-colors">
                <div>
                    <div class="font-medium text-slate-300">${p.name}</div>
                    <div class="text-[10px] text-slate-500 font-mono">${p.base_url}</div>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-[10px] ${p.has_key ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10'} px-2 py-0.5 rounded border border-current opacity-80">
                        ${p.has_key ? 'KEY SET' : 'NO KEY'}
                    </span>
                    <div class="text-xs text-slate-500">${p.models.length} Models</div>
                </div>
            </li>
        `).join('');
    }

    populateSelects(providers) {
        const select = document.getElementById('active-provider');
        if (!select) return;

        select.innerHTML = `<option value="">Select Provider</option>` +
            providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }

    setActiveState(active, providers) {
        if (!active.base_url) return;

        const select = document.getElementById('active-provider');
        const p = providers.find(x => x.name === active.provider_name);
        if (p) {
            select.value = p.id;
            this.loadProviderModels(p.id, active.model);
        }
    }

    loadProviderModels(providerId, selectedModel = null) {
        // We assume we have the provider list in memory or fetch models again?
        // Ideally fetch models dynamic if needed, but here we assume static list in provider object.
        // But `loadProviders` fetched list. I should store it or re-fetch.
        // Let's re-fetch config/models/{id} if needed, but existing logic used local list.
        // I'll fetch fresh to be safe.

        // Actually, the `loadProviders` returns providers with models.
        // I'll cache them in `this.providers` if I change `loadProviders` to store them.
        // Let's just fetch from API to be clean.

        // Wait, AI Service has getProviders.
        aiService.getProviders().then(providers => {
            const provider = providers.find(p => p.id === providerId);
            const modelSelect = document.getElementById('active-model');
            modelSelect.innerHTML = "";

            if (provider && provider.models) {
                modelSelect.innerHTML = provider.models.map(m => `<option value="${m}">${m}</option>`).join('');
                if (selectedModel) modelSelect.value = selectedModel;
            }
        });
    }

    async saveActiveConfig() {
        const pid = document.getElementById('active-provider').value;
        const mid = document.getElementById('active-model').value;

        try {
            await aiService.setActiveConfig(pid, mid);
            toast.success("Active Configuration Updated!");
        } catch (e) {}
    }

    async addProvider() {
        const name = document.getElementById('new-prov-name').value;
        const url = document.getElementById('new-prov-url').value;
        const key = document.getElementById('new-prov-key').value;

        if(!name || !url || !key) {
            toast.error("Please fill all fields");
            return;
        }

        try {
            await aiService.addProvider({name, base_url: url, api_key: key});
            toast.success("Provider added.");
            this.loadProviders(); // Refresh

            document.getElementById('new-prov-name').value = "";
            document.getElementById('new-prov-url').value = "";
            document.getElementById('new-prov-key').value = "";
        } catch(e) {
            toast.error("Error adding provider");
        }
    }
}
