# Giselo — Asistente de Voz Local

Asistente de voz para Linux (KDE Plasma / Wayland) que escucha comandos, los transcribe con Whisper, y responde usando Claude u otros backends de IA.

## Stack

- **Python 3.14** + venv
- **faster-whisper** — transcripción local (modelo `small`, CPU/INT8)
- **Claude CLI** — respuestas vía suscripción (OAuth, sin costo de API)
- **OpenCode backend** — backend alternativo vía OpenCode CLI
- **Codex backend** — backend alternativo vía OpenAI Codex
- **giselo-browser** — control de Firefox con Playwright (automatización web)
- **giselo-google** — integración Gmail + Google Calendar
- **giselo-remind** — sistema de recordatorios vía systemd timers
- **Anthropic SDK** — solo para análisis de pantalla (visión)
- **piper-tts** — voz en español natural (modelo `es_ES-davefx-medium`)
- **sounddevice + webrtcvad** — modo siempre activo con wake word
- **spectacle** — capturas de pantalla (KDE Wayland)
- **pactl** — control de volumen
- **FastAPI + uvicorn** — servidor web para acceso remoto vía PWA
- **marked.js** — renderizado de markdown en el chat web

## Modos de uso

### Modo hotkey (por defecto)
```bash
.venv/bin/python3 crowia.py
```
Presiona `Right-Ctrl + \`` para iniciar grabación, vuelve a presionar para enviar.

### Modo siempre activo (wake word)
```bash
.venv/bin/python3 crowia.py --always-on
```
Di "oye giselo", "hey giselo" o "giselo" para activar. El siguiente utterance va al backend activo.

### Múltiples instancias
```bash
.venv/bin/python3 crowia.py --backend claude --hotkey "KEY_RIGHTCTRL,KEY_GRAVE"
.venv/bin/python3 crowia.py --backend opencode --hotkey "KEY_LEFTCTRL,KEY_LEFTSHIFT,KEY_LEFTALT,KEY_1"
```

### Flags de línea de comandos

| Flag | Descripción |
|------|-------------|
| `--backend claude\|opencode\|codex` | Override del backend desde config al arrancar |
| `--hotkey "KEY_A,KEY_B,KEY_C"` | Override de la combinación de teclas (nombres evdev separados por coma) |
| `--always-on` | Activa modo siempre activo con wake word |
| `--list-devices` | Lista dispositivos de entrada disponibles |

## Comandos de voz

| Di esto | Resultado |
|---------|-----------|
| "oye giselo / hey giselo" | activa en modo always-on |
| "mira la pantalla" | captura pantalla → IA analiza |
| "sube / baja el volumen" | pactl ±10% |
| "volumen al 50%" | pactl al 50% |
| "silencia" | mute toggle |
| "abre Firefox" | lanza firefox |
| "abre la terminal" | lanza alacritty |
| "abre Zed" | lanza zeditor |
| "borra el historial" | limpia conversación |
| "/ruta/a/archivo.py" | lee el archivo → IA comenta |
| "usa Claude / usa OpenCode" | cambia backend activo |
| "usa giselo-browser" | control Firefox con Playwright |
| "revisa mi correo" | giselo-google gmail unread |
| "¿qué tengo hoy?" | giselo-google calendar today |
| "recuérdame X a las Y" | giselo-remind add |

## Capacidades de IA (herramientas habilitadas)

- `WebSearch` — búsqueda en internet en tiempo real
- `Bash(git *)` — operaciones git (sin push)
- `Bash(zeditor*)` / `Bash(alacritty*)` / `Bash(firefox*)` — abrir apps
- `Read` / `Edit` / `Write` — leer y modificar archivos en `/home/jesusu/`
- Acceso a todo `/home/jesusu/` vía `--add-dir`

## Instalación

### Pasos comunes (todos los OS)

