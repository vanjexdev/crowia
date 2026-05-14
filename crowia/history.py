import json
import logging
import pathlib

log = logging.getLogger(__name__)


class ConversationHistory:
    def __init__(self, path: pathlib.Path, max_turns: int = 10):
        self.path = path
        self.max_turns = max_turns
        self._messages: list[dict] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._messages = data.get("messages", [])
            except Exception as e:
                log.warning("Failed to load history: %s", e)
                self._messages = []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"messages": self._messages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add(self, role: str, content):
        self._messages.append({"role": role, "content": content})
        limit = self.max_turns * 2
        if len(self._messages) > limit:
            self._messages = self._messages[-limit:]
        self._save()

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def clear(self):
        self._messages = []
        self._save()
        log.info("History cleared")
