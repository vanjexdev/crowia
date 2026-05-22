from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppState:
    active_instance: str = "claude"
    active_drawer: Optional[str] = None   # "memoria"|"historial"|"sistema"|"cola"|"notif"|None
    camera_active: bool = False
    voice_active: bool = False
    giselo_state: str = "idle"             # idle|thinking|speaking|success|error
    accent: str = "#88c93a"
    breakpoint: str = "MIN"               # MIN|COMPACT|MEDIUM|LARGE
    messages: list = field(default_factory=list)
    mem_tokens: int = 0
    version: str = "v0.5.0"
    build: str = "phase-a"

    INSTANCES: tuple = ("opencode", "claude", "codex")
    DRAWERS: tuple = ("memoria", "historial", "sistema", "cola", "notif")

    def toggle_drawer(self, name: str) -> None:
        self.active_drawer = name if self.active_drawer != name else None

    def set_breakpoint(self, width: int) -> str:
        if width <= 620:
            bp = "MIN"
        elif width <= 920:
            bp = "COMPACT"
        elif width <= 1280:
            bp = "MEDIUM"
        else:
            bp = "LARGE"
        self.breakpoint = bp
        return bp


state = AppState()