```bash
# 1. Clonar repo
git clone <repo-url> crowia && cd crowia

# 2. Venv y dependencias Python
python3 -m venv --system-site-packages .venv
.venv/bin/pip install faster-whisper anthropic sounddevice webrtcvad-wheels numpy

# 3. Claude CLI
npm install -g @anthropic-ai/claude-code

# 4. Correr doctor (detecta OS y genera config.local.yaml)
./scripts/giselo-doctor

# 5. Arrancar
.venv/bin/python3 crowia.py
```

---

### Arch / CachyOS / Manjaro

```bash
# Dependencias del sistema
paru -S python-evdev python-yaml alsa-utils libnotify spectacle piper-tts playerctl kdialog

# Modelo de voz español
mkdir -p ~/.local/share/piper
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"

# Acceso a dispositivos de teclado (requiere re-login)
sudo usermod -aG input $USER
```

---

### Ubuntu / Debian

```bash
# Dependencias del sistema
sudo apt install -y python3-evdev python3-yaml alsa-utils libnotify-bin \
                   espeak-ng playerctl zenity python3-venv python3-pip

# piper-tts (no está en apt — instalar binario)
pip install piper-tts
# O descargar binario desde https://github.com/rhasspy/piper/releases

# Modelo de voz español
mkdir -p ~/.local/share/piper
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"

# Venv (Ubuntu no usa --system-site-packages por defecto)
python3 -m venv .venv
.venv/bin/pip install faster-whisper anthropic sounddevice webrtcvad-wheels numpy PyQt6 pyyaml

# Acceso a dispositivos de teclado (requiere re-login)
sudo usermod -aG input $USER
```

> **Nota:** En Ubuntu/GNOME usar `zenity` como file picker. `giselo-doctor` lo detecta automáticamente.

---

### Fedora

```bash
# Dependencias del sistema
sudo dnf install -y python3-evdev python3-pyyaml alsa-utils libnotify \
                   espeak-ng playerctl zenity python3-pip

# piper-tts (no está en dnf — instalar con pip)
pip install piper-tts

# Modelo de voz español
mkdir -p ~/.local/share/piper
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"

.venv/bin/pip install faster-whisper anthropic sounddevice webrtcvad-wheels numpy PyQt6 pyyaml

# Acceso a dispositivos de teclado (requiere re-login)
sudo usermod -aG input $USER
```

---

### macOS

> Requiere macOS 12+ y Homebrew.

```bash
# Dependencias
brew install python@3.12 node

# TTS nativo (say) — no requiere instalación
# File picker nativo (osascript) — no requiere instalación
# Hotkey vía pynput (no evdev en macOS)

.venv/bin/pip install faster-whisper anthropic sounddevice webrtcvad-wheels numpy PyQt6 pyyaml pynput

# Claude CLI
npm install -g @anthropic-ai/claude-code
```

> **Nota:** En macOS el hotkey usa `pynput` (accesibilidad del sistema). Habilitar en: Preferencias del Sistema → Privacidad → Accesibilidad → agregar Terminal/iTerm.

---

### Windows

> Soporte experimental. Requiere Python 3.10+, Node.js y Git Bash.

```powershell
# Instalar Python desde python.org
# Instalar Node.js desde nodejs.org

pip install faster-whisper anthropic sounddevice PyQt6 pyyaml pynput

# Claude CLI
npm install -g @anthropic-ai/claude-code

# espeak-ng para TTS
winget install espeak-ng
```

> **Limitaciones en Windows:** evdev no disponible (hotkey usa pynput), playerctl no disponible (sin control de media), kdialog/zenity no disponibles (file picker limitado).

## giselo-doctor

Detecta el sistema operativo y genera `config.local.yaml` con comandos ajustados automáticamente. Ejecutar una vez después de instalar, o al cambiar de máquina/OS.

```bash
./scripts/giselo-doctor
```

Qué hace:

