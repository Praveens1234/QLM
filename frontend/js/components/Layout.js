export class Layout {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.overlay = document.getElementById('sidebar-overlay');
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.sidebarOpen = false;
        this.bindEvents();
    }

    bindEvents() {
        // Expose toggle globally for onclick attributes
        window.toggleSidebar = this.toggleSidebar.bind(this);

        // Listen for route changes to close mobile menu
        window.addEventListener('hashchange', () => {
            if (window.innerWidth < 768 && this.sidebarOpen) {
                this.closeSidebar();
            }
        });

        // Swipe-to-close/open sidebar on mobile
        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!e.changedTouches || !e.changedTouches.length) return;
            const deltaX = e.changedTouches[0].clientX - this.touchStartX;
            const deltaY = Math.abs(e.changedTouches[0].clientY - this.touchStartY);

            // Only trigger if horizontal swipe is dominant
            if (deltaY > Math.abs(deltaX)) return;

            // Swipe LEFT to close sidebar
            if (deltaX < -80 && this.sidebarOpen) {
                if (window.innerWidth < 768) {
                    this.closeSidebar();
                }
            }
            // Swipe RIGHT from left edge to open sidebar
            if (deltaX > 80 && this.touchStartX < 30 && !this.sidebarOpen) {
                if (window.innerWidth < 768) {
                    this.openSidebar();
                }
            }
        }, { passive: true });

        // Mobile "More" button opens sidebar
        const moreBtn = document.getElementById('btn-mobile-more');
        if (moreBtn) {
            moreBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (window.innerWidth < 768) {
                    this.openSidebar();
                }
            });
        }

        // Close sidebar when clicking a nav item on mobile
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth < 768 && this.sidebarOpen) {
                    this.closeSidebar();
                }
            });
        });
    }

    toggleSidebar() {
        if (window.innerWidth >= 768) {
            // Desktop Mode
            if (this.sidebar.classList.contains('md:translate-x-0')) {
                this.sidebar.classList.remove('md:translate-x-0');
                this.sidebar.classList.add('-translate-x-full', 'md:w-0', 'md:overflow-hidden');
            } else {
                this.sidebar.classList.add('md:translate-x-0');
                this.sidebar.classList.remove('-translate-x-full', 'md:w-0', 'md:overflow-hidden');
            }
        } else {
            // Mobile Mode
            if (this.sidebarOpen) {
                this.closeSidebar();
            } else {
                this.openSidebar();
            }
        }
    }

    openSidebar() {
        this.sidebarOpen = true;
        this.sidebar.classList.remove('-translate-x-full');
        this.overlay.classList.remove('hidden');
        // Force reflow then animate
        void this.overlay.offsetWidth;
        this.overlay.classList.remove('opacity-0', 'pointer-events-none');
    }

    closeSidebar() {
        this.sidebarOpen = false;
        this.sidebar.classList.add('-translate-x-full');
        this.overlay.classList.add('opacity-0', 'pointer-events-none');
        // After transition completes, hide the overlay
        const overlay = this.overlay;
        const handler = () => {
            if (!this.sidebarOpen) {
                overlay.classList.add('hidden');
            }
            overlay.removeEventListener('transitionend', handler);
        };
        overlay.addEventListener('transitionend', handler);
    }
}
