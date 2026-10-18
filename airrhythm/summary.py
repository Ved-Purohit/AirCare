"""Plain-language briefing for the care team.

Uses Google Gemini through a Google AI Studio API key when configured. Only
aggregated numbers are sent, never video or images. The built-in template
keeps the report fully usable without an API key.
"""
import json
import os
import urllib.request

_cache = {}


def template_summary(patient, a):
    n = a["n_sessions"]
    if a["status"] == "no_data":
        return "No sessions recorded yet."
    if a["status"] == "building_baseline":
        return (f"{n} session(s) recorded for {patient}. A personal baseline needs at least 3, "
                "so no flags are raised yet.")
    if a["status"] == "ok":
        return f"{patient} is tracking within their own baseline across {n} sessions. No action needed."
    lead = [f["text"].split(". ")[0] for f in a["flags"][:3]]
    head = "Needs review" if a["status"] == "alert" else "Worth watching"
    return f"{head}: " + "; ".join(lead) + ". Suggest a short check-in and a look at the trends below."


def llm_summary(patient, a):
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    facts = {"sessions": a["n_sessions"], "status": a["status"],
             "flags": [{"metric": f["label"], "severity": f["severity"], "detail": f["text"]} for f in a["flags"]]}
    body = {
        "contents": [{"parts": [{"text": (
            "Brief an occupational therapist or nurse about upper-limb movement trends from an "
            "air-drumming rehabilitation game. Write at most 90 words in plain language. Do not "
            "diagnose or make medical claims beyond the data. Say what changed, why it might matter, "
            "and one suggested next step.\n\n" + json.dumps(facts)
        )}]}],
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.2},
    }
    model = os.environ.get("AIRCARE_GEMINI_MODEL", "gemini-2.0-flash")
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    candidates = data.get("candidates") or []
    parts = (candidates[0].get("content", {}).get("parts", []) if candidates else [])
    return "".join(p.get("text", "") for p in parts).strip() or None


def get_summary(patient, sessions, a):
    if a["status"] in ("alert", "watch") and sessions:
        ck = (patient, sessions[-1].get("started_at"), len(sessions))
        if ck not in _cache:
            try:
                _cache[ck] = llm_summary(patient, a)
            except Exception:
                _cache[ck] = None
        if _cache[ck]:
            return _cache[ck], "ai"
    return template_summary(patient, a), "template"
