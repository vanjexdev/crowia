import pathlib
from abc import ABC, abstractmethod


class Backend(ABC):
    name: str = "unknown"

    @abstractmethod
    def ask(
        self,
        text: str,
        system_prompt: str,
        history: list[dict] | None = None,
        image_path: pathlib.Path | None = None,
        file_paths: list[pathlib.Path] | None = None,
        timeout: int = 120,
    ) -> str: ...
