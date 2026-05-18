import logging
import os
import pathlib

from .base import Backend

log = logging.getLogger(__name__)

_BASE_URL = "https://api.moonshot.cn/v1"
_DEFAULT_MODEL = "moonshot-v1-8k"


class MoonshotBackend(Backend):
    """
    Moonshot (Kimi) API backend — OpenAI-compatible REST API.

    Registry entry fields:
      model    — moonshot-v1-8k | moonshot-v1-32k | moonshot-v1-128k (default: moonshot-v1-8k)
      api_key  — leave empty to use MOONSHOT_API_KEY env var
    """

    def __init__(self, _cfg: dict, entry: dict):
        self.name = entry.get("label", "Kimi")
        self._model = entry.get("model", _DEFAULT_MODEL)
        self._api_key = entry.get("api_key", "") or os.environ.get("MOONSHOT_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
            if not self._api_key:
                raise RuntimeError("MOONSHOT_API_KEY no configurada. Exporta la variable o agrega api_key al registry.")
            self._client = OpenAI(api_key=self._api_key, base_url=_BASE_URL)
        return self._client

    def cancel(self) -> None:
        pass  # HTTP requests don't support mid-flight cancel cleanly

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
                log.info("Moonshot response (%d chars): %s", len(accumulated), accumulated[:200])
                return accumulated
            else:
                resp = client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    timeout=timeout,
                )
                result = resp.choices[0].message.content or ""
                log.info("Moonshot response (%d chars): %s", len(result), result[:200])
                return result

        except RuntimeError as exc:
            return f"[crowia] {exc}"
        except Exception as exc:
            log.error("Moonshot error: %s", exc)
            msg = str(exc).lower()
            if "401" in msg or "unauthorized" in msg or "api key" in msg:
                return "[crowia] Moonshot API key inválida. Verifica MOONSHOT_API_KEY."
            if "rate" in msg or "429" in msg:
                return f"[crowia] rate limit Moonshot (429)"
            return f"[crowia] Error de Moonshot: {exc}"
