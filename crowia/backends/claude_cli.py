import json
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

    def __init__(self, cfg: dict, instance_cfg: dict | None = None):
        inst = instance_cfg or {}
        self._binary = cfg["claude"]["binary"] or shutil.which("claude") or ""
        self._model = inst.get("model", "") or cfg["claude"].get("model", "claude-haiku-4-5")
        self._api_key_override = inst.get("api_key", "")
        tools = cfg["claude"].get("allowed_tools",
            "WebSearch Bash(git *) Bash(zeditor*) Bash(alacritty*) Bash(giselo-ask*) Bash(giselo-askpass*) Bash(giselo-pick*) Bash(giselo-browser*) Bash(giselo-google*) Bash(giselo-remind*) Read Edit Write")
        self._allowed_tools = tools
        self._disallowed_tools = cfg["claude"].get("disallowed_tools", "Bash(git push*)")
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def cancel(self) -> None:
        with self._lock:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
                log.info("Claude CLI process killed by cancel()")

    def ask(self, text, system_prompt, history=None, image_path=None, file_paths=None, timeout=120, on_chunk=None):
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
                if fp.is_dir():
                    lines = []
                    for item in sorted(fp.rglob("*")):
                        if any(p.startswith(".") for p in item.parts):
                            continue
                        try:
                            rel = item.relative_to(fp)
                            indent = "  " * (len(rel.parts) - 1)
                            lines.append(f"{indent}{item.name}{'/' if item.is_dir() else ''}")
                        except Exception:
                            pass
                        if len(lines) >= 200:
                            lines.append("  …(truncado)")
                            break
                    full_text += f"[Directorio: {fp}]\n```\n" + "\n".join(lines) + "\n```\n\n"
                else:
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
            "--add-dir", str(pathlib.Path.home()),
            "--allowedTools", self._allowed_tools,
            "--disallowedTools", self._disallowed_tools,
            "--output-format", "stream-json",
            "--verbose",
        ]

        env = os.environ.copy()
        if self._api_key_override:
            env["ANTHROPIC_API_KEY"] = self._api_key_override
        else:
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
                    text=True, env=env, bufsize=0,
                )
            log.debug("Claude CLI started (pid=%d)", self._proc.pid)

            accumulated = ""
            stderr_lines: list[str] = []

            # Drain stderr in background to prevent pipe deadlock
            def _drain_stderr():
                try:
                    for line in self._proc.stderr:
                        stderr_lines.append(line)
                except Exception:
                    pass
            stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
            stderr_thread.start()

            if on_chunk:
                # stream-json: each stdout line is a JSON event.
                # Use buffer_size=1 so readline() blocks at each byte — if the CLI
                # flushes events progressively, we receive them one by one.
                import io as _io
                _stdout = _io.TextIOWrapper(
                    _io.BufferedReader(self._proc.stdout.buffer, buffer_size=1),
                    encoding="utf-8", errors="replace",
                )
                for raw in _stdout:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        log.debug("non-json stdout: %s", raw[:80])
                        continue

                    ev_type = event.get("type", "")

                    if ev_type == "assistant":
                        msg = event.get("message", {})
                        for block in msg.get("content", []):
                            if not isinstance(block, dict):
                                continue
                            btype = block.get("type", "")
                            if btype == "text":
                                text = block.get("text", "")
                                if not text:
                                    continue
                                # stream-json sends accumulated text per event
                                if text.startswith(accumulated):
                                    accumulated = text  # accumulated format
                                else:
                                    accumulated += text  # delta format
                                on_chunk(accumulated)
                            elif btype == "text_delta":
                                delta = block.get("text", "")
                                if delta:
                                    accumulated += delta
                                    on_chunk(accumulated)

                    elif ev_type == "result":
                        result = event.get("result", "")
                        if result:
                            accumulated = result

            else:
                stdout_data, _ = self._proc.communicate(timeout=timeout)
                # stdout may be stream-json too; extract result event if so
                for raw in stdout_data.splitlines():
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        event = json.loads(raw)
                        if event.get("type") == "result":
                            accumulated = event.get("result", accumulated)
                    except json.JSONDecodeError:
                        accumulated += raw + "\n"

            stderr_thread.join(timeout=5)
            stderr_data = "".join(stderr_lines)
            self._proc.wait(timeout=10)

            rc = self._proc.returncode
            log.debug("Claude CLI finished (rc=%d, out_len=%d)", rc, len(accumulated))
        except subprocess.TimeoutExpired:
            self.cancel()
            return f"[crowia] Claude tardó demasiado ({timeout}s)."
        except FileNotFoundError:
            return "[crowia] claude CLI no encontrado."
        finally:
            with self._lock:
                self._proc = None

        # -9 = SIGKILL (our cancel), -15 or 143 = SIGTERM (external kill / cancel)
        if rc in (-9, -15, 143):
            return ""

        if rc != 0:
            log.error("CLI error (rc=%d) stderr: %s | stdout: %s", rc, stderr_data[:300], accumulated[:300])
            return f"[crowia] Error del CLI (rc={rc})"

        response = accumulated.strip()
        log.info("Claude response (%d chars): %s", len(response), response[:200])
        return response
