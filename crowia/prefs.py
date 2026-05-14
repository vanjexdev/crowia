import json
import pathlib

PREFS_PATH = pathlib.Path.home() / ".config/crowia/prefs.json"

DEFAULTS: dict = {
    "show_response_text": True,
}


def load() -> dict:
    if PREFS_PATH.exists():
        try:
            data = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(prefs: dict):
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFS_PATH.write_text(
        json.dumps(prefs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
