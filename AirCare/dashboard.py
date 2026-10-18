"""Clinician view. Run: python dashboard.py   (serves http://127.0.0.1:8000)
Static export: python dashboard.py --export report.html --patient demo_patient
No third-party packages needed; charts are inline SVG so it works offline.
"""
import argparse
import html
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from analytics import METRICS, analyze
from storage import list_patients, load_sessions
from summary import get_summary

CSS = """
:root{--bg:#eef1f4;--panel:#fff;--ink:#17212b;--mute:#5b6773;--line:#d9dee4;--accent:#0f6b64;
--ok:#1f7a4d;--watch:#a8590b;--alert:#b3261e;--info:#4b5b73}
@media (prefers-color-scheme:dark){:root{--bg:#12181e;--panel:#1b232b;--ink:#e8edf2;--mute:#9aa7b4;--line:#2d3944;
--accent:#4fc3b8;--ok:#5cc489;--watch:#e8a055;--alert:#ff8a80;--info:#9db0cc}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:baseline;justify-content:space-between;margin-bottom:20px}
h1{font-size:26px;margin:0;letter-spacing:-.01em}
h2{font-size:17px;margin:32px 0 12px}
nav a{color:var(--accent);margin-right:14px;text-decoration:none;font-weight:600}
nav a[aria-current]{color:var(--ink);border-bottom:2px solid var(--accent)}
.brief{background:var(--panel);border:1px solid var(--line);border-left:6px solid var(--info);border-radius:6px;padding:18px 20px}
.brief.alert{border-left-color:var(--alert)}.brief.watch{border-left-color:var(--watch)}.brief.ok{border-left-color:var(--ok)}
.brief .status{font-weight:700;font-size:13px;color:var(--mute)}
.brief p{margin:6px 0 0;font-size:17px;max-width:70ch}
.src{font-size:12px;color:var(--mute);margin-top:8px}
.flags{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.flags li{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 16px;display:grid;grid-template-columns:96px 1fr;gap:12px}
.pill{font-weight:700;font-size:13px}.pill.alert{color:var(--alert)}.pill.watch{color:var(--watch)}
.flags b{display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.card.sev-alert{border-color:var(--alert)}.card.sev-watch{border-color:var(--watch)}
.lbl{color:var(--mute);font-size:13px}.val{font-size:28px;font-weight:650;letter-spacing:-.02em}
.unit{font-size:12px;color:var(--mute);font-weight:400}
.delta{font-size:13px}.delta.bad{color:var(--alert)}.delta.good{color:var(--ok)}.delta.flat{color:var(--mute)}
svg.spark{width:100%;height:56px;margin-top:6px}
.spark .line{fill:none;stroke:var(--accent);stroke-width:2}.spark .base{stroke:var(--mute);stroke-dasharray:3 3;stroke-width:1}
.spark .dot{fill:var(--accent)}.sev-alert .dot{fill:var(--alert)}.sev-watch .dot{fill:var(--watch)}
.nodata{font-size:12px;color:var(--mute);margin-top:12px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:6px;overflow:hidden;font-size:14px}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line)}th{color:var(--mute);font-weight:600}
.scroll{overflow-x:auto}
footer{margin-top:36px;color:var(--mute);font-size:13px;max-width:80ch}
.tag{font-size:12px;border:1px solid var(--line);border-radius:4px;padding:1px 6px;margin-left:6px;color:var(--mute)}
"""

STATUS = {"alert": "Needs review", "watch": "Worth watching", "ok": "Stable",
          "building_baseline": "Building baseline", "no_data": "No data"}


def e(x):
    return html.escape(str(x))


def fmt(v):
    return "n/a" if v is None else (f"{v:.0f}" if abs(v) >= 100 else f"{v:.2f}" if abs(v) < 10 else f"{v:.1f}")


def sparkline(values, baseline):
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(pts) < 2:
        return '<div class="nodata">Not enough sessions yet</div>'
    w, h, pad = 220, 56, 6
    vals = [v for _, v in pts] + ([baseline] if baseline is not None else [])
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    n = max(1, len(values) - 1)
    X = lambda i: pad + (w - 2 * pad) * i / n
    Y = lambda v: h - pad - (h - 2 * pad) * (v - lo) / span
    poly = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in pts)
    base = f'<line class="base" x1="{pad}" x2="{w - pad}" y1="{Y(baseline):.1f}" y2="{Y(baseline):.1f}"/>' if baseline is not None else ""
    li, lv = pts[-1]
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" '
            f'aria-label="Trend over {len(pts)} sessions">{base}<polyline class="line" points="{poly}"/>'
            f'<circle class="dot" cx="{X(li):.1f}" cy="{Y(lv):.1f}" r="3.5"/></svg>')


