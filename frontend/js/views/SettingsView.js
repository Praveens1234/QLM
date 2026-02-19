import { aiService } from '../services/AIService.js';
import { toast } from '../notifications.js';

export class SettingsView {
    constructor() {
        this.container = document.getElementById('page-settings');
        this.providers = [];
        this.activeConfig = {};
        this.bindEvents();
    }

    bindEvents() {
        // Apply Config
        const applyBtn = document.getElementById('btn-apply-config');
        if (applyBtn) applyBtn.addEventListener('click', () => this.saveActiveConfig());

        // Add Provider
        const addBtn = document.getElementById('btn-add-provider');
        if (addBtn) addBtn.addEventListener('click', () => this.addProvider());

        // Provider select change -> auto-fetch models
        const providerSelect = document.getElementById('active-provider');
        if (providerSelect) providerSelect.addEventListener('change', (e) => this.onProviderChange(e.target.value));

        // Fetch Models button
        const fetchBtn = document.getElementById('btn-fetch-models');
        if (fetchBtn) fetchBtn.addEventListener('click', () => this.fetchModelsForSelected());

        // Custom model toggle
        const customToggle = document.getElementById('use-custom-model');
        if (customToggle) {
            customToggle.addEventListener('change', (e) => {
                const customInput = document.getElementById('custom-model-id');
                const modelSelect = document.getElementById('active-model');
                if (e.target.checked) {
                    customInput.classList.remove('hidden');
                    modelSelect.classList.add('hidden');
                } else {
                    customInput.classList.add('hidden');
                    modelSelect.classList.remove('hidden');
                }
            });
        }
    }

    async mount() {
        await this.loadProviders();
    }

    async loadProviders() {
        try {
            this.providers = await aiService.getProviders();
            this.renderProviderList(this.providers);
            this.populateSelects(this.providers);

            this.activeConfig = await aiService.getActiveConfig();
            this.setActiveState(this.activeConfig, this.providers);
            this.updateActiveBanner(this.activeConfig);
        } catch (e) {
            console.error("Failed to load providers:", e);
        }
    }

    updateActiveBanner(active) {
        const provName = document.getElementById('active-config-provider-name');
        const modelName = document.getElementById('active-config-model-name');
        const statusBadge = document.getElementById('active-config-status');
        const banner = document.getElementById('active-config-banner');

        if (!provName || !modelName || !statusBadge) return;

        if (active && active.provider_name && active.model) {
            provName.textContent = active.provider_name;
            modelName.textContent = active.model;
            statusBadge.textContent = 'Active';
            statusBadge.className = 'text-[10px] font-bold uppercase px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
            if (banner) {
                const dot = banner.querySelector('.rounded-full');
                if (dot) dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse';
            }
        } else {
            provName.textContent = '—';
            modelName.textContent = '—';
            statusBadge.textContent = 'Not Configured';
            statusBadge.className = 'text-[10px] font-bold uppercase px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30';
            if (banner) {
                const dot = banner.querySelector('.rounded-full');
                if (dot) dot.className = 'w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse';
            }
        }
    }

