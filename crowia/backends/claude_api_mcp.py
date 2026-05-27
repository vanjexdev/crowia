import base64
import logging
import os
import pathlib
import threading

from .base import Backend

log = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-opus-4-7"
_MCP_BETA = "mcp-client-2025-04-04"
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_EXT_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
             ".webp": "image/webp", ".png": "image/png", ".bmp": "image/png"}


def _detect_mime(path: pathlib.Path) -> str:
    """Detect image MIME type from magic bytes, fall back to extension."""
    try:
        header = path.read_bytes()[:16]
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if header[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
        if header[:4] in (b"GIF8", b"GIF9"):
            return "image/gif"
    except Exception:
        pass
    return _EXT_MIME.get(path.suffix.lower(), "image/png")


class ClaudeApiMcpBackend(Backend):
    """
    Claude API backend with MCP server support (beta).

    Registry entry fields:
      model          — Claude model (default: claude-opus-4-7)
      api_key        — leave empty to use ANTHROPIC_API_KEY env var
      max_tokens     — default 4096
      mcp_servers    — list of MCP server objects:
                       [{name, url, auth_header, auth_value, auth_value_env}]
                       auth_value_env: name of env var that holds the token
    """

    def __init__(self, _cfg: dict, entry: dict):
        self.name = entry.get("label", "Claude+MCP")
        self._model = entry.get("model", _DEFAULT_MODEL)
        self._max_tokens = entry.get("max_tokens", 4096)
        self._api_key = entry.get("api_key", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        self._mcp_servers_cfg: list[dict] = entry.get("mcp_servers", [])
        self._client = None
        self._cancel = threading.Event()

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY no configurada. Exporta la variable o agrega api_key al registry.")
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _build_mcp_tools(self) -> list[dict]:
        tools = []
        for srv in self._mcp_servers_cfg:
            headers: dict[str, str] = {}
            header_name = srv.get("auth_header", "")
            header_val = srv.get("auth_value", "") or os.environ.get(srv.get("auth_value_env", ""), "")
            if header_name and header_val:
                headers[header_name] = header_val
            tools.append({
                "type": "mcp",
                "server_label": srv.get("name", "mcp"),
                "server_url": srv["url"],
                **({"headers": headers} if headers else {}),
                "require_approval": "never",
            })
        return tools

    def cancel(self) -> None:
        self._cancel.set()

    def ask(self, text, system_prompt, history=None, image_path=None,
            file_paths=None, timeout=120, on_chunk=None):
        self._cancel.clear()

        messages: list[dict] = []
        if history:
            for msg in history[-10:]:
                role = msg.get("role", "user")
                content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                if content.strip():
                    messages.append({"role": role, "content": content})

        user_parts: list[dict] = []

        # Attach screenshot or image_path
        if image_path:
            img_p = pathlib.Path(image_path)
            if img_p.exists():
                user_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": _detect_mime(img_p),
                               "data": base64.b64encode(img_p.read_bytes()).decode()},
                })

        # Attach extra file_paths
        if file_paths:
            for fp in file_paths:
                fp = pathlib.Path(fp)
                ext = fp.suffix.lower()
                if ext in _IMAGE_EXTS:
                    try:
                        user_parts.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": _detect_mime(fp),
                                       "data": base64.b64encode(fp.read_bytes()).decode()},
                        })
                    except Exception as exc:
                        log.warning("Cannot read image %s: %s", fp, exc)
                elif fp.is_dir():
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
                    user_parts.append({"type": "text",
                                       "text": f"[Directorio: {fp}]\n```\n" + "\n".join(lines) + "\n```\n\n"})
                else:
                    try:
                        user_parts.append({"type": "text",
                                           "text": f"[Archivo: {fp}]\n```\n{fp.read_text(encoding='utf-8', errors='replace')}\n```\n\n"})
                    except Exception as exc:
                        log.warning("Cannot read %s: %s", fp, exc)

        user_parts.append({"type": "text", "text": text})
        # Simplify content if only one text block
        user_content = user_parts if len(user_parts) > 1 else text
        messages.append({"role": "user", "content": user_content})

        tools = self._build_mcp_tools()
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "betas": [_MCP_BETA],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools

        try:
            client = self._get_client()
            response = client.beta.messages.create(**kwargs)

            if self._cancel.is_set():
                return ""

            result = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

            if on_chunk and result:
                on_chunk(result)

            log.info("Claude+MCP response (%d chars): %s", len(result), result[:200])
            return result

        except RuntimeError as exc:
            return f"[crowia] {exc}"
        except Exception as exc:
            log.error("Claude API MCP error: %s", exc)
            msg_lower = str(exc).lower()
            if "401" in msg_lower or "unauthorized" in msg_lower or "api_key" in msg_lower:
                return "[crowia] ANTHROPIC_API_KEY inválida o no configurada."
            if "rate" in msg_lower or "429" in msg_lower:
                return "[crowia] rate limit Claude API (429)"
            return f"[crowia] Error de Claude API MCP: {exc}"
