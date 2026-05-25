import logging
import os
import select
import shutil
import subprocess
import threading
import time

from .base import Backend

log = logging.getLogger(__name__)


class GeminiBackend(Backend):
    name = "Gemini"

    def __init__(self, cfg: dict):
        self._binary = shutil.which("gemini") or "gemini"
        self._model: str = cfg.get("gemini", {}).get("model", "")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=600, on_chunk=None):
        full = f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}\n[FIN INSTRUCCIONES]\n\n" if system_prompt else ""
        if history:
            lines = []
            for msg in history[-6:]:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            full += "\n".join(lines) + "\n\n"
        if file_paths:
            for fp in file_paths:
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    full += f"[Archivo: {fp}]\n```\n{content}\n```\n\n"
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)
        full += text

        cmd = [self._binary, "--skip-trust", "--yolo", "-p", full]
        if self._model:
            cmd = [self._binary, "--skip-trust", "--yolo", "-m", self._model, "-p", full]

        env = os.environ.copy()
        env["GEMINI_CLI_TRUST_WORKSPACE"] = "true"

        try:
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    env=env,
                    bufsize=1,
                )

            if on_chunk:
                accumulated = ""
                deadline = time.monotonic() + timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self.cancel()
                        return f"[crowia] Gemini tardó demasiado ({timeout}s)."
                    ready = select.select([self._proc.stdout], [], [], min(remaining, 1.0))
                    if ready[0]:
                        line = self._proc.stdout.readline()
                        if not line:
                            break
                        accumulated += line
                        on_chunk(accumulated.strip())
                    elif self._proc.poll() is not None:
                        break
                self._proc.stdout.close()
                self._proc.wait(timeout=10)
                stdout = accumulated
            else:
                stdout, _ = self._proc.communicate(timeout=timeout)

            rc = self._proc.returncode
            with self._lock:
                self._proc = None

            if rc == -9:
                return ""
            if rc != 0:
                log.error("Gemini error rc=%d", rc)
                return f"[crowia] Error de Gemini (rc={rc})"

            response = stdout.strip()
            log.info("Gemini response (%d chars): %s", len(response), response[:200])
            return response

        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] Gemini tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] gemini no encontrado. Instala con: npm i -g @google/gemini-cli"
        finally:
            with self._lock:
                self._proc = None