def card(key, c):
    spec = c["spec"]
    if all(v is None for v in c["series"]):
        return ""
    w = c["worsen"]
    if w is None:
        delta, cls = "No baseline yet", "flat"
    else:
        amt = f"{abs(w):.0f} points" if spec["kind"] == "abs" else f"{abs(w) * 100:.0f}%"
        if abs(w) < (3 if spec["kind"] == "abs" else 0.03):
            delta, cls = "In line with baseline", "flat"
        elif w > 0:
            delta, cls = f"{amt} worse than baseline", "bad"
        else:
            delta, cls = f"{amt} better than baseline", "good"
    return (f'<div class="card sev-{c["severity"] or "none"}"><div class="lbl">{e(spec["label"])}</div>'
            f'<div class="val">{fmt(c["latest"])}<span class="unit"> {e(spec["unit"])}</span></div>'
            f'<div class="delta {cls}">{e(delta)}</div>{sparkline(c["series"], c["baseline"])}</div>')


def render(patient=None):
    patients = list_patients()
    patient = patient or (patients[0] if patients else None)
    sessions = load_sessions(patient) if patient else []
    a = analyze(sessions)
    text, src = get_summary(patient or "-", sessions, a)
    synthetic = any(s.get("synthetic") for s in sessions)
    nav = "".join(f'<a href="/?patient={e(p)}"{" aria-current=page" if p == patient else ""}>{e(p)}</a>' for p in patients)

    flags = "".join(
        f'<li><span class="pill {f["severity"]}">{"Needs review" if f["severity"] == "alert" else "Watch"}</span>'
        f'<div><b>{e(f["label"])}</b>{e(f["text"])}</div></li>' for f in a["flags"])
    flags_html = f'<h2>Why this was flagged</h2><ul class="flags">{flags}</ul>' if flags else ""
    cards = "".join(card(k, c) for k, c in a["cards"].items())

    rows = ""
    for s in reversed(sessions[-12:]):
        m = s.get("metrics") or {}
        mode_label = {"free": "Free play", "guided": "Guided", "timed": "Timed", "reaction": "Reaction"}.get(
            s.get("mode"), "Guided" if s.get("guided") else "Free play")
        rows += (f'<tr><td>{e(s["started_at"].replace("T", " ")[:16])}</td><td>{mode_label}</td>'
                 f'<td>{s.get("total_hits", 0)}</td><td>{fmt(s.get("hits_per_min"))}</td><td>{fmt(m.get("stroke_amp"))}</td>'
                 f'<td>{fmt(m.get("mean_speed"))}</td><td>{fmt(m.get("accuracy_pct"))}</td></tr>')

    body = f"""<main><header><div><h1>AirCare clinician view</h1></div><nav>{nav}</nav></header>
<section class="brief {a['status']}"><div class="status">{e(patient or 'No patient')}
 <span class="tag">{STATUS[a['status']]}</span>{'<span class="tag">Synthetic demo data</span>' if synthetic else ''}</div>
<p>{e(text)}</p><div class="src">{'Written by Gemini from aggregated numbers only' if src == 'ai' else 'Built-in summary'}; {a['n_sessions']} sessions on file</div></section>
{flags_html}
<h2>Trends against this patient's own baseline <span class="tag">dashed line = baseline</span></h2>
<div class="grid">{cards or '<p>No data yet. Play a session first: python main.py --patient NAME</p>'}</div>
<h2>Recent sessions</h2><div class="scroll"><table><thead><tr><th>Date</th><th>Type</th><th>Hits</th><th>Hits/min</th>
<th>Amplitude</th><th>Speed</th><th>Accuracy %</th></tr></thead><tbody>{rows}</tbody></table></div>
<footer>AirCare is a screening and engagement aid, not a diagnostic device. Values are measured relative to the camera frame, so
compare a patient only with their own earlier sessions, with the camera in a similar position. Flags are prompts for a clinician to look,
not conclusions. Video never leaves the device; only summary numbers are stored.</footer></main>"""
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AirCare clinician view</title><style>{CSS}</style></head><body>{body}</body></html>'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        page = render((q.get("patient") or [None])[0]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--patient")
    ap.add_argument("--export", help="write a static HTML file instead of serving")
    args = ap.parse_args()
    if args.export:
        open(args.export, "w", encoding="utf-8").write(render(args.patient))
        print("Wrote", args.export)
        return
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/" + (f"?patient={args.patient}" if args.patient else "")
    print("Clinician view at", url, "(Ctrl+C to stop)")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