    renderProviderList(providers) {
        const list = document.getElementById('provider-list');
        if (!list) return;

        if (!providers || providers.length === 0) {
            list.innerHTML = `<li class="px-6 py-8 text-center text-xs text-slate-500 uppercase tracking-wide">No providers registered. Add one above.</li>`;
            return;
        }

        const activeId = this.activeConfig?.provider_id;

        list.innerHTML = providers.map(p => `
            <li class="px-6 py-4 hover:bg-slate-800/30 transition-colors group ${p.id === activeId ? 'border-l-2 border-indigo-500 bg-indigo-500/5' : ''}">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-slate-200">${p.name}</span>
                            ${p.id === activeId ? '<span class="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">Default</span>' : ''}
                        </div>
                        <div class="text-[10px] text-slate-500 font-mono mt-0.5">${p.base_url}</div>
                        <div class="flex items-center gap-3 mt-1.5">
                            <span class="text-[10px] ${p.has_key ? 'text-emerald-500' : 'text-rose-500'} font-bold uppercase">
                                ${p.has_key ? 'KEY SET' : 'NO KEY'}
                            </span>
                            <span class="text-[10px] text-slate-500 font-mono">${p.models.length} model${p.models.length !== 1 ? 's' : ''}</span>
                            ${p.api_key_masked ? `<span class="text-[10px] text-slate-600 font-mono">${p.api_key_masked}</span>` : ''}
                        </div>
                    </div>
                    <div class="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button data-provider-id="${p.id}" class="btn-fetch-prov text-slate-400 hover:text-indigo-400 p-1.5 rounded hover:bg-slate-800 transition-colors" title="Fetch models from API">
                            <i class="fa-solid fa-rotate text-xs"></i>
                        </button>
                        <button data-provider-id="${p.id}" class="btn-delete-prov text-slate-400 hover:text-rose-400 p-1.5 rounded hover:bg-slate-800 transition-colors" title="Delete provider">
                            <i class="fa-solid fa-trash-can text-xs"></i>
                        </button>
                    </div>
                </div>
                ${p.models.length > 0 ? `
                <div class="mt-2 flex flex-wrap gap-1">
                    ${p.models.slice(0, 8).map(m => `<span class="text-[9px] font-mono bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700">${m}</span>`).join('')}
                    ${p.models.length > 8 ? `<span class="text-[9px] font-mono text-slate-500">+${p.models.length - 8} more</span>` : ''}
                </div>` : ''}
            </li>
        `).join('');

        // Bind fetch buttons on list items
        list.querySelectorAll('.btn-fetch-prov').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.providerId;
                this.fetchModelsForProvider(id);
            });
        });

        // Bind delete buttons on list items
        list.querySelectorAll('.btn-delete-prov').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.dataset.providerId;
                this.deleteProvider(id);
            });
        });
    }

    populateSelects(providers) {
        const select = document.getElementById('active-provider');
        if (!select) return;

        select.innerHTML = `<option value="">Select Provider</option>` +
            providers.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }

    setActiveState(active, providers) {
        if (!active || !active.provider_id) return;

        const select = document.getElementById('active-provider');
        const p = providers.find(x => x.id === active.provider_id);
        if (p) {
            select.value = p.id;
            this.populateModelDropdown(p.models, active.model);
        }
    }

    populateModelDropdown(models, selectedModel = null) {
        const modelSelect = document.getElementById('active-model');
        if (!modelSelect) return;

        if (!models || models.length === 0) {
            modelSelect.innerHTML = `<option value="">No models available — click Fetch</option>`;
            return;
        }

        modelSelect.innerHTML = models.map(m =>
            `<option value="${m}" ${m === selectedModel ? 'selected' : ''}>${m}</option>`
        ).join('');
    }

    async onProviderChange(providerId) {
        if (!providerId) {
            const modelSelect = document.getElementById('active-model');
            modelSelect.innerHTML = `<option value="">Select a provider first</option>`;
            return;
        }

        // Try local models first
        const provider = this.providers.find(p => p.id === providerId);
        if (provider && provider.models.length > 0) {
            this.populateModelDropdown(provider.models);
        } else {
            // Auto-fetch models from API
            await this.fetchModelsForProvider(providerId);
        }
    }

    async fetchModelsForSelected() {
        const select = document.getElementById('active-provider');
        const pid = select?.value;
        if (!pid) {
            toast.error("Select a provider first");
            return;
        }
        await this.fetchModelsForProvider(pid);
    }

    async fetchModelsForProvider(providerId) {
        const fetchBtn = document.getElementById('btn-fetch-models');
        const modelSelect = document.getElementById('active-model');

        // Show loading state
        if (fetchBtn) {
            fetchBtn.disabled = true;
            fetchBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Fetching...`;
        }
        if (modelSelect) {
            modelSelect.innerHTML = `<option value="">Fetching models...</option>`;
        }

        try {
            const result = await aiService.fetchModels(providerId);
            const models = result.models || [];

            // Update local cache
            const provider = this.providers.find(p => p.id === providerId);
            if (provider) provider.models = models;

            // Update dropdown if this is the selected provider
            const currentPid = document.getElementById('active-provider')?.value;
            if (currentPid === providerId) {
                this.populateModelDropdown(models);
            }

            // Re-render provider list to show updated model count
            this.renderProviderList(this.providers);

            if (models.length > 0) {
                toast.success(`Found ${models.length} models`);
            } else {
                toast.error("No models found. Check API key and base URL.");
            }
        } catch (e) {
            console.error("Failed to fetch models:", e);
            toast.error("Failed to fetch models. Check provider configuration.");
            if (modelSelect) {
                modelSelect.innerHTML = `<option value="">Fetch failed — try again or use custom</option>`;
            }
        } finally {
            if (fetchBtn) {
                fetchBtn.disabled = false;
                fetchBtn.innerHTML = `<i class="fa-solid fa-rotate"></i> Fetch`;
            }
        }
    }

    async saveActiveConfig() {
        const pid = document.getElementById('active-provider').value;
        const useCustom = document.getElementById('use-custom-model')?.checked;
        const mid = useCustom
            ? document.getElementById('custom-model-id').value
            : document.getElementById('active-model').value;

        if (!pid) {
            toast.error("Please select a provider");
            return;
        }
        if (!mid) {
            toast.error("Please select or enter a model");
            return;
        }

        try {
            await aiService.setActiveConfig(pid, mid);
            toast.success("Configuration applied!");

            // Refresh state
            this.activeConfig = await aiService.getActiveConfig();
            this.updateActiveBanner(this.activeConfig);
            this.renderProviderList(this.providers);
        } catch (e) {
            toast.error("Failed to save configuration");
        }
    }

    async addProvider() {
        const name = document.getElementById('new-prov-name').value;
        const url = document.getElementById('new-prov-url').value;
        const key = document.getElementById('new-prov-key').value;

        if (!name || !url || !key) {
            toast.error("Please fill all fields");
            return;
        }

        try {
            await aiService.addProvider({ name, base_url: url, api_key: key });
            toast.success("Provider added!");
            await this.loadProviders();

            document.getElementById('new-prov-name').value = "";
            document.getElementById('new-prov-url').value = "";
            document.getElementById('new-prov-key').value = "";
        } catch (e) {
            toast.error("Error adding provider");
        }
    }

    async deleteProvider(providerId) {
        const provider = this.providers.find(p => p.id === providerId);
        const name = provider ? provider.name : providerId;

        if (!confirm(`Delete provider "${name}"? This cannot be undone.`)) return;

        try {
            await aiService.deleteProvider(providerId);
            toast.success(`Provider "${name}" deleted`);
            await this.loadProviders();
        } catch (e) {
            toast.error("Failed to delete provider");
        }
    }
}
