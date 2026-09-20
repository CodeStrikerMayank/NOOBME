# ThermoShelter AI

### Area-Specific Shelter Design and Thermal Comfort Analysis

ThermoShelter AI is a Python-based software prototype designed to support the analysis and design of shelters for location-specific thermal conditions.

The system combines climate inputs, shelter dimensions, material properties, thermodynamic calculations, PMV/PPD-based thermal comfort evaluation, 3D thermal visualization, recommendations, and PDF report generation in a single workflow.

---

## 🚀 Project Overview

Generic shelters may not perform equally well across different environmental conditions.

ThermoShelter AI aims to provide a software-based workflow for evaluating shelter thermal performance using area-specific environmental inputs and shelter design parameters.

The prototype is intended for research, demonstration, and engineering-design exploration.

> **Note:** This project is a software prototype. It is not a certified engineering, medical, or building-compliance tool.

---

## 🎯 Problem Statement

Shelters deployed in different climatic environments can experience significantly different thermal conditions.

Factors such as:

- Outdoor temperature
- Relative humidity
- Wind speed
- Solar radiation
- Mean radiant temperature
- Shelter dimensions
- Wall thickness
- Insulation/material properties
- Occupant assumptions

can influence the resulting indoor thermal environment.

A single generic shelter configuration may therefore require different design considerations for different locations.

---

## 💡 Proposed Solution

ThermoShelter AI provides a unified software workflow to:

1. Collect shelter dimensions and location information
2. Enter environmental/climate conditions
3. Calculate thermal performance
4. Evaluate thermal comfort using PMV/PPD
5. Visualize thermal conditions using a 3D heatmap
6. Generate design recommendations
7. Export the analysis as a PDF report
8. Provide an administrative view for reviewing user sessions and results

---

# 🔄 User Workflow

```text
Login / Signup (Compulsory Operator Gate)
      ↓
GPS and Shelter Dimensions
      ↓
Climate Data Collection
      ↓
Thermodynamic Solver (1D Heat Transfer & PMV/PPD)
      ↓
3D Heatmap Visualization (Three.js)
      ↓
Save Blueprint / Export PDF Report
```

---

## 🔒 Onboard Operator Authentication & Blueprint Storage

ThermoShelter AI features an onboard user registry and persistence layer:
- **Compulsory Operator Gate**: Protects the solver controls, real-time parameters, and PDF generation behind verified operator accounts.
- **Pre-configured Accounts**:
  - **Admin**: `admin` / `admin123` (Full system privileges, operator registry management)
  - **Senior Engineer**: `engineer` / `thermo2026`
- **Persistent Data Store**: User credentials and saved design blueprints are stored in `data/onboard_users.json` for lightweight zero-dependency deployment.

---

## ☁️ Deployment on Render (Render.com)

ThermoShelter AI is pre-configured for deployment on Render as a Python Web Service.

### Quick Deploy to Render

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ThermoShelter AI"
   git remote add origin https://github.com/<your-username>/ThermoShelter-AI.git
   git branch -M main
   git push -u origin main
   ```

2. **Create a Web Service on Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com/) and click **New + > Web Service**.
   - Connect your GitHub repository: `ThermoShelter-AI`.
   - Configure the service:
     - **Name**: `thermoshelter-ai` (or your preferred name)
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
     - **Instance Type**: `Free`
   - Alternatively, Render will automatically detect the included [render.yaml](file:///d:/GROUP@/ThermoShelter-AI/render.yaml) blueprint!

3. **Set Environment Variables (Optional)**:
   - `RENDER_EXTERNAL_URL`: Set to your Render URL (e.g. `https://thermoshelter-ai.onrender.com`) to activate the internal 10-minute self-ping loop.

---

## ⏰ 24/7 Keep-Awake & Health System (Free Tier Sleep Prevention)

Render's free tier automatically suspends web services after **15 minutes of inactivity**. ThermoShelter AI incorporates a dedicated 3-tier keep-awake architecture to keep your application awake 24/7 without paid upgrades:

### Dedicated Health Endpoints
- `GET /health` (or `/api/health`, `/healthz`)
- **JSON Response**:
  ```json
  {
    "status": "healthy",
    "uptime_seconds": 3600,
    "uptime_human": "1h 0m 0s",
    "total_pings_received": 142,
    "last_ping_timestamp": "2026-09-20T10:30:00Z",
    "database": "connected"
  }
  ```

### Setting Up Free 24/7 Monitoring (Takes 2 minutes)

To ensure your application never sleeps:

1. **Option A: UptimeRobot (Recommended - Free)**
   - Sign up at [uptimerobot.com](https://uptimerobot.com/) (100% Free).
   - Click **+ Add New Monitor**.
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `ThermoShelter AI`
   - **URL (or IP)**: `https://<your-render-app>.onrender.com/health`
   - **Monitoring Interval**: `Every 10 minutes` (or 5 minutes)
   - Click **Create Monitor**.

2. **Option B: cron-job.org (Alternative - Free)**
   - Sign up at [cron-job.org](https://cron-job.org/).
   - Create a cron job with URL: `https://<your-render-app>.onrender.com/health`.
   - Schedule execution every `10 minutes`.

3. **Option C: In-App Browser Pulse**
   - While any operator or kiosk screen has the dashboard open, ThermoShelter AI automatically fires a client-side health pulse every 5 minutes.

You can inspect the live uptime, ping counters, and copy your exact `/health` URL anytime via the **System Online** button in the dashboard sidebar footer.

---

## 💻 Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/ThermoShelter-AI.git
   cd ThermoShelter-AI
   ```

2. **Create a virtual environment & install dependencies**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Start the server**:
   ```bash
   python server.py
   # Or using uvicorn directly:
   uvicorn server:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Open in browser**:
   - Access `http://localhost:8000`
   - Log in using `admin` / `admin123` or `engineer` / `thermo2026`.
