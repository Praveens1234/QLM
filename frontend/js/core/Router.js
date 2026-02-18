export class Router {
    constructor(routes) {
        this.routes = routes;
        this.currentRoute = null;
        this.beforeHooks = [];
        window.addEventListener('hashchange', this.handleHashChange.bind(this));
        window.addEventListener('load', this.handleHashChange.bind(this));
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
            if (result === false) return; // Block navigation
            if (typeof result === 'string') {
                window.location.hash = result;
                return;
            }
        }

        const route = this.routes[routePath] || this.routes['dashboard'];
        this.currentRoute = routePath;

        // Hide all pages
        document.querySelectorAll('.page').forEach(el => el.classList.add('hidden'));

        // Show target page
        const target = document.getElementById(`page-${routePath}`);
        if (target) {
            target.classList.remove('hidden');
            target.classList.add('animate-fade-in');
        }

        // Update Navigation UI
        this.updateNav(routePath);

        // Execute route callback (controller)
        if (route && typeof route.action === 'function') {
            route.action();
        }
    }

    updateNav(activePath) {
        document.querySelectorAll('.nav-item').forEach(btn => {
            // Reset styles
            btn.classList.remove('bg-indigo-600/10', 'text-indigo-400', 'border-l-2', 'border-indigo-500');
            btn.classList.add('text-slate-400', 'hover:bg-slate-800');

            const icon = btn.querySelector('i');
            if(icon) {
                icon.classList.remove('text-indigo-400');
                icon.classList.add('text-slate-500');
            }
        });

        const activeBtn = document.getElementById(`nav-${activePath}`);
        if (activeBtn) {
            activeBtn.classList.remove('text-slate-400', 'hover:bg-slate-800');
            activeBtn.classList.add('bg-indigo-600/10', 'text-indigo-400', 'border-l-2', 'border-indigo-500');
            const icon = activeBtn.querySelector('i');
            if(icon) {
                icon.classList.remove('text-slate-500');
                icon.classList.add('text-indigo-400');
            }
        }
    }
}
