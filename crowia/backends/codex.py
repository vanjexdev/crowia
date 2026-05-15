import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading

from .base import Backend

log = logging.getLogger(__name__)


class CodexBackend(Backend):
    name = "Codex"

    def __init__(self, cfg: dict):
        self._binary = shutil.which("codex") or "codex"
        self._model = cfg.get("codex", {}).get("model", "")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()

    def ask(self, text, system_prompt, history=None, image_path=None, file_paths=None, timeout=120, on_chunk=None):
        full_text = f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}\n[FIN INSTRUCCIONES]\n\n" if system_prompt else ""
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
            with self._lock:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            stdout, stderr = self._proc.communicate(timeout=timeout)
            rc = self._proc.returncode
            with self._lock:
                self._proc = None
            if rc == -9:
                return ""
            if out_file.exists():
                response = out_file.read_text(encoding="utf-8").strip()
                out_file.unlink(missing_ok=True)
                log.info("Codex response (%d chars): %s", len(response), response[:200])
                if on_chunk: on_chunk(response)
                return response
            if rc != 0:
                log.error("Codex error (rc=%d): %s", rc, stderr[:300])
                return f"[crowia] Error de Codex (rc={rc})"
            response = stdout.strip()
            if on_chunk: on_chunk(response)
            return response
        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] Codex tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] codex CLI no encontrado. Instala con: npm i -g @openai/codex"
