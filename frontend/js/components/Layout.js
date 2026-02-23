export class Layout {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.overlay = document.getElementById('sidebar-overlay');
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.bindEvents();
    }

    bindEvents() {
        // Expose toggle globally for onclick attributes (legacy support)
        window.toggleSidebar = this.toggleSidebar.bind(this);

        // Listen for route changes to close mobile menu + update bottom tab
        window.addEventListener('hashchange', () => {
            if (window.innerWidth < 768) {
                this.closeSidebar();
            }
            this.updateBottomTab();
        });

        // Swipe-to-close sidebar on mobile
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!e.changedTouches || !e.changedTouches.length) return;
            const deltaX = e.changedTouches[0].clientX - this.touchStartX;
            const deltaY = Math.abs(e.changedTouches[0].clientY - this.touchStartY);

            // Only trigger if horizontal swipe is dominant (not scrolling)
            if (deltaY > Math.abs(deltaX)) return;

            // Swipe LEFT to close sidebar (if open)
            if (deltaX < -80 && !this.sidebar.classList.contains('-translate-x-full')) {
                if (window.innerWidth < 768) {
                    this.closeSidebar();
                }
            }
            // Swipe RIGHT to open sidebar (from left edge)
            if (deltaX > 80 && this.touchStartX < 30 && this.sidebar.classList.contains('-translate-x-full')) {
                if (window.innerWidth < 768) {
                    this.openSidebar();
                }
            }
        }, { passive: true });

        // Initialize bottom tab bar on load
        this.updateBottomTab();
    }

    toggleSidebar() {
        if (window.innerWidth >= 768) {
            // Desktop Mode
            if (this.sidebar.classList.contains('md:translate-x-0')) {
                // Currently Open -> Close it
                this.sidebar.classList.remove('md:translate-x-0');
                this.sidebar.classList.add('-translate-x-full', 'md:w-0', 'md:overflow-hidden');
            } else {
                // Currently Closed -> Open it
                this.sidebar.classList.add('md:translate-x-0');
                this.sidebar.classList.remove('-translate-x-full', 'md:w-0', 'md:overflow-hidden');
            }
        } else {
            // Mobile Mode
            if (this.sidebar.classList.contains('-translate-x-full')) {
                this.openSidebar();
            } else {
                this.closeSidebar();
            }
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

    updateBottomTab() {
        const hash = window.location.hash.replace('#', '') || 'dashboard';
        const tabs = document.querySelectorAll('.mobile-bottom-bar .tab-item');
        tabs.forEach(tab => {
            if (tab.dataset.tab === hash) {
                tab.classList.add('active-tab');
            } else {
                tab.classList.remove('active-tab');
            }
        });
    }
}
