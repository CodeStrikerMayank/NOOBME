import os
import urllib.request
import urllib.parse
import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from core.thermo_solver import (
    calculate_state,
    generate_architectural_shelter,
    MATERIAL_DATABASE,
    EXTREME_LOCATION_PRESETS
)
from core.pdf_generator import generate_blueprint_pdf

app = FastAPI(title="ThermoShelter AI API", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ONBOARD AUDIT & STORAGE ----------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
ONBOARD_DATA_FILE = os.path.join(DATA_DIR, "onboard_users.json")

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def load_onboard_data() -> Dict[str, Any]:
    if not os.path.exists(ONBOARD_DATA_FILE):
        default_data = {
            "users": {
                "admin": {
                    "username": "admin",
                    "name": "DRDO Oversight & Admin",
                    "password_hash": hash_pw("12345"),
                    "password_hash_alt": hash_pw("admin123"),
                    "role": "Chief Administrator",
                    "created_at": datetime.now().isoformat(),
                    "designs": []
                },
                "engineer": {
                    "username": "engineer",
                    "name": "Lead Thermal Systems Engineer",
                    "password_hash": hash_pw("engineer123"),
                    "password_hash_alt": hash_pw("12345"),
                    "role": "Alpine Design Engineer",
                    "created_at": datetime.now().isoformat(),
                    "designs": []
                }
            },
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
        save_onboard_data(default_data)
        return default_data
    try:
        with open(ONBOARD_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure admin password accepts 1234@admin (and backwards-compatible 12345)
            if "users" in data and "admin" in data["users"]:
                data["users"]["admin"]["password_hash"] = hash_pw("1234@admin")
                data["users"]["admin"]["password_hash_alt"] = hash_pw("12345")
                data["users"]["admin"]["role"] = "Chief Administrator"
            data.setdefault("login_history", [])
            data.setdefault("activity_log", [])
            data.setdefault("reports_generated", [])
            return data
    except Exception:
        return {"users": {}, "login_history": [], "activity_log": [], "reports_generated": []}

def save_onboard_data(data: Dict[str, Any]):
    with open(ONBOARD_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

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
    data = load_onboard_data()
    users = data.get("users", {})
    uname = req.username.strip().lower()
    
    # Special admin check (accepts 1234@admin, 12345, or admin123)
    if uname == "admin":
        if req.password not in ["1234@admin", "12345", "admin123"]:
            raise HTTPException(status_code=401, detail="Invalid admin password. Admin password is '1234@admin'.")
        user = users.get("admin")
    else:
        user = users.get(uname)
        if not user:
            raise HTTPException(status_code=401, detail="User account not found.")
        pw_hash = hash_pw(req.password)
        if user.get("password_hash") != pw_hash and user.get("password_hash_alt") != pw_hash:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    # Log session in audit history
    login_entry = {
        "username": user["username"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "role": user.get("role", "Engineer"),
        "status": "Success",
        "remember_me": bool(req.remember_me),
        "client": request.client.host if request.client else "Localhost"
    }
    data.setdefault("login_history", []).insert(0, login_entry)
    # Cap history at 100 entries
    data["login_history"] = data["login_history"][:100]
    save_onboard_data(data)

    return {
        "status": "success",
        "user": {
            "username": user["username"],
            "name": user["name"],
            "role": user.get("role", "Engineer"),
            "is_admin": (user["username"] == "admin"),
            "designs": user.get("designs", []),
            "remember_me": req.remember_me
        }
    }

@app.post("/api/auth/signup")
def signup(req: SignUpRequest):
    u = req.username.strip().lower()
    if not u:
        raise HTTPException(status_code=400, detail="Username is required.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")
    
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

# ---------------- ADMIN & USER ROLE ENDPOINTS ----------------
@app.get("/api/admin/audit")
def get_admin_audit_data(username: Optional[str] = None):
    """Returns complete onboard storage data for the DRDO Admin Dashboard (Admin Clearance Only)."""
    if username != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access Denied: DRDO Chief Administrator clearance required to access the whole-system storage vault."
        )
    
    data = load_onboard_data()
    users_summary = [
        {
            "username": u["username"],
            "name": u["name"],
            "role": u.get("role", "User"),
            "created_at": u.get("created_at", "Pre-configured"),
            "designs_count": len(u.get("designs", []))
        }
        for u in data.get("users", {}).values()
    ]
    
    # Storage file metrics
    storage_size_kb = 0
    if os.path.exists(ONBOARD_DATA_FILE):
        storage_size_kb = round(os.path.getsize(ONBOARD_DATA_FILE) / 1024, 2)

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

@app.get("/api/admin/raw-vault")
def get_raw_storage_vault(username: Optional[str] = None):
    """Admin Power: Inspect raw JSON vault directly."""
    if username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")
    data = load_onboard_data()
    # Mask password hashes for defense security while showing structure
    safe_data = json.loads(json.dumps(data))
    for u in safe_data.get("users", {}).values():
        if "password_hash" in u:
            u["password_hash"] = "[SHA-256 ENCRYPTED]"
        if "password_hash_alt" in u:
            u["password_hash_alt"] = "[SHA-256 ENCRYPTED]"
    return safe_data

@app.post("/api/admin/purge-logs")
def purge_audit_logs(req: PurgeLogsRequest):
    """Admin Power: Cleanse and archive old audit logs."""
    if req.admin_username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")
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
    save_onboard_data(data)
    return {"status": "success", "message": "Audit logs purged successfully."}

@app.delete("/api/admin/user/{target_username}")
def delete_user_account(target_username: str, admin_username: Optional[str] = None):
    """Admin Power: Decommission an operator account."""
    if admin_username != "admin":
        raise HTTPException(status_code=403, detail="Administrator clearance required.")
    if target_username.lower() == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete Master Administrator account.")
    
    data = load_onboard_data()
    users = data.get("users", {})
    if target_username.lower() not in users:
        raise HTTPException(status_code=404, detail="Operator account not found.")
    
    del users[target_username.lower()]
    data.setdefault("activity_log", []).insert(0, {
        "username": "admin",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": "Operator Decommissioned",
        "details": f"Account '{target_username}' removed from onboard system"
    })
    save_onboard_data(data)
    return {"status": "success", "message": f"Operator '{target_username}' successfully decommissioned."}

@app.get("/api/user/account")
def get_user_personal_account(username: str):
    """Normal User: Compartmentalized personal profile and activity ONLY (cannot see whole system)."""
    uname = username.strip().lower()
    data = load_onboard_data()
    users = data.get("users", {})
    
    user = users.get(uname)
    if not user:
        raise HTTPException(status_code=404, detail="Operator account not found.")
    
    # Filter ONLY this user's personal entries
    personal_logins = [l for l in data.get("login_history", []) if l.get("username", "").lower() == uname][:20]
    personal_activities = [a for a in data.get("activity_log", []) if a.get("username", "").lower() == uname][:20]
    personal_reports = [r for r in data.get("reports_generated", []) if r.get("username", "").lower() == uname][:20]

    return {
        "status": "success",
        "is_admin": (uname == "admin"),
        "user": {
            "username": user["username"],
            "name": user["name"],
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

        # Log action in onboard activity history
        data = load_onboard_data()
        data.setdefault("activity_log", []).insert(0, {
            "username": req.username or "guest",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Simulation Computed",
            "details": f"{req.material_name} | {req.thickness_mm:.0f}mm | Tamb {req.ambient_temp}°C | Eff {results['thermal_efficiency']:.0f}%"
        })
        data["activity_log"] = data["activity_log"][:60]
        save_onboard_data(data)

        return {
            "status": "success",
            "results": results,
            "shelter_3d": shelter_3d
        }
    except Exception as e:
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
        
        # Log report generation in audit store
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

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=ThermoShelter_Tactical_Blueprint.pdf"}
        )
    except Exception as e:
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
    except Exception as e:
        return {
            "temperature": -25.0,
            "humidity": 40.0,
            "wind_speed": 10.5,
            "solar_radiation": 160.0,
            "fallback": True
        }

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting ThermoShelter AI v2.5 at http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
