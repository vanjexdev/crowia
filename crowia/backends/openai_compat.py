import json
import logging
import os
import pathlib
import re
import subprocess

from .base import Backend

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434/v1"
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# Only giselo-* tools and git are allowed — same whitelist as Claude CLI
_ALLOWED_PREFIXES = ("giselo-", "git ")

_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": (
                "Ejecuta un comando del sistema. Solo se permiten comandos giselo-* y git. "
                "Úsalo para controlar el browser (giselo-browser), lanzar apps "
                "(giselo-launch-app), buscar en Google (giselo-google), "
                "manipular archivos (giselo-pick), o correr git."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Comando completo a ejecutar, e.g. 'giselo-browser navigate https://example.com'"
                    }
                },
                "required": ["command"],
            },
        },
    }
]


class OpenAICompatBackend(Backend):
    """
    Generic OpenAI-compatible backend (Ollama, LM Studio, OpenRouter, etc.).

    Registry entry fields:
      base_url      — API base URL (default: http://localhost:11434/v1)
      model         — required, e.g. deepseek-coder-v2:16b
      api_key       — optional, defaults to "ollama"
      label         — display name
      enable_tools  — bool, enables function calling loop (default: false)
    """

    def __init__(self, _cfg: dict, entry: dict):
        self.name = entry.get("label", entry.get("model", "Ollama"))
        self._model = entry["model"]
        self._base_url = entry.get("base_url", _DEFAULT_BASE_URL).rstrip("/")
        self._api_key = entry.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "ollama")
        self._enable_tools = bool(entry.get("enable_tools", False))
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def cancel(self) -> None:
        pass

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=120, on_chunk=None):
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if history:
            for msg in history[-10:]:
                role = msg.get("role", "user")
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                if content.strip():
                    messages.append({"role": role, "content": content})

        user_content = ""
        if file_paths:
            for fp in file_paths:
                fp = pathlib.Path(fp)
                if fp.suffix.lower() in _IMG_EXTS:
                    log.warning("Ollama vision not supported via text path, skipping %s", fp)
                    continue
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
                    user_content += f"[Directorio: {fp}]\n```\n" + "\n".join(lines) + "\n```\n\n"
                else:
                    try:
                        user_content += f"[Archivo: {fp}]\n```\n{fp.read_text(encoding='utf-8', errors='replace')}\n```\n\n"
                    except Exception as exc:
                        log.warning("Cannot read %s: %s", fp, exc)

        user_content += text
        messages.append({"role": "user", "content": user_content})

        if self._enable_tools:
            return self._ask_with_tools(messages, timeout, on_chunk)

        try:
            client = self._get_client()

            if on_chunk:
                accumulated = ""
                with client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    timeout=timeout,
                ) as stream:
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            accumulated += delta
                            on_chunk(accumulated)
                log.info("%s response (%d chars): %s", self.name, len(accumulated), accumulated[:200])
                return accumulated
            else:
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    timeout=timeout,
                )
                result = resp.choices[0].message.content or ""
                log.info("%s response (%d chars): %s", self.name, len(result), result[:200])
                return result

        except RuntimeError as exc:
            return f"[crowia] {exc}"
        except Exception as exc:
            log.error("%s error: %s", self.name, exc)
            msg = str(exc).lower()
            if "connection" in msg or "refused" in msg:
                return f"[crowia] No se pudo conectar a Ollama en {self._base_url}. ¿Está corriendo?"
            if "rate" in msg or "429" in msg:
                return f"[crowia] rate limit {self.name} (429)"
            return f"[crowia] Error de {self.name}: {exc}"

    # ------------------------------------------------------------------ tools

    def _execute_tool(self, command: str) -> str:
        """Execute a whitelisted command and return stdout+stderr."""
        cmd = command.strip()
        if not any(cmd.startswith(p) for p in _ALLOWED_PREFIXES):
            log.warning("Tool blocked (not in whitelist): %s", cmd)
            return f"[blocked] Solo se permiten comandos giselo-* y git. Comando rechazado: {cmd}"
        log.info("Executing tool: %s", cmd)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            output = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if result.returncode != 0:
                return f"[rc={result.returncode}] {err or output}"
            return output or "(sin salida)"
        except subprocess.TimeoutExpired:
            return "[timeout] El comando tardó más de 30s"
        except Exception as exc:
            return f"[error] {exc}"

    def _ask_with_tools(self, messages: list, timeout: int, on_chunk) -> str:
        """Tool-calling loop: call → execute tools → call again (max 5 rounds)."""
        client = self._get_client()
        accumulated = ""

        for _round in range(5):
            try:
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    tools=_TOOL_SCHEMAS,
                    tool_choice="auto",
                    timeout=timeout,
                )
            except Exception as exc:
                log.error("%s tool-call error: %s", self.name, exc)
                return f"[crowia] Error de {self.name}: {exc}"

            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []

            if not tool_calls:
                result = msg.content or accumulated
                if on_chunk and result:
                    on_chunk(result)
                log.info("%s tool-loop done (%d rounds)", self.name, _round + 1)
                return result

            # Append assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            })

            # Execute each tool and feed results back
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                    command = args.get("command", "")
                except (json.JSONDecodeError, KeyError):
                    command = ""
                tool_result = self._execute_tool(command) if command else "[error] no command"
                log.info("Tool result for '%s': %s", command, tool_result[:200])
                if on_chunk:
                    on_chunk(f"[tool] {command}\n→ {tool_result}\n\n")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

        return accumulated or "[crowia] Tool loop limit reached"
