import logging
import os
import pathlib

from .base import Backend

log = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434/v1"
_IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


class OpenAICompatBackend(Backend):
    """
    Generic OpenAI-compatible backend (Ollama, LM Studio, etc.).

    Registry entry fields:
      base_url   — API base URL (default: http://localhost:11434/v1)
      model      — required, e.g. deepseek-coder-v2:16b
      api_key    — optional, defaults to "ollama" (ignored by local servers)
      label      — display name
    """

    def __init__(self, _cfg: dict, entry: dict):
        self.name = entry.get("label", entry.get("model", "Ollama"))
        self._model = entry["model"]
        self._base_url = entry.get("base_url", _DEFAULT_BASE_URL).rstrip("/")
        self._api_key = entry.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "ollama")
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
