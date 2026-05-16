import json
import logging
import pathlib
from typing import Callable

log = logging.getLogger(__name__)

_DEFAULT_DIR = pathlib.Path.home() / ".config" / "crowia"


class MemoryManager:
    def __init__(self, config_dir: pathlib.Path = _DEFAULT_DIR):
        self._dir = config_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._summary_path = self._dir / "session_summary.json"
        self._long_term_path = self._dir / "long_term.txt"

    def build_memory_prompt(self) -> str:
        parts = []
        lt = self._load_long_term()
        if lt:
            parts.append(f"[Memoria acumulada]\n{lt}")
        prev = self._load_session_summary()
        if prev:
            parts.append(f"[Sesión anterior]\n{prev}")
        if not parts:
            return ""
        return "## Memoria de sesiones previas\n" + "\n\n".join(parts)

    def save_session(self, messages: list[dict], ask_fn: Callable[[str], str]) -> None:
        if not messages:
            return

        conv_lines = []
        for m in messages:
            role = m.get("role", "?")
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") for c in content if isinstance(c, dict)
                )
            conv_lines.append(f"{role}: {str(content)[:400]}")
        conv_text = "\n".join(conv_lines)

        summary_prompt = (
            "Resume esta conversación en ~100 palabras en el mismo idioma que se usó. "
            "Incluye qué pidió el usuario, decisiones clave y contexto importante:\n\n"
            + conv_text
        )
        try:
            summary = ask_fn(summary_prompt)
        except Exception as e:
            log.warning("Memory summary LLM call failed: %s", e)
            summary = conv_text[:600]

        self._save_session_summary(summary)

        old_lt = self._load_long_term()
        if old_lt:
            lt_prompt = (
                "Combina estas memorias en ~50 palabras en el mismo idioma. "
                "Conserva solo hechos duraderos útiles para sesiones futuras:\n\n"
                f"Memoria acumulada anterior:\n{old_lt}\n\nSesión nueva:\n{summary}"
            )
            try:
                new_lt = ask_fn(lt_prompt)
            except Exception as e:
                log.warning("Long-term memory update failed: %s", e)
                new_lt = " ".join(summary.split()[:60])
        else:
            new_lt = " ".join(summary.split()[:60])

        self._save_long_term(new_lt)
        log.info("Memory saved: session_summary + long_term updated")

    def _load_session_summary(self) -> str:
        if self._summary_path.exists():
            try:
                data = json.loads(self._summary_path.read_text(encoding="utf-8"))
                return data.get("summary", "")
            except Exception:
                return ""
        return ""

    def _save_session_summary(self, summary: str) -> None:
        self._summary_path.write_text(
            json.dumps({"summary": summary}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_long_term(self) -> str:
        if self._long_term_path.exists():
            try:
                return self._long_term_path.read_text(encoding="utf-8").strip()
            except Exception:
                return ""
        return ""

    def _save_long_term(self, text: str) -> None:
        self._long_term_path.write_text(text, encoding="utf-8")
