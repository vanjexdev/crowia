# Skill: Proyecto Crowia / Giselo

Giselo es el asistente de voz local del usuario. El código vive en `~/Workspace/agents/crowia/`. Repo GitHub: `vanjexdev/crowia` (cuenta `github-vanjex`).

## Estructura clave

```
crowia/
├── crowia.py              # Entry point hotkey/always-on
├── run_server.py          # Entry point servidor web PWA
├── config.yaml            # Config principal
├── config.local.yaml      # Generado por giselo-doctor (ignorado en git)
├── scripts/giselo-doctor  # Detecta OS, escribe config.local.yaml
├── site/                  # Fuente del landing page (Vite + Courvux)
├── docs/                  # Build compilado → GitHub Pages
├── .github/workflows/pages.yml  # CI deploy GH Pages
└── crowia/
    ├── config.py          # load() — deep merge config.yaml + config.local.yaml
    ├── assistant.py       # ask() con on_chunk streaming, switch_backend()
    ├── output.py          # _strip_markdown(), _speak() via piper-tts subprocess
    ├── intent.py          # detect() — keywords en español
    ├── transcriber.py     # Whisper via faster-whisper
    ├── ui.py              # PyQt6 QSplitter overlay (CrowiaOverlay)
    ├── prefs.py           # Persistencia de preferencias UI
    ├── history.py         # ConversationHistory JSON
    └── server/
        ├── app.py         # FastAPI + WebSocket (voz+texto+TTS)
        ├── audio.py       # webm_to_wav() ffmpeg, tts_to_wav_bytes() piper
        └── web/           # PWA: index.html, app.js, audio.js, style.css
```

## Cómo correr

```bash
# Modo hotkey (desktop)
.venv/bin/python3 crowia.py

# Modo always-on (wake word)
.venv/bin/python3 crowia.py --always-on

# Servidor web (acceso remoto desde celular/VM)
.venv/bin/python3 run_server.py --port 8181 \
  --config ~/config.server.yaml \
  --ssl-cert ~/giselo.crt --ssl-key ~/giselo.key

# Landing page (desarrollo)
cd site && npm run dev

# Landing page (build para GH Pages)
cd site && npm run build  # genera docs/
```

## Backends disponibles

| Backend | Config | Comando de voz |
|---------|--------|----------------|
| Claude CLI | `backend: claude` | "usa claude" |
| OpenCode | `backend: opencode` | "usa opencode" |
| Codex | `backend: codex` | "usa codex" |

## Ramas git

- `main` — producción
- `staging` — pre-producción
- `feat/*` — features en desarrollo

Flujo: `feat/x` → `staging` → `main`. No hacer push directo sin confirmar.

**Git config local del repo:** `Vanjex <vanjexdev@gmail.com>` (seteado con `git config --local`).
No heredar del global — el global tiene otro email.

## TTS (piper-tts)

- **Host (CachyOS)**: binario en `/usr/bin/piper-tts`, modelo en `~/.local/share/piper/es_ES-davefx-medium.onnx`
- **VM (Ubuntu Server)**: usa Python API `PiperVoice.load()` + `synthesize_wav()` — no binario, modelo accesible vía mount
- `output.py._speak()` detecta si el cmd tiene `piper-tts` en `cmd[0]` → pipe a aplay
- `server/audio.py.tts_to_wav_bytes()` → si binario no existe → fallback Python API
- WAV params deben setearse ANTES de llamar `synthesize_wav()`

## Servidor Web PWA

- FastAPI + WebSocket en `/ws`
- Frontend Material Design 3, vanilla JS
- Mobile: bottom nav + FAB micrófono central
- Desktop/tablet: navigation rail lateral
- Voz: `MediaRecorder` → WebM → ffmpeg → WAV → Whisper → LLM → piper → WAV → Web Audio API
- HTTPS requerido para micrófono: `sudo tailscale cert <hostname>.ts.net`
- `AudioContext.resume()` debe llamarse en gesture del usuario (autoplay policy)

## Landing Page (GitHub Pages)

- Fuente: `site/` — Vite + Courvux (`vanjexdev/courvux` de GitHub)
- Output: `docs/` — commiteado al repo, sirve como GH Pages
- URL: `https://vanjexdev.github.io/crowia/`
- Config GH Pages: Settings → Pages → Deploy from branch → `main` / `/docs`
- Para agregar GIFs: poner en `site/public/`, reemplazar `placeholder-media` en `site/src/components/Hero.js`, hacer build y commitear `docs/`

## VM Ubuntu Server (Tailscale)

- Hostname: `vanjex-ubuntu.tailc65b67.ts.net`
- IP Tailscale: `100.113.181.126`
- Mount del host: `~/host/` (= `/home/jesusu/` del host)
- Proyecto: `~/host/Workspace/agents/crowia/`
- Venv servidor: `~/host/Workspace/agents/crowia/.venv-server/`
- Config servidor: `~/config.server.yaml`
- Certs: `~/giselo.crt`, `~/giselo.key`
- Comando arranque: `.venv-server/bin/python3 run_server.py --port 8181 --config ~/config.server.yaml --ssl-cert ~/giselo.crt --ssl-key ~/giselo.key`

## Config importante

- `config.local.yaml` se genera con `./scripts/giselo-doctor` — no editar a mano, no committear
- Para la VM usar `~/config.server.yaml` aparte (no se sube al repo)
- `CROWIA_CONFIG` env var overridea el path de config en `app.py`

## Comandos de voz clave

| Voz | Acción |
|-----|--------|
| "borra el historial" | Limpia conversación |
| "usa claude/opencode/codex" | Cambia backend |
| "silencia las respuestas" | TTS off |
| "activa el audio" | TTS on |
| "mira la pantalla" | Screenshot → IA |
| "sube/baja el volumen" | pactl ±10% |

## Archivos sensibles (NO committear)

- `config.local.yaml` — paths locales del OS (ya desTrackeado)
- `~/.config/crowia/google_credentials.json`
- `~/.config/crowia/google_token.json`
- Certs Tailscale (`*.crt`, `*.key`)
- `~/config.server.yaml` en la VM
