import math
import numpy as np

# Material database with thermal conductivity (k), density, heat capacity (cp), and cost index
MATERIAL_DATABASE = {
    "High-Performance Composite": {"k": 0.022, "density": 45.0, "cp": 1200.0, "emissivity": 0.92, "cost_index": 2.10, "source": "Aerogel-Polymer Nanoporous Hybrid"},
    "Aerogel": {"k": 0.015, "density": 150.0, "cp": 1000.0, "emissivity": 0.90, "cost_index": 4.00, "source": "Silica Nanoporous Super-insulator"},
    "XPS": {"k": 0.034, "density": 35.0, "cp": 1400.0, "emissivity": 0.90, "cost_index": 1.20, "source": "Extruded Polystyrene High-Density"},
    "EPS": {"k": 0.040, "density": 20.0, "cp": 1400.0, "emissivity": 0.90, "cost_index": 1.00, "source": "Expanded Polystyrene Standard"},
    "Mineral Wool": {"k": 0.040, "density": 70.0, "cp": 1030.0, "emissivity": 0.90, "cost_index": 1.20, "source": "Rockwool Acoustic & Fire-safe"}
}

EXTREME_LOCATION_PRESETS = {
    "Siachen Glacier Base": {"temp": -45.0, "rh": 40.0, "wind": 18.0, "solar": 120.0, "altitude_m": 5400, "desc": "Extreme Alpine Sub-Zero Military Post"},
    "Dras Sector": {"temp": -35.0, "rh": 45.0, "wind": 12.0, "solar": 140.0, "altitude_m": 3280, "desc": "Second Coldest Inhabited Settlement"},
    "Leh Alpine Zone": {"temp": -25.0, "rh": 35.0, "wind": 8.0, "solar": 220.0, "altitude_m": 3500, "desc": "High-Altitude Arid Plateau"},
    "Arctic Expedition Station": {"temp": -50.0, "rh": 65.0, "wind": 22.0, "solar": 40.0, "altitude_m": 250, "desc": "Polar Sea-Ice Expedition Enclosure"},
    "Antarctic Research Pod": {"temp": -60.0, "rh": 30.0, "wind": 26.0, "solar": 20.0, "altitude_m": 2835, "desc": "South Pole Extreme Glacial Environment"}
}

def calculate_wind_chill(ta, vel):
    """Wind-chill temperature formula for extreme sub-zero conditions."""
    if ta <= 10.0 and vel > 1.3:
        v_kmh = vel * 3.6
        wc = 13.12 + 0.6215 * ta - 11.37 * (v_kmh ** 0.16) + 0.3965 * ta * (v_kmh ** 0.16)
        return round(float(wc), 1)
    return round(float(ta), 1)

def fanger_pmv_ppd(ta, tr, vel, rh, met, clo, wme=0.0):
    """
    Standard Fanger PMV/PPD thermal comfort evaluation (ISO 7730 / ASHRAE 55).
    ta, tr in °C, vel in m/s, rh in %, met in met units, clo in clo units.
    """
    m = met * 58.15
    w = wme * 58.15
    mw = m - w
    icl = 0.155 * clo
    fcl = 1.05 + 0.645 * icl if icl > 0.078 else 1 + 1.29 * icl
    pa = rh * 10.0 * np.exp(16.6536 - 4030.183 / (ta + 235.0))
    hcf = 12.1 * np.sqrt(max(0.01, vel))
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
        xn = xf
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
        return "CRITICAL POINT", "#f59e0b"
    if pmv > 0.5:
        return "OVER HEATED", "#ef4444"
    if pmv < -0.5:
        return "UNDER HEATED", "#38bdf8"
    if abs(pmv) <= 0.5 and ppd <= 10:
        return "OPTIMAL COMFORT", "#10b981"
    return "MARGINAL COMFORT", "#f59e0b"