- Verifica dependencias (Python, PyQt6, faster-whisper, Claude CLI, arecord, piper-tts, notify-send, evdev, kdialog, playerctl, playwright)
- Imprime ✓/✗ por componente con hint de instalación si falta algo
- Escribe `config.local.yaml` con la ruta correcta de `piper-tts`, backend de audio, picker, etc.

`config.local.yaml` se fusiona automáticamente sobre `config.yaml` al arrancar. No hace falta editar `config.yaml` a mano para ajustes de OS.

Ejemplo de salida:

```
╔══════════════════════════════════════╗
║        giselo-doctor  v1.0           ║
╚══════════════════════════════════════╝

  Sistema: CachyOS Linux
  Familia: arch  |  Pkg: paru

  Python y dependencias core
    ✓ Python  3.14.4
    ✓ PyYAML  6.0.3
    ✓ PyQt6  6.11.0
    ✗ faster-whisper
    ✓ Claude CLI  2.1.142

  ...

  ✓ Escrito: /ruta/al/proyecto/config.local.yaml
  ✓ Todo listo para correr Giselo en CachyOS Linux
```

Sistemas soportados: Arch/CachyOS/Manjaro, Ubuntu/Debian, Fedora, openSUSE, macOS, Windows.

## Configuración

Todo en `config.yaml`. Claves importantes:

```yaml
hotkey:
  keys: ["KEY_RIGHTCTRL", "KEY_GRAVE"]  # Right-Ctrl + `
  max_record_seconds: 300

whisper:
  model: "small"       # base | small | medium | large-v3
  language: "es"

always_on:
  wake_phrases: ["oye giselo", "hey giselo", "giselo"]
  silence_duration_ms: 800    # ms de silencio para cortar utterance
  vad_aggressiveness: 2       # 0-3

backend: "claude"    # claude | opencode | codex

claude:
  model: "claude-sonnet-4-6"

output:
  tts_enabled: true
  tts_command: ["piper-tts", "--model", "~/.local/share/piper/es_ES-davefx-medium.onnx", "--output_raw"]
```

## Configuración de hotkeys

Las teclas se especifican con nombres evdev. Usa `--list-devices` para ver dispositivos disponibles.

### Nombres de teclas comunes

| Tecla | Nombre evdev |
|-------|-------------|
| Ctrl derecho | `KEY_RIGHTCTRL` |
| Ctrl izquierdo | `KEY_LEFTCTRL` |
| Shift izquierdo | `KEY_LEFTSHIFT` |
| Shift derecho | `KEY_RIGHTSHIFT` |
| Alt izquierdo | `KEY_LEFTALT` |
| Alt derecho / AltGr | `KEY_RIGHTALT` |
| Super / Windows | `KEY_LEFTMETA` |
| Backtick / ` | `KEY_GRAVE` |
| Números 1-9 | `KEY_1` … `KEY_9` |
| F1-F12 | `KEY_F1` … `KEY_F12` |
| Espacio | `KEY_SPACE` |
| Enter | `KEY_ENTER` |

### Combinaciones recomendadas

Estas combinaciones raramente chocan con apps del sistema:

```yaml
# Instancia Claude
hotkey:
  keys: ["KEY_RIGHTCTRL", "KEY_GRAVE"]

# Instancia OpenCode (Ctrl+Shift+Alt+1)
hotkey:
  keys: ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_1"]

# Instancia Codex (Ctrl+Shift+Alt+2)
hotkey:
  keys: ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_LEFTALT", "KEY_2"]
```

O vía CLI sin editar config.yaml:
```bash
.venv/bin/python3 crowia.py --hotkey "KEY_LEFTCTRL,KEY_LEFTSHIFT,KEY_LEFTALT,KEY_1"
```

Para ver todos los nombres de tecla disponibles:
```bash
python3 -c "from evdev import ecodes; [print(k) for k in dir(ecodes) if k.startswith('KEY_')]"
```

## Servicio systemd (opcional)

```bash
cp crowia.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now crowia
```

## Giselo Web (acceso remoto vía PWA)

