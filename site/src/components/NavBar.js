export default {
    template: `
        <header class="navbar" :class="{ scrolled: scrolled }">
            <div class="navbar-inner">
                <a href="#" class="navbar-brand">
                    <span class="navbar-logo material-symbols-rounded">smart_toy</span>
                    <span class="navbar-name">Giselo</span>
                </a>
                <nav class="navbar-links">
                    <a href="#features" class="navbar-link">Features</a>
                    <a href="#why" class="navbar-link">Why Giselo</a>
                    <a href="#install" class="navbar-link">Install</a>
                    <a href="https://github.com/vanjexdev/crowia" target="_blank" rel="noopener" class="navbar-link">GitHub</a>
                </nav>
                <a href="https://github.com/vanjexdev/crowia" target="_blank" rel="noopener" class="btn btn-filled navbar-cta">
                    <span class="material-symbols-rounded">download</span>
                    Get Started
                </a>
            </div>
        </header>
    `,
    data: { scrolled: false },
    onMount() {
        const onScroll = () => { this.scrolled = window.scrollY > 40; };
        window.addEventListener('scroll', onScroll, { passive: true });
        this.$addCleanup(() => window.removeEventListener('scroll', onScroll));
    },
};
