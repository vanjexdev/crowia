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

```bash
# Dependencias del sistema
sudo pacman -S python-evdev python-yaml alsa-utils libnotify espeak-ng spectacle piper-tts-bin

# Venv y faster-whisper
python3 -m venv --system-site-packages .venv
.venv/bin/pip install faster-whisper anthropic sounddevice webrtcvad-wheels numpy

# Modelo de voz español
mkdir -p ~/.local/share/piper
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx"
curl -L -o ~/.local/share/piper/es_ES-davefx-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json"

# Agregar usuario al grupo input (requiere re-login)
sudo usermod -aG input $USER
```

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

## Estructura del proyecto

```
crowia/
├── crowia.py           # Entry point, pipeline principal
├── config.yaml         # Configuración
├── crowia.service      # Servicio systemd
├── setup.sh            # Script de instalación
└── crowia/
    ├── config.py       # Carga y merge de configuración
    ├── hotkey.py       # Listener de teclado (evdev, async)
    ├── recorder.py     # Grabación de audio (arecord)
    ├── transcriber.py  # Whisper (modelo cargado una vez en memoria)
    ├── assistant.py    # Claude CLI (texto) + API (visión)
    ├── output.py       # Notificaciones + TTS piper
    ├── history.py      # Historial de conversación (JSON)
    ├── always_on.py    # Wake word + VAD (modo siempre activo)
    ├── intent.py       # Detección de intents en español
    ├── screen.py       # Captura de pantalla (spectacle/grim)
    └── system_control.py  # Control de volumen (pactl)
```
