export default {
    template: `
        <section class="hero">
            <div class="hero-bg-glow"></div>

            <div class="hero-content">
                <!-- Badges -->
                <div class="hero-badges">
                    <span class="chip">
                        <span class="material-symbols-rounded">lock</span>
                        100% Local
                    </span>
                    <span class="chip">
                        <span class="material-symbols-rounded">open_in_new</span>
                        Open Source
                    </span>
                    <span class="chip">
                        <span class="material-symbols-rounded">language</span>
                        Spanish Voice
                    </span>
                </div>

                <!-- Headline -->
                <h1 class="display-large hero-headline">
                    Your AI assistant,<br>
                    <span class="gradient-text">always at hand</span>
                </h1>

                <p class="body-large hero-sub">
                    Giselo is an open-source, privacy-first voice assistant that runs entirely on your machine.
                    Powered by Claude, OpenCode, Codex, Moonshot/Kimi, or any custom CLI — switches backends automatically when rate limits hit.
                </p>

                <!-- CTAs -->
                <div class="hero-actions">
                    <a href="https://github.com/vanjexdev/crowia" target="_blank" rel="noopener" class="btn btn-filled">
                        <span class="material-symbols-rounded">code</span>
                        View on GitHub
                    </a>
                    <a href="#install" class="btn btn-outlined">
                        Install in one line
                        <span class="material-symbols-rounded">arrow_downward</span>
                    </a>
                </div>
            </div>

            <!-- Mockup -->
            <div class="hero-mockups">
                <div class="mockup-laptop hero-laptop">
                    <div class="mockup-laptop-lid">
                        <div class="mockup-laptop-display">
                            <img src="/crowia/desktop.gif" alt="Giselo Desktop Overlay" />
                        </div>
                    </div>
                    <div class="mockup-laptop-base"></div>
                </div>
            </div>
        </section>
    `,
};
