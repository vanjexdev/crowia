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
        title: 'Natural TTS — Local or Cloud',
        desc: 'Choose from multiple piper-tts voice models (es_ES, es_MX, es_AR) for fully offline speech, or switch to ElevenLabs for studio-quality cloned voices. Markdown is stripped automatically so responses sound natural.',
        color: '#A3D8F4',
    },
    {
        icon: 'stream',
        title: 'Streaming Responses + Cancel',
        desc: 'Responses render word-by-word as the LLM streams them. TTS starts speaking the first sentence while the rest is still generating — no waiting for the full reply. Hit Cancel any time to stop mid-stream.',
        color: '#FFB7C5',
    },
    {
        icon: 'smart_toy',
        title: 'Multi-Backend + Auto-Failover',
        desc: 'Registry of backends (Claude, OpenCode, Codex, Moonshot/Kimi, any custom CLI). Switch by voice or UI. Automatically falls back to the next backend when rate limits hit — same context, zero interruption.',
        color: '#B5EAD7',
    },
    {
        icon: 'desktop_windows',
        title: 'Desktop Overlay',
        desc: 'Floating PyQt6 overlay with a two-column QSplitter. Keyboard-driven, transparent, always on top when you need it.',
        color: '#FF9AA2',
    },
    {
        icon: 'psychology',
        title: 'Persona & Skills',
        desc: 'Set the assistant\'s name and gender (male/female) with hot-reload — no restart needed. Enable toggleable skill files like Caveman Mode for ultra-terse responses, or define your own.',
        color: '#C7CEEA',
    },
    {
        icon: 'history',
        title: 'Persistent Memory',
        desc: '3-layer memory system: session history, per-session summaries, and long-term memory injected into every prompt. Giselo remembers context across restarts.',
        color: '#FFDAC1',
    },
    {
        icon: 'devices',
        title: 'Cross-Platform',
        desc: 'Tested on Arch Linux, Ubuntu, Fedora, macOS, and Windows. giselo-doctor auto-configures your environment in seconds.',
        color: '#D4F0A5',
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
