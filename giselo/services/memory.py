import pathlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from crowia.history import ConversationHistory
from crowia.config import load as load_config

_cfg  = load_config()
_hist = ConversationHistory(
    path=pathlib.Path(_cfg["history"]["path"]),
    max_turns=_cfg["history"].get("max_turns", 10),
)


def add_user(text: str) -> None:
    _hist.add("user", text)


def add_assistant(text: str) -> None:
    _hist.add("assistant", text)


def get_messages() -> list[dict]:
    return _hist.get_messages()


def clear() -> None:
    _hist.clear()
