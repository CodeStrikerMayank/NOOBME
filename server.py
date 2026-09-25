import os
import time
import urllib.request
import urllib.parse
import json
import hashlib
import threading
import uuid
import shutil
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any, List

from core.thermo_solver import (
    calculate_state,
    generate_architectural_shelter,
    MATERIAL_DATABASE,
    EXTREME_LOCATION_PRESETS
)
from core.pdf_generator import generate_blueprint_pdf

app = FastAPI(title="ThermoShelter AI API", version="2.5.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- GLOBAL EXCEPTION SAFETY NET ----------
# Guarantees EVERY response is valid JSON, preventing frontend "Unexpected token" crashes.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all: converts any unhandled Python crash into a proper JSON response."""
    print(f"[UNHANDLED EXCEPTION] {request.method} {request.url.path}: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request: Request, exc: ValidationError):
    """Pydantic model validation errors → clean JSON instead of raw 422 HTML."""
    return JSONResponse(
        status_code=422,
        content={"detail": f"Invalid request data: {exc.error_count()} validation error(s)."}
    )

# ---------- ONBOARD AUDIT & STORAGE (CORRUPTION-PROOF) ----------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
ONBOARD_DATA_FILE = os.path.join(DATA_DIR, "onboard_users.json")
ONBOARD_BACKUP_FILE = os.path.join(DATA_DIR, "onboard_users.json.bak")
STORAGE_LOCK = threading.RLock()

# Protected accounts that can never be wiped or deleted
PROTECTED_ACCOUNTS = frozenset({"admin", "engineer"})

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_default_users() -> Dict[str, Any]:
    return {
        "admin": {
            "username": "admin",
            "name": "DRDO Oversight & Admin",
            "password_hash": hash_pw("1234@admin"),
            "password_hash_alt": hash_pw("12345"),
            "role": "Chief Administrator",
            "created_at": "2026-09-20T10:02:10.737829",
            "designs": []
        },
        "engineer": {
            "username": "engineer",
            "name": "Lead Thermal Systems Engineer",
            "password_hash": hash_pw("engineer123"),
            "password_hash_alt": hash_pw("12345"),
            "role": "Alpine Design Engineer",
            "created_at": "2026-09-20T10:02:10.737882",
            "designs": []
        }
    }

def get_default_database() -> Dict[str, Any]:
    return {
        "users": get_default_users(),
        "login_history": [
            {
                "username": "admin",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "role": "Chief Administrator",
                "status": "Success",
                "client": "Onboard Workstation"
            }
        ],
        "activity_log": [
            {
                "username": "system",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "Database Initialized",
                "details": "Ready for high-capacity sub-zero thermal simulation"
            }
        ],
        "reports_generated": []
    }

def _sanitize_data(data: Any) -> Dict[str, Any]:
    """Ensures structure integrity, guarantees essential admin/engineer accounts, and types."""
    default_users = get_default_users()
    if not isinstance(data, dict):
        data = get_default_database()

    users = data.get("users")
    if not isinstance(users, dict) or not users:
        data["users"] = default_users
    else:
        # Guarantee admin account exists and has valid credentials
        if "admin" not in data["users"] or not isinstance(data["users"].get("admin"), dict):
            data["users"]["admin"] = default_users["admin"]
        else:
            data["users"]["admin"]["username"] = "admin"
            data["users"]["admin"]["password_hash"] = hash_pw("1234@admin")
            data["users"]["admin"]["password_hash_alt"] = hash_pw("12345")
            data["users"]["admin"]["role"] = "Chief Administrator"
            if not data["users"]["admin"].get("name"):
                data["users"]["admin"]["name"] = "DRDO Oversight & Admin"
            if not isinstance(data["users"]["admin"].get("designs"), list):
                data["users"]["admin"]["designs"] = []

        # Guarantee engineer account exists and has valid credentials
        if "engineer" not in data["users"] or not isinstance(data["users"].get("engineer"), dict):
            data["users"]["engineer"] = default_users["engineer"]
        else:
            data["users"]["engineer"]["username"] = "engineer"
            data["users"]["engineer"]["password_hash"] = hash_pw("engineer123")
            data["users"]["engineer"]["password_hash_alt"] = hash_pw("12345")
            data["users"]["engineer"]["role"] = "Alpine Design Engineer"
            if not data["users"]["engineer"].get("name"):
                data["users"]["engineer"]["name"] = "Lead Thermal Systems Engineer"
            if not isinstance(data["users"]["engineer"].get("designs"), list):
                data["users"]["engineer"]["designs"] = []

        # Validate all user entries have required fields
        for uname, udata in list(data["users"].items()):
            if not isinstance(udata, dict):
                del data["users"][uname]
                continue
            udata.setdefault("username", uname)
            udata.setdefault("name", uname)
            udata.setdefault("role", "Thermal Design Engineer")
            udata.setdefault("created_at", datetime.now().isoformat())
            if not isinstance(udata.get("designs"), list):
                udata["designs"] = []

    if not isinstance(data.get("login_history"), list):
        data["login_history"] = []
    if not isinstance(data.get("activity_log"), list):
        data["activity_log"] = []
    if not isinstance(data.get("reports_generated"), list):
        data["reports_generated"] = []

    return data

def load_onboard_data() -> Dict[str, Any]:
    with STORAGE_LOCK:
        default_data = get_default_database()

        if not os.path.exists(ONBOARD_DATA_FILE):
            save_onboard_data(default_data)
            return default_data

        data = None

        # 1. Attempt reading primary database file
        try:
            with open(ONBOARD_DATA_FILE, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except Exception as e:
            print(f"[WARN] Primary database read failed: {e}")
            data = None

        # 2. If primary failed or empty, attempt reading backup file
        if data is None and os.path.exists(ONBOARD_BACKUP_FILE):
            try:
                with open(ONBOARD_BACKUP_FILE, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        print(f"[INFO] Restored database from backup file {ONBOARD_BACKUP_FILE}")
            except Exception as e:
                print(f"[WARN] Backup database read failed: {e}")
                data = None

        # 3. If both failed, use default database and quarantine corrupt file
        if data is None:
            data = default_data
            try:
                corrupt_backup = ONBOARD_DATA_FILE + f".corrupt_{int(datetime.now().timestamp())}"
                if os.path.exists(ONBOARD_DATA_FILE):
                    shutil.copy2(ONBOARD_DATA_FILE, corrupt_backup)
                    print(f"[WARN] Quarantined corrupted file to {corrupt_backup}")
            except Exception:
                pass

        # 4. Enforce strict sanitization and guarantee required structure
        sanitized = _sanitize_data(data)
        return sanitized

def save_onboard_data(data: Dict[str, Any]):
    with STORAGE_LOCK:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            sanitized = _sanitize_data(data)

            # Step 1: Pre-serialize in memory to guarantee zero serialization errors
            json_text = json.dumps(sanitized, indent=2, ensure_ascii=False)

            # Step 2: Write to a unique temporary file to eliminate race conditions
            unique_tmp = os.path.join(DATA_DIR, f".tmp_{uuid.uuid4().hex}.json")
            with open(unique_tmp, "w", encoding="utf-8") as f:
                f.write(json_text)
                f.flush()
                os.fsync(f.fileno())

            # Step 3: Maintain rolling backup before replacement
            if os.path.exists(ONBOARD_DATA_FILE):
                try:
                    shutil.copy2(ONBOARD_DATA_FILE, ONBOARD_BACKUP_FILE)
                except Exception:
                    pass

            # Step 4: Atomic rename/replace (with multi-attempt lock release guard)
            replaced = False
            for _ in range(5):
                try:
                    os.replace(unique_tmp, ONBOARD_DATA_FILE)
                    replaced = True
                    break
                except (PermissionError, OSError):
                    time.sleep(0.02)
            if not replaced:
                with open(ONBOARD_DATA_FILE, "w", encoding="utf-8") as f:
                    f.write(json_text)
                try:
                    os.remove(unique_tmp)
                except Exception:
                    pass

        except Exception as e:
            print(f"[CRITICAL ERROR] Failed to save onboard data: {e}")

def _cleanup_stale_tmp_files():
    """Remove any leftover .tmp_*.json files from interrupted saves."""
    try:
        for f in os.listdir(DATA_DIR):
            if f.startswith(".tmp_") and f.endswith(".json"):
                try:
                    os.remove(os.path.join(DATA_DIR, f))
                except Exception:
                    pass
    except Exception:
        pass

# ---------------- MODELS ----------------
class SolveRequest(BaseModel):
    thickness_mm: float = 250.0
    ambient_temp: float = -10.0
    material_name: str = "High-Performance Composite"
    target_temp: float = 21.0
    shelter_length: float = 6.0
    shelter_width: float = 5.0
    shelter_height: float = 2.8
    relative_humidity: float = 50.0
    wind_speed: float = 0.5
    solar_radiation: float = 150.0
    occupancy_count: int = 6
    username: Optional[str] = "guest"

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = False

class SignUpRequest(BaseModel):
    username: str
    name: str
    password: str
    role: Optional[str] = "Thermal Design Engineer"

class SaveDesignRequest(BaseModel):
    username: str
    design_name: Optional[str] = "Alpine Emergency Shelter"
    parameters: Dict[str, Any]
    results: Dict[str, Any]

class PurgeLogsRequest(BaseModel):
    admin_username: str

# ---------------- AUTH ENDPOINTS ----------------
@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request):
    try:
        data = load_onboard_data()
        users = data.get("users", {})
        uname = req.username.strip().lower()

        if not uname:
            raise HTTPException(status_code=400, detail="Username is required.")

        # Special admin check (accepts 1234@admin, 12345, or admin123)
        if uname == "admin":
            if req.password not in ["1234@admin", "12345", "admin123"]:
                raise HTTPException(status_code=401, detail="Invalid admin password. Admin password is '1234@admin'.")
            user = users.get("admin") or get_default_users()["admin"]
        elif uname == "engineer":
            user = users.get("engineer") or get_default_users()["engineer"]
            pw_hash = hash_pw(req.password)
            if user.get("password_hash") != pw_hash and user.get("password_hash_alt") != pw_hash and req.password not in ["engineer123", "12345"]:
                raise HTTPException(status_code=401, detail="Invalid password for engineer account.")
        else:
            user = users.get(uname)
            if not user:
                raise HTTPException(status_code=401, detail=f"User account '{req.username}' not found. Please verify username or register a new operator account.")
            pw_hash = hash_pw(req.password)
            if user.get("password_hash") != pw_hash and user.get("password_hash_alt") != pw_hash:
                raise HTTPException(status_code=401, detail="Invalid username or password.")

        # Safely extract client IP
        client_ip = "Unknown"
        try:
            if request and request.client and request.client.host:
                client_ip = request.client.host
        except Exception:
            pass

        # Log session in audit history safely
        login_entry = {
            "username": user.get("username", uname),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": user.get("role", "Engineer"),
            "status": "Success",
            "remember_me": bool(req.remember_me),
            "client": client_ip
        }
        data.setdefault("login_history", []).insert(0, login_entry)
        data["login_history"] = data["login_history"][:100]
        save_onboard_data(data)

        return {
            "status": "success",
            "user": {
                "username": user.get("username", uname),
                "name": user.get("name", uname),
                "role": user.get("role", "Engineer"),
                "is_admin": (uname == "admin"),
                "designs": user.get("designs", []),
                "remember_me": bool(req.remember_me)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Login exception: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@app.post("/api/auth/signup")
def signup(req: SignUpRequest):
    try:
        u = req.username.strip().lower()
        if not u:
            raise HTTPException(status_code=400, detail="Username is required.")
        if len(u) < 2:
            raise HTTPException(status_code=400, detail="Username must be at least 2 characters.")
        if len(req.password) < 4:
            raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
        if u in PROTECTED_ACCOUNTS:
            raise HTTPException(status_code=400, detail=f"Username '{u}' is reserved and cannot be registered.")

        data = load_onboard_data()
        users = data.setdefault("users", {})
        if u in users:
            raise HTTPException(status_code=400, detail="Username already exists in onboard system.")

        users[u] = {
            "username": u,
            "name": req.name.strip() or u,
            "password_hash": hash_pw(req.password),
            "role": req.role or "Thermal Design Engineer",
            "created_at": datetime.now().isoformat(),
            "designs": []
        }

        # Log signup
        data.setdefault("activity_log", []).insert(0, {
            "username": u,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Account Created",
            "details": f"Role: {users[u]['role']}"
        })
        data["activity_log"] = data["activity_log"][:100]
        save_onboard_data(data)

        return {
            "status": "success",
            "user": {
                "username": u,
                "name": users[u]["name"],
                "role": users[u]["role"],
                "designs": []
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Signup exception: {e}")
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

# ---------------- ADMIN & USER ROLE ENDPOINTS ----------------
@app.get("/api/admin/audit")
def get_admin_audit_data(username: Optional[str] = None):
    """Returns complete onboard storage data for the DRDO Admin Dashboard (Admin Clearance Only)."""
    if username != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access Denied: DRDO Chief Administrator clearance required to access the whole-system storage vault."
        )

    try:
        data = load_onboard_data()
        users_summary = []
        for u in data.get("users", {}).values():
            if not isinstance(u, dict):
                continue
            users_summary.append({
                "username": u.get("username", "unknown"),
                "name": u.get("name", "Unknown"),
                "role": u.get("role", "User"),
                "created_at": u.get("created_at", "Pre-configured"),
                "designs_count": len(u.get("designs", []))
            })

        # Storage file metrics
        storage_size_kb = 0
        if os.path.exists(ONBOARD_DATA_FILE):
            try:
                storage_size_kb = round(os.path.getsize(ONBOARD_DATA_FILE) / 1024, 2)
            except Exception:
                pass

        return {
            "status": "success",
            "total_users": len(users_summary),
            "storage_size_kb": storage_size_kb,
            "storage_path": ONBOARD_DATA_FILE,
            "users": users_summary,
            "login_history": data.get("login_history", [])[:50],
            "activity_log": data.get("activity_log", [])[:50],
            "reports_generated": data.get("reports_generated", [])[:50]
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Admin audit exception: {e}")
        raise HTTPException(status_code=500, detail=f"Admin audit error: {str(e)}")

@app.get("/api/admin/raw-vault")
def get_raw_storage_vault(username: Optional[str] = None):
    """Admin Power: Inspect raw JSON vault directly."""
    if username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")
    try:
        data = load_onboard_data()
        # Mask password hashes for defense security while showing structure
        safe_data = json.loads(json.dumps(data))
        for u in safe_data.get("users", {}).values():
            if isinstance(u, dict):
                if "password_hash" in u:
                    u["password_hash"] = "[SHA-256 ENCRYPTED]"
                if "password_hash_alt" in u:
                    u["password_hash_alt"] = "[SHA-256 ENCRYPTED]"
        return safe_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Raw vault exception: {e}")
        raise HTTPException(status_code=500, detail=f"Vault inspection error: {str(e)}")

@app.post("/api/admin/purge-logs")
def purge_audit_logs(req: PurgeLogsRequest):
    """Admin Power: Cleanse and archive old audit logs."""
    if req.admin_username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")
    try:
        data = load_onboard_data()
        data["login_history"] = data.get("login_history", [])[:3]
        data["activity_log"] = [
            {
                "username": "admin",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "System Logs Purged",
                "details": "Admin executed audit log clearance protocol"
            }
        ]
        data["reports_generated"] = data.get("reports_generated", [])[:5]
        save_onboard_data(data)
        return {"status": "success", "message": "Audit logs purged successfully."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Purge logs exception: {e}")
        raise HTTPException(status_code=500, detail=f"Purge error: {str(e)}")

@app.delete("/api/admin/user/{target_username}")
def delete_user_account(target_username: str, admin_username: Optional[str] = None):
    """Admin Power: Decommission an operator account."""
    if admin_username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")

    target_lower = target_username.strip().lower()

    if target_lower in PROTECTED_ACCOUNTS:
        raise HTTPException(status_code=400, detail=f"Cannot delete protected system account '{target_lower}'.")

    try:
        data = load_onboard_data()
        users = data.get("users", {})
        if target_lower not in users:
            raise HTTPException(status_code=404, detail="Operator account not found.")

        del users[target_lower]
        data.setdefault("activity_log", []).insert(0, {
            "username": "admin",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Operator Decommissioned",
            "details": f"Account '{target_username}' removed from onboard system"
        })
        save_onboard_data(data)
        return {"status": "success", "message": f"Operator '{target_username}' successfully decommissioned."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Delete user exception: {e}")
        raise HTTPException(status_code=500, detail=f"Account deletion error: {str(e)}")

@app.get("/api/user/account")
def get_user_personal_account(username: str):
    """Normal User: Compartmentalized personal profile and activity ONLY (cannot see whole system)."""
    try:
        uname = username.strip().lower()
        if not uname:
            raise HTTPException(status_code=400, detail="Username is required.")

        data = load_onboard_data()
        users = data.get("users", {})

        user = users.get(uname)
        if not user:
            # Fallback for protected accounts even if wiped from disk
            default_users = get_default_users()
            if uname in default_users:
                user = default_users[uname]
            else:
                raise HTTPException(status_code=404, detail="Operator account not found.")

        # Filter ONLY this user's personal entries
        personal_logins = [l for l in data.get("login_history", []) if isinstance(l, dict) and l.get("username", "").lower() == uname][:20]
        personal_activities = [a for a in data.get("activity_log", []) if isinstance(a, dict) and a.get("username", "").lower() == uname][:20]
        personal_reports = [r for r in data.get("reports_generated", []) if isinstance(r, dict) and r.get("username", "").lower() == uname][:20]

        return {
            "status": "success",
            "is_admin": (uname == "admin"),
            "user": {
                "username": user.get("username", uname),
                "name": user.get("name", uname),
                "role": user.get("role", "Field Engineer"),
                "created_at": user.get("created_at", "Active"),
                "designs_count": len(user.get("designs", []))
            },
            "personal_metrics": {
                "my_total_logins": len(personal_logins),
                "my_total_simulations": len(personal_activities),
                "my_total_reports": len(personal_reports)
            },
            "personal_logins": personal_logins,
            "personal_activities": personal_activities,
            "personal_reports": personal_reports
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] User account exception: {e}")
        raise HTTPException(status_code=500, detail=f"Account lookup error: {str(e)}")

# ---------------- SIMULATION & PDF ENDPOINTS ----------------
@app.get("/api/materials")
def get_materials():
    return MATERIAL_DATABASE

@app.get("/api/presets")
def get_presets():
    return EXTREME_LOCATION_PRESETS

@app.post("/api/solve")
def solve_thermal_model(req: SolveRequest):
    try:
        results = calculate_state(
            thickness_mm=req.thickness_mm,
            ambient_temp=req.ambient_temp,
            material_name=req.material_name,
            target_temp=req.target_temp,
            shelter_length=req.shelter_length,
            shelter_width=req.shelter_width,
            shelter_height=req.shelter_height,
            relative_humidity=req.relative_humidity,
            wind_speed=req.wind_speed,
            solar_radiation=req.solar_radiation,
            occupancy_count=req.occupancy_count
        )
        shelter_3d = generate_architectural_shelter(
            thickness_mm=req.thickness_mm,
            ambient_temp=req.ambient_temp,
            indoor_temp=results["t_in"]
        )

        # Log action in onboard activity history (non-blocking: don't crash solve if logging fails)
        try:
            data = load_onboard_data()
            data.setdefault("activity_log", []).insert(0, {
                "username": req.username or "guest",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "Simulation Computed",
                "details": f"{req.material_name} | {req.thickness_mm:.0f}mm | Tamb {req.ambient_temp}°C | Eff {results['thermal_efficiency']:.0f}%"
            })
            data["activity_log"] = data["activity_log"][:60]
            save_onboard_data(data)
        except Exception as log_err:
            print(f"[WARN] Simulation logging failed (non-fatal): {log_err}")

        return {
            "status": "success",
            "results": results,
            "shelter_3d": shelter_3d
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Solve exception: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/export-pdf")
def export_pdf(req: SolveRequest):
    try:
        results = calculate_state(
            thickness_mm=req.thickness_mm,
            ambient_temp=req.ambient_temp,
            material_name=req.material_name,
            target_temp=req.target_temp,
            shelter_length=req.shelter_length,
            shelter_width=req.shelter_width,
            shelter_height=req.shelter_height,
            relative_humidity=req.relative_humidity,
            wind_speed=req.wind_speed,
            solar_radiation=req.solar_radiation,
            occupancy_count=req.occupancy_count
        )
        pdf_bytes = generate_blueprint_pdf(results)

        # Log report generation in audit store (non-blocking)
        try:
            data = load_onboard_data()
            report_record = {
                "username": req.username or "engineer",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "material": req.material_name,
                "thickness": f"{req.thickness_mm:.0f}mm",
                "efficiency": f"{results['thermal_efficiency']:.0f}%",
                "heating_load": f"{results['heating_load_kwh_day']:.1f} kWh/day",
                "diesel_liters": f"{results['diesel_liters_day']:.1f} L/day",
                "status": results["status"]
            }
            data.setdefault("reports_generated", []).insert(0, report_record)
            data["reports_generated"] = data["reports_generated"][:50]
            save_onboard_data(data)
        except Exception as log_err:
            print(f"[WARN] PDF report logging failed (non-fatal): {log_err}")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ThermoShelter_Tactical_Blueprint.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] PDF export exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live-climate")
def fetch_live_climate(lat: float = 34.2090, lon: float = 77.5750):
    try:
        params = urllib.parse.urlencode({
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation",
            "timezone": "auto"
        })
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "ThermoShelter-AI/2.5"})
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
        cur = data.get("current", {})
        return {
            "temperature": float(cur.get("temperature_2m", -18.0)),
            "humidity": float(cur.get("relative_humidity_2m", 45.0)),
            "wind_speed": round(float(cur.get("wind_speed_10m", 12.0)) / 3.6, 2),
            "solar_radiation": float(cur.get("shortwave_radiation", 180.0))
        }
    except Exception:
        return {
            "temperature": -25.0,
            "humidity": 40.0,
            "wind_speed": 10.5,
            "solar_radiation": 160.0,
            "fallback": True
        }

# ---------------- HEALTH & KEEP-AWAKE WORKER ----------------
@app.get("/healthz")
def healthz():
    """Health check endpoint used by keep-awake worker and external monitors."""
    return {"status": "ok", "service": "thermoshelter-ai", "version": "2.5.1", "timestamp": datetime.now().isoformat()}

def _keep_awake_worker():
    """Background thread that pings the server every N seconds to prevent Render free-tier sleep."""
    interval = int(os.environ.get("KEEP_AWAKE_INTERVAL_SECONDS", "600"))
    ext_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    print(f"[KEEP-AWAKE] Started worker (interval: {interval}s, external_url: {ext_url or 'Localhost'})")

    time.sleep(20)  # Wait for server to fully boot
    while True:
        try:
            if ext_url:
                target_url = f"{ext_url.rstrip('/')}/healthz"
            else:
                port = os.environ.get("PORT", "8000")
                target_url = f"http://127.0.0.1:{port}/healthz"

            req = urllib.request.Request(target_url, headers={"User-Agent": "ThermoShelter-KeepAwake/1.0"})
            with urllib.request.urlopen(req, timeout=15) as res:
                pass
        except Exception:
            pass
        time.sleep(interval)

@app.on_event("startup")
def startup_event():
    """Pre-initialize database and start background services on server boot."""
    print("[STARTUP] ThermoShelter AI v2.5.1 initializing...")

    # Clean up leftover temp files from interrupted saves
    _cleanup_stale_tmp_files()

    # Pre-initialize and verify onboard user database
    data = load_onboard_data()
    user_count = len(data.get("users", {}))
    print(f"[STARTUP] Database verified: {user_count} operator accounts loaded.")

    # Start keep-awake worker thread to prevent Render free instance spin-down
    t = threading.Thread(target=_keep_awake_worker, daemon=True)
    t.start()
    print("[STARTUP] Keep-awake worker launched.")

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting ThermoShelter AI v2.5.1 at http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
