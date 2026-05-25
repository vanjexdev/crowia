import pathlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from crowia.semantic_memory import SemanticMemory as ConversationHistory
from crowia.config import load as load_config

_cfg = load_config()
_histories: dict[str, ConversationHistory] = {}
_active_name: str = _cfg.get("backend", "claude")


def _get_or_create(name: str) -> ConversationHistory:
    if name not in _histories:
        base = pathlib.Path(_cfg["history"]["path"])
        # Each instance gets its own history file: history_claude.json etc.
        path = base.parent / f"{base.stem}_{name}{base.suffix}"
        _histories[name] = ConversationHistory(
            path=path,
            max_turns=_cfg["history"].get("max_turns", 10),
        )
    return _histories[name]


def set_active(name: str) -> None:
    global _active_name
    _active_name = name


def _hist() -> ConversationHistory:
    return _get_or_create(_active_name)


def add_user(text: str) -> None:
    _hist().add("user", text)


def add_assistant(text: str) -> None:
    _hist().add("assistant", text)


def get_messages() -> list[dict]:
    return _hist().get_messages()


def search(query: str, limit: int = 5) -> list[dict]:
    return _hist().search(query, limit)


def clear() -> None:
    _hist().clear()
