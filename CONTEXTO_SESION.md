# Contexto de sesion — Crowia / Giselo

> Pega este archivo al inicio de una nueva conversacion con Claude para retomar el hilo exacto.

---

## Quien soy

Usuario: Vanjex (vanjexdev@gmail.com)
Sistema host: CachyOS Linux + KDE Plasma 6 (Wayland), teclado Epomaker F75
Shell: fish
Repo: `vanjexdev/crowia` en GitHub (remote `origin` con alias `github-vanjex`)

---

## Que es el proyecto

**Giselo** es un asistente de voz local. Codigo en `~/Workspace/agents/crowia/`.

- Escucha via hotkey o wake word ("oye giselo")
- Transcribe con faster-whisper (local, CPU)
- Responde con Claude CLI, OpenCode o Codex
- Habla con piper-tts (espanol, modelo `es_ES-davefx-medium`)
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
- `MediaRecorder` -> WebM -> ffmpeg -> WAV -> Whisper -> LLM -> piper -> WAV -> Web Audio API
- `marked.js` renderiza markdown en burbujas
- HTTPS via Tailscale certs (requerido para microfono)
- `AudioContext.resume()` en gesture del usuario

### 3. Auth JWT (`feat/web-auth`)
- `crowia/server/auth.py`: bcrypt (hash_password, verify_password) + PyJWT (create_token, verify_token, random_secret)
- `app.py`: endpoints `/auth/login` y `/auth/status`; Bearer token en rutas API; WS cierra con codigo 4401 si token invalido
- Frontend: pantalla de login, token en localStorage, Bearer header en fetch, `?token=` en WS URL, boton logout en Settings
- Auth desactivado por defecto (`enabled: false`). Activar en `config.local.yaml` o `config.server.yaml`
- Credenciales sensibles NUNCA en `config.yaml` (trackeado). Van en `config.local.yaml` o `config.server.yaml` (ambos en `.gitignore`)

**Generar credenciales:**
```bash
# Hash de contrasena
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

### 4. GitHub Pages landing site (`site/` -> `docs/`)
- Vite + Courvux (vendoreado en `site/src/vendor/courvux.js` -- sin git deps)
- pnpm configurado: `pnpm.onlyBuiltDependencies: ["esbuild"]` en `package.json`
- Material Design 3: hero con mockups CSS de telefono + laptop, GIFs reales
- GIFs: `site/public/mobile.gif` (web app) y `site/public/desktop.gif` (overlay)
- Build: `cd site && pnpm build` -> genera `docs/`
- GH Pages: Settings -> Pages -> Deploy from branch -> `main` / `/docs`
- URL: `https://vanjexdev.github.io/crowia/`

### 5. Scripts de arranque
- `launch-desktop.sh` -> lanza `giselo-launcher` (UI PyQt6 para multiples instancias)
- `launch-server.sh` -> lanza `run_server.py` con port 8181, config y certs

### 6. Git / repo
- Config local del repo: `Vanjex <vanjexdev@gmail.com>`
- Historial reescrito (70 commits) con autor correcto via `git filter-branch`
- `.gitignore` incluye: `config.local.yaml`, `config.server.yaml`, `*.crt`, `*.key`, `site/node_modules/`, `site/pnpm-lock.yaml`

---

## Estado actual de ramas (crowia)

```
main          <- produccion, al dia
staging       <- al dia
feat/web-auth <- rama activa (auth JWT + pnpm + GIFs)
```

**Flujo:** `feat/web-auth` -> `staging` -> `main`. No hacer push sin que el usuario lo pida.

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

## Pendientes (crowia)

- [ ] Configurar GH Pages en el repo: Settings -> Pages -> `main` / `/docs`
- [ ] Mergear `feat/web-auth` -> `staging` -> `main` (cuando el usuario lo apruebe)
- [ ] Remover logs de debug TTS en `app.py` y `app.js`
- [ ] Iconos PWA reales (actualmente placeholders morados)
- [ ] Renovar certs Tailscale cuando expiren (`sudo tailscale cert`)

---

## Sesion 2026-05-17: Investigacion Ollama AI

**Contexto:** Usuario quiere instalar Ollama en su PC CachyOS y saber que modelo usar.

**Specs del usuario:**
- CPU: Intel Core i7-1355U (13th gen, 12 threads)
- RAM: 32GB
- GPU: Intel Iris Xe (integrada, sin GPU dedicada)

**Recomendacion:**
- Instalar `ollama-vulkan` (AUR) para aceleracion GPU con Intel Iris Xe
- Modelo recomendado: `qwen2.5:14b` (~9GB RAM) -- buen espanol, razonamiento solido
- Alternativas: `llama3.1:8b` (mas rapido), `qwen2.5:32b` (maxima calidad, mas lento), `deepseek-r1:8b` (thinking)

