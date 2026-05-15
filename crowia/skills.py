import logging
import pathlib

log = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def _skills_dir(cfg: dict) -> pathlib.Path:
    return PROJECT_ROOT / cfg.get("skills", {}).get("path", "skills")


def available(cfg: dict) -> list[str]:
    d = _skills_dir(cfg)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.md"))


def load_list(cfg: dict, names: list[str]) -> str:
    if not names:
        return ""
    skills_dir = _skills_dir(cfg)
    parts = []
    for name in names:
        path = skills_dir / f"{name}.md"
        if path.exists():
            parts.append(path.read_text(encoding="utf-8").strip())
            log.info("Skill cargada: %s", name)
        else:
            log.warning("Skill no encontrada: %s (%s)", name, path)
    return "\n\n---\n\n".join(parts)


def load(cfg: dict) -> str:
    enabled = cfg.get("skills", {}).get("enabled", [])
    return load_list(cfg, enabled)
