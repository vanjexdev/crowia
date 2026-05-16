const ADVANTAGES = [
    {
        icon: 'savings',
        color: '#B5EAD7',
        title: 'Zero API cost',
        desc: 'Giselo talks to Claude CLI, OpenCode, and Codex directly — not through their paid APIs. No per-token billing, no monthly quotas. You already have the CLI authenticated; Giselo just uses it.',
    },
    {
        icon: 'hearing',
        color: '#A3D8F4',
        title: 'Local speech, no cloud',
        desc: 'Transcription runs on faster-whisper (CPU, fully offline). Voice synthesis uses piper-tts locally. Your audio never leaves your machine — not even for a millisecond.',
    },
    {
        icon: 'lock',
        color: '#D0BCFF',
        title: 'True privacy',
        desc: 'Nothing is sent to a third-party speech service. Your conversations stay in a local JSON file. No telemetry, no analytics, no account required.',
    },
    {
        icon: 'bolt',
        color: '#FFD700',
        title: 'No intermediary latency',
        desc: 'Responses stream directly from the CLI process to your speakers. There is no SaaS layer, no webhook, no message queue between you and the model.',
    },
    {
        icon: 'desktop_windows',
        color: '#FF9AA2',
        title: 'Built for the desktop',
        desc: 'A floating overlay that appears on hotkey and disappears when done. It does not hijack a browser tab or require a chat app open. Works while you code, design, or write.',
    },
    {
        icon: 'wifi_off',
        color: '#FFDAC1',
        title: 'Works offline (mostly)',
        desc: 'Whisper transcribes without internet. piper-tts speaks without internet. Only the LLM call requires a connection — and even that can be swapped for a local model.',
    },
];

const COMPARE = [
    { feature: 'LLM cost',            giselo: 'Free (CLI)',         others: 'Per-token API billing' },
    { feature: 'Speech-to-text',      giselo: 'Local (Whisper)',    others: 'Cloud API (charged)' },
    { feature: 'Text-to-speech',      giselo: 'Local (piper-tts)',  others: 'Cloud API (charged)' },
    { feature: 'Audio privacy',       giselo: 'Never leaves device',others: 'Sent to cloud' },
    { feature: 'Account required',    giselo: 'No',                 others: 'Yes (API key)' },
    { feature: 'Desktop overlay',     giselo: '✓',                  others: '✗' },
    { feature: 'Wake word (offline)', giselo: '✓',                  others: 'Rarely' },
    { feature: 'Self-hosted web app', giselo: '✓ (PWA)',            others: 'Sometimes' },
];

export default {
    template: `
        <section id="why" class="section why-section">
            <div>
                <span class="section-label">
                    <span class="material-symbols-rounded">compare</span>
                    Why Giselo
                </span>
                <h2 class="headline-large">
                    Other tools charge per word.<br>
                    <span class="gradient-text">Giselo doesn't.</span>
                </h2>
                <p class="body-large why-sub">
                    Most AI assistants — including open-source ones — call paid speech and LLM APIs under the hood.
                    Giselo is different: it drives the <strong>CLI tools you already use</strong> and runs speech entirely on your hardware.
                </p>
            </div>

            <!-- Advantage cards -->
            <div class="why-grid">
                <div class="card why-card" cv-for="a in advantages" :key="a.title">
                    <div class="feature-icon" :style="'color:' + a.color">
                        <span class="material-symbols-rounded">{{ a.icon }}</span>
                    </div>
                    <h3 class="title-large">{{ a.title }}</h3>
                    <p class="body-medium why-desc">{{ a.desc }}</p>
                </div>
            </div>

            <!-- Comparison table -->
            <div class="compare-wrap">
                <h3 class="headline-medium compare-title">Giselo vs API-based assistants</h3>
                <div class="compare-table">
                    <div class="compare-header">
                        <div class="compare-cell compare-feature">Feature</div>
                        <div class="compare-cell compare-giselo">
                            <span class="material-symbols-rounded" style="font-size:18px;vertical-align:middle;margin-right:6px;">smart_toy</span>Giselo
                        </div>
                        <div class="compare-cell compare-other">Typical alternative</div>
                    </div>
                    <div class="compare-row" cv-for="r in compare" :key="r.feature">
                        <div class="compare-cell compare-feature">{{ r.feature }}</div>
                        <div class="compare-cell compare-giselo good">{{ r.giselo }}</div>
                        <div class="compare-cell compare-other muted">{{ r.others }}</div>
                    </div>
                </div>
            </div>
        </section>
    `,
    data: { advantages: ADVANTAGES, compare: COMPARE },
};
