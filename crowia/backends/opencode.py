import logging
import os
import pathlib
import re
import shutil
import subprocess

from .base import Backend

log = logging.getLogger(__name__)

_ANSI = re.compile(r'\x1b\[[0-9;]*m')


class OpenCodeBackend(Backend):
    name = "OpenCode"

    def __init__(self, cfg: dict):
        self._binary = shutil.which("opencode") or "opencode"
        self._model = cfg.get("opencode", {}).get("model", "opencode/big-pickle")

    def ask(self, text, system_prompt, history=None, image_path=None, file_paths=None, timeout=120):
        full_text = ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            full_text += "\n".join(lines) + "\n\n"

        if file_paths:
            for fp in file_paths:
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    full_text += f"[Archivo: {fp}]\n```\n{content}\n```\n\n"
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)

        full_text += text

        cmd = [
            self._binary, "run",
            "--model", self._model,
            "--dangerously-skip-permissions",
            full_text,
        ]

        env = os.environ.copy()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return f"[crowia] OpenCode tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] opencode no encontrado."

        if result.returncode != 0:
            log.error("OpenCode error (rc=%d): %s", result.returncode, result.stderr[:300])
            return f"[crowia] Error de OpenCode (rc={result.returncode})"

        # Strip ANSI and header lines ("> build · model")
        response = self._clean_output(result.stdout)
        log.info("OpenCode response (%d chars): %s", len(response), response[:200])
        return response

    def _clean_output(self, output: str) -> str:
        lines = []
        for line in output.splitlines():
            clean = _ANSI.sub("", line).strip()
            if not clean:
                continue
            if clean.startswith(">"):  # header line "> build · model"
                continue
            lines.append(clean)
        return "\n".join(lines).strip() or "[crowia] OpenCode no devolvió respuesta."