**Estado:** Investigacion completada. Instalacion pendiente para proxima sesion.

---

## SESION 2026-05-25: Rebranding hub-juztstack -> hub-vanjex

### Contexto
El usuario tiene un proyecto llamado **hub-juztstack** en:
`/home/jesusu/Workspace/vanjexdev/php/wordpress/hub-juztstack`

Este proyecto es un backend hub central construido con Fastify + TypeScript, originalmente para el ecosistema "JuztStack". El usuario quiere renombrarlo a **hub-vanjex** porque todos sus productos pertenecen a la marca Vanjex y su dominio vanjex.com. El remote actual apunta a `git@github-personal:juztstack/hub-juztstack.git`.

### Cambios identificados

| Archivo | Cambio |
|---------|--------|
| `package.json` | `name` de "hub-juztstack" a "hub-vanjex", `description` de "JuztStack Hub Backend" a "Vanjex Hub Backend" |
| `README.md` | 14 referencias a "JuztStack", "hub-juztstack", "juztstack.dev", "hub-juztstack.git", "your-org" |
| `src/app.ts` | Import `juztDeployModule` desde `./modules/juztdeploy/juztdeploy.module`, prefix `/juztdeploy` |
| `src/modules/juztdeploy/` | Todo el directorio y sus archivos nombrados `juztdeploy` |
| `src/modules/juztdeploy/controllers/auth.controller.ts` | 3 ocurrencias de "JuztStack" en HTML renderizado (lineas 86, 138, 181) |
| `.env.example` | `GITHUB_CALLBACK_URL=https://hub.juztstack.dev/...` |
| `Caddyfile.example` | `local.juztstack.dev` |
| `Caddyfile` | `local.juztstack.dev` |

### Todos los archivos del proyecto

```
hub-juztstack/
  .env.example
  .gitignore
  Caddyfile
  Caddyfile.example
  docker-compose.local.yml
  docker-compose.yml
  Dockerfile
  package.json
  pnpm-lock.yaml
  README.md
  tsconfig.json
  src/
    app.ts          (import modulo juztdeploy, prefix /juztdeploy)
    server.ts       (entry point, sin referencias directas a JuztStack)
    config/
      env.ts        (valida env vars, sin referencias a JuztStack)
    modules/
      juztdeploy/
        juztdeploy.module.ts              (entry point del modulo)
        controllers/
          auth.controller.ts              (3x "JuztStack" en HTML)
        services/
          github-auth.service.ts          (sin referencias JuztStack)
        routes/
          auth.routes.ts                  (sin referencias JuztStack)
        types/
          auth.types.ts                   (sin referencias JuztStack)
```

### Git
- Branch: `main`
- Remote: `git@github-personal:juztstack/hub-juztstack.git`
- Working tree: limpio
- 3 commits: `a1a8a6e`, `fe65699`, `dca481a`

### Decision del usuario (confirmado)
- Nueva identidad: **hub-vanjex** (todo bajo marca Vanjex/vanjex.com)
- Modulo renombrado: `juztdeploy` -> **`nodus-jet`**
- Remote: `vanjexdev/hub-vanjex` en GitHub
- Dominios: **hub.vanjex.dev** (produccion) / **hub.vanjex.localhost** (local)
- Pendiente: ejecutar los cambios de rebranding (archivos y modulo)

---

## Archivos sensibles (NUNCA committear)

| Archivo | Contenido |
|---------|-----------|
| `config.local.yaml` | paths locales + auth credentials del host |
| `config.server.yaml` | TTS config + auth credentials de la VM |
| `*.crt`, `*.key` | Certs Tailscale |
| `~/.config/crowia/google_*.json` | OAuth Google |

---

## Sesion 2026-05-17: Investigacion Ollama AI

**Contexto:** Usuario quiere instalar Ollama en su PC CachyOS y saber que modelo usar.

**Specs del usuario:**
- CPU: Intel Core i7-1355U (13th gen, 12 threads)
- RAM: 32GB
- GPU: Intel Iris Xe (integrada, sin GPU dedicada)

**Recomendacion:**
- Instalar `ollama-vulkan` (AUR) para aceleracion GPU con Intel Iris Xe
- Modelo recomendado: `qwen2.5:14b` (~9GB RAM) -- buen espanol, razonamiento solido
- Alternativas: `llama3.1:8b` (mas rapido), `qwen2.5:32b` (maxima calidad, mas lento), `deepseek-r1:8b` (thinking)

**Estado:** Investigacion completada. Instalacion pendiente para proxima sesion.
