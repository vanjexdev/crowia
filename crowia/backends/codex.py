import logging
import os
import pathlib
import shutil
import subprocess
import tempfile

from .base import Backend

log = logging.getLogger(__name__)


class CodexBackend(Backend):
    name = "Codex"

    def __init__(self, cfg: dict):
        self._binary = shutil.which("codex") or "codex"
        self._model = cfg.get("codex", {}).get("model", "")

    def ask(self, text, system_prompt, history=None, image_path=None, file_paths=None, timeout=120):
        full_text = ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            full_text += "\n".join(lines) + "\n\n"

        if file_paths:
            for fp in file_paths:
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    full_text += f"[File: {fp}]\n```\n{content}\n```\n\n"
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)

        full_text += text

        out_file = pathlib.Path(tempfile.mktemp(suffix=".txt", dir="/tmp/crowia"))
        cmd = ["codex", "exec", "--output-last-message", str(out_file), full_text]
        if self._model:
            cmd += ["--model", self._model]

        env = os.environ.copy()

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if out_file.exists():
                response = out_file.read_text(encoding="utf-8").strip()
                out_file.unlink(missing_ok=True)
                log.info("Codex response (%d chars): %s", len(response), response[:200])
                return response
            if result.returncode != 0:
                log.error("Codex error (rc=%d): %s", result.returncode, result.stderr[:300])
                return f"[crowia] Error de Codex (rc={result.returncode})"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return f"[crowia] Codex tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] codex CLI no encontrado. Instala con: npm i -g @openai/codex"
