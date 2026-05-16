const FEATURES = [
    {
        icon: 'mic',
        title: 'Voice Control',
        desc: 'Trigger with a hotkey or always-on wake word ("oye giselo"). Transcribed locally with faster-whisper — zero latency, zero cloud.',
        color: '#D0BCFF',
    },
    {
        icon: 'security',
        title: 'Privacy First',
        desc: 'All processing runs on your machine. No API calls to speech clouds, no data collection. Your conversations stay yours.',
        color: '#EFB8C8',
    },
    {
        icon: 'language',
        title: 'Natural TTS',
        desc: 'Speaks with piper-tts using the es_ES-davefx-medium voice model. Markdown is stripped automatically so responses sound natural.',
        color: '#A3D8F4',
    },
    {
        icon: 'smart_toy',
        title: 'Multi-Backend',
        desc: 'Switch between Claude CLI, OpenCode, and Codex by voice. Say "usa claude" or "usa opencode" to change on the fly.',
        color: '#B5EAD7',
    },
    {
        icon: 'web',
        title: 'Web App (PWA)',
        desc: 'Remote access from any device on your Tailscale VPN. Installable as a PWA on Android or desktop. Voice + text, full TTS.',
        color: '#FFD700',
    },
    {
        icon: 'desktop_windows',
        title: 'Desktop Overlay',
        desc: 'Floating PyQt6 overlay with a two-column QSplitter. Keyboard-driven, transparent, always on top when you need it.',
        color: '#FF9AA2',
    },
    {
        icon: 'history',
        title: 'Conversation History',
        desc: 'Persistent JSON history with instant replay in the overlay. Clear with a voice command or a button click.',
        color: '#C7CEEA',
    },
    {
        icon: 'devices',
        title: 'Cross-Platform',
        desc: 'Tested on Arch Linux, Ubuntu, Fedora, macOS, and Windows. giselo-doctor auto-configures your environment in seconds.',
        color: '#FFDAC1',
    },
];

export default {
    template: `
        <section id="features" class="section features-section">
            <div>
                <span class="section-label">
                    <span class="material-symbols-rounded">auto_awesome</span>
                    Features
                </span>
                <h2 class="headline-large">Everything you need,<br>nothing you don't</h2>
                <p class="body-large features-sub">
                    Giselo is intentionally minimal — a focused tool that does one thing exceptionally well.
                </p>
            </div>

            <div class="features-grid">
                <div class="card feature-card" cv-for="f in features" :key="f.title">
                    <div class="feature-icon" :style="'color:' + f.color">
                        <span class="material-symbols-rounded">{{ f.icon }}</span>
                    </div>
                    <h3 class="title-large feature-title">{{ f.title }}</h3>
                    <p class="body-medium feature-desc">{{ f.desc }}</p>
                </div>
            </div>
        </section>
    `,
    data: { features: FEATURES },
};
