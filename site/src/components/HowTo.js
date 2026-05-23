const STEPS = [
    {
        n: 1,
        title: 'One-line install',
        desc: 'Run the installer — it detects your OS, installs dependencies, clones the repo, sets up a Python venv, and creates the giselo command.',
        code: [
            { type: 'comment', text: '# Linux (pacman / apt / dnf) + macOS (brew)' },
            { type: 'cmd', text: 'curl', args: ' -L https://raw.githubusercontent.com/vanjexdev/crowia/main/install.sh', flag: ' | bash' },
        ],
    },
    {
        n: 2,
        title: 'Authenticate your LLM',
        desc: 'Log in to the CLI backend(s) you want to use. Claude CLI uses OAuth — free with your subscription.',
        code: [
            { type: 'comment', text: '# Claude CLI (OAuth, no API key needed)' },
            { type: 'cmd', text: 'claude', args: ' login' },
            { type: 'comment', text: '# Optional: Moonshot/Kimi API key' },
            { type: 'cmd', text: 'export', args: ' MOONSHOT_API_KEY=sk-...' },
        ],
    },
    {
        n: 3,
        title: 'Launch Giselo',
        desc: 'Run the system diagnostic first, then start the desktop overlay. The doctor auto-detects your audio, TTS, and hotkey setup.',
        code: [
            { type: 'comment', text: '# Verify system dependencies' },
            { type: 'cmd', text: 'giselo', args: ' doctor' },
            { type: 'comment', text: '# Launch desktop overlay' },
            { type: 'cmd', text: 'giselo', args: '' },
        ],
    },
];

export default {
    template: `
        <section id="install" class="section howto-section">
            <div>
                <span class="section-label">
                    <span class="material-symbols-rounded">rocket_launch</span>
                    Get Started
                </span>
                <h2 class="headline-large">Up and running<br>in minutes</h2>
                <p class="body-large howto-sub">
                    One curl command installs everything. The launcher manages multiple instances with different backends and hotkeys.
                </p>
            </div>

            <div class="howto-steps">
                <div class="howto-step" cv-for="s in steps" :key="s.n">
                    <div class="step-number">{{ s.n }}</div>
                    <div class="howto-step-body">
                        <h3 class="title-large">{{ s.title }}</h3>
                        <p class="body-medium howto-step-desc">{{ s.desc }}</p>
                        <div class="code-block">
                            <div cv-for="(line, i) in s.code" :key="i" class="code-line">
                                <span cv-if="line.type === 'comment'" class="comment">{{ line.text }}</span>
                                <span cv-else-if="line.type === 'cmd'">
                                    <span class="cmd">{{ line.text }}</span><span>{{ line.args }}</span><span cv-if="line.flag" class="flag">{{ line.flag }}</span>
                                </span>
                                <span cv-else class="str">{{ line.text }}{{ line.args }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="howto-os-chips">
                <p class="label-large howto-os-label">Supported platforms</p>
                <div class="howto-os-list">
                    <span class="chip" cv-for="os in platforms" :key="os">{{ os }}</span>
                </div>
            </div>
        </section>
    `,
    data: {
        steps: STEPS,
        platforms: ['Arch Linux', 'Ubuntu / Debian', 'Fedora', 'macOS', 'Windows (WSL)'],
    },
};
