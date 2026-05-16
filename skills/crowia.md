# Skill: Proyecto Crowia / Giselo

Giselo es el asistente de voz local del usuario. Código en `~/Workspace/agents/crowia/`. Repo: `vanjexdev/crowia` (remote `origin`, alias SSH `github-vanjex`).

## Estructura clave

```
crowia/
├── crowia.py              # Entry point hotkey/always-on
├── giselo-launcher        # UI PyQt6 para gestionar instancias
├── run_server.py          # Entry point servidor web PWA
├── launch-desktop.sh      # Script: lanza giselo-launcher
├── launch-server.sh       # Script: lanza servidor web
├── config.yaml            # Config base (trackeado, sin secrets)
├── config.local.yaml      # Generado por giselo-doctor (gitignored)
├── config.server.yaml     # Config VM/VPS con auth (gitignored)
├── scripts/giselo-doctor  # Detecta OS, escribe config.local.yaml
├── site/                  # Fuente del landing page (Vite + Courvux)
│   ├── src/vendor/courvux.js  # Courvux vendoreado (sin git deps)
│   ├── src/components/    # NavBar, Hero, Features, HowTo, Footer
│   └── public/            # GIFs: mobile.gif, desktop.gif
├── docs/                  # Build compilado → GitHub Pages
├── .github/workflows/pages.yml
└── crowia/
    ├── config.py          # deep merge config.yaml + config.local.yaml
    ├── assistant.py       # ask() con on_chunk streaming
    ├── output.py          # _strip_markdown(), _speak() piper-tts
    ├── intent.py          # detect() keywords español
    ├── transcriber.py     # Whisper via faster-whisper
    ├── ui.py              # PyQt6 QSplitter overlay
    └── server/
        ├── app.py         # FastAPI + WebSocket + auth JWT
        ├── auth.py        # bcrypt + PyJWT
        ├── audio.py       # webm_to_wav(), tts_to_wav_bytes()
        └── web/           # PWA: index.html, app.js, audio.js, style.css
```

## Comandos de arranque

```bash
# Desktop
./launch-desktop.sh           # lanza giselo-launcher (UI instancias)

# Servidor web (desde la VM, en ~/host/Workspace/agents/crowia/)
./launch-server.sh

# Landing page
cd site && pnpm dev           # desarrollo
cd site && pnpm build         # genera docs/
```

## Auth JWT (web app)

- Desactivado por defecto. Activar en `config.local.yaml` o `config.server.yaml`:
  ```yaml
  server:
    auth:
      enabled: true
      username: "vanjex"
      password_hash: "<bcrypt>"   # generar con auth.hash_password()
      token_secret: "<hex>"       # generar con auth.random_secret()
      token_expire_hours: 72
  ```
- Token se guarda en `localStorage` del browser
- WS protegido con `?token=<jwt>` en la URL
- API protegida con `Authorization: Bearer <token>`
- WS cierra con código 4401 si token inválido → browser hace logout

## Backends

| Backend | Config | Voz |
|---------|--------|-----|
| Claude CLI | `backend: claude` | "usa claude" |
| OpenCode | `backend: opencode` | "usa opencode" |
| Codex | `backend: codex` | "usa codex" |

## Ramas git

- `main` — producción
- `staging` — pre-producción
- `feat/web-auth` — auth JWT + pnpm + GIFs (activa)

Flujo: `feat/x` → `staging` → `main`. **No hacer push sin que el usuario lo pida.**

## TTS (piper-tts)

- **Host**: `/usr/bin/piper-tts`, modelo `~/.local/share/piper/es_ES-davefx-medium.onnx`
- **VM**: Python API `PiperVoice.load() + synthesize_wav()` (sin binario)
- WAV params deben setearse ANTES de `synthesize_wav()`
- `AudioContext.resume()` requerido en gesture del usuario (autoplay policy)

## VM Ubuntu Server (Tailscale)

```
hostname: vanjex-ubuntu.tailc65b67.ts.net  |  IP: 100.113.181.126
mount:    ~/host/ = /home/jesusu/ del host
proyecto: ~/host/Workspace/agents/crowia/
venv:     .venv-server/
config:   config.server.yaml (en raíz del proyecto, gitignored)
certs:    ~/giselo.crt, ~/giselo.key
```

## Landing Page (GitHub Pages)

- `site/` → Vite + Courvux (vendoreado, sin dependencias git)
- `docs/` → build commiteado, sirve GH Pages
- pnpm: `onlyBuiltDependencies: ["esbuild"]` en `package.json`
- URL: `https://vanjexdev.github.io/crowia/`
- GIFs en `site/public/`: `mobile.gif` (web app) y `desktop.gif` (overlay)

## Archivos sensibles (NUNCA committear)

- `config.local.yaml` — gitignored
- `config.server.yaml` — gitignored
- `*.crt`, `*.key` — gitignored
- `~/.config/crowia/google_*.json` — fuera del repo

## Comandos de voz clave

| Voz | Acción |
|-----|--------|
| "borra el historial" | Limpia conversación |
| "usa claude/opencode/codex" | Cambia backend |
| "silencia las respuestas" | TTS off |
| "activa el audio" | TTS on |
| "mira la pantalla" | Screenshot → IA |
| "sube/baja el volumen" | pactl ±10% |
