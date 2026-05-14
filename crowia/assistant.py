import base64
import logging
import os
import pathlib
import shutil
import subprocess

import anthropic

log = logging.getLogger(__name__)


class Assistant:
    def __init__(self, cfg: dict):
        self.system_prompt = cfg["claude"]["system_prompt"]
        self.timeout = cfg["claude"]["timeout_seconds"]
        self.model = cfg["claude"].get("model", "claude-sonnet-4-6")
        self._binary = cfg["claude"]["binary"]
        self._cfg_api_key = cfg["claude"].get("api_key", "")
        self._api_client: anthropic.Anthropic | None = None

    def _client(self) -> anthropic.Anthropic:
        if self._api_client is None:
            api_key = self._cfg_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self._api_client = anthropic.Anthropic(api_key=api_key)
        return self._api_client

    def ask(
        self,
        text: str,
        history: list[dict] | None = None,
        image_path: pathlib.Path | None = None,
        file_paths: list[pathlib.Path] | None = None,
    ) -> str:
        if image_path and image_path.exists():
            return self._ask_api(text, history, image_path, file_paths)
        return self._ask_cli(text, history, file_paths)

    def _ask_cli(
        self,
        text: str,
        history: list[dict] | None,
        file_paths: list[pathlib.Path] | None,
    ) -> str:
        full_text = ""

        if history:
            lines = []
            for msg in history[-10:]:
                role = "Usuario" if msg["role"] == "user" else "Asistente"
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                lines.append(f"{role}: {content}")
            if lines:
                full_text += "Historial de conversación:\n" + "\n".join(lines) + "\n\n"

        if file_paths:
            for fp in file_paths:
                try:
                    content = fp.read_text(encoding="utf-8", errors="replace")
                    full_text += f"[Archivo: {fp}]\n```\n{content}\n```\n\n"
                except Exception as e:
                    log.warning("Cannot read file %s: %s", fp, e)

        full_text += text

        binary = self._binary or shutil.which("claude") or ""
        if not binary:
            return "[crowia] claude CLI no encontrado."

        cmd = [
            binary, "-p", full_text,
            "--system-prompt", self.system_prompt,
            "--no-session-persistence",
            "--dangerously-skip-permissions",
            "--add-dir", "/home/jesusu",
            "--add-dir", str(pathlib.Path.home()),
            "--allowedTools", "WebSearch Bash(git *) Bash(zeditor*) Bash(alacritty*) Bash(firefox*) Read Edit Write",
            "--disallowedTools", "Bash(git push*)",
        ]

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)  # fuerza OAuth (suscripción), no API key
        uid = os.getuid()
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        env.setdefault("DISPLAY", ":0")
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return f"[crowia] Claude tardó demasiado ({self.timeout}s)."
        except FileNotFoundError:
            return f"[crowia] claude CLI no encontrado en: {binary}"

        if result.returncode != 0:
            log.error("CLI error (rc=%d) stderr: %s | stdout: %s",
                      result.returncode, result.stderr[:300], result.stdout[:300])
            return f"[crowia] Error del CLI (rc={result.returncode})"

        response = result.stdout.strip()
        log.info("CLI response (%d chars): %s", len(response), response[:200])
        return response

    def _ask_api(
        self,
        text: str,
        history: list[dict] | None,
        image_path: pathlib.Path,
        file_paths: list[pathlib.Path] | None,
    ) -> str:
        content: list[dict] = []

        img_data = base64.standard_b64encode(image_path.read_bytes()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_data},
        })
        log.debug("Attached screenshot: %s", image_path)

        if file_paths:
            for fp in file_paths:
                try:
                    file_text = fp.read_text(encoding="utf-8", errors="replace")
                    content.append({
                        "type": "text",
                        "text": f"[Archivo: {fp}]\n```\n{file_text}\n```\n",
                    })
                except Exception as e:
                    log.warning("Cannot read file %s: %s", fp, e)

        content.append({"type": "text", "text": text})
        messages = list(history or []) + [{"role": "user", "content": content}]

        try:
            response = self._client().messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                timeout=self.timeout,
            )
            result = response.content[0].text
            log.info("API response (%d chars): %s", len(result), result[:200])
            return result
        except anthropic.APITimeoutError:
            return f"[crowia] Claude tardó demasiado ({self.timeout}s)."
        except anthropic.APIError as e:
            log.error("API error: %s", e)
            return f"[crowia] Error de API: {e}"
