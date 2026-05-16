# Contexto de sesión — Crowia / Giselo

> Pega este archivo al inicio de una nueva conversación con Claude para retomar el hilo exacto.

---

## Quién soy

Usuario: Vanjex (vanjexdev@gmail.com)
Sistema host: CachyOS Linux + KDE Plasma 6 (Wayland), teclado Epomaker F75
Shell: fish
Repo: `vanjexdev/crowia` en GitHub (usando remote `origin` con host alias `github-vanjex`)

---

## Qué es el proyecto

**Giselo** es un asistente de voz local. Código en `~/Workspace/agents/crowia/`.

- Escucha vía hotkey o wake word ("oye giselo")
- Transcribe con faster-whisper (local, CPU)
- Responde con Claude CLI, OpenCode o Codex
- Habla con piper-tts (español, modelo `es_ES-davefx-medium`)
- UI: overlay PyQt6 con QSplitter dos columnas

---

## Lo que se hizo (sesiones anteriores)

### 1. giselo-doctor (`scripts/giselo-doctor`)
Script Python ejecutable:
- Detecta OS (Arch/Debian/Fedora/macOS/Windows)
- Verifica 10 dependencias con ✓/✗ y hints de instalación
- Genera `config.local.yaml` con paths correctos para el OS actual

`config.py` deep-mergea `config.local.yaml` sobre `config.yaml` automáticamente.

**Bug corregido:** `shutil.which("piper")` encontraba la app GTK. Swapped a `piper-tts` primero.
**Bug corregido:** `~` en paths no se expande en subprocess. `output.py._speak()` ahora hace `Path(c).expanduser()`.

### 2. Giselo Web (`crowia/server/` + `run_server.py`)
PWA completa con acceso remoto vía Tailscale VPN:

**Backend (FastAPI + WebSocket `/ws`):**
- `POST /ask` — texto → LLM → JSON
- `WebSocket /ws` — voz + texto + TTS streaming
- Config via `CROWIA_CONFIG` env var

**Frontend (Material Design 3, vanilla JS):**
- Desktop/tablet: navigation rail lateral
- Mobile: bottom nav estilo Android + FAB micrófono central
- `MediaRecorder` → WebM → WebSocket → Whisper
- Web Audio API reproduce WAV del servidor
- `marked.js` renderiza markdown en burbujas
- PWA instalable

**Fixes TTS VM:**
- `piper-tts` Python package no instala binario → fallback `PiperVoice.load() + synthesize_wav()`
- WAV params deben setearse ANTES de llamar `synthesize_wav()`
- `AudioContext.resume()` en gesture del usuario → bypass autoplay policy

### 3. GitHub Pages landing site (`site/` → `docs/`)
- Vite + Courvux framework (desde GitHub `vanjexdev/courvux`)
- Material Design 3, vanilla JS, totalmente responsive
- Hero: mockup CSS de teléfono + laptop con placeholders para GIFs
- Secciones: Features (8 cards), How to Install (4 pasos), Footer
- Navbar con blur al hacer scroll, botón Get Started alineado en móvil
- Build: `npm run build` en `site/` → genera `docs/`
- GH Pages: Settings → Pages → Deploy from branch → `main` / `/docs`
- URL: `https://vanjexdev.github.io/crowia/`

**Para agregar GIFs:**
- Poner archivo en `site/public/` (ej. `site/public/web-demo.gif`)
- En `Hero.js` reemplazar `<div class="placeholder-media">` con `<img src="/crowia/web-demo.gif" alt="...">`
- `npm run build` y commit de `docs/`

### 4. Fixes de git/repo
- Git config local del repo: `Vanjex <vanjexdev@gmail.com>` (antes heredaba global incorrecto)
- Reescritura de los 70 commits del historial con autor correcto vía `git filter-branch`
- Force push a `main` y `staging`
- `config.local.yaml` removido del tracking (estaba trackeado a pesar del .gitignore)
- `.gitignore` actualizado: `.venv-server/`, `*.crt`, `*.key`, `site/node_modules/`

---

## Estado actual de ramas

```
main    ← pusheado, al día (a89d2f7)
staging ← pusheado, al día
feat/giselo-doctor ← local, mergeada (historia reescrita)
```

---

## Setup VM Ubuntu Server

```
hostname: vanjex-ubuntu.tailc65b67.ts.net
IP Tailscale: 100.113.181.126
mount host: ~/host/  (= /home/jesusu/ del host)
proyecto: ~/host/Workspace/agents/crowia/
venv servidor: ~/host/Workspace/agents/crowia/.venv-server/
config servidor: ~/config.server.yaml
certs: ~/giselo.crt, ~/giselo.key
```

**Arranque servidor:**
```bash
cd ~/host/Workspace/agents/crowia
.venv-server/bin/python3 run_server.py --port 8181 \
  --config ~/config.server.yaml \
  --ssl-cert ~/giselo.crt \
  --ssl-key  ~/giselo.key
```

**config.server.yaml:**
```yaml
output:
  tts_enabled: true
  tts_command:
    - "/home/vanjex/host/Workspace/agents/crowia/.venv-server/bin/piper-tts"
    - "--model"
    - "/home/vanjex/host/.local/share/piper/es_ES-davefx-medium.onnx"
    - "--output_raw"
```

---

## Pendientes / próximos pasos

- [ ] Grabar GIFs del web app (móvil) y del overlay de escritorio → meter en `site/public/` y actualizar `Hero.js`
- [ ] Configurar GH Pages en el repo: Settings → Pages → Deploy from branch → `main` / `/docs`
- [ ] Logs de debug TTS en `app.py` y `app.js` — remover cuando audio esté confirmado estable
- [ ] Iconos PWA reales (actualmente son placeholders morados generados con Python)
- [ ] Certs Tailscale expiran — renovar con `sudo tailscale cert` cuando expire

---

## Archivos clave

| Archivo | Descripción |
|---------|-------------|
| `crowia/config.py` | Merge config.yaml + config.local.yaml |
| `crowia/output.py` | TTS con piper-tts, expandir ~, fallback Python API |
| `crowia/server/app.py` | FastAPI + WebSocket, CROWIA_CONFIG env var |
| `crowia/server/audio.py` | webm→wav (ffmpeg), tts→wav (piper Python API) |
| `crowia/server/web/` | PWA: index.html, app.js, audio.js, style.css |
| `scripts/giselo-doctor` | Diagnóstico OS + config.local.yaml |
| `run_server.py` | CLI del servidor web |
| `site/` | Fuente del landing page (Vite + Courvux) |
| `docs/` | Build compilado → GitHub Pages |
| `.github/workflows/pages.yml` | CI para GH Pages (opcional, también funciona con docs/ directo) |

---

## Archivos sensibles (NO committear)

- `config.local.yaml` — paths locales del OS (ya está en .gitignore y desTrackeado)
- `~/.config/crowia/google_credentials.json`
- `~/.config/crowia/google_token.json`
- Certs Tailscale (`*.crt`, `*.key`) — en .gitignore
- `~/config.server.yaml` en la VM — no está en el repo
