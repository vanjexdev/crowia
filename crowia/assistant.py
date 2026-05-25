import base64
import logging
import os
import pathlib

import anthropic

from .backends.base import Backend
from .backends.claude_api_mcp import ClaudeApiMcpBackend
from .backends.claude_cli import ClaudeCliBackend
from .backends.codex import CodexBackend
from .backends.generic_cli import GenericCliBackend
from .backends.moonshot import MoonshotBackend
from .backends.openai_compat import OpenAICompatBackend
from .backends.gemini import GeminiBackend
from .backends.opencode import OpenCodeBackend
from .registry import BackendRegistry
from . import skills as skills_mod
from . import i18n as _i18n

log = logging.getLogger(__name__)

# Kept for switch_backend("name") backward compat when id not in registry
_BUILTIN: dict[str, type] = {
    "claude":    ClaudeCliBackend,
    "codex":     CodexBackend,
    "gemini":    GeminiBackend,
    "opencode":  OpenCodeBackend,
}

_FAILOVER_TRIGGERS = frozenset([
    "rate limit", "rate_limit", "ratelimit",
    "too many requests", "overloaded",
    "quota exceeded", "usage limit",
    "429", "503",
])


class Assistant:
    def __init__(self, cfg: dict, instance_config: dict | None = None):
        self._cfg = cfg
        self._instance_cfg = instance_config or {}
        self._base_prompt = cfg["claude"]["system_prompt"]
        self._memory_text: str = ""
        self._enabled_skills: list[str] = list(cfg.get("skills", {}).get("enabled", []))
        self._available_skills: list[str] = skills_mod.available(cfg)
        self.system_prompt = self._build_prompt()
        self.timeout = cfg["claude"]["timeout_seconds"]
        self._cfg_api_key = cfg["claude"].get("api_key", "")
        self._api_client: anthropic.Anthropic | None = None
        self._vision_model = cfg["claude"].get("model", "claude-sonnet-4-6")

        self._registry = BackendRegistry()
        self._active_id: str = cfg.get("backend", "claude")
        self._backend: Backend = self._build_by_id(self._active_id)
        self._failover_tried: set[str] = set()
        log.info("Backend activo: %s", self._backend.name)
        self._language: str = "es"

    # ------------------------------------------------------------------ build

    def _build_by_id(self, backend_id: str) -> Backend:
        entry = self._registry.get(backend_id)
        if entry:
            merged = {**entry, **{k: v for k, v in self._instance_cfg.items() if v}}
            return self._build_entry(merged)
        cls = _BUILTIN.get(backend_id.lower())
        if cls:
            return cls(self._cfg, self._instance_cfg)
        log.warning("Backend '%s' desconocido, usando claude.", backend_id)
        return ClaudeCliBackend(self._cfg, self._instance_cfg)

    def _build_entry(self, entry: dict) -> Backend:
        btype = entry.get("type", "generic_cli")
        if btype == "claude_cli":
            return ClaudeCliBackend(self._cfg, self._instance_cfg)
        if btype == "codex":
            return CodexBackend(self._cfg)
        if btype == "gemini":
            return GeminiBackend(self._cfg, self._instance_cfg)
        if btype == "opencode":
            return OpenCodeBackend(self._cfg)
        if btype == "moonshot":
            return MoonshotBackend(self._cfg, entry)
        if btype == "claude_api_mcp":
            return ClaudeApiMcpBackend(self._cfg, entry)
        if btype == "openai_compat":
            return OpenAICompatBackend(self._cfg, entry)
        return GenericCliBackend(self._cfg, entry)

    # ------------------------------------------------------------------ prompt

    def set_memory_context(self, memory_text: str) -> None:
        self._memory_text = memory_text
        self.system_prompt = self._build_prompt()

    def set_language(self, lang: str) -> None:
        self._language = lang
        _i18n.set_lang(lang)
        self.system_prompt = self._build_prompt()

    def _build_prompt(self) -> str:
        parts = [_i18n.t("lang_instruction")]
        if self._memory_text:
            parts.append(self._memory_text)
        parts.append(self._base_prompt)
        skill_text = skills_mod.load_list(self._cfg, self._enabled_skills)
        if skill_text:
            parts.append(skill_text)
        return "\n\n".join(parts)

    # ------------------------------------------------------------------ skills

    def _find_skill(self, name: str) -> str | None:
        name_low = name.lower()
        for s in self._available_skills:
            if s.lower() == name_low:
                return s
        for s in self._available_skills:
            if name_low in s.lower() or s.lower() in name_low:
                return s
        return None

    def enable_skill(self, name: str) -> str:
        match = self._find_skill(name)
        if not match:
            return _i18n.t("skill_not_found", name=name, list=", ".join(self._available_skills))
        if match in self._enabled_skills:
            return _i18n.t("skill_already_on", name=match)
        self._enabled_skills.append(match)
        self.system_prompt = self._build_prompt()
        return _i18n.t("skill_enabled", name=match)

    def disable_skill(self, name: str) -> str:
        match = self._find_skill(name)
        if not match:
            return _i18n.t("skill_not_found", name=name, list=", ".join(self._available_skills))
        if match not in self._enabled_skills:
            return _i18n.t("skill_already_off", name=match)
        self._enabled_skills.remove(match)
        self.system_prompt = self._build_prompt()
        return _i18n.t("skill_disabled", name=match)

    def list_skills(self) -> str:
        none_str = _i18n.t("skills_none")
        enabled = ", ".join(self._enabled_skills) or none_str
        disabled = ", ".join(s for s in self._available_skills if s not in self._enabled_skills) or none_str
        return _i18n.t("skills_list", enabled=enabled, disabled=disabled)

    # ------------------------------------------------------------------ control

    def cancel(self) -> None:
        self._backend.cancel()

    def switch_backend(self, name: str) -> str:
        name = name.lower().strip()
        entry = self._registry.get(name)
        if entry is None and name not in _BUILTIN:
            available = ", ".join(self._registry.ids())
            return _i18n.t("backend_not_found", name=name, list=available)
        self._active_id = name
        self._backend = self._build_by_id(name)
        self._failover_tried.clear()
        log.info("Backend cambiado a: %s", self._backend.name)
        return _i18n.t("backend_switched", name=self._backend.name)

    @property
    def current_backend_name(self) -> str:
        return self._backend.name

    @property
    def registry(self) -> BackendRegistry:
        return self._registry

    # ------------------------------------------------------------------ failover

    def _is_rate_limit(self, response: str) -> bool:
        r = response.lower()
        return any(p in r for p in _FAILOVER_TRIGGERS)

    def _failover_ask(self, text, history, image_path, file_paths, on_chunk) -> str:
        self._failover_tried.add(self._active_id)
        candidates = [
            e for e in self._registry.enabled_sorted()
            if e["id"] not in self._failover_tried
        ]
        if not candidates:
            return _i18n.t("all_rate_limited")

        next_entry = candidates[0]
        old_name = self._backend.name
        self._active_id = next_entry["id"]
        self._backend = self._build_entry(next_entry)
        log.warning("Failover automático: %s → %s", old_name, self._backend.name)

        response = self._backend.ask(
            text=text,
            system_prompt=self.system_prompt,
            history=history,
            file_paths=file_paths,
            timeout=self.timeout,
            on_chunk=on_chunk,
        )

        if self._is_rate_limit(response):
            return self._failover_ask(text, history, image_path, file_paths, on_chunk)

        return _i18n.t("failover_prefix", old=old_name, new=self._backend.name) + "\n\n" + response

    # ------------------------------------------------------------------ ask

    def ask(
        self,
        text: str,
        history: list[dict] | None = None,
        image_path: pathlib.Path | None = None,
        file_paths: list[pathlib.Path] | None = None,
        on_chunk=None,
    ) -> str:
        # Promote image files from file_paths to vision API path
        _IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        if not image_path and file_paths:
            img_files = [fp for fp in file_paths if pathlib.Path(fp).suffix.lower() in _IMG_EXTS]
            text_files = [fp for fp in file_paths if pathlib.Path(fp).suffix.lower() not in _IMG_EXTS]
            if img_files:
                image_path = pathlib.Path(img_files[0])
                file_paths = (img_files[1:] + text_files) or None

        if image_path and image_path.exists():
            return self._ask_vision_api(text, history, image_path, file_paths)

        response = self._backend.ask(
            text=text,
            system_prompt=self.system_prompt,
            history=history,
            file_paths=file_paths,
            timeout=self.timeout,
            on_chunk=on_chunk,
        )

        if self._is_rate_limit(response):
            return self._failover_ask(text, history, image_path, file_paths, on_chunk)

        self._failover_tried.clear()
        return response

    # ------------------------------------------------------------------ vision

    def _client(self) -> anthropic.Anthropic:
        if self._api_client is None:
            api_key = self._cfg_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self._api_client = anthropic.Anthropic(api_key=api_key)
        return self._api_client

    def _ask_vision_api(self, text, history, image_path, file_paths):
        content: list[dict] = []
        img_data = base64.standard_b64encode(image_path.read_bytes()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_data},
        })
        _IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        _IMG_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                     ".webp": "image/webp"}
        if file_paths:
            for fp in file_paths:
                fp = pathlib.Path(fp)
                ext = fp.suffix.lower()
                if ext in _IMG_EXTS:
                    try:
                        mime = _IMG_MIME.get(ext, "image/png")
                        img2 = base64.standard_b64encode(fp.read_bytes()).decode()
                        content.append({"type": "image",
                                        "source": {"type": "base64", "media_type": mime, "data": img2}})
                    except Exception as exc:
                        log.warning("Cannot read image %s: %s", fp, exc)
                else:
                    try:
                        file_text = fp.read_text(encoding="utf-8", errors="replace")
                        content.append({"type": "text", "text": f"[Archivo: {fp}]\n```\n{file_text}\n```\n"})
                    except Exception as exc:
                        log.warning("Cannot read %s: %s", fp, exc)
        content.append({"type": "text", "text": text})
        messages = list(history or []) + [{"role": "user", "content": content}]
        try:
            response = self._client().messages.create(
                model=self._vision_model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                timeout=self.timeout,
            )
            result = response.content[0].text
            log.info("Vision API response (%d chars): %s", len(result), result[:200])
            return result
        except anthropic.APITimeoutError:
            return f"[crowia] Claude tardó demasiado ({self.timeout}s)."
        except anthropic.APIError as exc:
            log.error("API error: %s", exc)
            return f"[crowia] Error de API: {exc}"
