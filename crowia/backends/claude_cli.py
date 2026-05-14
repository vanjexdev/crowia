import logging
import os
import pathlib
import shutil
import subprocess
import threading

from .base import Backend

log = logging.getLogger(__name__)


class ClaudeCliBackend(Backend):
    name = "Claude"

    def __init__(self, cfg: dict):
        self._binary = cfg["claude"]["binary"] or shutil.which("claude") or ""
        self._model = cfg["claude"].get("model", "claude-haiku-4-5")
        tools = cfg["claude"].get("allowed_tools",
            "WebSearch Bash(git *) Bash(zeditor*) Bash(alacritty*) Bash(firefox*) Bash(giselo-ask*) Bash(giselo-askpass*) Bash(giselo-pick*) Bash(giselo-browser*) Bash(giselo-google*) Read Edit Write")
        self._allowed_tools = tools
        self._disallowed_tools = cfg["claude"].get("disallowed_tools", "Bash(git push*)")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
                log.info("Claude CLI process killed by cancel()")

    def ask(self, text, system_prompt, history=None, image_path=None, file_paths=None, timeout=120):
        full_text = ""

        if history:
            lines = []
            for msg in history[-10:]:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            if lines:
                full_text += "Historial:\n" + "\n".join(lines) + "\n\n"

        if file_paths:
            for fp in file_paths:
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    full_text += f"[Archivo: {fp}]\n```\n{content}\n```\n\n"
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)

        full_text += text

        cmd = [
            self._binary, "-p", full_text,
            "--model", self._model,
            "--system-prompt", system_prompt,
            "--no-session-persistence",
            "--dangerously-skip-permissions",
            "--add-dir", "/home/jesusu",
            "--add-dir", str(pathlib.Path.home()),
            "--allowedTools", self._allowed_tools,
            "--disallowedTools", self._disallowed_tools,
        ]

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)
        uid = os.getuid()
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        env.setdefault("DISPLAY", ":0")
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
        env["SUDO_ASKPASS"] = str(pathlib.Path.home() / ".local/bin/giselo-askpass")

        log.debug("Launching claude CLI (prompt_len=%d, sysprompt_len=%d)",
                  len(full_text), len(system_prompt))
        try:
            with self._lock:
                self._proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, env=env,
                )
            log.debug("Claude CLI started (pid=%d), waiting...", self._proc.pid)
            stdout, stderr = self._proc.communicate(timeout=timeout)
            log.debug("Claude CLI finished (rc=%d, stdout_len=%d)", self._proc.returncode, len(stdout))
            rc = self._proc.returncode
        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] Claude tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] claude CLI no encontrado."
        finally:
            with self._lock:
                self._proc = None

        if rc not in (0, -9):  # -9 = killed by cancel
            log.error("CLI error (rc=%d) stderr: %s | stdout: %s", rc, stderr[:300], stdout[:300])
            return f"[crowia] Error del CLI (rc={rc})"

        if rc == -9:
            return ""

        response = stdout.strip()
        log.info("Claude response (%d chars): %s", len(response), response[:200])
        return response
