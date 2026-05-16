# Contexto de sesión — Crowia / Giselo

> Pega este archivo al inicio de una nueva conversación con Claude para retomar el hilo exacto.

---

## Quién soy

Usuario: Vanjex (vanjexdev@gmail.com)
Sistema host: CachyOS Linux + KDE Plasma 6 (Wayland), teclado Epomaker F75
Shell: fish
Repo: `vanjexdev/crowia` en GitHub (remote `origin` con alias `github-vanjex`)

---

## Qué es el proyecto

**Giselo** es un asistente de voz local. Código en `~/Workspace/agents/crowia/`.

- Escucha vía hotkey o wake word ("oye giselo")
- Transcribe con faster-whisper (local, CPU)
- Responde con Claude CLI, OpenCode o Codex
- Habla con piper-tts (español, modelo `es_ES-davefx-medium`)
- UI: overlay PyQt6 con QSplitter dos columnas

---

## Lo que se hizo (historial de sesiones)

### 1. giselo-doctor + config merge
- `scripts/giselo-doctor` detecta OS y genera `config.local.yaml`
- `config.py` deep-mergea `config.local.yaml` sobre `config.yaml`
- Bug fix: `piper-tts` antes que `piper` (GTK app) en `shutil.which()`
- Bug fix: `Path(c).expanduser()` en `output.py._speak()`

### 2. Giselo Web (PWA)
- FastAPI + WebSocket en `/ws`
- Frontend Material Design 3, vanilla JS
- Mobile: bottom nav + FAB. Desktop: navigation rail
- `MediaRecorder` → WebM → ffmpeg → WAV → Whisper → LLM → piper → WAV → Web Audio API
- `marked.js` renderiza markdown en burbujas
- HTTPS via Tailscale certs (requerido para micrófono)
- `AudioContext.resume()` en gesture del usuario

### 3. Auth JWT (`feat/web-auth`)
- `crowia/server/auth.py`: bcrypt (hash_password, verify_password) + PyJWT (create_token, verify_token, random_secret)
- `app.py`: endpoints `/auth/login` y `/auth/status`; Bearer token en rutas API; WS cierra con código 4401 si token inválido
- Frontend: pantalla de login, token en localStorage, Bearer header en fetch, `?token=` en WS URL, botón logout en Settings
- Auth desactivado por defecto (`enabled: false`). Activar en `config.local.yaml` o `config.server.yaml`
- Credenciales sensibles NUNCA en `config.yaml` (trackeado). Van en `config.local.yaml` o `config.server.yaml` (ambos en `.gitignore`)

**Generar credenciales:**
```bash
# Hash de contraseña
python3 -c "from crowia.server.auth import hash_password; print(hash_password('TU_CLAVE'))"
# Secret JWT
python3 -c "from crowia.server.auth import random_secret; print(random_secret())"
```

**Activar auth en `config.local.yaml` (o `config.server.yaml`):**
```yaml
server:
  auth:
    enabled: true
    username: "vanjex"
    password_hash: "<bcrypt hash>"
    token_secret: "<hex secret>"
    token_expire_hours: 72
```

### 4. GitHub Pages landing site (`site/` → `docs/`)
- Vite + Courvux (vendoreado en `site/src/vendor/courvux.js` — sin git deps)
- pnpm configurado: `pnpm.onlyBuiltDependencies: ["esbuild"]` en `package.json`
- Material Design 3: hero con mockups CSS de teléfono + laptop, GIFs reales
- GIFs: `site/public/mobile.gif` (web app) y `site/public/desktop.gif` (overlay)
- Build: `cd site && pnpm build` → genera `docs/`
- GH Pages: Settings → Pages → Deploy from branch → `main` / `/docs`
- URL: `https://vanjexdev.github.io/crowia/`

### 5. Scripts de arranque
- `launch-desktop.sh` → lanza `giselo-launcher` (UI PyQt6 para múltiples instancias)
- `launch-server.sh` → lanza `run_server.py` con port 8181, config y certs

### 6. Git / repo
- Config local del repo: `Vanjex <vanjexdev@gmail.com>`
- Historial reescrito (70 commits) con autor correcto vía `git filter-branch`
- `.gitignore` incluye: `config.local.yaml`, `config.server.yaml`, `*.crt`, `*.key`, `site/node_modules/`, `site/pnpm-lock.yaml`

---

## Estado actual de ramas

```
main          ← producción, al día
staging       ← al día
feat/web-auth ← rama activa (auth JWT + pnpm + GIFs)
```

**Flujo:** `feat/web-auth` → `staging` → `main`. No hacer push sin que el usuario lo pida.

---

## Setup VM Ubuntu Server

```
hostname:  vanjex-ubuntu.tailc65b67.ts.net
IP:        100.113.181.126
mount:     ~/host/ = /home/jesusu/ del host
proyecto:  ~/host/Workspace/agents/crowia/
venv:      ~/host/Workspace/agents/crowia/.venv-server/
```

**Arranque (desde la VM):**
```bash
cd ~/host/Workspace/agents/crowia
./launch-server.sh
# o manualmente:
.venv-server/bin/python3 run_server.py --port 8181 \
  --config config.server.yaml \
  --ssl-cert ~/giselo.crt --ssl-key ~/giselo.key
```

`config.server.yaml` vive en `~/host/Workspace/agents/crowia/config.server.yaml` (gitignored).

---

## Pendientes

- [ ] Configurar GH Pages en el repo: Settings → Pages → `main` / `/docs`
- [ ] Mergear `feat/web-auth` → `staging` → `main` (cuando el usuario lo apruebe)
- [ ] Remover logs de debug TTS en `app.py` y `app.js`
- [ ] Iconos PWA reales (actualmente placeholders morados)
- [ ] Renovar certs Tailscale cuando expiren (`sudo tailscale cert`)

---

## Archivos sensibles (NUNCA committear)

| Archivo | Contenido |
|---------|-----------|
| `config.local.yaml` | paths locales + auth credentials del host |
| `config.server.yaml` | TTS config + auth credentials de la VM |
| `*.crt`, `*.key` | Certs Tailscale |
| `~/.config/crowia/google_*.json` | OAuth Google |
