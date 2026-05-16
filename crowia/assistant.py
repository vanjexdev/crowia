import base64
import logging
import os
import pathlib

import anthropic

from .backends.base import Backend
from .backends.claude_cli import ClaudeCliBackend
from .backends.codex import CodexBackend
from .backends.opencode import OpenCodeBackend
from . import skills as skills_mod

log = logging.getLogger(__name__)

BACKENDS = {
    "claude": ClaudeCliBackend,
    "codex": CodexBackend,
    "opencode": OpenCodeBackend,
}


class Assistant:
    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._base_prompt = cfg["claude"]["system_prompt"]
        self._memory_text: str = ""
        self._enabled_skills: list[str] = list(cfg.get("skills", {}).get("enabled", []))
        self._available_skills: list[str] = skills_mod.available(cfg)
        self.system_prompt = self._build_prompt()
        self.timeout = cfg["claude"]["timeout_seconds"]
        self._cfg_api_key = cfg["claude"].get("api_key", "")
        self._api_client: anthropic.Anthropic | None = None
        self._vision_model = cfg["claude"].get("model", "claude-sonnet-4-6")

        default_backend = cfg.get("backend", "claude")
        self._backend: Backend = self._build(default_backend)
        log.info("Backend activo: %s", self._backend.name)

    def _build(self, name: str) -> Backend:
        cls = BACKENDS.get(name.lower())
        if cls is None:
            log.warning("Backend '%s' desconocido, usando claude.", name)
            cls = ClaudeCliBackend
        return cls(self._cfg)

    def set_memory_context(self, memory_text: str) -> None:
        self._memory_text = memory_text
        self.system_prompt = self._build_prompt()

    def _build_prompt(self) -> str:
        parts = []
        if self._memory_text:
            parts.append(self._memory_text)
        parts.append(self._base_prompt)
        skill_text = skills_mod.load_list(self._cfg, self._enabled_skills)
        if skill_text:
            parts.append(skill_text)
        return "\n\n".join(parts)

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
            return f"Skill '{name}' no encontrada. Disponibles: {', '.join(self._available_skills)}"
        if match in self._enabled_skills:
            return f"Skill '{match}' ya estaba activa."
        self._enabled_skills.append(match)
        self.system_prompt = self._build_prompt()
        log.info("Skill activada: %s", match)
        return f"Skill '{match}' activada."

    def disable_skill(self, name: str) -> str:
        match = self._find_skill(name)
        if not match:
            return f"Skill '{name}' no encontrada. Disponibles: {', '.join(self._available_skills)}"
        if match not in self._enabled_skills:
            return f"Skill '{match}' ya estaba desactivada."
        self._enabled_skills.remove(match)
        self.system_prompt = self._build_prompt()
        log.info("Skill desactivada: %s", match)
        return f"Skill '{match}' desactivada."

    def list_skills(self) -> str:
        enabled = ", ".join(self._enabled_skills) or "ninguna"
        disabled = ", ".join(s for s in self._available_skills if s not in self._enabled_skills) or "ninguna"
        return f"Skills activas: {enabled}. Desactivadas: {disabled}."

    def cancel(self) -> None:
        self._backend.cancel()

    def switch_backend(self, name: str) -> str:
        name = name.lower().strip()
        if name not in BACKENDS:
            return f"Backend '{name}' no disponible. Opciones: {', '.join(BACKENDS)}"
        self._backend = self._build(name)
        log.info("Backend cambiado a: %s", self._backend.name)
        return f"Ahora uso {self._backend.name}."

    @property
    def current_backend_name(self) -> str:
        return self._backend.name

    def ask(
        self,
        text: str,
        history: list[dict] | None = None,
        image_path: pathlib.Path | None = None,
        file_paths: list[pathlib.Path] | None = None,
        on_chunk=None,
    ) -> str:
        if image_path and image_path.exists():
            return self._ask_vision_api(text, history, image_path, file_paths)
        return self._backend.ask(
            text=text,
            system_prompt=self.system_prompt,
            history=history,
            file_paths=file_paths,
            timeout=self.timeout,
            on_chunk=on_chunk,
        )

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
        if file_paths:
            for fp in file_paths:
                try:
                    file_text = fp.read_text(encoding="utf-8", errors="replace")
                    content.append({"type": "text", "text": f"[Archivo: {fp}]\n```\n{file_text}\n```\n"})
                except Exception as e:
                    log.warning("Cannot read %s: %s", fp, e)
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
        except anthropic.APIError as e:
            log.error("API error: %s", e)
            return f"[crowia] Error de API: {e}"
