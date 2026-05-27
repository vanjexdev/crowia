import logging
import os
import re
import shutil
import subprocess

from .base import Backend

log = logging.getLogger(__name__)

_SIMPLE_WORD_LIMIT = 15
_OLLAMA_MAX_HISTORY = 2   # max turns (user+assistant pairs) sent to Ollama

# App name → binary mapping for voice-launched apps
_APP_MAP: dict[str, str] = {
    # browsers
    "firefox": "firefox",
    "floorp": "floorp",
    "chrome": "chromium",
    "chromium": "chromium",
    "navegador": "floorp",
    # terminals
    "terminal": "alacritty",
    "alacritty": "alacritty",
    "konsole": "konsole",
    # editors
    "zed": "zeditor",
    "editor": "zeditor",
    "código": "zeditor",
    "vscode": "code",
    "code": "code",
    # files
    "dolphin": "dolphin",
    "archivos": "dolphin",
    "nautilus": "nautilus",
    # music/media
    "spotify": "spotify",
    "vlc": "vlc",
    # system
    "discord": "discord",
    "telegram": "telegram-desktop",
    "obsidian": "obsidian",
    "figma": "figma-linux",
}

_LAUNCH_RE = re.compile(
    r'^(?:abre?|lanza?|inicia?|ejecuta?|corre?|abre el|abre la|open|launch|start)\s+(.+)$',
    re.I,
)
_CLOSE_RE = re.compile(
    r'^(?:cierra?|mata?|termina?|cierra el|cierra la|close|kill|apaga?)\s+(.+)$',
    re.I,
)

# Patterns that indicate a complex task → route to primary backend, not Ollama
_COMPLEX_HINTS = frozenset([
    "código", "code", "debug", "error", "función", "función", "clase", "archivo",
    "script", "explica", "analiza", "refactoriza", "implementa", "programa",
    "python", "javascript", "typescript", "yaml", "json", "sql", "html", "css",
    "por qué", "cómo funciona", "qué significa",
    # System info queries — Ollama can't answer them; handled by _system_answer or primary
    "ram", "memoria", "disco", "cpu", "temperatura", "batería", "bateria",
    "ip local", "mi ip", "espacio",
])

# System queries answered instantly with a subprocess — no LLM needed
_SYSTEM_CMDS: list[tuple[list[str], str]] = [
    # (trigger keywords, shell command)
    (["hora", "time", "what time", "qué hora", "que hora"],
     "date +'Son las %H:%M del %A %d de %B de %Y'"),
    (["fecha", "qué día", "que dia", "what day", "what date", "qué fecha"],
     "date +'Hoy es %A %d de %B de %Y'"),
    (["batería", "bateria", "battery"],
     "upower -i $(upower -e | grep BAT) 2>/dev/null | grep -E 'state|percentage' | awk '{print $2}' | tr '\\n' ' '"),
    (["memoria ram", "memoria disponible", "ram disponible", "ram tengo",
      "uso de memoria", "uso de ram", "ram libre", "memoria libre",
      "cuanta ram", "cuánta ram", "cuanta memoria", "cuánta memoria",
      "memory usage", "free memory", "disponible ram"],
     "free -h | awk '/^Mem:/{print \"RAM: \" $4 \" libre de \" $2 \" totales (usado: \" $3 \")\"}'"),
    (["uso de cpu", "cpu usage", "cpu tengo", "carga del cpu", "procesador"],
     "top -bn1 | grep 'Cpu(s)' | awk '{print \"CPU: \" $2+$4 \"% en uso\"}'"),
    (["espacio en disco", "disco duro", "espacio libre", "disk space", "storage"],
     "df -h / | awk 'NR==2{print \"Disco: \" $4 \" libre de \" $2 \" (\" $5 \" usado)\"}'"),
    (["ip local", "mi ip", "dirección ip", "ip address", "what is my ip"],
     "ip route get 1 | awk '{print \"IP local: \" $7; exit}'"),
    (["temperatura", "temperatura cpu", "cpu temp", "temperature"],
     "sensors 2>/dev/null | awk '/Core 0/{print \"Temp CPU: \" $3; exit}' || echo 'sensors no disponible'"),
]


