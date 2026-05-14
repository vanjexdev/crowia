import logging
import pathlib

log = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def load(cfg: dict) -> str:
    skills_cfg = cfg.get("skills", {})
    enabled = skills_cfg.get("enabled", [])
    if not enabled:
        return ""
    skills_dir = PROJECT_ROOT / skills_cfg.get("path", "skills")
    parts = []
    for name in enabled:
        path = skills_dir / f"{name}.md"
        if path.exists():
            parts.append(path.read_text(encoding="utf-8").strip())
            log.info("Skill cargada: %s", name)
        else:
            log.warning("Skill no encontrada: %s (%s)", name, path)
    return "\n\n---\n\n".join(parts)
