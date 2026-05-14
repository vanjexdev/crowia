import logging
import pathlib
import re

log = logging.getLogger(__name__)

_SCREENSHOT_KW = [
    "mira la pantalla", "mira la pantalla", "qué ves", "que ves",
    "captura de pantalla", "screenshot", "qué hay en pantalla",
    "que hay en pantalla", "muéstrame la pantalla", "muestrame la pantalla",
    "analiza la pantalla", "qué está en pantalla", "que esta en pantalla",
    "mira esto en pantalla", "describe la pantalla",
]

_VOLUME_UP_KW = [
    "sube el volumen", "aumenta el volumen", "más volumen", "mas volumen",
    "sube el audio", "aumenta el audio", "sube el sonido",
]

_VOLUME_DOWN_KW = [
    "baja el volumen", "reduce el volumen", "menos volumen",
    "baja el audio", "reduce el audio", "baja el sonido",
]

_VOLUME_MUTE_KW = [
    "silencia", "mutea", "sin sonido", "apaga el sonido",
    "silencia el audio", "quita el sonido",
]

_BACKEND_SWITCH = {
    "claude": [
        "usa claude", "cambia a claude", "usa el claude",
        # Whisper mis-transcriptions of "Claude" in Spanish context
        "usa cloud", "usa clouding", "usa cloude", "usa clod", "usa clau",
        "cambia a cloud", "cambia a clouding", "cambia a cloude",
        "usa el cloud", "usa el clouding",
    ],
    "codex": ["usa codex", "cambia a codex", "usa el codex"],
    "opencode": [
        "usa opencode", "cambia a opencode", "usa el opencode",
        "usa open code", "cambia a open code", "usa el open code",
        "usa openco", "usa openko",
    ],
}

_CLEAR_HISTORY_KW = [
    "borra el historial", "limpia el historial", "olvida la conversación",
    "olvida la conversacion", "nueva conversación", "nueva conversacion",
    "reinicia la conversación", "reinicia la conversacion",
]

_VOLUME_PCT = re.compile(r'volumen\s+al\s+(\d{1,3})\s*%?', re.IGNORECASE)
_FILE_PATH = re.compile(r'(?:~/|/)[^\s,;:]+\.\w+')


class Intents:
    def __init__(self):
        self.screenshot: bool = False
        self.files: list[pathlib.Path] = []
        self.volume = None  # "up" | "down" | "mute" | int
        self.clear_history: bool = False
        self.switch_backend: str | None = None  # "claude" | "codex" | "opencode"


def detect(text: str) -> Intents:
    low = text.lower()
    result = Intents()

    for kw in _SCREENSHOT_KW:
        if kw in low:
            result.screenshot = True
            break

    for backend, phrases in _BACKEND_SWITCH.items():
        if any(p in low for p in phrases):
            result.switch_backend = backend
            break

    for kw in _CLEAR_HISTORY_KW:
        if kw in low:
            result.clear_history = True
            break

    m = _VOLUME_PCT.search(low)
    if m:
        result.volume = int(m.group(1))
    elif any(kw in low for kw in _VOLUME_UP_KW):
        result.volume = "up"
    elif any(kw in low for kw in _VOLUME_DOWN_KW):
        result.volume = "down"
    elif any(kw in low for kw in _VOLUME_MUTE_KW):
        result.volume = "mute"

    for raw in _FILE_PATH.findall(text):
        p = pathlib.Path(raw.replace("~", str(pathlib.Path.home())))
        if p.exists() and p.is_file():
            result.files.append(p)

    return result