class HybridBackend(Backend):
    """
    Routes queries to the fastest available backend:
      1. Simple / short → local Ollama model (free, <1s)
      2. Complex / long  → primary backend (Claude CLI or configured fallback)

    Registry entry fields:
      ollama_model    — Ollama model for simple queries (default: qwen2.5:3b)
      ollama_url      — Ollama API base (default: http://localhost:11434/v1)
      primary_backend — backend id to use for complex queries (default: claude)
      simple_words    — word threshold to classify as simple (default: 15)
    """

    name = "Hybrid"

    def __init__(self, cfg: dict, entry: dict):
        self.name = entry.get("label", "Hybrid")
        self._ollama_model = entry.get("ollama_model", "qwen2.5:3b")
        self._ollama_url = entry.get("ollama_url", "http://localhost:11434/v1")
        self._simple_words = int(entry.get("simple_words", _SIMPLE_WORD_LIMIT))
        self._cfg = cfg
        self._entry = entry
        self._ollama: Backend | None = None
        self._primary: Backend | None = None
        self._ollama_ok: bool | None = None  # None = untested
        self._init_backends(cfg, entry)

    def _init_backends(self, cfg: dict, entry: dict) -> None:
        from .openai_compat import OpenAICompatBackend
        ollama_entry = {
            "id": "_hybrid_ollama",
            "label": f"Ollama ({self._ollama_model})",
            "model": self._ollama_model,
            "base_url": self._ollama_url,
            "api_key": "ollama",
        }
        self._ollama = OpenAICompatBackend(cfg, ollama_entry)

        primary_id = entry.get("primary_backend", "claude")
        try:
            if primary_id == "claude":
                from .claude_cli import ClaudeCliBackend
                self._primary = ClaudeCliBackend(cfg)
            elif primary_id == "opencode":
                from .opencode import OpenCodeBackend
                primary_model = entry.get("primary_model", "")
                self._primary = OpenCodeBackend(cfg, {"model": primary_model} if primary_model else None)
            elif primary_id == "gemini":
                from .gemini import GeminiBackend
                self._primary = GeminiBackend(cfg)
            else:
                from .openai_compat import OpenAICompatBackend as _OA
                self._primary = _OA(cfg, {"model": primary_id, "label": primary_id,
                                          "base_url": entry.get("primary_base_url", "")})
        except Exception as exc:
            log.warning("Hybrid: could not init primary backend '%s': %s", primary_id, exc)

    def cancel(self) -> None:
        if self._ollama:
            self._ollama.cancel()
        if self._primary:
            self._primary.cancel()

    def _is_ollama_available(self) -> bool:
        if self._ollama_ok is not None:
            return self._ollama_ok
        try:
            import urllib.request
            url = self._ollama_url.rstrip("/v1").rstrip("/") + "/api/tags"
            req = urllib.request.urlopen(url, timeout=1)
            self._ollama_ok = req.status == 200
        except Exception:
            self._ollama_ok = False
        if not self._ollama_ok:
            log.info("Hybrid: Ollama not available at %s — using primary only", self._ollama_url)
        return self._ollama_ok

    def _classify(self, text: str) -> str:
        words = text.split()
        if len(words) > self._simple_words:
            return "complex"
        text_lower = text.lower()
        if any(hint in text_lower for hint in _COMPLEX_HINTS):
            return "complex"
        return "simple"

    def _system_answer(self, text: str) -> str | None:
        """Return instant answer from OS for known system queries, or None."""
        low = text.lower()
        for keywords, cmd in _SYSTEM_CMDS:
            if any(kw in low for kw in keywords):
                try:
                    out = subprocess.check_output(cmd, shell=True, text=True, timeout=3).strip()
                    log.info("Hybrid: system_cmd answer for '%s': %s", text[:40], out)
                    return out or None
                except Exception as exc:
                    log.warning("Hybrid: system_cmd failed: %s", exc)
                    return None
        return None

    def _app_command(self, text: str) -> str | None:
        """Detect 'abre/cierra [app]' and execute via giselo-launch-app or pkill."""
        low = text.strip()
        launch_m = _LAUNCH_RE.match(low)
        if launch_m:
            app_hint = launch_m.group(1).strip().lower()
            binary = _APP_MAP.get(app_hint)
            if not binary:
                for k, v in _APP_MAP.items():
                    if k in app_hint or app_hint in k:
                        binary = v
                        break
            if binary:
                launcher = shutil.which("giselo-launch-app")
                if launcher:
                    try:
                        out = subprocess.check_output(
                            [launcher, binary], text=True, timeout=5
                        ).strip()
                        log.info("App launch: %s → %s", binary, out)
                        return out or f"Abriendo {binary}…"
                    except Exception as e:
                        log.warning("App launch failed: %s", e)
                else:
                    try:
                        subprocess.Popen([binary], start_new_session=True,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return f"Abriendo {binary}…"
                    except Exception as e:
                        return f"No pude abrir {binary}: {e}"
            return None

        close_m = _CLOSE_RE.match(low)
        if close_m:
            app_hint = close_m.group(1).strip().lower()
            binary = _APP_MAP.get(app_hint)
            if not binary:
                for k, v in _APP_MAP.items():
                    if k in app_hint or app_hint in k:
                        binary = v
                        break
            if binary:
                try:
                    subprocess.run(["pkill", "-x", binary], timeout=3)
                    return f"Cerrando {binary}."
                except Exception as e:
                    log.warning("pkill failed: %s", e)
        return None

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=120, on_chunk=None):
        # 1. Instant system answer (no LLM)
        sys_ans = self._system_answer(text)
        if sys_ans:
            if on_chunk:
                on_chunk(sys_ans)
            return sys_ans

        # 2. App launch/close command
        app_ans = self._app_command(text)
        if app_ans is not None:
            if on_chunk:
                on_chunk(app_ans)
            return app_ans

        query_type = self._classify(text)
        log.debug("Hybrid: query_type=%s words=%d", query_type, len(text.split()))

        if query_type == "simple" and self._is_ollama_available() and self._ollama:
            log.info("Hybrid: routing to Ollama (%s)", self._ollama_model)
            # Truncate history — local models choke on large contexts
            trimmed_history = (history or [])[-(_OLLAMA_MAX_HISTORY * 2):]
            result = self._ollama.ask(
                text, system_prompt, history=trimmed_history,
                image_path=image_path, file_paths=file_paths,
                timeout=timeout, on_chunk=on_chunk,
            )
            # If Ollama connection failed, mark unavailable and fall through
            if "No se pudo conectar" in result or "[crowia]" in result:
                log.warning("Hybrid: Ollama failed, marking unavailable")
                self._ollama_ok = False
            else:
                return result

        if self._primary:
            log.info("Hybrid: routing to primary backend")
            return self._primary.ask(
                text, system_prompt, history=history,
                image_path=image_path, file_paths=file_paths,
                timeout=timeout, on_chunk=on_chunk,
            )

        return "[crowia] Hybrid: no backend disponible"
