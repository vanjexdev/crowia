import logging
import pathlib

import yaml

log = logging.getLogger(__name__)

_CONFIG_DIR = pathlib.Path.home() / ".config" / "crowia"
DEFAULT_PATH = _CONFIG_DIR / "backends.yaml"

_DEFAULTS = [
    {"id": "claude",    "type": "claude_cli", "label": "Claude CLI", "enabled": True,  "priority": 1},
    {"id": "codex",     "type": "codex",      "label": "Codex",      "enabled": True,  "priority": 3},
    {"id": "opencode",  "type": "opencode",   "label": "OpenCode",   "enabled": True,  "priority": 4,
     "model": "opencode/qwen3.6-plus-free"},
]


class BackendRegistry:
    def __init__(self, path: pathlib.Path = DEFAULT_PATH):
        self._path = path
        self._entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._entries = [dict(e) for e in _DEFAULTS]
            self._save()
            return
        try:
            data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
            self._entries = data.get("backends", [dict(e) for e in _DEFAULTS])
        except Exception as exc:
            log.warning("Registry load failed (%s): using defaults", exc)
            self._entries = [dict(e) for e in _DEFAULTS]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.dump({"backends": self._entries}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def all(self) -> list[dict]:
        return [dict(e) for e in self._entries]

    def enabled_sorted(self) -> list[dict]:
        return sorted(
            [dict(e) for e in self._entries if e.get("enabled", True)],
            key=lambda e: e.get("priority", 99),
        )

    def get(self, backend_id: str) -> dict | None:
        for e in self._entries:
            if e["id"] == backend_id:
                return dict(e)
        return None

    def add(self, entry: dict) -> None:
        if any(e["id"] == entry["id"] for e in self._entries):
            raise ValueError(f"Backend '{entry['id']}' ya existe.")
        entry.setdefault("enabled", True)
        entry.setdefault("priority", max((e.get("priority", 0) for e in self._entries), default=0) + 1)
        self._entries.append(entry)
        self._save()
        log.info("Registry: added '%s'", entry["id"])

    def update(self, backend_id: str, fields: dict) -> bool:
        for e in self._entries:
            if e["id"] == backend_id:
                e.update(fields)
                self._save()
                return True
        return False

    def remove(self, backend_id: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e["id"] != backend_id]
        changed = len(self._entries) < before
        if changed:
            self._save()
        return changed

    def ids(self) -> list[str]:
        return [e["id"] for e in self._entries]
