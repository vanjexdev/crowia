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
                    Powered by Claude, OpenCode, or Codex — no data leaves your computer.
                </p>

                <!-- CTAs -->
                <div class="hero-actions">
                    <a href="https://github.com/vanjexdev/crowia" target="_blank" rel="noopener" class="btn btn-filled">
                        <span class="material-symbols-rounded">code</span>
                        View on GitHub
                    </a>
                    <a href="#features" class="btn btn-outlined">
                        See features
                        <span class="material-symbols-rounded">arrow_downward</span>
                    </a>
                </div>
            </div>

            <!-- Mockups -->
            <div class="hero-mockups">
                <!-- Phone mockup — Giselo Web PWA -->
                <div class="mockup-phone hero-phone" style="transform: rotate(-4deg) translateY(20px);">
                    <div class="mockup-phone-island"></div>
                    <div class="mockup-phone-screen">
                        <div class="placeholder-media">
                            <span class="material-symbols-rounded">smartphone</span>
                            <span>Web App GIF</span>
                            <span style="opacity:0.5;font-size:0.7rem;">Drop your recording here</span>
                        </div>
                    </div>
                </div>

                <!-- Laptop mockup — Desktop overlay -->
                <div class="mockup-laptop hero-laptop">
                    <div class="mockup-laptop-lid">
                        <div class="mockup-laptop-display">
                            <div class="placeholder-media">
                                <span class="material-symbols-rounded">computer</span>
                                <span>Desktop Overlay GIF</span>
                                <span style="opacity:0.5;font-size:0.7rem;">Drop your recording here</span>
                            </div>
                        </div>
                    </div>
                    <div class="mockup-laptop-base"></div>
                </div>
            </div>
        </section>
    `,
};