Servidor web con WebSocket que permite usar Giselo desde cualquier dispositivo en la red Tailscale — celular, tablet, PC remota.

### Características
- **Chat con streaming** — respuestas en tiempo real mientras Claude genera
- **Voz bidireccional** — graba desde el browser → Whisper transcribe → piper-tts responde con audio
- **Material Design 3** — UI adaptativa: navigation rail en desktop/tablet, bottom nav estilo Android en mobile
- **PWA instalable** — Chrome → "Agregar a pantalla de inicio" → queda como app nativa
- **Markdown** — respuestas renderizadas con formato (negritas, listas, código)
- **TTS sin símbolos** — piper-tts recibe texto plano, sin asteriscos ni markdown

### Requisitos en el servidor
```bash
# En la máquina que corre el servidor (VM o host)
pip install fastapi 'uvicorn[standard]' piper-tts
sudo apt install -y ffmpeg   # para convertir audio del browser a WAV
```

### Arranque
```bash
# Config mínimo (si piper-tts está en ruta diferente a la del host)
nano ~/config.server.yaml
# output:
#   tts_enabled: true
#   tts_command: ["/ruta/a/piper-tts", "--model", "/ruta/al/modelo.onnx", "--output_raw"]

python3 run_server.py --port 8181 \
  --config ~/config.server.yaml \
  --ssl-cert /ruta/cert.crt \
  --ssl-key  /ruta/cert.key
```

### HTTPS (requerido para micrófono)
```bash
# Habilitar en tailscale.com/admin → DNS → HTTPS Certificates
sudo tailscale cert <hostname>.ts.net

python3 run_server.py --port 8181 \
  --ssl-cert <hostname>.ts.net.crt \
  --ssl-key  <hostname>.ts.net.key
```

Acceso: `https://<hostname>.ts.net:8181`

### Flags de run_server.py

| Flag | Default | Descripción |
|------|---------|-------------|
| `--port` | 8080 | Puerto de escucha |
| `--host` | 0.0.0.0 | Dirección de bind |
| `--config` | config.yaml | Config a cargar |
| `--ssl-cert` | — | Certificado TLS (.crt) |
| `--ssl-key` | — | Clave privada TLS (.key) |
| `--debug` | false | Reload automático + logs verbosos |

---

## Estructura del proyecto

```
crowia/
├── crowia.py               # Entry point, pipeline principal
├── run_server.py           # Entry point del servidor web
├── config.yaml             # Configuración
├── config.local.yaml       # Generado por giselo-doctor (no committear)
├── crowia.service          # Servicio systemd
├── setup.sh                # Script de instalación
├── scripts/
│   └── giselo-doctor       # Diagnóstico de OS y generación de config.local.yaml
└── crowia/
    ├── config.py           # Carga y merge de configuración
    ├── hotkey.py           # Listener de teclado (evdev, async)
    ├── recorder.py         # Grabación de audio (arecord)
    ├── transcriber.py      # Whisper (modelo cargado una vez en memoria)
    ├── assistant.py        # Claude CLI (texto) + API (visión)
    ├── output.py           # Notificaciones + TTS piper
    ├── history.py          # Historial de conversación (JSON)
    ├── always_on.py        # Wake word + VAD (modo siempre activo)
    ├── intent.py           # Detección de intents en español
    ├── screen.py           # Captura de pantalla (spectacle/grim)
    ├── system_control.py   # Control de volumen (pactl)
    └── server/
        ├── app.py          # FastAPI + WebSocket (voz + texto + TTS)
        ├── audio.py        # Conversión WebM→WAV (ffmpeg) + piper-tts→WAV
        └── web/
            ├── index.html  # Shell PWA
            ├── app.js      # Lógica principal (chat, nav, settings)
            ├── audio.js    # MediaRecorder + Web Audio API
            ├── style.css   # Material Design 3
            ├── manifest.json
            └── sw.js       # Service worker (offline shell)
```
