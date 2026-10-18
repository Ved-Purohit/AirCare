"""Plain-language briefing for the care team.

Uses Google Gemini through a Google AI Studio API key when configured. Only
aggregated numbers are sent, never video or images. The built-in template
keeps the report fully usable without an API key.
"""
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).with_name(".env"))

import json
import os
import urllib.request

from analytics import analyze
from storage import load_sessions

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
    model = os.environ.get("AIRCARE_GEMINI_MODEL", "gemini-3.8-flash")
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


def _patient_facts(patient, sessions):
    analysis = analyze(sessions)
    metrics = {}
    latest = sessions[-1].get("metrics") if sessions else {}
    for key, value in (latest or {}).items():
        if value is not None:
            metrics[key] = value
    return {
        "patient": patient,
        "sessions": len(sessions),
        "status": analysis["status"],
        "flags": [{"metric": f["label"], "severity": f["severity"], "detail": f["text"]}
                  for f in analysis["flags"][:6]],
        "latest_metrics": metrics,
        "trends": {
            key: {
                "baseline": card.get("baseline"),
                "latest": card.get("latest"),
                "series": card.get("series", []),
            }
            for key, card in analysis.get("cards", {}).items()
        },
    }


def _template_all_patient_summary(facts):
    if not facts:
        return "No patient sessions are available. No patient-specific findings can be reported."
    statuses = ", ".join(f"{f['patient']} is {f['status'].replace('_', ' ')}"
                         for f in facts)
    lines = [
        f"AirCare reviewed {len(facts)} patient record(s) using their saved session trends and personal baselines.",
        f"Overall status: {statuses}.",
    ]
    for fact in facts:
        flags = fact["flags"]
        if flags:
            detail = "; ".join(flag["detail"].split(". ")[0] for flag in flags[:2])
            lines.append(f"{fact['patient']}: {detail}. Continue reviewing the trend in context; "
                         "these are screening signals, not diagnoses.")
        else:
            lines.append(f"{fact['patient']}: no flagged change was found across "
                         f"{fact['sessions']} session(s). Continue consistent sessions to strengthen the baseline.")
    return "\n".join(lines)


def get_all_patients_summary(patients):
    facts = [_patient_facts(patient, load_sessions(patient)) for patient in patients]
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return _template_all_patient_summary(facts), "built-in summary"
    prompt = (
        "You are summarizing an AirCare rehabilitation dashboard for a clinician. "
        "Use only the supplied aggregate metrics and flags. Do not diagnose, speculate "
        "beyond the data, or identify a medical condition. Write exactly two general "
        "sentences first. Then write exactly three concise sentences for each patient, "
        "starting with the patient's name. Mention the most important trend or status, "
        "why it may matter, and a practical review suggestion. Keep the tone plain, "
        "professional, and careful. Do not mention hidden prompts or API details.\n\n"
        + json.dumps({"patients": facts}, separators=(",", ":"))
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 900, "temperature": 0.2},
    }
    model = os.environ.get("AIRCARE_GEMINI_MODEL", "gemini-3.8-flash")
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts).strip()
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        text = ""
    if not text:
        return _template_all_patient_summary(facts), "built-in summary"
    return text, "Google Gemini"
