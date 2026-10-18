"""AirCare desktop launcher.

Run with: python app.py
The launcher starts the existing OpenCV game and clinician dashboard as
separate local processes, so the core experience remains easy to test.
"""
import math
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from storage import list_patients
from summary import get_all_patients_summary


ROOT = Path(__file__).resolve().parent
ASSET = ROOT / "assets" / "aircare_banner.png"


def _frozen_target():
    """Run a bundled child target when the launcher is packaged as an exe."""
    if "--aircare-game" in sys.argv:
        sys.argv.remove("--aircare-game")
        from main import main as game_main
        game_main()
        return True
    if "--aircare-dashboard" in sys.argv:
        sys.argv.remove("--aircare-dashboard")
        from dashboard import main as dashboard_main
        dashboard_main()
        return True
    return False


class AirCareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AirCare")
        self.root.geometry("900x705")
        self.root.minsize(760, 600)
        self.root.configure(bg="#0b1016")
        self.game_process = None
        self.report_process = None

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("Air.TButton", font=("Segoe UI", 12, "bold"),
                        padding=(18, 10), foreground="#ffffff", background="#0f6b64")
        style.map("Air.TButton", background=[("active", "#168f84")])
        style.configure("Secondary.TButton", font=("Segoe UI", 11),
                        padding=(14, 8), foreground="#dce7ec", background="#24313c")
        style.map("Secondary.TButton", background=[("active", "#334654")])
        style.configure("Danger.TButton", font=("Segoe UI", 11, "bold"),
                        padding=(14, 8), foreground="#ffffff", background="#8f3f4a")
        style.map("Danger.TButton", background=[("active", "#b34d5c")])
        style.configure("Air.TLabel", background="#0b1016", foreground="#edf4f7")
        style.configure("Muted.TLabel", background="#0b1016", foreground="#9eb0bb")

        self.patient = tk.StringVar(value="demo_patient")
        self.mode = tk.StringVar(value="Free Play")
        self.sensitivity = tk.StringVar(value="0.8")

        self._build()

    def _build(self):
        outer = tk.Frame(self.root, bg="#0b1016")
        outer.pack(fill="both", expand=True, padx=26, pady=22)

        if ASSET.exists():
            try:
                self.banner = tk.PhotoImage(file=str(ASSET))
                max_width = 848
                if self.banner.width() > max_width:
                    factor = max(1, math.ceil(self.banner.width() / max_width))
                    self.banner = self.banner.subsample(factor, factor)
                tk.Label(outer, image=self.banner, bg="#0b1016").pack(fill="x")
            except tk.TclError:
                self._fallback_title(outer)
        else:
            self._fallback_title(outer)

        tk.Label(outer, text="AirCare control center",
                 font=("Segoe UI", 18, "bold"), bg="#0b1016",
                 fg="#edf4f7").pack(pady=(18, 4))
        tk.Label(outer, text="Play virtual instruments, build a personal movement history, "
                 "and give the care team an explainable report.\n"
                 "Close your fist, place your palm over a drum, then open your hand to play.",
                 font=("Segoe UI", 11), bg="#0b1016", fg="#9eb0bb",
                 wraplength=720).pack()

        form = tk.Frame(outer, bg="#131d26", padx=20, pady=16)
        form.pack(fill="x", pady=22)
        tk.Label(form, text="Patient", bg="#131d26", fg="#dce7ec",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Entry(form, textvariable=self.patient, width=28, relief="flat",
                 bg="#24313c", fg="#ffffff", insertbackground="#ffffff",
                 font=("Segoe UI", 11)).grid(row=1, column=0, padx=(0, 18), pady=(5, 0), sticky="ew")
        tk.Label(form, text="Sensitivity", bg="#131d26", fg="#dce7ec",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w")
        tk.Entry(form, textvariable=self.sensitivity, width=10, relief="flat",
                 bg="#24313c", fg="#ffffff", insertbackground="#ffffff",
                 font=("Segoe UI", 11)).grid(row=1, column=1, padx=(0, 18), pady=(5, 0), sticky="w")
        tk.Label(form, text="Game mode", bg="#131d26", fg="#dce7ec",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=2, sticky="w")
        modes = ("Free Play", "Guided", "Timed", "Reaction Test")
        ttk.Combobox(form, textvariable=self.mode, values=modes, state="readonly",
                     width=22).grid(row=1, column=2, padx=(0, 18), pady=(5, 0), sticky="w")
        form.columnconfigure(0, weight=1)

        buttons = tk.Frame(outer, bg="#0b1016")
        buttons.pack()
        ttk.Button(buttons, text="Start AirCare", style="Air.TButton",
                   command=self.start_game).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open Report", style="Secondary.TButton",
                   command=self.open_report).pack(side="left", padx=6)
        ttk.Button(buttons, text="Summarize", style="Secondary.TButton",
                   command=self.summarize).pack(side="left", padx=6)
        ttk.Button(buttons, text="Exit", style="Danger.TButton",
                   command=self.exit_app).pack(side="left", padx=6)

        self.status = tk.Label(outer, text="Ready. Start a session, view the report, or summarize saved sessions.",
                               bg="#0b1016", fg="#9eb0bb", font=("Segoe UI", 10))
        self.status.pack(pady=16)

    def _fallback_title(self, parent):
        tk.Label(parent, text="AirCare", font=("Segoe UI", 42, "bold"),
                 bg="#0b1016", fg="#ffffff").pack(pady=40)

    def _patient_name(self):
        name = self.patient.get().strip()
        return name or "demo_patient"

    def start_game(self):
        if self.game_process and self.game_process.poll() is None:
            self.status.config(text="A session is already running.")
            return
        try:
            sensitivity = float(self.sensitivity.get())
            if sensitivity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid sensitivity", "Sensitivity must be a positive number.")
            return
        mode = {
            "Free Play": "free",
            "Guided": "guided",
            "Timed": "timed",
            "Reaction Test": "reaction",
        }[self.mode.get()]
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--aircare-game"]
        else:
            cmd = [sys.executable, str(ROOT / "main.py")]
        cmd += ["--patient", self._patient_name(), "--sensitivity", str(sensitivity), "--mode", mode]
        try:
            self.game_process = subprocess.Popen(cmd, cwd=str(ROOT))
        except OSError as exc:
            messagebox.showerror("Could not start AirCare", str(exc))
            return
        self.status.config(text="AirCare is running. Use q in the game window to finish and save.")
        self.root.after(500, self._watch_game)

    def _watch_game(self):
        if self.game_process and self.game_process.poll() is None:
            self.root.after(500, self._watch_game)
        else:
            self.status.config(text="Session finished. Open the report to review the latest data.")

    def open_report(self):
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--aircare-dashboard"]
        else:
            cmd = [sys.executable, str(ROOT / "dashboard.py")]
        cmd += ["--patient", self._patient_name()]
        try:
            self.report_process = subprocess.Popen(cmd, cwd=str(ROOT))
        except OSError as exc:
            messagebox.showerror("Could not open report", str(exc))
            return
        self.status.config(text="Opening the AirCare clinician report in your browser.")

    def summarize(self):
        patients = list_patients()
        if not patients:
            messagebox.showinfo("AirCare summary", "No saved patient sessions were found.")
            return
        self.status.config(text="Preparing the all-patient summary...")
        self.root.update_idletasks()
        text, source = get_all_patients_summary(patients)
        self._show_summary(text, source)

    def _show_summary(self, text, source):
        dialog = tk.Toplevel(self.root)
        dialog.title("AirCare overall summary")
        dialog.geometry("760x600")
        dialog.configure(bg="#0b1016")
        tk.Label(dialog, text=f"AirCare overall summary ({source})",
                 bg="#0b1016", fg="#edf4f7",
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        box = tk.Text(dialog, wrap="word", bg="#131d26", fg="#edf4f7",
                      insertbackground="#ffffff", relief="flat", padx=14, pady=12)
        box.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        box.insert("1.0", text)
        box.configure(state="disabled")
        self.status.config(text="Summary ready.")

    def exit_app(self):
        if self.game_process and self.game_process.poll() is None:
            if not messagebox.askyesno("Exit AirCare", "A session is still running. Exit anyway?"):
                return
            self.game_process.terminate()
        if self.report_process and self.report_process.poll() is None:
            self.report_process.terminate()
        self.root.destroy()


def main():
    root = tk.Tk()
    AirCareApp(root)
    root.mainloop()


if __name__ == "__main__":
    if not _frozen_target():
        main()
