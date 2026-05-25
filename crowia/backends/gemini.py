import json
import logging
import os
import select
import shutil
import subprocess
import threading
import time

import requests

from .base import Backend

log = logging.getLogger(__name__)

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiBackend(Backend):
    name = "Gemini"

    def __init__(self, cfg: dict, instance_cfg: dict | None = None):
        inst = instance_cfg or {}
        self._binary = shutil.which("gemini") or "gemini"
        self._model: str = inst.get("model", "") or cfg.get("gemini", {}).get("model", _DEFAULT_MODEL)
        self._api_key_override = inst.get("api_key", "")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()

    # ------------------------------------------------------------------ API

    def _ask_api(self, text, system_prompt, history, file_paths, timeout, on_chunk) -> str:
        model = self._model or _DEFAULT_MODEL
        url = f"{_GEMINI_API_BASE}/{model}:{'streamGenerateContent' if on_chunk else 'generateContent'}?key={self._api_key_override}"

        contents = []
        if history:
            for msg in history[-10:]:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                contents.append({"role": role, "parts": [{"text": content}]})

        user_parts = []
        if file_paths:
            for fp in file_paths:
                try:
                    c = fp.read_text(encoding="utf-8", errors="replace")
                    user_parts.append({"text": f"[Archivo: {fp}]\n```\n{c}\n```\n"})
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)
        user_parts.append({"text": text})
        contents.append({"role": "user", "parts": user_parts})

        payload: dict = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        log.info("Gemini API request (model=%s, stream=%s)", model, bool(on_chunk))
        try:
            if on_chunk:
                accumulated = ""
                with requests.post(url, json=payload, timeout=timeout, stream=True) as resp:
                    if resp.status_code != 200:
                        log.error("Gemini API error %d: %s", resp.status_code, resp.text[:300])
                        return f"[crowia] Gemini API error ({resp.status_code})"
                    for line in resp.iter_lines():
                        if self._cancelled:
                            return ""
                        if not line:
                            continue
                        raw = line.decode("utf-8") if isinstance(line, bytes) else line
                        if raw.startswith("data:"):
                            raw = raw[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(raw)
                            for cand in chunk.get("candidates", []):
                                for part in cand.get("content", {}).get("parts", []):
                                    delta = part.get("text", "")
                                    if delta:
                                        accumulated += delta
                                        on_chunk(accumulated)
                        except json.JSONDecodeError:
                            pass
                return accumulated.strip()
            else:
                resp = requests.post(url, json=payload, timeout=timeout)
                if resp.status_code != 200:
                    log.error("Gemini API error %d: %s", resp.status_code, resp.text[:300])
                    return f"[crowia] Gemini API error ({resp.status_code})"
                data = resp.json()
                result = ""
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        result += part.get("text", "")
                return result.strip()
        except requests.Timeout:
            return f"[crowia] Gemini tardó demasiado ({timeout}s)."
        except Exception as exc:
            log.error("Gemini API exception: %s", exc)
            return f"[crowia] Error Gemini API: {exc}"

    # ------------------------------------------------------------------ CLI

    def _ask_cli(self, text, system_prompt, history, file_paths, timeout, on_chunk) -> str:
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

        log.info("Gemini CLI request (model=%s)", self._model)
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
                    if self._cancelled:
                        return ""
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
                log.error("Gemini CLI error rc=%d", rc)
                return f"[crowia] Error de Gemini CLI (rc={rc})"

            return stdout.strip()
        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] Gemini tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] gemini no encontrado. Instala con: npm i -g @google/gemini-cli"
        finally:
            with self._lock:
                self._proc = None

    # ------------------------------------------------------------------ ask

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=600, on_chunk=None):
        self._cancelled = False
        if self._api_key_override:
            log.info("Gemini: using direct API (key configured)")
            return self._ask_api(text, system_prompt, history, file_paths, timeout, on_chunk)
        else:
            log.info("Gemini: using CLI (no instance key)")
            return self._ask_cli(text, system_prompt, history, file_paths, timeout, on_chunk)
