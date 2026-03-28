export class Router {
    constructor(routes) {
        this.routes = routes;
        this.currentRoute = null;
        this.beforeHooks = [];
        window.addEventListener('hashchange', this.handleHashChange.bind(this));
    }

    beforeEach(hook) {
        this.beforeHooks.push(hook);
    }

    handleHashChange() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        this.navigate(hash);
    }

    async navigate(routePath) {
        // Run hooks
        for (const hook of this.beforeHooks) {
            const result = await hook(routePath);
            if (result === false) return;
            if (typeof result === 'string') {
                window.location.hash = result;
                return;
            }
        }

        const route = this.routes[routePath] || this.routes['dashboard'];
        this.currentRoute = routePath;

        // Update hash without triggering another hashchange
        if (window.location.hash.slice(1) !== routePath) {
            history.replaceState(null, '', '#' + routePath);
        }

        // Hide all pages
        document.querySelectorAll('.page').forEach(el => {
            el.classList.add('hidden');
            el.classList.remove('animate-fade-in');
        });

        // Show target page
        const target = document.getElementById(`page-${routePath}`);
        if (target) {
            target.classList.remove('hidden');
            // Re-trigger animation
            void target.offsetWidth; // force reflow
            target.classList.add('animate-fade-in');
        }

        // Update Navigation UI (sidebar + bottom tabs)
        this.updateNav(routePath);

        // Execute route callback (controller)
        if (route && typeof route.action === 'function') {
            route.action();
        }
    }

    updateNav(activePath) {
        // --- Sidebar Nav ---
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.remove('active-nav');
        });

        const activeBtn = document.getElementById(`nav-${activePath}`);
        if (activeBtn) {
            activeBtn.classList.add('active-nav');
        }

        // --- Mobile Bottom Tab Bar ---
        document.querySelectorAll('.bottom-tab-item').forEach(tab => {
            const route = tab.dataset.route;
            if (route === activePath) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // For routes that don't have a direct bottom tab (strategies, inspector, mcp, settings),
        // highlight "More"
        const directTabs = ['dashboard', 'data', 'chart', 'backtest'];
        if (!directTabs.includes(activePath)) {
            const moreTab = document.getElementById('btn-mobile-more');
            if (moreTab) moreTab.classList.add('active');
        }
    }
}
