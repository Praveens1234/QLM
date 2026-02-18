export class Layout {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.overlay = document.getElementById('sidebar-overlay');
        this.bindEvents();
    }

    bindEvents() {
        // Expose toggle globally for onclick attributes (legacy support)
        window.toggleSidebar = this.toggleSidebar.bind(this);

        // Listen for route changes to close mobile menu
        window.addEventListener('hashchange', () => {
            if (window.innerWidth < 768) {
                this.closeSidebar();
            }
        });
    }

    toggleSidebar() {
        if (this.sidebar.classList.contains('-translate-x-full')) {
            this.openSidebar();
        } else {
            this.closeSidebar();
        }
    }

    openSidebar() {
        this.sidebar.classList.remove('-translate-x-full');
        this.overlay.classList.remove('hidden', 'opacity-0', 'pointer-events-none');
    }

    closeSidebar() {
        this.sidebar.classList.add('-translate-x-full');
        this.overlay.classList.add('opacity-0', 'pointer-events-none');
        setTimeout(() => this.overlay.classList.add('hidden'), 300);
    }
}
