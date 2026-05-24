from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_INSTANCES = ["opencode", "claude", "codex"]
_DEFAULT_BACKENDS  = {"opencode": "opencode", "claude": "claude", "codex": "codex"}


def _load_instances() -> tuple[list, dict]:
    try:
        import yaml, pathlib
        cfg = yaml.safe_load(
            (pathlib.Path(__file__).parents[2] / "config.yaml").read_text(encoding="utf-8")
        )
        inst_cfg = cfg.get("instances", {})
        instances = inst_cfg.get("list", _DEFAULT_INSTANCES)
        backends  = inst_cfg.get("backends", _DEFAULT_BACKENDS)
        return instances, backends
    except Exception:
        return _DEFAULT_INSTANCES, _DEFAULT_BACKENDS


def save_instances(instances: list, backends: dict) -> None:
    try:
        from ruamel.yaml import YAML
        import io, pathlib
        _yaml = YAML(); _yaml.preserve_quotes = True
        p = pathlib.Path(__file__).parents[2] / "config.yaml"
        cfg = _yaml.load(p.read_text(encoding="utf-8"))
        cfg["instances"] = {"list": list(instances), "backends": dict(backends)}
        buf = io.StringIO(); _yaml.dump(cfg, buf)
        p.write_text(buf.getvalue(), encoding="utf-8")
    except Exception:
        pass


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

    INSTANCES: list = field(default_factory=lambda: _load_instances()[0])
    INSTANCE_BACKENDS: dict = field(default_factory=lambda: _load_instances()[1])
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
