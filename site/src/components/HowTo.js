const STEPS = [
    {
        n: 1,
        title: 'Clone & Setup',
        desc: 'Clone the repository and run the setup script to create the Python virtual environment.',
        code: [
            { type: 'comment', text: '# Clone the repo' },
            { type: 'cmd',  text: 'git', args: ' clone https://github.com/vanjexdev/crowia' },
            { type: 'cmd',  text: 'cd', args: ' crowia' },
            { type: 'cmd',  text: './setup.sh', args: '' },
        ],
    },
    {
        n: 2,
        title: 'Run giselo-doctor',
        desc: 'The doctor checks all dependencies and auto-generates a config tailored to your OS and paths.',
        code: [
            { type: 'comment', text: '# Diagnose + configure' },
            { type: 'cmd', text: './scripts/giselo-doctor', args: '' },
        ],
    },
    {
        n: 3,
        title: 'Launch Giselo',
        desc: 'Start the desktop assistant with hotkey mode or always-on wake word.',
        code: [
            { type: 'comment', text: '# Hotkey mode (Ctrl+Space by default)' },
            { type: 'cmd', text: '.venv/bin/python3', args: ' crowia.py' },
            { type: 'comment', text: '# Always-on wake word' },
            { type: 'cmd', text: '.venv/bin/python3', args: ' crowia.py', flag: ' --always-on' },
        ],
    },
    {
        n: 4,
        title: 'Optional: Web App',
        desc: 'Run the FastAPI server to access Giselo from any device on your Tailscale VPN.',
        code: [
            { type: 'comment', text: '# Server with HTTPS (required for mic access)' },
            { type: 'cmd', text: '.venv/bin/python3', args: ' run_server.py', flag: ' --port 8181 \\' },
            { type: 'str',  text: '  --ssl-cert ~/giselo.crt', args: ' \\' },
            { type: 'str',  text: '  --ssl-key ~/giselo.key', args: '' },
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
                    giselo-doctor handles OS detection, dependency checks, and config generation automatically.
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
