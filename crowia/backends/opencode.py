import json
import logging
import os
import pathlib
import select
import shutil
import subprocess
import threading
import time

from .base import Backend

log = logging.getLogger(__name__)


class OpenCodeBackend(Backend):
    name = "OpenCode"

    def __init__(self, cfg: dict):
        self._binary = shutil.which("opencode") or "opencode"
        self._model = cfg.get("opencode", {}).get("model", "opencode/big-pickle")
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
            "--format", "json",
            "--dangerously-skip-permissions",
            full_text,
        ]

        env = os.environ.copy()

        try:
            with self._lock:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

            if on_chunk:
                accumulated = ""
                raw_lines = []
                deadline = time.monotonic() + timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self.cancel()
                        return f"[crowia] OpenCode tardó demasiado ({timeout}s)."
                    ready = select.select([self._proc.stdout], [], [], min(remaining, 1.0))
                    if ready[0]:
                        line = self._proc.stdout.readline()
                        if not line:
                            break
                        raw_lines.append(line)
                        stripped = line.strip()
                        if stripped:
                            try:
                                event = json.loads(stripped)
                                if event.get("type") == "text":
                                    text = event.get("part", {}).get("text", "")
                                    if text:
                                        accumulated += text
                                        on_chunk(accumulated)
                            except json.JSONDecodeError:
                                pass
                    elif self._proc.poll() is not None:
                        break
                self._proc.stdout.close()
                stderr = self._proc.stderr.read()
                self._proc.wait(timeout=10)
                stdout = "".join(raw_lines)
            else:
                stdout, stderr = self._proc.communicate(timeout=timeout)

            rc = self._proc.returncode
            with self._lock:
                self._proc = None
        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] OpenCode tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] opencode no encontrado."
        finally:
            with self._lock:
                self._proc = None

        if rc == -9:
            return ""
        if rc != 0:
            log.error("OpenCode error (rc=%d): %s", rc, stderr[:300])
            return f"[crowia] Error de OpenCode (rc={rc})"

        response = self._parse_json_output(stdout)
        if not response:
            log.error("OpenCode empty response. stderr: %s", stderr[:300])
            return "[crowia] OpenCode no devolvió respuesta."
        log.info("OpenCode response (%d chars): %s", len(response), response[:200])
        return response

    def _parse_json_output(self, output: str) -> str:
        parts = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "text":
                    text = event.get("part", {}).get("text", "")
                    if text:
                        parts.append(text)
            except json.JSONDecodeError:
                continue
        return "".join(parts).strip()
