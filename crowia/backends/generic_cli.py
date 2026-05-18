import logging
import os
import select
import shutil
import subprocess
import threading
import time

from .base import Backend

log = logging.getLogger(__name__)


class GenericCliBackend(Backend):
    """
    Generic subprocess backend for any CLI that accepts a text prompt.

    Registry entry fields:
      binary      — command name or full path
      args        — list of fixed args inserted before the prompt (default [])
      input_mode  — "arg" (prompt as last arg) | "stdin" (prompt via stdin)
      label       — display name
    """

    def __init__(self, _cfg: dict, entry: dict):
        self.name = entry.get("label", entry.get("id", "CLI"))
        binary = entry.get("binary", entry.get("id", ""))
        self._binary = shutil.which(binary) or binary
        self._args: list[str] = [str(a) for a in entry.get("args", [])]
        self._input_mode: str = entry.get("input_mode", "arg")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=120, on_chunk=None):
        full = f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}\n[FIN INSTRUCCIONES]\n\n" if system_prompt else ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "User" if msg["role"] == "user" else "Assistant"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            full += "\n".join(lines) + "\n\n"
        if file_paths:
            for fp in file_paths:
                try:
                    full += f"[File: {fp}]\n```\n{fp.read_text(encoding='utf-8', errors='replace')}\n```\n\n"
                except Exception as exc:
                    log.warning("Cannot read %s: %s", fp, exc)
        full += text

        cmd = [self._binary] + self._args
        pipe_stdin = None
        stdin_data = None
        if self._input_mode == "stdin":
            pipe_stdin = subprocess.PIPE
            stdin_data = full
        else:
            cmd.append(full)

        try:
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=pipe_stdin,
                    text=True,
                    env=os.environ.copy(),
                    bufsize=1,
                )
            if stdin_data:
                self._proc.stdin.write(stdin_data)
                self._proc.stdin.close()

            if on_chunk:
                live = ""
                deadline = time.monotonic() + timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self.cancel()
                        return f"[crowia] {self.name} tardó demasiado ({timeout}s)."
                    ready = select.select([self._proc.stdout], [], [], min(remaining, 1.0))
                    if ready[0]:
                        line = self._proc.stdout.readline()
                        if not line:
                            break
                        live += line
                        on_chunk(live.strip())
                    elif self._proc.poll() is not None:
                        break
                self._proc.stdout.close()
                stderr = self._proc.stderr.read()
                self._proc.wait(timeout=10)
                stdout = live
            else:
                stdout, stderr = self._proc.communicate(timeout=timeout)

            rc = self._proc.returncode
            with self._lock:
                self._proc = None

            if rc == -9:
                return ""
            if rc != 0:
                log.error("%s error rc=%d: %s", self.name, rc, stderr[:300])
                return f"[crowia] Error de {self.name} (rc={rc})"

            response = stdout.strip()
            log.info("%s response (%d chars): %s", self.name, len(response), response[:200])
            return response

        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] {self.name} tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return f"[crowia] {self.name} no encontrado. Verifica que '{self._binary}' esté instalado."
        finally:
            with self._lock:
                self._proc = None