def calculate_state(
    thickness_mm=250.0,
    ambient_temp=-10.0,
    material_name="High-Performance Composite",
    target_temp=21.0,
    shelter_length=6.0,
    shelter_width=5.0,
    shelter_height=2.8,
    relative_humidity=50.0,
    wind_speed=0.5,
    solar_radiation=150.0,
    occupancy_count=6,
    mean_radiant_temp=21.0,
    indoor_air_speed=0.1,
    metabolic_rate=1.2,
    clothing_level=1.2,
    ventilation_ach=0.5,
    window_wall_ratio=0.10,
    window_shgc=0.70
):
    mat = MATERIAL_DATABASE.get(material_name, MATERIAL_DATABASE["High-Performance Composite"])
    d = max(0.01, thickness_mm / 1000.0)
    tin_target = float(target_temp)
    t_out = float(ambient_temp)
    rh = float(relative_humidity)
    occupancy = max(1, int(occupancy_count))

    # Calculate shelter dimensions scaled by occupancy if large
    L, W, H = float(shelter_length), float(shelter_width), float(shelter_height)
    base_area = 2 * (L * W + L * H + W * H)
    window_area = min(base_area * window_wall_ratio, 0.8 * (2 * (L * H + W * H)))
    envelope_area = max(1.0, base_area - window_area)
    volume = L * W * H

    # Thermal conductivity and resistance
    R = d / max(mat["k"], 1e-6)
    U = 1.0 / max(R, 1e-6)
    delta = tin_target - t_out
    q_cond = U * envelope_area * delta

    # Dynamic ventilation based on occupancy (min 15 CFM or 0.5 ACH)
    ach = max(0.35, float(ventilation_ach))
    rho_air, cp_air = 1.2, 1006.0
    q_vent = rho_air * cp_air * volume * (ach / 3600.0) * delta
    q_solar = solar_radiation * window_area * float(window_shgc)

    # Biological heat generation: ~100W per human occupant + 200W communications/equipment
    internal_gain = (occupancy * 105.0) + 200.0 
    net_load = q_cond + q_vent - q_solar - internal_gain

    # Conductance & passive temperature
    conductance = max(U * envelope_area + rho_air * cp_air * volume * (ach / 3600.0), 1e-6)
    predicted_t = t_out + (q_solar + internal_gain) / conductance
    predicted_t = float(np.clip(predicted_t, min(t_out - 10, tin_target - 15), max(t_out + 40, tin_target + 12)))
    predicted_tr = 0.65 * predicted_t + 0.35 * float(mean_radiant_temp)

    pmv, ppd, vapor = fanger_pmv_ppd(predicted_t, predicted_tr, indoor_air_speed, rh, metabolic_rate, clothing_level)
    status, color = thermal_status(pmv, ppd)

    # Thermal efficiency percentage
    baseline_u = 1.0 / (0.05 / mat["k"])
    efficiency = np.clip((1.0 - (U / baseline_u) * 0.45) * 100.0, 45.0, 97.0)
    
    # Critical cold bridges: reduced as insulation thickness increases
    cold_bridges = int(max(1, round(6 - (thickness_mm / 90.0))))

    # Total heating demand in kWh/day
    heating_load_kwh_day = max(0.5, (max(0.0, net_load) * 24.0) / 1000.0)

    # Diesel heating fuel consumption (Liters/day): ~10 kWh per liter at 85% heating appliance efficiency
    diesel_liters_day = round(heating_load_kwh_day / (10.0 * 0.85), 1)

    # Wind-chill temperature
    wind_chill = calculate_wind_chill(t_out, wind_speed)

    return {
        "material": material_name,
        "thickness_mm": thickness_mm,
        "thickness_m": d,
        "t_target": tin_target,
        "t_in": round(predicted_t, 2),
        "t_out": round(t_out, 2),
        "wind_chill": wind_chill,
        "tr": round(predicted_tr, 2),
        "rh": rh,
        "wind": wind_speed,
        "solar": solar_radiation,
        "occupancy_count": occupancy,
        "r_value": round(R, 3),
        "u_value": round(U, 3),
        "envelope_area": round(envelope_area, 2),
        "volume": round(volume, 2),
        "window_area": round(window_area, 2),
        "q_conduction": round(q_cond, 1),
        "q_ventilation": round(q_vent, 1),
        "q_solar": round(q_solar, 1),
        "internal_gain": round(internal_gain, 1),
        "net_load_watts": round(net_load, 1),
        "pmv": round(pmv, 2),
        "ppd": round(ppd, 1),
        "status": status,
        "status_color": color,
        "thermal_efficiency": round(float(efficiency), 0),
        "cold_bridge_count": cold_bridges,
        "heating_load_kwh_day": round(float(heating_load_kwh_day), 1),
        "diesel_liters_day": diesel_liters_day,
        "cost_index": mat.get("cost_index", 1.0)
    }

def generate_architectural_shelter(thickness_mm=250.0, ambient_temp=-10.0, indoor_temp=20.0):
    t_min = min(ambient_temp, -30.0)
    t_max = max(indoor_temp, 22.0)

    walls = [
        {"x1": 0, "y1": 0, "x2": 6, "y2": 0, "h": 2.8, "name": "South Wall", "has_door": True, "has_window": True},
        {"x1": 6, "y1": 0, "x2": 6, "y2": 5, "h": 2.8, "name": "East Wall", "has_door": False, "has_window": True},
        {"x1": 6, "y1": 5, "x2": 0, "y2": 5, "h": 2.8, "name": "North Wall", "has_door": False, "has_window": True},
        {"x1": 0, "y1": 5, "x2": 0, "y2": 0, "h": 2.8, "name": "West Wall", "has_door": False, "has_window": False},
        {"x1": 3, "y1": 0, "x2": 3, "y2": 5, "h": 2.6, "name": "Main Partition", "has_door": True, "has_window": False},
        {"x1": 0, "y1": 2.5, "x2": 3, "y2": 2.5, "h": 2.6, "name": "Room A Partition", "has_door": True, "has_window": False},
    ]

    return {
        "walls": walls,
        "t_ambient": ambient_temp,
        "t_indoor": indoor_temp,
        "t_range": [t_min, t_max]
    }
