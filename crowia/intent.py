import logging
import pathlib
import re

log = logging.getLogger(__name__)

_SCREENSHOT_KW = [
    "mira la pantalla", "qué ves", "que ves",
    "captura de pantalla", "screenshot", "qué hay en pantalla",
    "que hay en pantalla", "muéstrame la pantalla", "muestrame la pantalla",
    "analiza la pantalla", "qué está en pantalla", "que esta en pantalla",
    "mira esto en pantalla", "describe la pantalla",
    # English
    "look at the screen", "look at screen", "what do you see",
    "what's on screen", "what is on screen", "show me the screen",
    "describe the screen", "analyze the screen",
]

_VOLUME_UP_KW = [
    "sube el volumen", "aumenta el volumen", "más volumen", "mas volumen",
    "sube el audio", "aumenta el audio", "sube el sonido",
    # English
    "volume up", "increase volume", "louder", "raise volume", "turn up",
]

_VOLUME_DOWN_KW = [
    "baja el volumen", "reduce el volumen", "menos volumen",
    "baja el audio", "reduce el audio", "baja el sonido",
    # English
    "volume down", "decrease volume", "quieter", "lower volume", "turn down",
]

_VOLUME_MUTE_KW = [
    "silencia", "mutea", "sin sonido", "apaga el sonido",
    "silencia el audio", "quita el sonido",
    # English
    "mute audio", "mute sound", "no sound", "silence audio",
]

def _sw(names: list[str]) -> list[str]:
    verbs = ["usa", "uses", "utiliza", "utilices", "cambia a", "cambiar a"]
    out = []
    for v in verbs:
        for n in names:
            out.append(f"{v} {n}")
            out.append(f"{v} el {n}")
    return out


_BACKEND_SWITCH = {
    "claude": _sw(["claude", "cloud", "clouding", "cloude", "clod", "clau"]),
    "codex": _sw(["codex"]),
    "opencode": _sw(["opencode", "open code", "openco", "openko"]),
    "qwen25-3b": _sw(["qwen", "qwen2", "qwen 2.5", "qwen2.5", "qwen local"]),
    "deepseek-coder": _sw(["deepseek", "deep seek", "deepseek coder", "deepseek-coder"]),
    "gemma4": _sw(["gemma", "gemma4", "gemma 4"]),
}

_CLEAR_HISTORY_KW = [
    "borra el historial", "limpia el historial", "olvida la conversación",
    "olvida la conversacion", "nueva conversación", "nueva conversacion",
    "reinicia la conversación", "reinicia la conversacion",
    # English
    "clear history", "clear the history", "forget the conversation",
    "forget conversation", "new conversation", "reset conversation",
]

_MEDIA_PAUSE_KW = [
    "pausa la música", "pausa el video", "pausa la canción", "pausa el audio",
    "pausar la música", "pausar el video",
    "para la música", "para la canción", "para el audio",
    "detén la música", "detener música", "detener el audio",
    "stop music",
    # English
    "pause music", "pause the music", "pause video", "pause audio",
]

_MEDIA_PLAY_KW = [
    "reanuda la música", "reanuda el audio", "reanuda el video",
    "continúa la música", "continua la música",
    "reproduce la música", "pon la música", "pon música",
    "sigue la música", "sigue reproduciendo",
    # English
    "play music", "resume music", "resume the music", "play the music",
]

_MEDIA_NEXT_KW = [
    "siguiente canción", "siguiente pista", "siguiente track",
    "salta la canción", "próxima canción", "proxima cancion",
    "pon la siguiente", "cambia la canción",
    # English
    "next song", "next track", "skip song", "skip the song",
]

_MEDIA_PREV_KW = [
    "canción anterior", "pista anterior", "track anterior",
    "vuelve a la anterior", "regresa la canción", "cancion anterior",
    # English
    "previous song", "previous track", "go back", "last song",
]

_TTS_MUTE_KW = [
    "silencia las respuestas", "desactiva el audio", "desactiva la voz",
    "silencia la voz", "sin audio", "modo silencioso", "no hables",
    "apaga el audio", "apaga la voz",
    # English
    "mute responses", "disable voice", "silent mode", "stop talking",
    "turn off voice", "disable audio",
]
_TTS_UNMUTE_KW = [
    "activa el audio", "activa la voz",
    "activa las respuestas de voz", "pon el audio", "pon la voz",
    "vuelve a hablar", "habla de nuevo", "quiero escucharte",
    # English
    "enable voice", "enable audio", "turn on voice", "start talking",
    "unmute", "unmute voice",
]

_SKILL_DISABLE_RE = re.compile(
    r'(?:desactiva|deshabilita|apaga|quita|desactiva)\s+(?:la\s+)?skill\s+([\w-]+)',
    re.IGNORECASE,
)
_SKILL_ENABLE_RE = re.compile(
    r'(?:activa|habilita|enciende|agrega|añade)\s+(?:la\s+)?skill\s+([\w-]+)',
    re.IGNORECASE,
)
_SKILL_LIST_KW = [
    "qué skills", "que skills", "lista de skills", "skills activas",
    "skills disponibles", "cuáles skills", "cuales skills",
]

_VOLUME_PCT = re.compile(r'volumen\s+al\s+(\d{1,3})\s*%?', re.IGNORECASE)
_FILE_PATH = re.compile(r'(?:~/|/)[^\s,;:]+\.\w+')


class Intents:
    def __init__(self):
        self.screenshot: bool = False
        self.files: list[pathlib.Path] = []
        self.volume = None  # "up" | "down" | "mute" | int
        self.media: str | None = None  # "pause" | "play" | "next" | "prev"
        self.clear_history: bool = False
        self.switch_backend: str | None = None  # "claude" | "codex" | "opencode"
        self.skill_enable: str | None = None
        self.skill_disable: str | None = None
        self.skill_list: bool = False
        self.tts_mute: bool = False
        self.tts_unmute: bool = False


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

    if any(kw in low for kw in _MEDIA_PAUSE_KW):
        result.media = "pause"
    elif any(kw in low for kw in _MEDIA_PLAY_KW):
        result.media = "play"
    elif any(kw in low for kw in _MEDIA_NEXT_KW):
        result.media = "next"
    elif any(kw in low for kw in _MEDIA_PREV_KW):
        result.media = "prev"

    if any(kw in low for kw in _TTS_MUTE_KW):
        result.tts_mute = True
    elif any(kw in low for kw in _TTS_UNMUTE_KW):
        result.tts_unmute = True

    m = _SKILL_DISABLE_RE.search(low)
    if m:
        result.skill_disable = m.group(1)
    else:
        m = _SKILL_ENABLE_RE.search(low)
        if m:
            result.skill_enable = m.group(1)

    if any(kw in low for kw in _SKILL_LIST_KW):
        result.skill_list = True

    for raw in _FILE_PATH.findall(text):
        p = pathlib.Path(raw.replace("~", str(pathlib.Path.home())))
        if p.exists() and p.is_file():
            result.files.append(p)

    return result
