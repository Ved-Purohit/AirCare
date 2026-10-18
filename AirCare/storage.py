"""Tiny JSON file store: data/<patient>/<timestamp>.json"""
import json
import re
from config import DATA_DIR


def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name) or "patient"


def save_session(summary: dict):
    d = DATA_DIR / _safe(summary["patient"])
    d.mkdir(parents=True, exist_ok=True)
    stamp = re.sub(r"[^0-9T]", "", summary["started_at"])
    path = d / f"{stamp}.json"
    path.write_text(json.dumps(summary, indent=2))
    return path


def load_sessions(patient: str):
    d = DATA_DIR / _safe(patient)
    if not d.exists():
        return []
    out = []
    for p in d.glob("*.json"):
        try:
            out.append(json.loads(p.read_text()))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda s: s.get("started_at", ""))


def list_patients():
    if not DATA_DIR.exists():
        return []
    return sorted(p.name for p in DATA_DIR.iterdir() if p.is_dir() and any(p.glob("*.json")))
