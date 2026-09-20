
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import urllib.request
import urllib.parse
import json
import math
import os
import hashlib
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import Normalize

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

APP_TITLE = "ThermoShelter AI — Final Prototype"
# Final prototype uses manual climate input as the active climate source.
# Live API/location integration is retained as a future extension and is not used by the active workflow.
LIVE_CLIMATE_ENABLED = False
DATA_FILE = os.path.join(os.path.expanduser("~"), "ThermoShelter_AI_data.json")
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

BG = "#0f172a"
CARD = "#1e293b"
CARD2 = "#111827"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
GREEN = "#10b981"
BLUE = "#38bdf8"
PURPLE = "#8b5cf6"
ORANGE = "#f59e0b"
RED = "#ef4444"
CYAN = "#22d3ee"


# ---------------- SCIENTIFIC CORE ----------------
def fanger_pmv_ppd(ta, tr, vel, rh, met, clo, wme=0.0):
    """Prototype Fanger PMV/PPD calculation.
    Inputs follow the conventional PMV variables: ta, tr [C], vel [m/s], rh [%], met, clo.
    """
    vals = [ta, tr, vel, rh, met, clo, wme]
    if not all(isinstance(x, (int, float, np.floating)) for x in vals):
        raise ValueError("PMV inputs must be numeric.")
    if vel <= 0 or met <= 0 or clo < 0 or wme < 0:
        raise ValueError("PMV requires air speed/met > 0 and non-negative clo/work.")
    if not 0 <= rh <= 100:
        raise ValueError("Relative humidity must be between 0 and 100%.")
    m = met * 58.15
    w = wme * 58.15
    mw = m - w
    icl = 0.155 * clo
    fcl = 1.05 + 0.645 * icl if icl > 0.078 else 1 + 1.29 * icl
    pa = rh * 10.0 * np.exp(16.6536 - 4030.183 / (ta + 235.0))
    hcf = 12.1 * np.sqrt(vel)
    taa = ta + 273.0
    tra = tr + 273.0
    tcla = taa + (35.5 - ta) / (3.5 * icl + 0.1) if icl > 0 else taa + 5.0
    p1 = icl * fcl
    p2 = p1 * 3.96
    p3 = p1 * 100.0
    p4 = p1 * taa
    p5 = 308.7 - 0.028 * mw + p2 * ((tra / 100.0) ** 4)
    xn = tcla / 100.0
    xf = tcla / 50.0
    eps = 0.00015
    hc = hcf
    for _ in range(200):
        xf = (xf + xn) / 2.0
        hcn = 2.38 * abs(100.0 * xf - taa) ** 0.25
        hc = max(hcf, hcn)
        xn_new = (p5 + p4 * hc - p2 * xf ** 4) / (100.0 + p3 * hc)
        if abs(xn_new - xf) <= eps:
            xn = xn_new
            break
        xn = xn_new
    else:
        raise ValueError("PMV iteration did not converge.")
    tcl = 100.0 * xn - 273.0
    hl1 = 3.05e-3 * (5733.0 - 6.99 * mw - pa)
    hl2 = 0.42 * (mw - 58.15) if mw > 58.15 else 0.0
    hl3 = 1.7e-5 * m * (5867.0 - pa)
    hl4 = 0.0014 * m * (34.0 - ta)
    hl5 = 3.96 * fcl * (xn ** 4 - (tra / 100.0) ** 4)
    hl6 = fcl * hc * (tcl - ta)
    thermal_load = mw - hl1 - hl2 - hl3 - hl4 - hl5 - hl6
    pmv = (0.303 * np.exp(-0.036 * m) + 0.028) * thermal_load
    ppd = 100.0 - 95.0 * np.exp(-0.03353 * pmv ** 4 - 0.2179 * pmv ** 2)
    return float(pmv), float(ppd), float(pa)


def thermal_status(pmv, ppd):
    if abs(pmv) >= 2.5 or ppd >= 90:
        return "CRITICAL POINT", ORANGE
    if pmv > 0.5:
        return "OVER HEATED", RED
    if pmv < -0.5:
        return "UNDER HEATED", BLUE
    if abs(pmv) <= 0.5 and ppd <= 10:
        return "OPTIMAL COMFORT", GREEN
    return "THERMAL COMFORT MARGINAL", ORANGE


def safe_float(value, label):
    try:
        return float(value)
    except Exception:
        raise ValueError(f"{label} must be a valid number.")


class ThermoShelterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1450x850")
        self.root.minsize(1180, 720)
        self.root.configure(bg=BG)

        self.user_accounts = {}
        # Provisional prototype properties. These must be verified against authoritative project-approved data before engineering deployment.
        self.material_database = {
            "EPS": {"k": 0.040, "density": 20.0, "cp": 1400.0, "emissivity": 0.90, "cost_index": 1.00, "source": "Prototype placeholder — verify authoritative data"},
            "XPS": {"k": 0.034, "density": 35.0, "cp": 1400.0, "emissivity": 0.90, "cost_index": 1.20, "source": "Prototype placeholder — verify authoritative data"},
            "Mineral Wool": {"k": 0.040, "density": 70.0, "cp": 1030.0, "emissivity": 0.90, "cost_index": 1.20, "source": "Prototype placeholder — verify authoritative data"},
            "Aerogel": {"k": 0.015, "density": 150.0, "cp": 1000.0, "emissivity": 0.90, "cost_index": 4.00, "source": "Prototype placeholder — verify authoritative data"},
        }
        self.load_accounts()
        self.current_user = None
        self.current_role = None
        self.selected_user = None
        self.current_screen = "auth"
        self.dirty = True
        self.climate_loaded = False
        self.climate_mode = "NOT APPLIED"
        self.climate_timestamp = "—"
        self.climate_data = {}
        self.last_results = {}
        self.last_heatmap_range = (None, None)
        self.last_optimization = []
        self.primary_buttons = {}
        self.admin_boundary_vars = {
            "min_temp": 18.0, "max_temp": 24.0,
            "min_thickness": 0.05, "max_thickness": 0.50,
            "min_pmv": -2.5, "max_pmv": 2.5,
        }

        self.geometry_type = tk.StringVar(value="Cuboid")
        self.corner_angle = tk.DoubleVar(value=90.0)
        self.target_temp = tk.DoubleVar(value=21.0)
        self.ambient_temp = tk.DoubleVar(value=-10.0)
        self.relative_humidity = tk.DoubleVar(value=50.0)
        self.wind_speed = tk.DoubleVar(value=0.50)
        self.solar_radiation = tk.DoubleVar(value=150.0)
        self.shelter_length = tk.DoubleVar(value=4.0)
        self.shelter_width = tk.DoubleVar(value=3.0)
        self.shelter_height = tk.DoubleVar(value=2.5)
        self.thickness = tk.DoubleVar(value=0.15)
        self.latitude = tk.DoubleVar(value=28.6139)
        self.longitude = tk.DoubleVar(value=77.2090)
        self.material_var = tk.StringVar(value="EPS")
        self.mean_radiant_temp = tk.DoubleVar(value=21.0)
        self.indoor_air_speed = tk.DoubleVar(value=0.10)
        self.metabolic_rate = tk.DoubleVar(value=1.2)
        self.clothing_level = tk.DoubleVar(value=1.0)
        self.ventilation_ach = tk.DoubleVar(value=0.5)
        self.window_wall_ratio = tk.DoubleVar(value=0.10)
        self.window_shgc = tk.DoubleVar(value=0.70)

        self.canvas = None
        self.ax = None
        self.heatmap_canvas = None
        self.heatmap_ax = None
        self.show_auth_screen()

    # ---------------- persistence ----------------
    def load_accounts(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.user_accounts = data.get("users", {})
                self.material_database = data.get("materials", getattr(self, "material_database", {}))
        except Exception:
            self.user_accounts = {}

    def save_accounts(self):
        try:
            payload = {"users": self.user_accounts, "materials": self.material_database}
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    # ---------------- common UI ----------------
    def clear_root(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.canvas = None
        self.ax = None
        self.heatmap_canvas = None
        self.heatmap_ax = None

    def button(self, parent, text, command, bg=BLUE, fg="white", width=None):
        b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg,
                      activeforeground=fg, relief="flat", font=("Arial", 9, "bold"),
                      padx=12, pady=7, cursor="hand2")
        if width:
            b.configure(width=width)
        return b

    def create_header(self, parent, title, subtitle):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(fill="x", padx=10, pady=8)
        tk.Label(frame, text=title, font=("Arial", 19, "bold"), fg=GREEN, bg=CARD).pack(anchor="w", padx=15, pady=(10, 2))
        tk.Label(frame, text=subtitle, font=("Arial", 9), fg=MUTED, bg=CARD).pack(anchor="w", padx=15, pady=(0, 10))

    def workflow_bar(self, parent, kind):
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=12, pady=(0, 5))
        if kind == "USER":
            label = "USER WORKFLOW"
            text = "1 Login / Signup  →  2 GPS and Shelter Dimensions  →  3 Climate Data Collection (manual)  →  4 Thermodynamic Solver  →  5 3D Heatmap Visualization  →  6 Export Blueprint PDF"
            color = GREEN
        else:
            label = "ADMIN / DRDO OVERSIGHT"
            text = "1 Admin Login  →  2 Material Bases  →  3 Shelter Specification  →  4 Environment Boundaries  →  5 Analytics and Reports"
            color = BLUE
        tk.Label(bar, text=label, font=("Arial", 9, "bold"), fg=color, bg=BG).pack(side="left", padx=(5, 10))
        tk.Label(bar, text=text, font=("Arial", 8), fg="#cbd5e1", bg=BG, wraplength=1150, justify="left").pack(side="left", fill="x", expand=True)

    def section(self, parent, title, color=GREEN):
        tk.Label(parent, text=title, font=("Arial", 10, "bold"), fg=color, bg=CARD).pack(anchor="w", padx=10, pady=(8, 3))

    def field(self, parent, label, variable, minimum, maximum, increment):
        tk.Label(parent, text=label, fg=MUTED, bg=CARD, font=("Arial", 8)).pack(anchor="w", padx=10, pady=(2, 0))
        s = tk.Spinbox(parent, from_=minimum, to=maximum, increment=increment, textvariable=variable,
                       bg=BG, fg="white", insertbackground="white", relief="flat", command=self.mark_dirty)
        s.pack(fill="x", padx=10, pady=2)
        s.bind("<Return>", lambda e: self.mark_dirty())
        s.bind("<FocusOut>", lambda e: self.mark_dirty())
        return s

    def configure_primary_actions(self):
        """Keep the workflow state visible: downstream actions activate only when prerequisites are met."""
        if not hasattr(self, "primary_buttons"):
            return
        solver_ready = bool(self.climate_loaded)
        result_ready = bool(self.last_results) and not self.dirty
        def state(name, enabled):
            btn = self.primary_buttons.get(name)
            if btn is not None:
                btn.configure(state=(tk.NORMAL if enabled else tk.DISABLED))
        state("apply_climate", True)
        state("solver", solver_ready)
        state("heatmap", result_ready)
        state("pdf", result_ready)
        state("analytics", result_ready)
        state("logout", True)
        if hasattr(self, "optimizer_button"):
            self.optimizer_button.configure(state=(tk.NORMAL if solver_ready else tk.DISABLED))

    def mark_dirty(self, *_):
        self.dirty = True
        if hasattr(self, "status_label") and self.current_screen == "user_dashboard":
            self.status_label.configure(text="⚠ Inputs changed — re-apply climate if needed, then RUN SOLVER.", fg=ORANGE)
        if self.current_screen == "user_dashboard":
            self.configure_primary_actions()

    def source_text(self):
        return self.climate_mode

    # ---------------- auth ----------------
    def show_auth_screen(self):
        self.current_screen = "auth"
        self.current_role = None
        self.current_user = None
        self.selected_user = None
        self.clear_root()
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)
        card = tk.Frame(outer, bg=CARD, highlightbackground="#334155", highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center", width=600, height=520)
        tk.Label(card, text="ThermoShelter AI", font=("Arial", 28, "bold"), fg=GREEN, bg=CARD).pack(pady=(38, 3))
        tk.Label(card, text="SMART INDIA HACKATHON 2026 | SIH26051 | TEAM AGNIT", font=("Arial", 9, "bold"), fg=MUTED, bg=CARD).pack()
        tk.Label(card, text="USER ACCESS", font=("Arial", 15, "bold"), fg=TEXT, bg=CARD).pack(pady=(28, 14))
        form = tk.Frame(card, bg=CARD); form.pack(fill="x", padx=70)
        tk.Label(form, text="Username / Email", fg="#cbd5e1", bg=CARD, font=("Arial", 10, "bold")).pack(anchor="w")
        self.auth_username = tk.Entry(form, font=("Arial", 11), bg=BG, fg="white", insertbackground="white", relief="flat")
        self.auth_username.pack(fill="x", pady=(5, 13), ipady=8)
        tk.Label(form, text="Password", fg="#cbd5e1", bg=CARD, font=("Arial", 10, "bold")).pack(anchor="w")
        self.auth_password = tk.Entry(form, font=("Arial", 11), show="*", bg=BG, fg="white", insertbackground="white", relief="flat")
        self.auth_password.pack(fill="x", pady=(5, 18), ipady=8)
        buttons = tk.Frame(card, bg=CARD); buttons.pack()
        self.button(buttons, "LOGIN", self.handle_user_login, GREEN).pack(side="left", padx=5)
        self.button(buttons, "SIGN UP", self.show_signup_screen, "#334155").pack(side="left", padx=5)
        self.button(card, "ADMIN / DRDO LOGIN", self.show_admin_login, BG, BLUE).pack(pady=(25, 3))
        tk.Label(card, text="Admin demo: admin / admin123", font=("Arial", 8), fg="#64748b", bg=CARD).pack()

    def show_signup_screen(self):
        self.current_screen = "signup"; self.clear_root()
        card = tk.Frame(self.root, bg=CARD, highlightbackground="#334155", highlightthickness=1)
        card.place(relx=.5, rely=.5, anchor="center", width=620, height=580)
        tk.Label(card, text="Create User Account", font=("Arial", 22, "bold"), fg=GREEN, bg=CARD).pack(pady=(30, 20))
        form = tk.Frame(card, bg=CARD); form.pack(fill="x", padx=75)
        self.signup_entries = {}
        for label, key in [("Name", "name"), ("Email / Username", "username"), ("Password", "password"), ("Confirm Password", "confirm")]:
            tk.Label(form, text=label, fg="#cbd5e1", bg=CARD, font=("Arial", 10, "bold")).pack(anchor="w")
            e = tk.Entry(form, font=("Arial", 11), bg=BG, fg="white", insertbackground="white", relief="flat", show="*" if key in ("password", "confirm") else "")
            e.pack(fill="x", pady=(5, 12), ipady=7); self.signup_entries[key] = e
        self.button(card, "CREATE ACCOUNT", self.handle_signup, GREEN).pack(pady=10)
        self.button(card, "BACK TO LOGIN", self.show_auth_screen, BG, MUTED).pack()

    def handle_signup(self):
        name = self.signup_entries["name"].get().strip()
        username = self.signup_entries["username"].get().strip()
        password = self.signup_entries["password"].get()
        confirm = self.signup_entries["confirm"].get()
        if not name or not username or not password:
            return messagebox.showwarning("Signup", "Please complete all required fields.")
        if len(password) < 4:
            return messagebox.showwarning("Signup", "Password must contain at least 4 characters.")
        if password != confirm:
            return messagebox.showerror("Signup", "Passwords do not match.")
        if username.lower() == ADMIN_USERNAME:
            return messagebox.showerror("Signup", "This username is reserved.")
        if username in self.user_accounts:
            return messagebox.showerror("Signup", "This username/email already exists.")
        self.user_accounts[username] = {
            "name": name,
            "password_hash": self.hash_password(password),
            "design": self.default_design(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.save_accounts()
        messagebox.showinfo("Signup", "Account created successfully.")
        self.show_auth_screen()

    def handle_user_login(self):
        username = self.auth_username.get().strip()
        password = self.auth_password.get()
        account = self.user_accounts.get(username)
        valid = account and account.get("password_hash") == self.hash_password(password)
        # Compatibility with older prototype accounts saved in plaintext.
        if account and not account.get("password_hash") and account.get("password") == password:
            valid = True
            account["password_hash"] = self.hash_password(password)
            account.pop("password", None)
            self.save_accounts()
        if not valid:
            return messagebox.showerror("Login Failed", "Invalid user credentials. Create an account first using SIGN UP.")
        self.current_role = "USER"; self.current_user = username; self.selected_user = username
        self.load_user_design(username)
        self.show_user_dashboard()

    def default_design(self):
        return {
            "geometry_type": "Cuboid", "corner_angle": 90.0, "target_temp": 21.0, "ambient_temp": -10.0,
            "length": 4.0, "width": 3.0, "height": 2.5, "thickness": 0.15,
            "latitude": 28.6139, "longitude": 77.2090, "material": "EPS",
            "relative_humidity": 50.0, "wind_speed": 0.50, "solar_radiation": 150.0,
            "mean_radiant_temp": 21.0, "indoor_air_speed": 0.10, "metabolic_rate": 1.2,
            "clothing_level": 1.0, "ventilation_ach": 0.5, "window_wall_ratio": 0.10, "window_shgc": 0.70,
            "climate_loaded": False, "climate_mode": "NOT APPLIED", "climate_data": {}, "last_results": {},
            "last_heatmap_range": [None, None], "updated_at": datetime.now().isoformat(timespec="seconds")
        }

    def load_user_design(self, username):
        d = self.user_accounts[username].get("design") or self.default_design()
        self.geometry_type.set(d.get("geometry_type", "Cuboid")); self.corner_angle.set(d.get("corner_angle", 90.0))
        self.target_temp.set(d.get("target_temp", 21.0)); self.ambient_temp.set(d.get("ambient_temp", -10.0))
        self.relative_humidity.set(d.get("relative_humidity", 50.0)); self.wind_speed.set(d.get("wind_speed", 0.50)); self.solar_radiation.set(d.get("solar_radiation", 150.0))
        self.shelter_length.set(d.get("length", 4.0)); self.shelter_width.set(d.get("width", 3.0)); self.shelter_height.set(d.get("height", 2.5))
        self.thickness.set(d.get("thickness", .15)); self.latitude.set(d.get("latitude", 28.6139)); self.longitude.set(d.get("longitude", 77.2090))
        self.material_var.set(d.get("material", "EPS")); self.mean_radiant_temp.set(d.get("mean_radiant_temp", 21.0))
        self.indoor_air_speed.set(d.get("indoor_air_speed", .10)); self.metabolic_rate.set(d.get("metabolic_rate", 1.2)); self.clothing_level.set(d.get("clothing_level", 1.0))
        self.ventilation_ach.set(d.get("ventilation_ach", .5)); self.window_wall_ratio.set(d.get("window_wall_ratio", .10)); self.window_shgc.set(d.get("window_shgc", .70))
        self.climate_data = d.get("climate_data", {}) or {}
        self.climate_loaded = bool(d.get("climate_loaded", False) and self.climate_data)
        self.climate_mode = d.get("climate_mode", "NOT APPLIED")
        self.climate_timestamp = self.climate_data.get("timestamp", "—") if self.climate_data else "—"
        self.last_results = d.get("last_results", {}) or {}
        self.last_heatmap_range = tuple(d.get("last_heatmap_range", [None, None]))
        self.dirty = True

    def save_current_user_design(self):
        if not self.current_user or self.current_user not in self.user_accounts:
            return
        self.user_accounts[self.current_user]["design"] = {
            "geometry_type": self.geometry_type.get(), "corner_angle": float(self.corner_angle.get()),
            "target_temp": float(self.target_temp.get()), "ambient_temp": float(self.ambient_temp.get()),
            "relative_humidity": float(self.relative_humidity.get()), "wind_speed": float(self.wind_speed.get()), "solar_radiation": float(self.solar_radiation.get()),
            "length": float(self.shelter_length.get()), "width": float(self.shelter_width.get()), "height": float(self.shelter_height.get()),
            "thickness": float(self.thickness.get()), "latitude": float(self.latitude.get()), "longitude": float(self.longitude.get()),
            "material": self.material_var.get(), "mean_radiant_temp": float(self.mean_radiant_temp.get()),
            "indoor_air_speed": float(self.indoor_air_speed.get()), "metabolic_rate": float(self.metabolic_rate.get()),
            "clothing_level": float(self.clothing_level.get()), "ventilation_ach": float(self.ventilation_ach.get()),
            "window_wall_ratio": float(self.window_wall_ratio.get()), "window_shgc": float(self.window_shgc.get()),
            "climate_loaded": bool(self.climate_loaded), "climate_mode": self.climate_mode,
            "climate_data": self.climate_data, "last_results": self.last_results,
            "last_heatmap_range": list(self.last_heatmap_range), "updated_at": datetime.now().isoformat(timespec="seconds")
        }
        self.user_accounts[self.current_user]["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.save_accounts()

    # ---------------- user workflow ----------------
    def show_user_dashboard(self):
        self.current_screen = "user_dashboard"; self.current_role = "USER"; self.clear_root()
        self.create_header(self.root, "ThermoShelter AI", "SIH26051 | Team Agnit | Final research-informed engineering prototype")
        self.workflow_bar(self.root, "USER")
        main = tk.Frame(self.root, bg=BG); main.pack(fill="both", expand=True, padx=8, pady=3)
        main.columnconfigure(0, weight=1); main.columnconfigure(1, weight=2); main.columnconfigure(2, weight=1); main.rowconfigure(0, weight=1)

        # Persistent primary action bar: important actions stay visible without scrolling.
        actionbar = tk.Frame(self.root, bg=CARD, highlightbackground="#334155", highlightthickness=1)
        actionbar.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(actionbar, text="PRIMARY ACTIONS", fg=BLUE, bg=CARD, font=("Arial", 8, "bold")).pack(side="left", padx=10)
        self.primary_buttons["apply_climate"] = self.button(actionbar, "✓ APPLY CLIMATE", self.apply_manual_climate, GREEN, BG)
        self.primary_buttons["apply_climate"].pack(side="left", padx=3, pady=4)
        self.primary_buttons["solver"] = self.button(actionbar, "RUN SOLVER", lambda: self.update_simulation(True), GREEN)
        self.primary_buttons["solver"].pack(side="left", padx=3, pady=4)
        self.primary_buttons["heatmap"] = self.button(actionbar, "3D HEATMAP", self.show_heatmap_screen, ORANGE, BG)
        self.primary_buttons["heatmap"].pack(side="left", padx=3, pady=4)
        self.primary_buttons["pdf"] = self.button(actionbar, "EXPORT RESULTS PDF", self.export_blueprint_pdf, BLUE)
        self.primary_buttons["pdf"].pack(side="left", padx=3, pady=4)
        self.primary_buttons["analytics"] = self.button(actionbar, "ANALYTICS", self.show_user_analytics, "#334155")
        self.primary_buttons["analytics"].pack(side="left", padx=3, pady=4)
        self.primary_buttons["logout"] = self.button(actionbar, "LOG OUT", self.show_auth_screen, RED)
        self.primary_buttons["logout"].pack(side="right", padx=6, pady=4)

        controls_holder = tk.Frame(main, bg=BG)
        controls_holder.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        controls_holder.rowconfigure(0, weight=1); controls_holder.columnconfigure(0, weight=1)
        controls_canvas = tk.Canvas(controls_holder, bg=BG, highlightthickness=0, bd=0)
        controls_scroll = ttk.Scrollbar(controls_holder, orient="vertical", command=controls_canvas.yview)
        controls_canvas.grid(row=0, column=0, sticky="nsew"); controls_scroll.grid(row=0, column=1, sticky="ns")
        controls_canvas.configure(yscrollcommand=controls_scroll.set)
        controls = tk.LabelFrame(controls_canvas, text=" GPS, Shelter & Thermal Inputs ", font=("Arial", 10, "bold"), fg=TEXT, bg=CARD)
        controls_window = controls_canvas.create_window((0, 0), window=controls, anchor="nw")
        controls.bind("<Configure>", lambda e: controls_canvas.configure(scrollregion=controls_canvas.bbox("all")))
        controls_canvas.bind("<Configure>", lambda e: controls_canvas.itemconfigure(controls_window, width=e.width))
        controls_canvas.bind_all("<MouseWheel>", lambda e: controls_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.section(controls, "SESSION", GREEN)
        tk.Label(controls, text=f"User: {self.user_accounts.get(self.current_user, {}).get('name', self.current_user)}", fg=TEXT, bg=CARD, font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=2)
        tk.Label(controls, text="Climate mode: MANUAL INPUT", fg=ORANGE, bg=CARD, font=("Arial", 8, "bold")).pack(anchor="w", padx=10, pady=2)

        self.section(controls, "GPS / LOCATION")
        self.field(controls, "Latitude", self.latitude, -90, 90, .0001)
        self.field(controls, "Longitude", self.longitude, -180, 180, .0001)
        self.button(controls, "📍 DETECT MY LOCATION", self.detect_device_location, BLUE).pack(fill="x", padx=10, pady=4)
        tk.Label(controls, text="Device location requires OS permission. Manual coordinates are the explicit fallback.", fg="#64748b", bg=CARD, font=("Arial", 7), wraplength=270, justify="left").pack(anchor="w", padx=10)

        self.section(controls, "CLIMATE DATA — MANUAL INPUT")
        tk.Label(controls, text="Enter the environmental conditions for this test case, then apply them before running the solver.", fg=MUTED, bg=CARD, font=("Arial", 7), wraplength=280, justify="left").pack(anchor="w", padx=10, pady=(0, 3))
        self.field(controls, "Outdoor Temperature (°C)", self.ambient_temp, -50, 60, .5)
        self.field(controls, "Relative Humidity (%)", self.relative_humidity, 0, 100, 1)
        self.field(controls, "Outdoor Wind Speed (m/s)", self.wind_speed, 0, 30, .1)
        self.field(controls, "Solar Radiation (W/m²)", self.solar_radiation, 0, 1200, 10)
        self.field(controls, "Mean Radiant Temp (°C)", self.mean_radiant_temp, -20, 60, .5)
        self.button(controls, "✓ APPLY CLIMATE DATA", self.apply_manual_climate, GREEN, BG).pack(fill="x", padx=10, pady=(3, 6))
        self.manual_climate_status = tk.Label(controls, text="Climate input not applied yet.", fg=ORANGE, bg=CARD, font=("Arial", 8, "bold"), wraplength=280, justify="left")
        self.manual_climate_status.pack(anchor="w", padx=10, pady=(0, 5))

        self.section(controls, "SHELTER DIMENSIONS")
        self.field(controls, "Length (m)", self.shelter_length, 1, 20, .1)
        self.field(controls, "Width (m)", self.shelter_width, 1, 20, .1)
        self.field(controls, "Height (m)", self.shelter_height, 1, 20, .1)
        self.section(controls, "GEOMETRY")
        self.geometry_combo = ttk.Combobox(controls, textvariable=self.geometry_type, values=["Cuboid", "Chamfered Corner"], state="readonly")
        self.geometry_combo.pack(fill="x", padx=10, pady=2); self.geometry_combo.bind("<<ComboboxSelected>>", self.mark_dirty)
        self.field(controls, "Corner Angle (30°–90°)", self.corner_angle, 30, 90, 5)
        self.section(controls, "THERMAL DESIGN")
        self.field(controls, "Target Indoor Temperature (°C)", self.target_temp, 10, 35, .5)
        tk.Label(controls, text="Wall Insulation Thickness (m)", fg=MUTED, bg=CARD, font=("Arial", 8)).pack(anchor="w", padx=10)
        tk.Scale(controls, from_=.05, to=.50, resolution=.01, orient="horizontal", variable=self.thickness, bg=CARD, fg="white", highlightthickness=0, command=self.mark_dirty).pack(fill="x", padx=10)
        tk.Label(controls, text="Wall Material", fg=MUTED, bg=CARD, font=("Arial", 8)).pack(anchor="w", padx=10)
        self.material_combo = ttk.Combobox(controls, textvariable=self.material_var, values=list(self.material_database.keys()), state="readonly")
        self.material_combo.pack(fill="x", padx=10, pady=2); self.material_combo.bind("<<ComboboxSelected>>", self.mark_dirty)
        self.section(controls, "PMV INPUTS")
        self.field(controls, "Indoor Air Speed (m/s)", self.indoor_air_speed, .05, 3, .05)
        self.field(controls, "Activity (met)", self.metabolic_rate, .8, 4, .1)
        self.field(controls, "Clothing (clo)", self.clothing_level, 0, 2, .1)
        self.field(controls, "Ventilation (ACH)", self.ventilation_ach, .1, 10, .1)
        self.field(controls, "Window-to-Wall Ratio", self.window_wall_ratio, 0, .5, .01)
        self.field(controls, "Window SHGC", self.window_shgc, .2, .9, .05)

        tk.Label(controls, text="Use the fixed PRIMARY ACTIONS bar above for Apply Climate, Solver, Heatmap, PDF and Analytics.", fg=MUTED, bg=CARD, font=("Arial", 8), wraplength=280, justify="left").pack(fill="x", padx=10, pady=(8, 4))
        self.optimizer_button = self.button(controls, "M4 — OPTIMIZE DESIGN", self.show_optimizer, PURPLE)
        self.optimizer_button.pack(fill="x", padx=10, pady=(2, 8))

        visual = tk.LabelFrame(main, text=" 3D Shelter + Simplified Thermal Visualization ", font=("Arial", 10, "bold"), fg=TEXT, bg=CARD)
        visual.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        fig = plt.Figure(figsize=(6.3, 6.0), facecolor=CARD); self.ax = fig.add_subplot(111, projection="3d")
        self.canvas = FigureCanvasTkAgg(fig, master=visual); self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.ax.set_facecolor(CARD)
        self.draw_placeholder()

        side = tk.Frame(main, bg=BG); side.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        summary = tk.LabelFrame(side, text=" CURRENT THERMAL STATE ", font=("Arial", 10, "bold"), fg=TEXT, bg=CARD)
        summary.pack(fill="x", pady=4)
        self.result_labels = {}
        for key, label in [("climate", "Environment"), ("outdoor", "Ambient Outdoor"), ("r", "R-value"), ("u", "U-value"), ("load", "Net Thermal Load"), ("pmv", "PMV"), ("ppd", "PPD"), ("status", "Thermal Status"), ("heatmap", "Heatmap Range"), ("source", "Environment Source")]:
            l = tk.Label(summary, text=f"{label}: —", font=(("Arial", 9, "bold") if key == "status" else ("Arial", 9)), fg=TEXT, bg=CARD, anchor="w", justify="left", wraplength=300)
            l.pack(fill="x", padx=12, pady=4); self.result_labels[key] = l
        self.status_label = tk.Label(side, text="⚠ Enter and APPLY manual climate data before running the solver.", font=("Arial", 9, "bold"), fg=ORANGE, bg=CARD, wraplength=320, justify="left")
        self.status_label.pack(fill="x", pady=4, padx=4)
        note = tk.LabelFrame(side, text=" MODEL TRANSPARENCY ", font=("Arial", 10, "bold"), fg=TEXT, bg=CARD)
        note.pack(fill="both", expand=True, pady=4)
        tk.Label(note, text="• PMV/PPD uses air temperature, mean radiant temperature, RH, air speed, activity and clothing.\n\n• 18–24°C is the project target design range, not a PMV comfort-zone shortcut.\n\n• Heatmap is a simplified visualization proxy, not CFD.\n\n• Material properties are provisional unless replaced with verified project-approved data.\n\n• Recommendations are screening outputs, not final engineering certification.", fg="#cbd5e1", bg=CARD, font=("Arial", 8), wraplength=310, justify="left", anchor="nw").pack(fill="both", expand=True, padx=12, pady=12)
        self.refresh_user_view()
        self.configure_primary_actions()

    def draw_placeholder(self):
        self.ax.clear(); self.ax.set_facecolor(CARD); self.ax.text2D(.5, .55, "Thermal model ready", transform=self.ax.transAxes, ha="center", color=GREEN, fontsize=14, weight="bold")
        self.ax.text2D(.5, .48, "Set shelter inputs and run the thermodynamic solver", transform=self.ax.transAxes, ha="center", color=MUTED, fontsize=9)
        self.ax.set_axis_off(); self.canvas.draw_idle()

    def validate_inputs(self):
        L, W, H = self.shelter_length.get(), self.shelter_width.get(), self.shelter_height.get()
        if not (1 <= L <= 20 and 1 <= W <= 20 and 1 <= H <= 20): raise ValueError("Shelter dimensions must be between 1 m and 20 m.")
        if not (30 <= self.corner_angle.get() <= 90): raise ValueError("Corner angle must be between 30° and 90°.")
        if not (-90 <= self.latitude.get() <= 90 and -180 <= self.longitude.get() <= 180): raise ValueError("Latitude/longitude are out of range.")
        if not (.05 <= self.thickness.get() <= .50): raise ValueError("Insulation thickness must be between 0.05 m and 0.50 m.")
        if not (10 <= self.target_temp.get() <= 35): raise ValueError("Target temperature must be between 10°C and 35°C.")
        if self.material_var.get() not in self.material_database: raise ValueError("Selected material is not available.")

    # ---------------- climate ----------------
    def fetch_climate_data(self, show_popup=True):
        try:
            lat, lon = float(self.latitude.get()), float(self.longitude.get())
            if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError("Coordinates are invalid.")
            params = urllib.parse.urlencode({
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,surface_pressure",
                "timezone": "auto"
            })
            url = "https://api.open-meteo.com/v1/forecast?" + params
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            cur = payload.get("current", {})
            required = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"]
            if any(k not in cur or cur[k] is None for k in required): raise ValueError("Climate API returned incomplete current data.")
            self.climate_data = {
                "temperature": float(cur["temperature_2m"]),
                "humidity": float(cur["relative_humidity_2m"]),
                "wind_speed": max(.05, float(cur["wind_speed_10m"]) / 3.6),
                "wind_direction": float(cur.get("wind_direction_10m") or 0),
                "solar_radiation": float(cur.get("shortwave_radiation") or 0),
                "surface_pressure": float(cur.get("surface_pressure") or 0),
                "timestamp": str(cur.get("time", datetime.now().isoformat(timespec="minutes"))),
                "latitude": lat, "longitude": lon,
            }
            self.ambient_temp.set(self.climate_data["temperature"])
            self.climate_loaded = True
            self.climate_mode = "LIVE — OPEN-METEO"
            self.climate_timestamp = self.climate_data["timestamp"]
            self.mark_dirty()
            if show_popup:
                messagebox.showinfo("Climate Data", f"Live climate loaded.\n\nTemperature: {self.climate_data['temperature']:.1f} °C\nRH: {self.climate_data['humidity']:.1f} %\nWind: {self.climate_data['wind_speed']:.2f} m/s\nSource: Open-Meteo\nTime: {self.climate_timestamp}")
            self.refresh_user_view()
        except Exception as exc:
            self.climate_loaded = False
            self.climate_mode = "NOT LOADED"
            self.climate_timestamp = "—"
            self.status_label.configure(text="⚠ Climate data unavailable — use Detect Location, check internet, or enter coordinates and try again.", fg=ORANGE) if hasattr(self, "status_label") else None
            if show_popup: messagebox.showerror("Climate Data", str(exc))

    def set_demo_climate(self):
        self.climate_data = {"temperature": -10.0, "humidity": 50.0, "wind_speed": .50, "wind_direction": 0.0, "solar_radiation": 150.0, "surface_pressure": 700.0, "timestamp": "DEMO DATASET", "latitude": self.latitude.get(), "longitude": self.longitude.get()}
        self.ambient_temp.set(-10.0); self.climate_loaded = True; self.climate_mode = "DEMO DATASET — NOT LIVE"; self.climate_timestamp = "DEMO DATASET"; self.mark_dirty(); self.refresh_user_view()

    def detect_device_location(self):
        try:
            import winrt.windows.devices.geolocation as geolocation
            import asyncio
            async def locate():
                access = await geolocation.Geolocator.request_access_async()
                access_s = str(access).lower()
                if "denied" in access_s or "unspecified" in access_s:
                    raise RuntimeError("Device location permission was not granted.")
                locator = geolocation.Geolocator()
                pos = await locator.get_geoposition_async()
                return pos.coordinate.point.position.latitude, pos.coordinate.point.position.longitude, getattr(pos.coordinate, "accuracy", None)
            lat, lon, acc = asyncio.run(locate())
            self.latitude.set(float(lat)); self.longitude.set(float(lon))
            self.mark_dirty()
            msg = f"Device location detected.\nLatitude: {lat:.6f}\nLongitude: {lon:.6f}"
            if acc: msg += f"\nAccuracy: {acc:.1f} m"
            messagebox.showinfo("Device Location", msg + "\n\nLocation updated. Climate values remain manually controlled in the Climate Data section.")
        except ImportError:
            messagebox.showwarning("Device Location", "Windows location support is not available in this Python environment. No coordinates were fabricated. Use manual coordinates or install the optional WinRT location dependency.")
        except Exception as exc:
            messagebox.showerror("Device Location", str(exc))

    def apply_manual_climate(self, show_popup=True):
        try:
            t = float(self.ambient_temp.get()); rh = float(self.relative_humidity.get())
            wind = float(self.wind_speed.get()); solar = float(self.solar_radiation.get()); tr = float(self.mean_radiant_temp.get())
            if not -50 <= t <= 60: raise ValueError("Outdoor temperature must be between -50°C and 60°C.")
            if not 0 <= rh <= 100: raise ValueError("Relative humidity must be between 0% and 100%.")
            if not 0 <= wind <= 30: raise ValueError("Wind speed must be between 0 and 30 m/s.")
            if not 0 <= solar <= 1200: raise ValueError("Solar radiation must be between 0 and 1200 W/m².")
            if not -20 <= tr <= 60: raise ValueError("Mean radiant temperature must be between -20°C and 60°C.")
            self.climate_data = {"temperature": t, "humidity": rh, "wind_speed": wind, "solar_radiation": solar, "mean_radiant_temp": tr, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "latitude": float(self.latitude.get()), "longitude": float(self.longitude.get())}
            self.climate_loaded = True; self.climate_mode = "MANUAL INPUT"; self.climate_timestamp = self.climate_data["timestamp"]
            self.last_results = {}
            self.last_heatmap_range = (None, None)
            self.dirty = True
            self.save_current_user_design(); self.refresh_user_view(); self.configure_primary_actions()
            if hasattr(self, "manual_climate_status"):
                self.manual_climate_status.configure(text=f"✓ Climate applied — {t:.1f}°C | RH {rh:.0f}% | Wind {wind:.1f} m/s | Solar {solar:.0f} W/m²", fg=GREEN)
            if show_popup: messagebox.showinfo("Climate Data", "Manual climate data applied successfully. Run the thermodynamic solver to calculate the updated thermal state.")
        except Exception as exc:
            self.climate_loaded = False; self.climate_mode = "NOT APPLIED"
            if show_popup: messagebox.showerror("Climate Data", str(exc))

    # ---------------- thermal model ----------------
    def calculate_state(self, material_name=None, thickness=None, target_temp=None, use_live=True):
        self.validate_inputs()
        mat = material_name or self.material_var.get()
        d = float(thickness if thickness is not None else self.thickness.get())
        tin_target = float(target_temp if target_temp is not None else self.target_temp.get())
        info = self.material_database[mat]
        if not self.climate_loaded:
            raise ValueError("Climate data has not been applied. Enter the manual climate values and click APPLY CLIMATE DATA first.")
        t_out = float(self.ambient_temp.get())
        rh = float(self.relative_humidity.get())
        wind_out = float(self.wind_speed.get())
        solar = float(self.solar_radiation.get())

        L, W, H = float(self.shelter_length.get()), float(self.shelter_width.get()), float(self.shelter_height.get())
        base_area = 2 * (L*W + L*H + W*H)
        wwr = float(self.window_wall_ratio.get())
        window_area = min(base_area * wwr, 0.8 * (2*(L*H + W*H)))
        envelope_area = max(1.0, base_area - window_area)
        volume = L * W * H
        R = d / max(info["k"], 1e-6)
        U = 1.0 / max(R, 1e-6)
        delta = tin_target - t_out
        q_cond = U * envelope_area * delta
        ach = float(self.ventilation_ach.get())
        rho_air, cp_air = 1.2, 1006.0
        q_vent = rho_air * cp_air * volume * (ach / 3600.0) * delta
        q_solar = solar * window_area * float(self.window_shgc.get())
        # A small fixed internal gain is explicitly labeled as an assumption, not a measurement.
        internal_gain = 150.0
        net_load = q_cond + q_vent - q_solar - internal_gain

        # Predict a passive indoor temperature for optimizer coupling.
        # This is a simplified steady-state balance, not a transient or CFD model.
        conductance = max(U * envelope_area + rho_air * cp_air * volume * (ach / 3600.0), 1e-6)
        predicted_t = t_out + (q_solar + internal_gain) / conductance
        # Keep prediction bounded around the design target to avoid an unstable visualization.
        predicted_t = float(np.clip(predicted_t, min(t_out - 10, tin_target - 8), max(t_out + 20, tin_target + 8)))
        predicted_tr = 0.65 * predicted_t + 0.35 * float(self.mean_radiant_temp.get())
        pmv, ppd, vapor = fanger_pmv_ppd(predicted_t, predicted_tr, float(self.indoor_air_speed.get()), rh, float(self.metabolic_rate.get()), float(self.clothing_level.get()))
        status, color = thermal_status(pmv, ppd)
        return {
            "material": mat, "thickness": d, "t_target": tin_target, "t_in": predicted_t, "t_out": t_out,
            "tr": predicted_tr, "rh": rh, "wind": wind_out, "solar": solar, "vapor_pressure": vapor,
            "r": R, "u": U, "envelope": envelope_area, "volume": volume, "window_area": window_area,
            "q_conduction": q_cond, "q_ventilation": q_vent, "q_solar": q_solar, "internal_gain": internal_gain,
            "net_load": net_load, "pmv": pmv, "ppd": ppd, "status": status, "color": color,
            "cost_index": info.get("cost_index", 0), "climate_source": "MANUAL INPUT",
        }

    def update_simulation(self, show_error=True):
        try:
            r = self.calculate_state()
            self.last_results = r
            self.dirty = False
            self.last_heatmap_range = self.heatmap_range(r)
            self.save_current_user_design()
            self.refresh_user_view()
            self.configure_primary_actions()
            if show_error:
                messagebox.showinfo("Thermodynamic Solver", f"Solver completed.\n\nPredicted indoor temperature: {r['t_in']:.2f} °C\nPMV: {r['pmv']:+.2f}\nPPD: {r['ppd']:.1f}%\nStatus: {r['status']}")
        except Exception as exc:
            if show_error: messagebox.showerror("Solver", str(exc))
            return None
        return r

    def heatmap_range(self, r):
        pts = self.generate_heatmap_points(r)
        return float(pts[:,3].min()), float(pts[:,3].max())

    # ---------------- geometry / heatmap ----------------
    def geometry_vertices_edges(self):
        L, W, H = float(self.shelter_length.get()), float(self.shelter_width.get()), float(self.shelter_height.get())
        if self.geometry_type.get() != "Chamfered Corner" or self.corner_angle.get() >= 89.9:
            v = np.array([[0,0,0],[L,0,0],[L,W,0],[0,W,0],[0,0,H],[L,0,H],[L,W,H],[0,W,H]], dtype=float)
            e = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
            return v, e
        # Visualization-only chamfer. Exact thermal-bridge behavior is not claimed.
        c = min(L, W) * .15 * (90 - float(self.corner_angle.get())) / 60
        c = max(0.02, min(c, min(L, W) * .24))
        base = np.array([[c,0],[L-c,0],[L,c],[L,W-c],[L-c,W],[c,W],[0,W-c],[0,c]], dtype=float)
        v = np.array([[x,y,z] for z in (0,H) for x,y in base], dtype=float)
        e = []
        for i in range(8): e += [(i,(i+1)%8),(8+i,8+(i+1)%8),(i,8+i)]
        return v, e

    def generate_heatmap_points(self, r, nx=10, ny=8, nz=5):
        L, W, H = float(self.shelter_length.get()), float(self.shelter_width.get()), float(self.shelter_height.get())
        x = np.linspace(.04*L, .96*L, nx); y = np.linspace(.04*W, .96*W, ny); z = np.linspace(.04*H, .96*H, nz)
        X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
        xn, yn, zn = X/L-.5, Y/W-.5, Z/H-.5
        geometry_factor = 1.0 + (90.0-float(self.corner_angle.get()))/180.0 if self.geometry_type.get() == "Chamfered Corner" else 1.0
        span = max(.25, min(5.0, abs(r["net_load"]) / max(1, r["envelope"]) / 120.0)) * geometry_factor
        spatial = .55*np.sin(math.pi*xn)*np.cos(math.pi*yn) + .35*zn
        boundary = .20*(abs(xn)+abs(yn)+abs(zn))
        temp = r["t_in"] + span*(spatial+boundary)
        return np.column_stack((X.ravel(), Y.ravel(), Z.ravel(), temp.ravel()))

    def draw_shelter(self, r):
        if not self.ax or not self.canvas: return
        self.ax.clear(); self.ax.set_facecolor(CARD)
        L, W, H = float(self.shelter_length.get()), float(self.shelter_width.get()), float(self.shelter_height.get())
        verts, edges = self.geometry_vertices_edges()
        for a,b in edges:
            self.ax.plot3D(*zip(*verts[[a,b]]), color=r["color"], linewidth=2.3)
        # Grid stays inside current geometry bounds.
        for gx in np.linspace(0,L,7): self.ax.plot([gx,gx],[0,W],[0,0], color="#475569", linewidth=.45, alpha=.6)
        for gy in np.linspace(0,W,7): self.ax.plot([0,L],[gy,gy],[0,0], color="#475569", linewidth=.45, alpha=.6)
        pts = self.generate_heatmap_points(r, 8, 6, 4)
        norm = Normalize(vmin=float(pts[:,3].min()), vmax=float(pts[:,3].max()) if pts[:,3].max()!=pts[:,3].min() else float(pts[:,3].min())+1)
        self.ax.scatter(pts[:,0], pts[:,1], pts[:,2], c=pts[:,3], cmap="coolwarm", norm=norm, s=16, alpha=.75)
        self.ax.set_xlim(0,L); self.ax.set_ylim(0,W); self.ax.set_zlim(0,H)
        self.ax.set_xlabel("Length (m)", color="white", fontsize=8); self.ax.set_ylabel("Width (m)", color="white", fontsize=8); self.ax.set_zlabel("Height (m)", color="white", fontsize=8)
        self.ax.tick_params(colors="white", labelsize=7)
        self.ax.set_title("ThermoShelter AI — 3D Thermal State", color="white", fontsize=11)
        self.ax.text2D(.02,.95, f"Proxy range: {pts[:,3].min():.1f}–{pts[:,3].max():.1f} °C\nPMV {r['pmv']:+.2f} | PPD {r['ppd']:.1f}%", transform=self.ax.transAxes, color="white", fontsize=8, va="top")
        self.canvas.draw_idle()

    # ---------------- user display ----------------
    def refresh_user_view(self):
        if self.current_screen != "user_dashboard" or not hasattr(self, "result_labels"): return
        self.result_labels["climate"].configure(text=f"Climate: {self.climate_mode}", fg=GREEN if self.climate_loaded else ORANGE)
        self.result_labels["outdoor"].configure(text=f"Ambient Outdoor: {self.ambient_temp.get():.1f} °C", fg=TEXT)
        if hasattr(self, "manual_climate_status"):
            if self.climate_loaded:
                self.manual_climate_status.configure(text=f"✓ Climate applied — {self.climate_mode} | {self.climate_timestamp}", fg=GREEN)
            else:
                self.manual_climate_status.configure(text="Climate input not applied yet. Click APPLY CLIMATE DATA before RUN SOLVER.", fg=ORANGE)
        self.result_labels["source"].configure(text=f"Climate Source: {self.climate_mode} | Updated: {self.climate_timestamp}", fg=MUTED)
        r = self.last_results if self.last_results and not self.dirty else None
        if r:
            self.result_labels["r"].configure(text=f"R-value: {r['r']:.3f} m²K/W")
            self.result_labels["u"].configure(text=f"U-value: {r['u']:.3f} W/m²K")
            self.result_labels["load"].configure(text=f"Net Thermal Load: {r['net_load']:+.1f} W")
            self.result_labels["pmv"].configure(text=f"PMV: {r['pmv']:+.2f}")
            self.result_labels["ppd"].configure(text=f"PPD: {r['ppd']:.1f}%")
            self.result_labels["status"].configure(text=f"Thermal Status: {r['status']}", fg=r['color'])
            lo, hi = self.last_heatmap_range
            self.result_labels["heatmap"].configure(text=f"Heatmap Range: {lo:.1f}–{hi:.1f} °C" if lo is not None else "Heatmap Range: —")
            self.status_label.configure(text="✓ Current design calculated — all displayed results are synchronized.", fg=GREEN)
            self.draw_shelter(r)
            self.configure_primary_actions()
        else:
            for key in ("r","u","load","pmv","ppd","status","heatmap"):
                self.result_labels[key].configure(text=self.result_labels[key].cget("text").split(":")[0] + ": —", fg=TEXT)
            self.status_label.configure(text="⚠ Apply manual climate data, then RUN SOLVER. Downstream results remain locked until calculation is synchronized.", fg=ORANGE)
            self.draw_placeholder()
            self.configure_primary_actions()

    # ---------------- optimizer ----------------
    def show_optimizer(self):
        # Optimizer uses the same manually applied climate conditions as the solver.
        if not self.climate_loaded:
            return messagebox.showwarning("Optimizer", "Apply the manual climate data first.")
        try: self.validate_inputs()
        except Exception as exc: return messagebox.showerror("Optimizer", str(exc))
        self.current_screen = "optimizer"; self.clear_root()
        self.create_header(self.root, "M4 — Material & Shelter Design Optimizer", "Candidate comparison uses the current climate, geometry and a simplified steady-state model.")
        top = tk.Frame(self.root, bg=BG); top.pack(fill="x", padx=12, pady=4)
        self.button(top, "← BACK TO DASHBOARD", self.show_user_dashboard, "#334155").pack(side="left")
        body = tk.Frame(self.root, bg=BG); body.pack(fill="both", expand=True, padx=12, pady=8)
        cols=("Material","Thickness","R","U","Pred. Indoor","Net Load","PMV","PPD","Status","Cost")
        tree=ttk.Treeview(body, columns=cols, show="headings", height=22)
        for c in cols: tree.heading(c,text=c); tree.column(c,width=105,anchor="center")
        tree.column("Material",width=140); tree.column("Status",width=170); tree.pack(fill="both",expand=True)
        rows=[]
        for mat in self.material_database:
            for d in [.05,.075,.10,.15,.20]:
                try:
                    rr=self.calculate_state(mat,d)
                    rows.append(rr)
                except Exception: pass
        rows.sort(key=lambda x:(abs(x["pmv"]),x["ppd"],abs(x["net_load"]),x["cost_index"]))
        self.last_optimization=rows
        for rr in rows:
            tree.insert("","end",values=(rr["material"],f"{rr['thickness']:.3f} m",f"{rr['r']:.3f}",f"{rr['u']:.3f}",f"{rr['t_in']:.1f} °C",f"{rr['net_load']:+.0f} W",f"{rr['pmv']:+.2f}",f"{rr['ppd']:.1f}%",rr["status"],f"{rr['cost_index']:.2f}"))
        tk.Label(self.root, text="Ranking is a prototype screening order: closest PMV to 0 → lower PPD → lower absolute load → lower cost index. This is not a final engineering selection.", fg=MUTED, bg=BG, font=("Arial",8), wraplength=1300, justify="left").pack(fill="x", padx=15, pady=8)

    # ---------------- integrated heatmap ----------------
    def show_heatmap_screen(self):
        if not self.last_results or self.dirty:
            return messagebox.showwarning("3D Heatmap", "Run the solver first. The heatmap uses the latest synchronized solver result.")
        self.current_screen="heatmap"; self.clear_root()
        self.create_header(self.root, "3D Thermal Heatmap", "Simplified spatial visualization derived from the current thermal state — not CFD.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4)
        self.button(top,"← BACK TO DASHBOARD",self.show_user_dashboard,"#334155").pack(side="left")
        self.button(top,"VIEW ANALYTICS",self.show_user_analytics,"#334155").pack(side="right")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=12,pady=8); body.columnconfigure(0,weight=3); body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1)
        vf=tk.LabelFrame(body,text=" 3D THERMAL HEATMAP ",font=("Arial",10,"bold"),fg=TEXT,bg=CARD); vf.grid(row=0,column=0,sticky="nsew",padx=5,pady=5)
        fig=plt.Figure(figsize=(8,6),facecolor=CARD); ax=fig.add_subplot(111,projection="3d"); self.heatmap_ax=ax; self.heatmap_canvas=FigureCanvasTkAgg(fig,master=vf); self.heatmap_canvas.get_tk_widget().pack(fill="both",expand=True)
        pts=self.generate_heatmap_points(self.last_results); self.draw_heatmap(ax,self.heatmap_canvas,pts,self.last_results)
        info=tk.LabelFrame(body,text=" HEATMAP ANALYTICS ",font=("Arial",10,"bold"),fg=TEXT,bg=CARD); info.grid(row=0,column=1,sticky="nsew",padx=5,pady=5)
        lo,hi=self.heatmap_range(self.last_results)
        lines=[f"Geometry: {self.geometry_type.get()}",f"Dimensions: {self.shelter_length.get():.2f} × {self.shelter_width.get():.2f} × {self.shelter_height.get():.2f} m",f"Corner: {self.corner_angle.get():.0f}°",f"Heatmap Range: {lo:.1f}–{hi:.1f} °C",f"Predicted Indoor: {self.last_results['t_in']:.1f} °C",f"PMV: {self.last_results['pmv']:+.2f}",f"PPD: {self.last_results['ppd']:.1f}%",f"Status: {self.last_results['status']}","","Interpretation","The field is a visualization proxy around the calculated indoor state. It is not measured data and is not a CFD result."]
        for i,t in enumerate(lines):
            tk.Label(info,text=t,font=(("Arial",9,"bold") if t in ("Interpretation",) else ("Arial",9)),fg=ORANGE if t=="Interpretation" else TEXT,bg=CARD,wraplength=300,justify="left",anchor="w").pack(fill="x",padx=15,pady=5)

    def draw_heatmap(self, ax, canvas, pts, r):
        ax.clear(); ax.set_facecolor(CARD)
        norm=Normalize(vmin=float(pts[:,3].min()),vmax=float(pts[:,3].max()) if pts[:,3].max()!=pts[:,3].min() else float(pts[:,3].min())+1)
        ax.scatter(pts[:,0],pts[:,1],pts[:,2],c=pts[:,3],cmap="coolwarm",norm=norm,s=24,alpha=.82)
        L,W,H=float(self.shelter_length.get()),float(self.shelter_width.get()),float(self.shelter_height.get())
        ax.set_xlim(0,L);ax.set_ylim(0,W);ax.set_zlim(0,H);ax.tick_params(colors="white",labelsize=7)
        ax.set_xlabel("Length (m)",color="white",fontsize=8);ax.set_ylabel("Width (m)",color="white",fontsize=8);ax.set_zlabel("Height (m)",color="white",fontsize=8)
        ax.set_title("ThermoShelter AI — Simplified Thermal Heatmap",color="white",fontsize=11)
        ax.text2D(.02,.96,f"{pts[:,3].min():.1f}–{pts[:,3].max():.1f} °C | PMV {r['pmv']:+.2f} | PPD {r['ppd']:.1f}%",transform=ax.transAxes,color="white",fontsize=9,va="top")
        canvas.draw_idle()

    # ---------------- analytics / recommendations ----------------
    def recommendations(self, r):
        rec=[]
        if r["pmv"] > .5:
            rec.append(("THERMAL RESPONSE", "Overheating tendency: review solar gain, ventilation/opening strategy and envelope assumptions, then recalculate."))
        elif r["pmv"] < -.5:
            rec.append(("THERMAL RESPONSE", "Underheating tendency: compare higher thermal resistance and ventilation control options, then recalculate."))
        else:
            rec.append(("THERMAL RESPONSE", "Current PMV is within the selected ±0.5 screening band; verify across seasonal/extreme conditions."))
        if r["t_out"] < 5:
            rec.append(("COLD-CLIMATE ADAPTATION", "Envelope resistance and uncontrolled ventilation deserve priority; review geometry for thermal-bridge-sensitive areas."))
        elif r["t_out"] > 30:
            rec.append(("HOT-CLIMATE ADAPTATION", "Review solar control, ventilation and passive/low-power cooling options."))
        else:
            rec.append(("CLIMATE ADAPTATION", "Current weather is one operating condition; test seasonal extremes before selecting a final design."))
        # Material screening recommendation uses the coupled simplified model.
        candidates=[]
        for mat in self.material_database:
            for d in [.05,.10,.15,.20]:
                try: candidates.append(self.calculate_state(mat,d))
                except Exception: pass
        if candidates:
            candidates.sort(key=lambda x:(abs(x["pmv"]),x["ppd"],abs(x["net_load"]),x["cost_index"]))
            best=candidates[0]
            rec.append(("MATERIAL SCREENING",f"Current screening selects {best['material']} at {best['thickness']:.2f} m by the prototype ranking. R={best['r']:.3f} m²K/W, predicted indoor={best['t_in']:.1f} °C. Verify properties and structural/moisture/fire requirements before engineering use."))
        return rec

    def show_user_analytics(self):
        if not self.last_results or self.dirty:
            return messagebox.showwarning("Analytics", "Run the solver after the latest changes so Analytics uses synchronized results.")
        self.current_screen="analytics"; self.clear_root()
        self.create_header(self.root,"ThermoShelter AI — Analytics & Recommendations","Integrated main-screen analytics — no disconnected popup window.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4)
        self.button(top,"← BACK TO DASHBOARD",self.show_user_dashboard,"#334155").pack(side="left")
        self.button(top,"EXPORT BLUEPRINT PDF",self.export_blueprint_pdf,GREEN).pack(side="right")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=12,pady=8)
        for c in range(3): body.columnconfigure(c,weight=1)
        body.rowconfigure(0,weight=1); body.rowconfigure(1,weight=1)
        def card(title,r,c):
            f=tk.LabelFrame(body,text=title,font=("Arial",10,"bold"),fg=TEXT,bg=CARD); f.grid(row=r,column=c,sticky="nsew",padx=5,pady=5); return f
        c1=card("CURRENT DESIGN & ENVIRONMENT",0,0); c2=card("THERMAL PERFORMANCE",0,1); c3=card("DESIGN RECOMMENDATIONS",0,2); c4=card("PMV MODEL INPUTS & ASSUMPTIONS",1,0); c5=card("GEOMETRY & HEATMAP",1,1); c6=card("TRACEABILITY",1,2)
        r=self.last_results; cd=self.climate_data
        for t in [f"User: {self.user_accounts[self.current_user]['name']}",f"Geometry: {self.geometry_type.get()}",f"Dimensions: {self.shelter_length.get():.2f} × {self.shelter_width.get():.2f} × {self.shelter_height.get():.2f} m",f"Corner: {self.corner_angle.get():.0f}°",f"Material: {r['material']}",f"Thickness: {r['thickness']:.3f} m",f"Target: {r['t_target']:.1f} °C",f"Ambient outdoor: {r['t_out']:.1f} °C",f"RH assumption: {r['rh']:.1f}%",f"Wind assumption: {r['wind']:.2f} m/s"]: tk.Label(c1,text=t,fg=TEXT,bg=CARD,font=("Arial",9),anchor="w").pack(fill="x",padx=12,pady=3)
        for t in [f"R-value: {r['r']:.3f} m²K/W",f"U-value: {r['u']:.3f} W/m²K",f"Conduction: {r['q_conduction']:+.1f} W",f"Ventilation: {r['q_ventilation']:+.1f} W",f"Solar proxy: {r['q_solar']:+.1f} W",f"Net load: {r['net_load']:+.1f} W",f"Predicted indoor: {r['t_in']:.1f} °C",f"PMV: {r['pmv']:+.2f}",f"PPD: {r['ppd']:.1f}%",f"Status: {r['status']}"]:
            tk.Label(c2,text=t,fg=r['color'] if t.startswith("Status") else TEXT,bg=CARD,font=(("Arial",9,"bold") if t.startswith("Status") else ("Arial",9)),anchor="w").pack(fill="x",padx=12,pady=3)
        for a,b in self.recommendations(r):
            tk.Label(c3,text=a,fg=GREEN,bg=CARD,font=("Arial",9,"bold"),wraplength=360,anchor="w",justify="left").pack(fill="x",padx=12,pady=(6,1)); tk.Label(c3,text=b,fg="#cbd5e1",bg=CARD,font=("Arial",8),wraplength=360,anchor="w",justify="left").pack(fill="x",padx=12,pady=(0,5))
        for t in [f"Air temperature used: {r['t_in']:.2f} °C",f"Mean radiant temperature: {r['tr']:.2f} °C",f"Relative humidity: {r['rh']:.1f}%",f"Air speed: {self.indoor_air_speed.get():.2f} m/s",f"Activity: {self.metabolic_rate.get():.1f} met",f"Clothing: {self.clothing_level.get():.1f} clo", "PMV/PPD: prototype Fanger formulation", "Target 18–24°C: project design range, not PMV shortcut"]: tk.Label(c4,text=t,fg=TEXT,bg=CARD,font=("Arial",8),anchor="w",wraplength=360,justify="left").pack(fill="x",padx=12,pady=3)
        lo,hi=self.last_heatmap_range
        for t in [f"Geometry: {self.geometry_type.get()}",f"Corner angle: {self.corner_angle.get():.0f}°",f"Surface envelope area: {r['envelope']:.2f} m²",f"Volume: {r['volume']:.2f} m³",f"Heatmap range: {lo:.1f}–{hi:.1f} °C", "Visualization: simplified spatial proxy", "Not CFD / not a measured temperature field"]: tk.Label(c5,text=t,fg=TEXT,bg=CARD,font=("Arial",8),anchor="w",wraplength=360,justify="left").pack(fill="x",padx=12,pady=3)
        for t in [f"Environment source: Manual ambient input",f"Climate mode: Manual input",f"Location: {self.latitude.get():.6f}, {self.longitude.get():.6f}",f"Last calculated: {self.user_accounts[self.current_user].get('updated_at','—')}","Research basis: supplied shelter/thermal-comfort papers, Fanger PMV/PPD, ASHRAE 55, ISO 7730", "Climate is manually entered for this prototype test", "No claim of standards certification or validated CFD"]: tk.Label(c6,text=t,fg=TEXT,bg=CARD,font=("Arial",8),anchor="w",wraplength=360,justify="left").pack(fill="x",padx=12,pady=3)

    # ---------------- PDF ----------------
    def export_blueprint_pdf(self):
        if not REPORTLAB_AVAILABLE:
            return messagebox.showerror("PDF Export", "ReportLab is not installed. Install reportlab and try again.")
        if not self.last_results or self.dirty:
            return messagebox.showwarning("PDF Export", "Run the solver after the latest changes before exporting.")
        path = filedialog.asksaveasfilename(title="Save ThermoShelter Blueprint PDF", defaultextension=".pdf", filetypes=[("PDF files","*.pdf")], initialfile="ThermoShelter_AI_Blueprint.pdf")
        if not path: return
        try:
            r=self.last_results; pts=self.generate_heatmap_points(r)
            doc=SimpleDocTemplate(path,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36)
            styles=getSampleStyleSheet(); title=ParagraphStyle("TS",parent=styles["Title"],fontSize=19,leading=23,spaceAfter=8); h=ParagraphStyle("H",parent=styles["Heading2"],fontSize=12,leading=15,spaceBefore=8,spaceAfter=5); body=ParagraphStyle("B",parent=styles["BodyText"],fontSize=8.5,leading=11)
            story=[Paragraph("ThermoShelter AI — Final Prototype Blueprint & Thermal Analysis",title),Paragraph("SIH26051 | Team Agnit | Software-based area-specific shelter thermal-comfort prototype",body),Spacer(1,10)]
            story.append(Paragraph("1. Shelter Specification",h)); spec=[["Parameter","Value"],["Geometry",self.geometry_type.get()],["Dimensions",f"{self.shelter_length.get():.2f} × {self.shelter_width.get():.2f} × {self.shelter_height.get():.2f} m"],["Corner angle",f"{self.corner_angle.get():.0f}°"],["Material",r["material"]],["Thickness",f"{r['thickness']:.3f} m"],["Location",f"{self.latitude.get():.6f}, {self.longitude.get():.6f}"]]
            t=Table(spec,colWidths=[155,325]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d9f99d")),("GRID",(0,0),(-1,-1),.4,colors.grey),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8)])); story.append(t)
            story.append(Paragraph("2. Climate & Thermal Results",h)); data=[["Metric","Result"],["Environment source","Manual climate input"],["Outdoor temperature",f"{r['t_out']:.2f} °C"],["RH",f"{r['rh']:.1f}%"],["R-value",f"{r['r']:.3f} m²K/W"],["U-value",f"{r['u']:.3f} W/m²K"],["Net thermal load",f"{r['net_load']:+.1f} W"],["Predicted indoor temperature",f"{r['t_in']:.2f} °C"],["PMV",f"{r['pmv']:+.2f}"],["PPD",f"{r['ppd']:.1f}%"],["Thermal status",r["status"]],["Heatmap proxy range",f"{pts[:,3].min():.1f}–{pts[:,3].max():.1f} °C"]]
            t=Table(data,colWidths=[155,325]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d9f99d")),("GRID",(0,0),(-1,-1),.4,colors.grey),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8)])); story.append(t)
            story.append(Paragraph("3. PMV Model Inputs",h)); story.append(Paragraph(f"Air temperature={r['t_in']:.2f} °C; mean radiant temperature={r['tr']:.2f} °C; RH={r['rh']:.1f}%; air speed={self.indoor_air_speed.get():.2f} m/s; activity={self.metabolic_rate.get():.1f} met; clothing={self.clothing_level.get():.1f} clo.",body))
            story.append(Paragraph("4. Recommendations",h));
            for a,b in self.recommendations(r): story.append(Paragraph(f"<b>{a}</b> — {b}",body)); story.append(Spacer(1,3))
            story.append(Paragraph("5. Research & Standards Basis",h)); story.append(Paragraph("Development basis includes the five supplied shelter/thermal-comfort studies, Fanger PMV/PPD methodology, ASHRAE Standard 55 and ISO 7730. The prototype does not claim standards certification, experimental validation or validated CFD. Material property values must be verified against authoritative project-approved data before engineering deployment.",body))
            story.append(Paragraph("6. Limitations",h)); story.append(Paragraph("The heatmap is a simplified spatial visualization proxy. The thermal solver is a simplified steady-state analytical model with an explicit internal-gain assumption and is not a complete transient shelter simulation. Corner-angle visualization does not constitute validated thermal-bridge simulation. Device location depends on operating-system support and permission.",body))
            doc.build(story)
            messagebox.showinfo("PDF Export", f"Blueprint PDF created successfully:\n{path}")
        except Exception as exc:
            messagebox.showerror("PDF Export", str(exc))

    # ---------------- admin ----------------
    def show_admin_login(self):
        self.current_screen="admin_login"; self.clear_root()
        card=tk.Frame(self.root,bg=CARD,highlightbackground="#334155",highlightthickness=1); card.place(relx=.5,rely=.5,anchor="center",width=580,height=470)
        tk.Label(card,text="ADMIN / DRDO OVERSIGHT",font=("Arial",20,"bold"),fg=BLUE,bg=CARD).pack(pady=(42,28))
        form=tk.Frame(card,bg=CARD); form.pack(fill="x",padx=75)
        tk.Label(form,text="Admin Username",fg="#cbd5e1",bg=CARD,font=("Arial",10,"bold")).pack(anchor="w")
        self.admin_user_entry=tk.Entry(form,bg=BG,fg="white",insertbackground="white",relief="flat",font=("Arial",11)); self.admin_user_entry.pack(fill="x",pady=(5,15),ipady=8)
        tk.Label(form,text="Admin Password",fg="#cbd5e1",bg=CARD,font=("Arial",10,"bold")).pack(anchor="w")
        self.admin_pass_entry=tk.Entry(form,show="*",bg=BG,fg="white",insertbackground="white",relief="flat",font=("Arial",11)); self.admin_pass_entry.pack(fill="x",pady=(5,22),ipady=8)
        self.button(card,"ADMIN LOGIN",self.handle_admin_login,BLUE,BG).pack()
        tk.Label(card,text="Demo admin: admin / admin123",font=("Arial",8),fg="#64748b",bg=CARD).pack(pady=9)
        self.button(card,"BACK TO USER LOGIN",self.show_auth_screen,BG,MUTED).pack()

    def handle_admin_login(self):
        if self.admin_user_entry.get().strip()==ADMIN_USERNAME and self.admin_pass_entry.get()==ADMIN_PASSWORD:
            self.current_role="ADMIN"; self.selected_user=next(iter(self.user_accounts), None); self.show_admin_dashboard()
        else: messagebox.showerror("Admin Login Failed","Invalid admin credentials.")

    def admin_nav(self, screen):
        if screen == "dashboard": self.show_admin_dashboard()
        elif screen == "materials": self.admin_materials()
        elif screen == "spec": self.admin_specification()
        elif screen == "boundaries": self.admin_boundaries()
        elif screen == "analytics": self.admin_analytics()
        elif screen == "switch": self.admin_switch_user()

    def show_admin_dashboard(self):
        self.current_screen="admin_dashboard"; self.current_role="ADMIN"; self.clear_root()
        self.create_header(self.root,"ThermoShelter AI — Admin / DRDO Oversight","SIH26051 | Team Agnit | Integrated administrative review")
        self.workflow_bar(self.root,"ADMIN")

        # Persistent admin action bar: Switch User and report export are always visible.
        actionbar=tk.Frame(self.root,bg=CARD,highlightbackground="#334155",highlightthickness=1); actionbar.pack(fill="x",padx=12,pady=4)
        tk.Label(actionbar,text="ADMIN ACTIONS",fg=BLUE,bg=CARD,font=("Arial",8,"bold")).pack(side="left",padx=10)
        self.button(actionbar,"SWITCH USER",self.admin_switch_user,BLUE,BG).pack(side="left",padx=3,pady=4)
        self.button(actionbar,"ANALYTICS & REPORTS",self.admin_analytics,GREEN).pack(side="left",padx=3,pady=4)
        self.button(actionbar,"EXPORT SELECTED USER PDF",self.export_admin_selected_pdf,ORANGE,BG).pack(side="left",padx=3,pady=4)
        self.button(actionbar,"LOG OUT",self.show_auth_screen,RED).pack(side="right",padx=6,pady=4)

        nav=tk.Frame(self.root,bg=CARD); nav.pack(fill="x",padx=12,pady=5)
        nav_items=[
            ("ADMIN HOME","dashboard"),("MATERIAL BASES","materials"),
            ("SHELTER SPECIFICATION","spec"),("ENVIRONMENT BOUNDARIES","boundaries"),
            ("ANALYTICS & REPORTS","analytics"),("SWITCH USER","switch")
        ]
        for text,screen in nav_items:
            self.button(nav,text,lambda s=screen:self.admin_nav(s),"#334155",TEXT).pack(side="left",padx=3,pady=5)

        main=tk.Frame(self.root,bg=BG); main.pack(fill="both",expand=True,padx=12,pady=6)
        main.rowconfigure(1,weight=1)
        main.columnconfigure(0,weight=1)

        selected=self.user_accounts.get(self.selected_user,{}) if self.selected_user else {}
        selected_name=selected.get("name","No user selected")
        session=tk.LabelFrame(main,text=" ADMIN SESSION ",font=("Arial",10,"bold"),fg=TEXT,bg=CARD)
        session.grid(row=0,column=0,sticky="ew",padx=5,pady=5)
        session.columnconfigure((0,1,2,3),weight=1)
        for col,(label,value) in enumerate([
            ("ROLE","ADMIN / DRDO"),("ACCOUNT",ADMIN_USERNAME),
            ("SELECTED USER",selected_name),("CLIMATE MODULE","MANUAL INPUT")
        ]):
            tk.Label(session,text=label,fg=MUTED,bg=CARD,font=("Arial",8,"bold")).grid(row=0,column=col,sticky="w",padx=12,pady=(9,2))
            tk.Label(session,text=value,fg=GREEN if "CLIMATE" in label else TEXT,bg=CARD,font=("Arial",9,"bold")).grid(row=1,column=col,sticky="w",padx=12,pady=(0,9))

        grid=tk.Frame(main,bg=BG); grid.grid(row=1,column=0,sticky="nsew",padx=0,pady=2)
        for c in range(2): grid.columnconfigure(c,weight=1)
        for r in range(3): grid.rowconfigure(r,weight=1)

        self.admin_card(grid,"2. Material Bases","View/edit prototype material properties and source labels.",0,0,"materials")
        self.admin_card(grid,"3. Shelter Specification","View the selected user's actual current shelter design.",0,1,"spec")
        self.admin_card(grid,"4. Environment Boundaries","Configure review boundaries and compare the selected user's manual environment.",1,0,"boundaries")
        self.admin_card(grid,"5. Analytics & Reports","Review synchronized thermal results, design and recommendations.",1,1,"analytics")
        self.admin_card(grid,"Switch User","Select another registered user without changing their credentials.",2,0,"switch")

        summary=tk.Frame(grid,bg=CARD,highlightbackground="#334155",highlightthickness=1)
        summary.grid(row=2,column=1,sticky="nsew",padx=7,pady=7)
        tk.Label(summary,text="CURRENT USER DETAILS",font=("Arial",12,"bold"),fg=BLUE,bg=CARD).pack(anchor="w",padx=15,pady=(15,7))
        d=selected.get("design",{}) if selected else {}
        r=d.get("last_results",{}) or {}
        lines=[
            f"User: {selected_name}",
            f"Geometry: {d.get('geometry_type','—')}",
            f"Dimensions: {d.get('length','—')} × {d.get('width','—')} × {d.get('height','—')} m",
            f"Material: {d.get('material','—')} | Thickness: {d.get('thickness','—')} m",
            f"Ambient outdoor: {d.get('ambient_temp','—')} °C", f"RH: {d.get('relative_humidity',50)} %", f"Wind: {d.get('wind_speed',0.5)} m/s", f"Solar: {d.get('solar_radiation',150)} W/m²",
            f"Last PMV: {r.get('pmv','—')} | PPD: {r.get('ppd','—')}%",
            f"Status: {r.get('status','—')}",
        ]
        for line in lines:
            tk.Label(summary,text=line,fg=TEXT,bg=CARD,font=("Arial",8),anchor="w",wraplength=500,justify="left").pack(fill="x",padx=15,pady=3)

    def admin_card(self,parent,title,desc,row,col,screen):
        card=tk.Frame(parent,bg=CARD,highlightbackground="#334155",highlightthickness=1); card.grid(row=row,column=col,sticky="nsew",padx=7,pady=7)
        tk.Label(card,text=title,font=("Arial",12,"bold"),fg=BLUE,bg=CARD).pack(anchor="w",padx=15,pady=(15,7)); tk.Label(card,text=desc,font=("Arial",9),fg=MUTED,bg=CARD,wraplength=520,justify="left").pack(anchor="w",padx=15,pady=(0,10)); self.button(card,"OPEN",lambda:self.admin_nav(screen),"#334155").pack(anchor="e",padx=15,pady=(0,14))

    def export_admin_selected_pdf(self):
        if not self.selected_user:
            return messagebox.showwarning("PDF Export", "Select a user first.")
        user = self.user_accounts.get(self.selected_user, {})
        d = user.get("design", {})
        r = d.get("last_results", {}) or {}
        if not r:
            return messagebox.showwarning("PDF Export", "The selected user has no completed solver result yet.")
        # Reuse the user's synchronized result by temporarily making it the active session.
        old_user = self.current_user
        old_results = self.last_results
        old_mode = self.climate_mode
        try:
            self.current_user = self.selected_user
            self.last_results = r
            self.climate_mode = "MANUAL INPUT"
            self.export_blueprint_pdf()
        finally:
            self.current_user = old_user
            self.last_results = old_results
            self.climate_mode = old_mode

    def admin_back(self): self.show_admin_dashboard()

    def admin_switch_user(self):
        self.current_screen="admin_switch"; self.clear_root(); self.create_header(self.root,"Admin — Switch User","Select a registered user for inspection. This does not impersonate or alter credentials.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4); self.button(top,"← ADMIN HOME",self.show_admin_dashboard,"#334155").pack(side="left")
        frame=tk.Frame(self.root,bg=CARD); frame.pack(fill="both",expand=True,padx=25,pady=15)
        tk.Label(frame,text="SELECT USER",font=("Arial",14,"bold"),fg=BLUE,bg=CARD).pack(anchor="w",padx=20,pady=15)
        if not self.user_accounts:
            tk.Label(frame,text="No registered users are available yet. Create a user account from User Access first.",fg=ORANGE,bg=CARD,font=("Arial",10)).pack(anchor="w",padx=20,pady=20); return
        var=tk.StringVar(value=self.selected_user or next(iter(self.user_accounts)))
        combo=ttk.Combobox(frame,textvariable=var,values=list(self.user_accounts.keys()),state="readonly",width=50); combo.pack(anchor="w",padx=20,pady=10)
        details=tk.Label(frame,text="",fg=TEXT,bg=CARD,font=("Arial",9),justify="left"); details.pack(anchor="w",padx=20,pady=10)
        def update_details(*_):
            u=self.user_accounts.get(var.get(),{}); d=u.get("design",{}); lr=d.get("last_results",{}); details.configure(text=f"Name: {u.get('name','—')}\nLast update: {u.get('updated_at','—')}\nAmbient outdoor: {d.get('ambient_temp','—')} °C\nLast PMV: {lr.get('pmv','—')}\nLast PPD: {lr.get('ppd','—')}")
        combo.bind("<<ComboboxSelected>>",update_details); update_details()
        def choose():
            self.selected_user=var.get(); self.load_user_design(self.selected_user); self.show_admin_dashboard()
        self.button(frame,"VIEW SELECTED USER",choose,BLUE,BG).pack(anchor="w",padx=20,pady=10)
        self.button(frame,"EXPORT SELECTED USER PDF",self.export_admin_selected_pdf,ORANGE,BG).pack(anchor="w",padx=20,pady=6)

    def admin_materials(self):
        self.current_screen="admin_materials"; self.clear_root(); self.create_header(self.root,"Admin — Material Bases","Step 2 of Admin / DRDO workflow — editable prototype material database.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4); self.button(top,"← ADMIN HOME",self.show_admin_dashboard,"#334155").pack(side="left")
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=15,pady=8)
        cols=("Material","k W/mK","Density kg/m³","Cp J/kgK","Emissivity","Cost","Source")
        tree=ttk.Treeview(body,columns=cols,show="headings",height=13)
        for c in cols: tree.heading(c,text=c); tree.column(c,width=120,anchor="center")
        tree.column("Material",width=145);tree.column("Source",width=380);tree.pack(fill="both",expand=True)
        def refresh():
            for i in tree.get_children(): tree.delete(i)
            for m,v in self.material_database.items(): tree.insert("","end",values=(m,f"{v['k']:.3f}",f"{v['density']:.1f}",f"{v['cp']:.0f}",f"{v['emissivity']:.2f}",f"{v['cost_index']:.2f}",v['source']))
        refresh()
        edit=tk.Frame(body,bg=CARD); edit.pack(fill="x",pady=8)
        vars_={k:tk.StringVar() for k in ["name","k","density","cp","emissivity","cost","source"]}
        for label,key in [("Material","name"),("k","k"),("Density","density"),("Cp","cp"),("Emissivity","emissivity"),("Cost","cost"),("Source","source")]:
            tk.Label(edit,text=label,fg=MUTED,bg=CARD,font=("Arial",8)).pack(side="left",padx=(8,2)); tk.Entry(edit,textvariable=vars_[key],width=12,bg=BG,fg="white",insertbackground="white",relief="flat").pack(side="left",padx=(0,7))
        def load(*_):
            s=tree.selection()
            if not s:return
            vals=tree.item(s[0],"values")
            for key,val in zip(["name","k","density","cp","emissivity","cost","source"],vals): vars_[key].set(val)
        def save():
            try:
                n=vars_["name"].get().strip();
                if not n: raise ValueError("Material name is required.")
                self.material_database[n]={"k":float(vars_["k"].get()),"density":float(vars_["density"].get()),"cp":float(vars_["cp"].get()),"emissivity":float(vars_["emissivity"].get()),"cost_index":float(vars_["cost"].get()),"source":vars_["source"].get().strip() or "Admin prototype entry"}
                self.save_accounts(); refresh(); messagebox.showinfo("Material Bases","Material saved.",parent=self.root)
            except Exception as exc: messagebox.showerror("Material Bases",str(exc),parent=self.root)
        tree.bind("<<TreeviewSelect>>",load); self.button(edit,"SAVE / ADD MATERIAL",save,BLUE,BG).pack(side="left",padx=5)
        tk.Label(self.root,text="Material values are provisional unless verified against authoritative project-approved data. They are not taken as exact values from the supplied research papers.",fg=MUTED,bg=BG,font=("Arial",8),wraplength=1250,justify="left").pack(fill="x",padx=18,pady=8)

    def admin_specification(self):
        self.current_screen="admin_spec"; self.clear_root(); self.create_header(self.root,"Admin — Shelter Specification","Step 3 of Admin / DRDO workflow — current selected user's design.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4); self.button(top,"← ADMIN HOME",self.show_admin_dashboard,"#334155").pack(side="left"); self.button(top,"SWITCH USER",self.admin_switch_user,BLUE,BG).pack(side="right")
        if not self.selected_user: return
        d=self.user_accounts[self.selected_user].get("design",{}); r=d.get("last_results",{}) or {}
        frame=tk.Frame(self.root,bg=CARD); frame.pack(fill="both",expand=True,padx=25,pady=15)
        rows=[("Selected User",self.user_accounts[self.selected_user].get("name","—")),("Geometry",d.get("geometry_type","—")),("Dimensions",f"{d.get('length','—')} × {d.get('width','—')} × {d.get('height','—')} m"),("Corner Angle",f"{d.get('corner_angle','—')}°"),("Material",d.get("material","—")),("Thickness",f"{d.get('thickness','—')} m"),("Target Temperature",f"{d.get('target_temp','—')} °C"),("Location",f"{d.get('latitude','—')}, {d.get('longitude','—')}"),("Ambient Outdoor",f"{d.get('ambient_temp','—')} °C"),("Environment Source","Manual climate input"),("Last PMV",str(r.get("pmv","—"))),("Last PPD",str(r.get("ppd","—"))),("Thermal Status",str(r.get("status","—")))]
        for i,(a,b) in enumerate(rows):
            tk.Label(frame,text=a,fg=MUTED,bg=CARD,font=("Arial",10,"bold")).grid(row=i,column=0,sticky="w",padx=20,pady=8); tk.Label(frame,text=b,fg=TEXT,bg=CARD,font=("Arial",10)).grid(row=i,column=1,sticky="w",padx=20,pady=8)

    def admin_boundaries(self):
        self.current_screen="admin_boundaries"; self.clear_root(); self.create_header(self.root,"Admin — Environment Boundaries","Step 4 of Admin / DRDO workflow — configurable review boundaries, not certification limits.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4); self.button(top,"← ADMIN HOME",self.show_admin_dashboard,"#334155").pack(side="left")
        frame=tk.Frame(self.root,bg=CARD); frame.pack(fill="both",expand=True,padx=25,pady=15)
        entries={}
        labels=[("Minimum design temperature","min_temp"),("Maximum design temperature","max_temp"),("Minimum thickness (m)","min_thickness"),("Maximum thickness (m)","max_thickness"),("Minimum PMV alert","min_pmv"),("Maximum PMV alert","max_pmv")]
        for i,(lab,key) in enumerate(labels):
            tk.Label(frame,text=lab,fg=MUTED,bg=CARD,font=("Arial",9)).grid(row=i,column=0,sticky="w",padx=20,pady=9); v=tk.StringVar(value=str(self.admin_boundary_vars[key])); entries[key]=v; tk.Entry(frame,textvariable=v,bg=BG,fg="white",insertbackground="white",relief="flat",width=20).grid(row=i,column=1,padx=20,pady=9)
        def save():
            try:
                vals={k:float(v.get()) for k,v in entries.items()}
                if vals["min_temp"]>=vals["max_temp"] or vals["min_thickness"]>=vals["max_thickness"] or vals["min_pmv"]>=vals["max_pmv"]: raise ValueError("Minimum values must be lower than maximum values.")
                self.admin_boundary_vars=vals; messagebox.showinfo("Environment Boundaries","Boundary values saved for this application session.",parent=self.root)
            except Exception as exc: messagebox.showerror("Environment Boundaries",str(exc),parent=self.root)
        self.button(frame,"SAVE BOUNDARY VALUES",save,BLUE,BG).grid(row=6,column=0,columnspan=2,pady=15)
        if self.selected_user:
            d=self.user_accounts[self.selected_user].get("design",{})
            temp=d.get("ambient_temp")
            status="NO AMBIENT VALUE"
            if temp is not None:
                status="WITHIN BOUNDARY" if self.admin_boundary_vars["min_temp"]<=float(temp)<=self.admin_boundary_vars["max_temp"] else "OUTSIDE BOUNDARY"
            tk.Label(frame,text=f"Selected user manual environment check: {status}",fg=GREEN if status=="WITHIN BOUNDARY" else ORANGE,bg=CARD,font=("Arial",10,"bold")).grid(row=7,column=0,columnspan=2,pady=12)
            tk.Label(frame,text="Boundary review uses the user's explicit manual climate inputs.",fg=MUTED,bg=CARD,font=("Arial",8)).grid(row=8,column=0,columnspan=2,pady=4)

    def admin_analytics(self):
        self.current_screen="admin_analytics"; self.clear_root(); self.create_header(self.root,"Admin — Analytics & Reports","Step 5 of Admin / DRDO workflow — selected user's synchronized project results.")
        top=tk.Frame(self.root,bg=BG); top.pack(fill="x",padx=12,pady=4); self.button(top,"← ADMIN HOME",self.show_admin_dashboard,"#334155").pack(side="left"); self.button(top,"SWITCH USER",self.admin_switch_user,BLUE,BG).pack(side="left",padx=5)
        if not self.selected_user: return
        d=self.user_accounts[self.selected_user].get("design",{}); r=d.get("last_results",{}) or {}
        if not r:
            tk.Label(self.root,text="No solver result is currently stored for the selected user. Open User Access, run the solver, then return to Admin.",fg=ORANGE,bg=BG,font=("Arial",11,"bold")).pack(anchor="w",padx=25,pady=25); return
        body=tk.Frame(self.root,bg=BG); body.pack(fill="both",expand=True,padx=15,pady=8)
        for col in range(3): body.columnconfigure(col,weight=1)
        for row in range(2): body.rowconfigure(row,weight=1)
        def card(title,row,col):
            f=tk.LabelFrame(body,text=title,font=("Arial",10,"bold"),fg=TEXT,bg=CARD); f.grid(row=row,column=col,sticky="nsew",padx=5,pady=5); return f
        a=card("SELECTED USER",0,0); b=card("THERMAL PERFORMANCE",0,1); cbox=card("CLIMATE",0,2); dbox=card("DESIGN & GEOMETRY",1,0); e=card("RECOMMENDATIONS",1,1); f=card("TRACEABILITY",1,2)
        for t in [f"User: {self.user_accounts[self.selected_user].get('name','—')}",f"Account: {self.selected_user}",f"Updated: {self.user_accounts[self.selected_user].get('updated_at','—')}","Admin action: VIEW / INSPECT"]: tk.Label(a,text=t,fg=TEXT,bg=CARD,font=("Arial",9),anchor="w").pack(fill="x",padx=12,pady=5)
        for t in [f"R-value: {r.get('r','—')}",f"U-value: {r.get('u','—')}",f"Net load: {r.get('net_load','—')} W",f"Predicted indoor: {r.get('t_in','—')} °C",f"PMV: {r.get('pmv','—')}",f"PPD: {r.get('ppd','—')}%",f"Status: {r.get('status','—')}"]:
            tk.Label(b,text=t,fg=r.get('color',TEXT) if t.startswith("Status") else TEXT,bg=CARD,font=(("Arial",9,"bold") if t.startswith("Status") else ("Arial",9)),anchor="w").pack(fill="x",padx=12,pady=5)
        for t in [f"Climate source: Manual input",f"Climate timestamp: {d.get('climate_data',{}).get('timestamp','—')}",f"Ambient outdoor: {d.get('ambient_temp','—')} °C", f"RH: {d.get('relative_humidity',50)} %", f"Wind: {d.get('wind_speed',0.5)} m/s", f"Solar radiation: {d.get('solar_radiation',150)} W/m²"]: tk.Label(cbox,text=t,fg=TEXT,bg=CARD,font=("Arial",9),anchor="w").pack(fill="x",padx=12,pady=5)
        for t in [f"Geometry: {d.get('geometry_type','—')}",f"Dimensions: {d.get('length','—')} × {d.get('width','—')} × {d.get('height','—')} m",f"Corner: {d.get('corner_angle','—')}°",f"Material: {d.get('material','—')}",f"Thickness: {d.get('thickness','—')} m"]: tk.Label(dbox,text=t,fg=TEXT,bg=CARD,font=("Arial",9),anchor="w").pack(fill="x",padx=12,pady=5)
        # Recommendations are recalculated from the selected user's saved state where possible.
        rec_text=["Use the selected user's stored solver state.","Compare material/thickness alternatives in the User optimizer.","Re-test after any geometry, material or ambient-temperature change.","Climate is manually entered; do not interpret it as live API data.","Do not treat the heatmap as CFD or measured data."]
        for t in rec_text: tk.Label(e,text="• "+t,fg="#cbd5e1",bg=CARD,font=("Arial",9),wraplength=350,justify="left",anchor="w").pack(fill="x",padx=12,pady=5)
        for t in ["Research basis: supplied project papers + Fanger PMV/PPD + ASHRAE 55 + ISO 7730","Material properties require authoritative verification","Admin analytics is oversight, not engineering certification"]: tk.Label(f,text=t,fg="#cbd5e1",bg=CARD,font=("Arial",8),wraplength=350,justify="left",anchor="w").pack(fill="x",padx=12,pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except Exception:
        pass
    app = ThermoShelterApp(root)
    root.mainloop()
