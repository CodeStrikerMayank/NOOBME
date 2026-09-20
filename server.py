import os
import urllib.request
import urllib.parse
import json
import hashlib
import time
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core.thermo_solver import (
    calculate_state,
    generate_architectural_shelter,
    MATERIAL_DATABASE
)
from core.pdf_generator import generate_blueprint_pdf

app = FastAPI(title="ThermoShelter AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- HEALTH & KEEP-AWAKE MONITORING ----------------
SERVER_START_TIME = time.time()
HEALTH_STATS = {
    "pings_received": 0,
    "last_ping_time": None,
    "self_pings_sent": 0,
    "last_self_ping_time": None,
    "keep_awake_running": False
}

def render_keep_awake_worker():
    """Background worker to ping self and prevent Render free tier from sleeping after 15 minutes."""
    HEALTH_STATS["keep_awake_running"] = True
    interval = int(os.environ.get("KEEP_AWAKE_INTERVAL_SECONDS", 600))  # default 10m
    
    # Wait 20 seconds after startup before starting ping loop
    time.sleep(20)
    
    while True:
        target_url = os.environ.get("RENDER_EXTERNAL_URL", os.environ.get("APP_URL"))
        if target_url:
            health_url = f"{target_url.rstrip('/')}/health"
            try:
                req = urllib.request.Request(health_url, headers={"User-Agent": "ThermoShelter-KeepAwake/2.0"})
                with urllib.request.urlopen(req, timeout=12) as res:
                    HEALTH_STATS["self_pings_sent"] += 1
                    HEALTH_STATS["last_self_ping_time"] = datetime.now().isoformat()
            except Exception as e:
                print(f"[KeepAwake] Ping notice for {health_url}: {e}")
        time.sleep(interval)

@app.on_event("startup")
def start_keep_awake():
    t = threading.Thread(target=render_keep_awake_worker, daemon=True)
    t.start()

@app.get("/health")
@app.get("/api/health")
@app.get("/healthz")
def health_check():
    """Health check endpoint for Render, UptimeRobot, and cron-job.org."""
    HEALTH_STATS["pings_received"] += 1
    HEALTH_STATS["last_ping_time"] = datetime.now().isoformat()
    uptime_sec = time.time() - SERVER_START_TIME
    hours, rem = divmod(int(uptime_sec), 3600)
    mins, secs = divmod(rem, 60)
    
    data = load_onboard_data()
    users_count = len(data.get("users", {}))
    
    return {
        "status": "healthy",
        "service": "ThermoShelter-AI Engine",
        "version": "2.0.0",
        "uptime_seconds": round(uptime_sec, 1),
        "uptime_formatted": f"{hours}h {mins}m {secs}s",
        "server_time": datetime.now().isoformat(),
        "pings_received": HEALTH_STATS["pings_received"],
        "last_ping_time": HEALTH_STATS["last_ping_time"],
        "self_pings_sent": HEALTH_STATS["self_pings_sent"],
        "last_self_ping_time": HEALTH_STATS["last_self_ping_time"],
        "keep_awake_running": HEALTH_STATS["keep_awake_running"],
        "onboard_users_count": users_count,
        "environment": "render" if os.environ.get("RENDER") else "local",
        "public_url": os.environ.get("RENDER_EXTERNAL_URL", os.environ.get("APP_URL", "http://localhost:8000"))
    }


# ---------------- ONBOARD USER STORAGE ----------------
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
                    "name": "System Administrator",
                    "password_hash": hash_pw("admin123"),
                    "role": "DRDO Oversight & Admin",
                    "created_at": datetime.now().isoformat(),
                    "designs": []
                },
                "engineer": {
                    "username": "engineer",
                    "name": "Lead Thermal Engineer",
                    "password_hash": hash_pw("engineer123"),
                    "role": "Lead Thermal Systems Engineer",
                    "created_at": datetime.now().isoformat(),
                    "designs": []
                }
            }
        }
        save_onboard_data(default_data)
        return default_data
    try:
        with open(ONBOARD_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

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

class LoginRequest(BaseModel):
    username: str
    password: str

class SignUpRequest(BaseModel):
    username: str
    name: str
    password: str
    role: Optional[str] = "Thermal Design Engineer"

class SaveDesignRequest(BaseModel):
    username: str
    design_name: Optional[str] = "Standard Alpine Shelter"
    parameters: Dict[str, Any]
    results: Dict[str, Any]

# ---------------- AUTH ENDPOINTS ----------------
@app.post("/api/auth/login")
def login(req: LoginRequest):
    data = load_onboard_data()
    users = data.get("users", {})
    user = users.get(req.username.strip())
    if not user or user.get("password_hash") != hash_pw(req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {
        "status": "success",
        "user": {
            "username": user["username"],
            "name": user["name"],
            "role": user.get("role", "Engineer"),
            "designs": user.get("designs", [])
        }
    }

@app.post("/api/auth/signup")
def signup(req: SignUpRequest):
    u = req.username.strip()
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

@app.post("/api/auth/save-design")
def save_user_design(req: SaveDesignRequest):
    data = load_onboard_data()
    users = data.setdefault("users", {})
    if req.username not in users:
        raise HTTPException(status_code=404, detail="User not found in onboard system.")
    
    design_entry = {
        "id": f"design_{len(users[req.username].get('designs', [])) + 1}",
        "name": req.design_name,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "parameters": req.parameters,
        "results": req.results
    }
    users[req.username].setdefault("designs", []).insert(0, design_entry)
    save_onboard_data(data)
    return {"status": "success", "design": design_entry}

@app.get("/api/auth/users")
def list_onboard_users():
    data = load_onboard_data()
    return [
        {
            "username": u["username"],
            "name": u["name"],
            "role": u.get("role", "User"),
            "created_at": u.get("created_at", "System Default"),
            "designs_count": len(u.get("designs", []))
        }
        for u in data.get("users", {}).values()
    ]

@app.get("/api/auth/user/{username}")
def get_user_profile(username: str):
    data = load_onboard_data()
    users = data.get("users", {})
    user = users.get(username.strip())
    if not user:
        raise HTTPException(status_code=404, detail="User not found in onboard system.")
    return {
        "status": "success",
        "user": {
            "username": user["username"],
            "name": user["name"],
            "role": user.get("role", "User"),
            "created_at": user.get("created_at", "System Default"),
            "designs": user.get("designs", [])
        }
    }

@app.delete("/api/auth/user/{username}/design/{design_id}")
def delete_user_design(username: str, design_id: str):
    data = load_onboard_data()
    users = data.get("users", {})
    user = users.get(username.strip())
    if not user:
        raise HTTPException(status_code=404, detail="User not found in onboard system.")
    
    designs = user.get("designs", [])
    updated_designs = [d for d in designs if d.get("id") != design_id]
    if len(updated_designs) == len(designs):
        raise HTTPException(status_code=404, detail="Design not found.")
    
    user["designs"] = updated_designs
    save_onboard_data(data)
    return {"status": "success", "message": "Design deleted successfully."}


# ---------------- SIMULATION ENDPOINTS ----------------
@app.get("/api/materials")
def get_materials():
    return MATERIAL_DATABASE

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
            solar_radiation=req.solar_radiation
        )
        shelter_3d = generate_architectural_shelter(
            thickness_mm=req.thickness_mm,
            ambient_temp=req.ambient_temp,
            indoor_temp=results["t_in"]
        )
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
            solar_radiation=req.solar_radiation
        )
        pdf_bytes = generate_blueprint_pdf(results)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ThermoShelter_AI_Report.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live-climate")
def fetch_live_climate(lat: float = 28.6139, lon: float = 77.2090):
    try:
        params = urllib.parse.urlencode({
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation",
            "timezone": "auto"
        })
        url = f"https://api.open-meteo.com/v1/forecast?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "ThermoShelter-AI/2.0"})
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
        cur = data.get("current", {})
        return {
            "temperature": float(cur.get("temperature_2m", 21.0)),
            "humidity": float(cur.get("relative_humidity_2m", 50.0)),
            "wind_speed": round(float(cur.get("wind_speed_10m", 1.8)) / 3.6, 2),
            "solar_radiation": float(cur.get("shortwave_radiation", 150.0))
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Open-Meteo API unreachable: {str(e)}")

# Mount static folder for serving web frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting ThermoShelter AI Web Server on port {port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
