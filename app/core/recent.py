"""Recent projects list stored locally as JSON (never transmitted)."""
import json
import os
import time

from .logging_setup import log_dir

_PATH = os.path.join(os.path.dirname(log_dir()), "recent.json")


def load() -> list:
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            return [r for r in json.load(f) if os.path.exists(r.get("path", ""))][:30]
    except Exception:
        return []


def add(path: str, kind: str, pages: int):
    items = [r for r in load() if r["path"] != path]
    items.insert(0, {"path": path, "kind": kind, "pages": pages, "time": time.strftime("%Y-%m-%d %H:%M")})
    try:
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(items[:30], f, indent=1)
    except Exception:
        pass
