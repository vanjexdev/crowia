# Contexto de sesión — Crowia / Giselo

> Pega este archivo al inicio de una nueva conversación con Claude para retomar el hilo exacto.

---

## Quién soy

Usuario: Vanjex (uzcateguijesusdev@gmail.com)
Sistema host: CachyOS Linux + KDE Plasma 6 (Wayland), teclado Epomaker F75
Shell: fish
Repo: `vanjexdev/crowia` en GitHub (usando `github-vanjex` como remote)

---

## Qué es el proyecto

**Giselo** es un asistente de voz local. Código en `~/Workspace/agents/crowia/`.

- Escucha vía hotkey o wake word ("oye giselo")
- Transcribe con faster-whisper (local, CPU)
- Responde con Claude CLI, OpenCode o Codex
- Habla con piper-tts (español, modelo `es_ES-davefx-medium`)
- UI: overlay PyQt6 con QSplitter dos columnas

---

## Lo que hicimos en esta sesión

### 1. giselo-doctor (`scripts/giselo-doctor`)
Script Python ejecutable que:
- Detecta OS (Arch/Debian/Fedora/macOS/Windows)
- Verifica 10 dependencias con ✓/✗ y hints de instalación
- Genera `config.local.yaml` con paths correctos para el OS actual

`config.py` ahora deep-mergea `config.local.yaml` sobre `config.yaml` automáticamente.

**Bug corregido:** `shutil.which("piper")` encontraba la app GTK antes que `piper-tts`. Swapped a `piper-tts` primero.

**Bug corregido:** `~` en paths no se expande en subprocess. `output.py._speak()` ahora hace `Path(c).expanduser()` antes de Popen.

### 2. Giselo Web (`crowia/server/` + `run_server.py`)
PWA completa con acceso remoto vía Tailscale VPN:

**Backend (FastAPI + WebSocket `/ws`):**
- `POST /ask` — texto → LLM → JSON
- `WebSocket /ws` — protocolo de mensajes JSON + binary:
  - `voice_start` / binary chunks / `voice_end` → ffmpeg → Whisper → LLM → piper → WAV binary
  - `text` → LLM → chunks streaming → WAV binary
  - `clear_history`, `switch_backend`
- `GET /api/status`, `GET/DELETE /api/history`
- Config via `CROWIA_CONFIG` env var (set por `run_server.py --config`)

**Frontend (Material Design 3, vanilla JS):**
- Desktop/tablet: navigation rail lateral
- Mobile: bottom nav estilo Android + FAB micrófono central
- `MediaRecorder` → WebM → WebSocket binary → Whisper
- `Web Audio API` → reproduce WAV del servidor
- `marked.js` → renderiza markdown en burbujas del asistente
- Service worker → PWA offline shell
- `AudioContext.resume()` en gesture del usuario → bypass autoplay policy

**Fixes TTS en la VM:**
- `piper-tts` Python package no instala binario → `audio.py` detecta si binario existe, si no usa `PiperVoice.load() + synthesize_wav()`
- `synthesize()` → 44 bytes (solo header WAV, sin audio) → cambiado a `synthesize_wav()`
- WAV params deben setearse ANTES de llamar `synthesize_wav()`

### 3. Instrucciones para instalación por OS
README actualizado con secciones para Arch, Ubuntu, Fedora, macOS, Windows.

---

## Estado actual de ramas

```
main    ← pusheado, al día
staging ← pusheado, al día
feat/giselo-doctor ← local, mergeada
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

## Pendientes / próximos pasos sugeridos

- [ ] Logs de debug TTS en `app.py` y `app.js` — remover cuando audio esté confirmado estable
- [ ] Iconos PWA reales (actualmente son placeholders morados generados con Python)
- [ ] `config.server.yaml` no está en el repo (correcto, es local de la VM)
- [ ] Certs Tailscale expiran — renovar con `sudo tailscale cert` cuando expire

---

## Archivos clave modificados en esta sesión

| Archivo | Cambio |
|---------|--------|
| `crowia/config.py` | Merge de `config.local.yaml` |
| `crowia/output.py` | Expandir `~` en tts_command, fallback Python API |
| `crowia/intent.py` | Fix false positive TTS unmute ("habla" → frases completas) |
| `scripts/giselo-doctor` | Nuevo — diagnóstico OS + config.local.yaml |
| `run_server.py` | Nuevo — CLI del servidor web |
| `crowia/server/app.py` | Nuevo — FastAPI + WebSocket |
| `crowia/server/audio.py` | Nuevo — conversión audio + piper Python API |
| `crowia/server/web/*` | Nuevo — PWA completa |
| `README.md` | Instrucciones por OS + sección Giselo Web |
| `.gitignore` | Nuevo |
| `skills/crowia.md` | Nuevo — skill del proyecto |
