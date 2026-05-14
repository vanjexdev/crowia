# Pepito — Asistente de Voz Local

Asistente de voz para Linux (KDE Plasma / Wayland) que escucha comandos, los transcribe con Whisper, y responde usando Claude.

## Stack

- **Python 3.14** + venv
- **faster-whisper** — transcripción local (modelo `small`, CPU/INT8)
- **Claude CLI** — respuestas vía suscripción (OAuth, sin costo de API)
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
Di "oye pepito", "hey pepito" o "pepito" para activar. El siguiente utterance va a Claude.

## Comandos de voz

| Di esto | Resultado |
|---------|-----------|
| "oye pepito / hey pepito" | activa en modo always-on |
| "mira la pantalla" | captura pantalla → Claude analiza |
| "sube / baja el volumen" | pactl ±10% |
| "volumen al 50%" | pactl al 50% |
| "silencia" | mute toggle |
| "abre Firefox" | lanza firefox |
| "abre la terminal" | lanza alacritty |
| "abre Zed" | lanza zeditor |
| "borra el historial" | limpia conversación |
| "/ruta/a/archivo.py" | lee el archivo → Claude comenta |

## Capacidades de Claude (herramientas habilitadas)

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
  wake_phrases: ["oye pepito", "hey pepito", "pepito"]
  silence_duration_ms: 800    # ms de silencio para cortar utterance
  vad_aggressiveness: 2       # 0-3

claude:
  model: "claude-sonnet-4-6"

output:
  tts_enabled: true
  tts_command: ["piper-tts", "--model", "~/.local/share/piper/es_ES-davefx-medium.onnx", "--output_raw"]
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
