// ThermoShelter-AI Web Dashboard Client v2.5

// State variables
let currentUser = null;
let currentParams = {
  thickness_mm: 350,
  ambient_temp: -45,
  material_name: "Aerogel",
  target_temp: 21.0,
  occupancy_count: 8,
  username: "admin"
};

const EXTREME_PRESETS = {
  "Siachen Glacier Base": { temp: -45, thick: 350, mat: "Aerogel", occ: 8 },
  "Dras Sector": { temp: -35, thick: 280, mat: "High-Performance Composite", occ: 6 },
  "Leh Alpine Zone": { temp: -25, thick: 220, mat: "High-Performance Composite", occ: 6 },
  "Arctic Expedition Station": { temp: -50, thick: 400, mat: "Aerogel", occ: 4 },
  "Antarctic Research Pod": { temp: -60, thick: 450, mat: "Aerogel", occ: 8 }
};

// DOM elements - Auth & HUD
const authScreen = document.getElementById("authScreen");
const hudLoadingScreen = document.getElementById("hudLoadingScreen");
const hudProgressBar = document.getElementById("hudProgressBar");
const hudProgressPct = document.getElementById("hudProgressPct");
const hudTelemetryText = document.getElementById("hudTelemetryText");

const tabLoginBtn = document.getElementById("tabLoginBtn");
const tabSignupBtn = document.getElementById("tabSignupBtn");
const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");
const loginUsername = document.getElementById("loginUsername");
const loginPassword = document.getElementById("loginPassword");
const rememberMeCheck = document.getElementById("rememberMeCheck");
const demoAdminBtn = document.getElementById("demoAdminBtn");
const demoEngineerBtn = document.getElementById("demoEngineerBtn");

const topProfileName = document.getElementById("topProfileName");
const operatorRoleLabel = document.getElementById("operatorRoleLabel");
const logoutBtn = document.getElementById("logoutBtn");
const modalLogoutBtn = document.getElementById("modalLogoutBtn");

// DOM elements - Solver & Presets
const presetLocationSelect = document.getElementById("presetLocationSelect");
const thicknessSlider = document.getElementById("thicknessSlider");
const thicknessBadge = document.getElementById("thicknessBadge");
const tempSlider = document.getElementById("tempSlider");
const tempBadge = document.getElementById("tempBadge");
const occupancySelect = document.getElementById("occupancySelect");
const occupancyBadge = document.getElementById("occupancyBadge");
const materialSelect = document.getElementById("materialSelect");
const startSimBtn = document.getElementById("startSimBtn");
const simProgressBar = document.getElementById("simProgressBar");
const simStatusText = document.getElementById("simStatusText");
const downloadReportBtn = document.getElementById("downloadReportBtn");
const liveWeatherBtn = document.getElementById("liveWeatherBtn");

const efficiencyVal = document.getElementById("efficiencyVal");
const bridgeCountVal = document.getElementById("bridgeCountVal");
const heatingLoadVal = document.getElementById("heatingLoadVal");
const dieselFuelVal = document.getElementById("dieselFuelVal");
const comfortStatusText = document.getElementById("comfortStatusText");
const pmvPpdText = document.getElementById("pmvPpdText");
const comfortBadge = document.getElementById("comfortBadge");

// Navigation & Modals
const navDashboard = document.getElementById("navDashboard");
const navSolver = document.getElementById("navSolver");
const navHeatmaps = document.getElementById("navHeatmaps");
const navReports = document.getElementById("navReports");
const navAdmin = document.getElementById("navAdmin");
const navAdminText = document.getElementById("navAdminText");
const navAccount = document.getElementById("navAccount");
const profileBtn = document.getElementById("profileBtn");
const notifBtn = document.getElementById("notifBtn");
const notifDropdown = document.getElementById("notifDropdown");

const adminModal = document.getElementById("adminModal");
const reportsModal = document.getElementById("reportsModal");
const accountModal = document.getElementById("accountModal");
const toastBox = document.getElementById("toastBox");

// ---------------- TOAST FEEDBACK ----------------
function showToast(message, icon = "✓") {
  const toast = document.createElement("div");
  toast.className = "toast-item";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  toastBox.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 2800);
}

// ---------------- AUTH & REMEMBER ME FLOW ----------------
function checkRememberedLogin() {
  const savedUser = localStorage.getItem("thermo_user");
  const isRemembered = localStorage.getItem("thermo_remember_me") === "true";

  if (savedUser && isRemembered) {
    try {
      currentUser = JSON.parse(savedUser);
      applyUserSession(currentUser);
      authScreen.classList.add("hidden");
      initThreeScene();
      runSolver(true);
      return true;
    } catch (e) {
      localStorage.removeItem("thermo_user");
    }
  }
  // Otherwise, leave auth screen visible
  authScreen.classList.remove("hidden");
  return false;
}

function applyUserSession(user) {
  currentUser = user;
  currentParams.username = user.username;
  const isAdmin = (user.username === "admin");

  const operatorBadge = document.getElementById("operatorBadge");
  const adminPowerStressBtn = document.getElementById("adminPowerStressBtn");

  if (isAdmin) {
    topProfileName.innerText = "admin (Chief Admin)";
    operatorRoleLabel.innerHTML = `<span style="color:#fdba74; font-weight:800;">⚡ CHIEF ADMINISTRATOR [ROOT ACCESS]</span>`;
    if (operatorBadge) operatorBadge.classList.add("admin-badge-glow");
    if (navAdmin) {
      navAdmin.style.display = "flex";
      navAdminText.innerText = "DRDO Admin Oversight";
    }
    if (adminPowerStressBtn) adminPowerStressBtn.classList.remove("hidden");
  } else {
    topProfileName.innerText = user.username;
    operatorRoleLabel.innerText = `Operator: ${user.role || 'Field Engineer'}`;
    if (operatorBadge) operatorBadge.classList.remove("admin-badge-glow");
    // Normal users cannot access admin oversight - completely hide it from menu
    if (navAdmin) navAdmin.style.display = "none";
    if (adminPowerStressBtn) adminPowerStressBtn.classList.add("hidden");
  }

  // Update account modal baseline labels
  document.getElementById("accountUsername").innerText = user.username;
  document.getElementById("accountFullName").innerText = user.name;
  document.getElementById("accountRolePill").innerText = user.role;
}

// Tab Switching
tabLoginBtn.addEventListener("click", () => {
  tabLoginBtn.classList.add("active");
  tabSignupBtn.classList.remove("active");
  loginForm.classList.remove("hidden");
  signupForm.classList.add("hidden");
});

tabSignupBtn.addEventListener("click", () => {
  tabSignupBtn.classList.add("active");
  tabLoginBtn.classList.remove("active");
  signupForm.classList.remove("hidden");
  loginForm.classList.add("hidden");
});

// Quick Demo Access
demoAdminBtn.addEventListener("click", () => {
  loginUsername.value = "admin";
  loginPassword.value = "1234@admin";
  rememberMeCheck.checked = true;
  loginSubmit(new Event("submit"));
});

demoEngineerBtn.addEventListener("click", () => {
  loginUsername.value = "engineer";
  loginPassword.value = "engineer123";
  rememberMeCheck.checked = true;
  loginSubmit(new Event("submit"));
});

// Login Form Submit
async function loginSubmit(e) {
  if (e && e.preventDefault) e.preventDefault();
  const username = loginUsername.value.trim();
  const password = loginPassword.value.trim();
  const remember = rememberMeCheck.checked;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, remember_me: remember })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed.");
    }

    const data = await res.json();
    const user = data.user;

    if (remember) {
      localStorage.setItem("thermo_user", JSON.stringify(user));
      localStorage.setItem("thermo_remember_me", "true");
    } else {
      localStorage.removeItem("thermo_user");
      localStorage.removeItem("thermo_remember_me");
    }

    applyUserSession(user);
    authScreen.classList.add("hidden");

    // Play HUD Loading Animation
    playHudLoading(() => {
      initThreeScene();
      runSolver(false);
      showToast(`Welcome, ${user.name} (${user.role})`);
    });
  } catch (err) {
    alert("Authentication Error: " + err.message);
  }
}
loginForm.addEventListener("submit", loginSubmit);

// Signup Form Submit
signupForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("signupName").value.trim();
  const username = document.getElementById("signupUsername").value.trim();
  const password = document.getElementById("signupPassword").value.trim();
  const role = document.getElementById("signupRole").value;

  try {
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, username, password, role })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed.");
    }

    const data = await res.json();
    const user = data.user;

    localStorage.setItem("thermo_user", JSON.stringify(user));
    localStorage.setItem("thermo_remember_me", "true");

    applyUserSession(user);
    authScreen.classList.add("hidden");

    playHudLoading(() => {
      initThreeScene();
      runSolver(false);
      showToast(`Account Created & Verified for ${user.name}`);
    });
  } catch (err) {
    alert("Registration Error: " + err.message);
  }
});

// Logout
function performLogout() {
  localStorage.removeItem("thermo_user");
  localStorage.removeItem("thermo_remember_me");
  currentUser = null;
  accountModal.classList.remove("open");
  authScreen.classList.remove("hidden");
  showToast("Workstation Locked. Operator Logged Out.", "🔒");
}
logoutBtn.addEventListener("click", performLogout);
modalLogoutBtn.addEventListener("click", performLogout);

// ---------------- HUD LOADING SEQUENCE ----------------
function playHudLoading(onComplete) {
  hudLoadingScreen.classList.add("show");
  hudProgressBar.style.width = "0%";
  hudProgressPct.innerText = "0%";

  const steps = [
    { pct: 25, text: "Authenticating operator cryptokey in onboard vault..." },
    { pct: 55, text: "Calibrating 3D WebGL Three.js thermodynamic mesh..." },
    { pct: 85, text: "Pulling sub-zero Himalayan meteorological telemetry..." },
    { pct: 100, text: "Verification complete. Initializing ISO 7730 solver..." }
  ];

  let i = 0;
  function nextStep() {
    if (i < steps.length) {
      hudProgressBar.style.width = `${steps[i].pct}%`;
      hudProgressPct.innerText = `${steps[i].pct}%`;
      hudTelemetryText.innerText = steps[i].text;
      i++;
      setTimeout(nextStep, 320);
    } else {
      setTimeout(() => {
        hudLoadingScreen.classList.remove("show");
        if (onComplete) onComplete();
      }, 400);
    }
  }
  nextStep();
}

// ---------------- THREE.JS 3D VISUALIZATION ----------------
let scene, camera, renderer, controls, shelterGroup;

function initThreeScene() {
  if (scene) return; // Prevent duplicate initialization
  const container = document.getElementById("threeCanvasContainer");
  const width = container.clientWidth || 400;
  const height = container.clientHeight || 330;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xffffff);

  camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 1000);
  camera.position.set(13, 11, 14);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.shadowMap.enabled = true;
  container.appendChild(renderer.domElement);

  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(3, 1.2, 2.5);

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xfff5eb, 0.9);
  dirLight.position.set(15, 25, 12);
  dirLight.castShadow = true;
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.4);
  fillLight.position.set(-10, 10, -10);
  scene.add(fillLight);

  buildGridAndAxes();

  shelterGroup = new THREE.Group();
  scene.add(shelterGroup);
  buildShelterGeometry(-45, 20);

  setupCameraButtons();

  window.addEventListener("resize", onWindowResize);
  animate();
}

function buildGridAndAxes() {
  const gridHelper = new THREE.GridHelper(8, 8, 0xcbd5e1, 0xe2e8f0);
  gridHelper.position.set(3, 0, 2.5);
  scene.add(gridHelper);

  const lineMat = new THREE.LineBasicMaterial({ color: 0x64748b, linewidth: 1 });
  const points = [
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(6.5, 0, 0),
    new THREE.Vector3(6.5, 0, 5.5),
    new THREE.Vector3(0, 0, 5.5),
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0, 3.2, 0)
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const line = new THREE.Line(geometry, lineMat);
  scene.add(line);
}

function tempToColor(t) {
  // Normalize between -60°C to +22°C for extreme cold visibility
  const norm = Math.max(0, Math.min(1, (t + 60) / 82));
  let r = 0, g = 0, b = 0;
  if (norm < 0.25) {
    const f = norm / 0.25;
    r = 0.15 + 0.1 * f;
    g = 0.2 + 0.4 * f;
    b = 0.65 + 0.35 * f;
  } else if (norm < 0.5) {
    const f = (norm - 0.25) / 0.25;
    r = 0.25 + 0.4 * f;
    g = 0.6 + 0.4 * f;
    b = 1.0 - 0.6 * f;
  } else if (norm < 0.75) {
    const f = (norm - 0.5) / 0.25;
    r = 0.75 + 0.25 * f;
    g = 1.0 - 0.35 * f;
    b = 0.4 - 0.3 * f;
  } else {
    const f = (norm - 0.75) / 0.25;
    r = 1.0;
    g = 0.65 - 0.5 * f;
    b = 0.1;
  }
  return new THREE.Color(r, g, b);
}

function buildShelterGeometry(ambientTemp, indoorTemp) {
  while (shelterGroup.children.length > 0) {
    const obj = shelterGroup.children[0];
    shelterGroup.remove(obj);
  }

  const wallDefs = [
    { x: 1.0, y: 1.3, z: 0, w: 2.0, h: 2.6, d: 0.22, t: ambientTemp + 4 },
    { x: 2.5, y: 2.2, z: 0, w: 1.0, h: 0.8, d: 0.22, t: ambientTemp + 3 },
    { x: 4.5, y: 1.3, z: 0, w: 3.0, h: 2.6, d: 0.22, t: ambientTemp + 2, hasWindow: true },
    { x: 6.0, y: 1.3, z: 2.5, w: 0.22, h: 2.6, d: 5.0, t: ambientTemp + 1, hasWindow: true },
    { x: 3.0, y: 1.3, z: 5.0, w: 6.0, h: 2.6, d: 0.22, t: ambientTemp },
    { x: 0, y: 1.3, z: 2.5, w: 0.22, h: 2.6, d: 5.0, t: ambientTemp + 2 },
    { x: 3.2, y: 1.3, z: 2.5, w: 0.16, h: 2.4, d: 5.0, t: indoorTemp - 2, isInterior: true },
    { x: 1.6, y: 1.3, z: 2.5, w: 3.0, h: 2.4, d: 0.16, t: indoorTemp, isInterior: true }
  ];

  wallDefs.forEach(wall => {
    const wallColor = tempToColor(wall.t);
    const material = new THREE.MeshLambertMaterial({ color: wallColor, roughness: 0.4 });

    if (wall.hasWindow) {
      const baseMesh = new THREE.Mesh(new THREE.BoxGeometry(wall.w, wall.h, wall.d), material);
      baseMesh.position.set(wall.x, wall.y, wall.z);
      shelterGroup.add(baseMesh);

      const frameGeom = new THREE.BoxGeometry(wall.w > wall.d ? 1.0 : wall.d * 0.4, 0.9, wall.w > wall.d ? wall.d * 1.1 : 1.0);
      const frameMat = new THREE.MeshBasicMaterial({ color: 0x1e293b });
      const windowMesh = new THREE.Mesh(frameGeom, frameMat);
      windowMesh.position.set(wall.x, wall.y * 0.9, wall.z);
      shelterGroup.add(windowMesh);
    } else {
      const geom = new THREE.BoxGeometry(wall.w, wall.h, wall.d);
      const mesh = new THREE.Mesh(geom, material);
      mesh.position.set(wall.x, wall.y, wall.z);
      shelterGroup.add(mesh);
    }

    const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(wall.w, wall.h, wall.d));
    const lineMat = new THREE.LineBasicMaterial({ color: 0x334155, linewidth: 1.2, transparent: true, opacity: 0.4 });
    const wireframe = new THREE.LineSegments(edges, lineMat);
    wireframe.position.set(wall.x, wall.y, wall.z);
    shelterGroup.add(wireframe);
  });

  const floorGeom = new THREE.BoxGeometry(6.0, 0.08, 5.0);
  const floorMat = new THREE.MeshLambertMaterial({ color: tempToColor(indoorTemp - 1) });
  const floor = new THREE.Mesh(floorGeom, floorMat);
  floor.position.set(3.0, 0.04, 2.5);
  shelterGroup.add(floor);
}

function setupCameraButtons() {
  const setCam = (btn, x, y, z, tx = 3, ty = 1.2, tz = 2.5) => {
    document.querySelectorAll(".cam-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    camera.position.set(x, y, z);
    controls.target.set(tx, ty, tz);
    controls.update();
  };

  document.getElementById("camIsometric").addEventListener("click", function() {
    setCam(this, 13, 11, 14);
    showToast("3D Isometric Camera Active");
  });
  document.getElementById("camTop").addEventListener("click", function() {
    setCam(this, 3, 16, 2.5);
    showToast("Top-Down Floorplan Camera Active");
  });
  document.getElementById("camFront").addEventListener("click", function() {
    setCam(this, 3, 2.5, 14);
    showToast("Front Elevation Camera Active");
  });
  document.getElementById("camCut").addEventListener("click", function() {
    setCam(this, 8, 6, 8);
    showToast("Section Thermal Cut Active");
  });
}

function onWindowResize() {
  const container = document.getElementById("threeCanvasContainer");
  if (!container || !renderer) return;
  const width = container.clientWidth;
  const height = container.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

// ---------------- SOLVER & API INTERACTIONS ----------------
async function runSolver(isSilent = false) {
  if (!isSilent) {
    simProgressBar.style.width = "0%";
    simStatusText.innerText = "Simulating...";
    startSimBtn.style.opacity = "0.85";

    setTimeout(() => { simProgressBar.style.width = "45%"; }, 80);
    setTimeout(() => { simProgressBar.style.width = "100%"; }, 220);
  }

  currentParams.thickness_mm = parseFloat(thicknessSlider.value);
  currentParams.ambient_temp = parseFloat(tempSlider.value);
  currentParams.material_name = materialSelect.value;
  currentParams.occupancy_count = parseInt(occupancySelect.value);

  try {
    const res = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentParams)
    });

    if (!res.ok) throw new Error("Solver calculation failed.");
    const data = await res.json();
    const r = data.results;

    // Update Analytics Summary metrics
    efficiencyVal.innerText = `${r.thermal_efficiency.toFixed(0)}%`;
    bridgeCountVal.innerText = `${r.cold_bridge_count}`;
    heatingLoadVal.innerText = `${r.heating_load_kwh_day.toFixed(1)} kWh/d`;
    dieselFuelVal.innerText = `${r.diesel_liters_day.toFixed(1)} L/day`;
    comfortStatusText.innerText = r.status;
    pmvPpdText.innerText = `PMV: ${r.pmv > 0 ? '+' : ''}${r.pmv.toFixed(2)} | PPD: ${r.ppd.toFixed(1)}%`;

    if (r.status === "OPTIMAL COMFORT") {
      comfortBadge.style.background = "#ecfdf5";
      comfortBadge.style.color = "#047857";
      comfortBadge.querySelector(".indicator-dot").style.background = "#10b981";
    } else {
      comfortBadge.style.background = "#fffbeb";
      comfortBadge.style.color = "#b45309";
      comfortBadge.querySelector(".indicator-dot").style.background = "#f59e0b";
    }

    buildShelterGeometry(r.t_out, r.t_in);
    updateFloatingHudValues();

    if (!isSilent) {
      simStatusText.innerText = "0.38s (Complete)";
      startSimBtn.style.opacity = "1";
      showToast(`Simulation Complete: ${r.thermal_efficiency.toFixed(0)}% Efficiency`);
    }
  } catch (err) {
    console.error("Solver error:", err);
    if (!isSilent) {
      simStatusText.innerText = "Error";
      startSimBtn.style.opacity = "1";
      showToast("Solver failed: " + err.message, "✕");
    }
  }
}

// ---------------- EVENT LISTENERS ----------------
thicknessSlider.addEventListener("input", (e) => {
  thicknessBadge.innerText = e.target.value;
  runSolver(true);
});

tempSlider.addEventListener("input", (e) => {
  const val = e.target.value;
  tempBadge.innerText = val > 0 ? `+${val}` : val;
  if (parseFloat(val) <= -20) {
    tempBadge.classList.add("extreme-cold");
  } else {
    tempBadge.classList.remove("extreme-cold");
  }
  runSolver(true);
});

occupancySelect.addEventListener("change", () => {
  occupancyBadge.innerText = `${occupancySelect.value} Persons`;
  runSolver(true);
  showToast(`Capacity Scaled to ${occupancySelect.value} Occupants`);
});

materialSelect.addEventListener("change", () => {
  runSolver(true);
  showToast(`Material updated: ${materialSelect.value}`);
});

// Extreme Location Preset Picker
presetLocationSelect.addEventListener("change", () => {
  const choice = presetLocationSelect.value;
  if (EXTREME_PRESETS[choice]) {
    const p = EXTREME_PRESETS[choice];
    tempSlider.value = p.temp;
    tempBadge.innerText = p.temp;
    tempBadge.classList.add("extreme-cold");

    thicknessSlider.value = p.thick;
    thicknessBadge.innerText = p.thick;

    materialSelect.value = p.mat;
    occupancySelect.value = p.occ;
    occupancyBadge.innerText = `${p.occ} Persons`;

    runSolver(false);
    showToast(`Preset Applied: ${choice} (${p.temp}°C)`, "🏔️");
  }
});

startSimBtn.addEventListener("click", () => {
  runSolver(false);
});

// Download PDF Report
downloadReportBtn.addEventListener("click", async () => {
  try {
    downloadReportBtn.style.opacity = "0.7";
    showToast("Generating Executive Blueprint PDF...", "⏳");

    const res = await fetch("/api/export-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentParams)
    });

    if (!res.ok) throw new Error("Could not generate PDF");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ThermoShelter_Tactical_Blueprint_${currentParams.material_name.replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    showToast("Executive Blueprint Downloaded Successfully!");
  } catch (err) {
    showToast("Report download failed: " + err.message, "✕");
  } finally {
    downloadReportBtn.style.opacity = "1";
  }
});

// Live Weather Sync
liveWeatherBtn.addEventListener("click", async () => {
  try {
    liveWeatherBtn.innerText = "Syncing weather...";
    showToast("Connecting Open-Meteo Alpine Telemetry...", "☁");
    const res = await fetch("/api/live-climate?lat=34.2090&lon=77.5750");
    if (!res.ok) throw new Error("Weather API failed");
    const data = await res.json();

    const roundedTemp = Math.round(data.temperature);
    tempSlider.value = roundedTemp;
    tempBadge.innerText = roundedTemp > 0 ? `+${roundedTemp}` : roundedTemp;
    
    await runSolver(false);
    liveWeatherBtn.innerHTML = `<span>✓ Synced (${roundedTemp}°C)</span>`;
    showToast(`Live Climate Synced: ${roundedTemp}°C`);

    setTimeout(() => {
      liveWeatherBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
        </svg>
        <span>Sync Open-Meteo Weather</span>
      `;
    }, 2500);
  } catch (err) {
    showToast("Weather sync failed: " + err.message, "✕");
  }
});

// ---------------- NAVIGATION & MODALS ----------------
function setActiveNav(btn) {
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

// ---------------- INTERACTIVE VIEW & 3D MODEL EXPAND LOGIC ----------------
let is3DExpanded = false;

function updateFloatingHudValues() {
  const temp = tempSlider ? tempSlider.value : "-45";
  const eff = efficiencyVal ? efficiencyVal.innerText : "94%";
  const load = heatingLoadVal ? heatingLoadVal.innerText : "1.2 kWh/day";
  const qTemp = document.getElementById("hudQuickTemp");
  const qEff = document.getElementById("hudQuickEff");
  const qLoad = document.getElementById("hudQuickLoad");
  if (qTemp) qTemp.innerText = `${temp}°C`;
  if (qEff) qEff.innerText = eff;
  if (qLoad) qLoad.innerText = load;
}

function toggle3DExpandedView(forceState = null) {
  if (forceState !== null) {
    is3DExpanded = forceState;
  } else {
    is3DExpanded = !is3DExpanded;
  }

  const threeBarBtn = document.getElementById("threeBarToggleBtn");
  const threeBarText = document.getElementById("threeBarBtnText");
  const canvasExpandBtn = document.getElementById("canvasExpandBtn");
  const canvasExpandText = document.getElementById("canvasExpandBtnText");
  const btnModeDash = document.getElementById("btnModeDashboard");
  const btnMode3D = document.getElementById("btnModeFull3D");
  const floatingHud = document.getElementById("floating3DHud");

  if (is3DExpanded) {
    document.body.classList.add("immersive-3d-expanded");
    if (threeBarBtn) threeBarBtn.classList.add("active");
    if (threeBarText) threeBarText.innerText = "Show Dashboard (☰)";
    if (canvasExpandBtn) canvasExpandBtn.classList.add("active");
    if (canvasExpandText) canvasExpandText.innerText = "Restore Dashboard";
    if (btnModeDash) btnModeDash.classList.remove("active");
    if (btnMode3D) btnMode3D.classList.add("active");
    if (floatingHud) {
      floatingHud.classList.remove("hidden");
      updateFloatingHudValues();
    }
    showToast("Expanded 3D Model Focus (Dashboard Panels Hidden)", "🔲");
  } else {
    document.body.classList.remove("immersive-3d-expanded");
    if (threeBarBtn) threeBarBtn.classList.remove("active");
    if (threeBarText) threeBarText.innerText = "Expand 3D Model";
    if (canvasExpandBtn) canvasExpandBtn.classList.remove("active");
    if (canvasExpandText) canvasExpandText.innerText = "Maximize 3D Model";
    if (btnModeDash) btnModeDash.classList.add("active");
    if (btnMode3D) btnMode3D.classList.remove("active");
    if (floatingHud) floatingHud.classList.add("hidden");
    showToast("Restored Full Operational Dashboard", "📊");
  }

  // Smooth resize of Three.js canvas
  setTimeout(onWindowResize, 60);
  setTimeout(onWindowResize, 180);
  setTimeout(onWindowResize, 350);
}

// 3-Bar Header Button
const threeBarToggleBtn = document.getElementById("threeBarToggleBtn");
if (threeBarToggleBtn) {
  threeBarToggleBtn.addEventListener("click", () => toggle3DExpandedView());
}

// 3-Button View Segment
const btnModeDashboard = document.getElementById("btnModeDashboard");
if (btnModeDashboard) {
  btnModeDashboard.addEventListener("click", () => toggle3DExpandedView(false));
}

const btnModeFull3D = document.getElementById("btnModeFull3D");
if (btnModeFull3D) {
  btnModeFull3D.addEventListener("click", () => toggle3DExpandedView(true));
}

// Canvas Expand Button in 3D Header
const canvasExpandBtn = document.getElementById("canvasExpandBtn");
if (canvasExpandBtn) {
  canvasExpandBtn.addEventListener("click", () => toggle3DExpandedView());
}

// Floating HUD controls
const hudRestoreDashboardBtn = document.getElementById("hudRestoreDashboardBtn");
if (hudRestoreDashboardBtn) {
  hudRestoreDashboardBtn.addEventListener("click", () => toggle3DExpandedView(false));
}

const hudQuickSolveBtn = document.getElementById("hudQuickSolveBtn");
if (hudQuickSolveBtn) {
  hudQuickSolveBtn.addEventListener("click", async () => {
    await runSolver(false);
    updateFloatingHudValues();
  });
}

// Keyboard shortcut: Escape to restore dashboard from 3D mode
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && is3DExpanded) {
    toggle3DExpandedView(false);
  }
});

navDashboard.addEventListener("click", () => {
  setActiveNav(navDashboard);
  toggle3DExpandedView(false);
  showToast("Switched to User Dashboard");
});

navSolver.addEventListener("click", () => {
  setActiveNav(navSolver);
  showToast("Switched to 3D Thermal Model Solver");
});

navHeatmaps.addEventListener("click", () => {
  setActiveNav(navHeatmaps);
  document.getElementById("camCut").click();
  showToast("3D Heatmaps Perspective Enabled");
});

navReports.addEventListener("click", async () => {
  setActiveNav(navReports);
  await populateReportsModal();
  reportsModal.classList.add("open");
});

// ADMIN OVERSIGHT MODAL (FULL TELEMETRY AUDIT - ADMIN POWER ONLY)
navAdmin.addEventListener("click", async () => {
  if (!currentUser || currentUser.username !== "admin") {
    showToast("Access Denied: DRDO Administrator clearance required.", "🔒");
    return;
  }
  setActiveNav(navAdmin);
  await populateAdminAuditDashboard();
  adminModal.classList.add("open");
});

navAccount.addEventListener("click", async () => {
  setActiveNav(navAccount);
  await populateUserAccountWorkstation(currentUser.username);
  accountModal.classList.add("open");
});

profileBtn.addEventListener("click", async () => {
  await populateUserAccountWorkstation(currentUser.username);
  accountModal.classList.add("open");
});

notifBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  notifDropdown.classList.toggle("show");
});

window.addEventListener("click", () => {
  notifDropdown.classList.remove("show");
});

document.querySelectorAll(".modal-close, .modal-overlay").forEach(el => {
  el.addEventListener("click", (e) => {
    if (e.target === el || e.target.classList.contains("modal-close")) {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("open"));
    }
  });
});

// ---------------- ADMIN POWERS & DASHBOARD ----------------
async function populateAdminAuditDashboard() {
  try {
    const res = await fetch("/api/admin/audit?username=admin");
    if (!res.ok) throw new Error("Failed to fetch admin audit telemetry");
    const data = await res.json();

    // 4 KPI Cards
    document.getElementById("adminTotalUsers").innerText = data.total_users;
    document.getElementById("adminStorageSize").innerText = `${data.storage_size_kb} KB`;
    document.getElementById("adminTotalLogins").innerText = data.login_history.length;
    document.getElementById("adminTotalReports").innerText = data.reports_generated.length;

    // Login History
    const loginTbody = document.getElementById("adminLoginsTbody");
    loginTbody.innerHTML = "";
    if (data.login_history.length === 0) {
      loginTbody.innerHTML = "<tr><td colspan='5'>No login sessions recorded yet.</td></tr>";
    } else {
      data.login_history.forEach(log => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${log.username}</strong></td>
          <td><small>${log.timestamp}</small></td>
          <td>${log.role}</td>
          <td>${log.client}</td>
          <td><span style="color:${log.remember_me ? '#10b981' : '#64748b'}">${log.remember_me ? '✓ Enabled' : 'No'}</span></td>
        `;
        loginTbody.appendChild(tr);
      });
    }

    // Activity Table
    const actTbody = document.getElementById("adminActivityTbody");
    actTbody.innerHTML = "";
    if (data.activity_log.length === 0) {
      actTbody.innerHTML = "<tr><td colspan='4'>No simulation events recorded yet.</td></tr>";
    } else {
      data.activity_log.forEach(act => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${act.username}</strong></td>
          <td><small>${act.timestamp}</small></td>
          <td><span class="comfort-badge-pill" style="font-size:0.65rem;padding:2px 6px;">${act.action}</span></td>
          <td><small>${act.details}</small></td>
        `;
        actTbody.appendChild(tr);
      });
    }

    // Users Table with Governance Action
    const userTbody = document.getElementById("adminUsersTbody");
    userTbody.innerHTML = "";
    data.users.forEach(u => {
      const tr = document.createElement("tr");
      const isMasterAdmin = (u.username === "admin");
      tr.innerHTML = `
        <td><strong>${u.username}</strong></td>
        <td>${u.name}</td>
        <td>${u.role}</td>
        <td><small>${u.created_at.split('T')[0]}</small></td>
        <td>${u.designs_count} Designs</td>
        <td>
          ${isMasterAdmin 
            ? '<span style="color:#f97316;font-size:0.7rem;font-weight:700;">★ Master Root</span>' 
            : `<button class="btn-delete-operator" onclick="deleteOperatorAccount('${u.username}')">Decommission</button>`}
        </td>
      `;
      userTbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Admin audit fetch error:", err);
    showToast("Failed to load admin audit: " + err.message, "✕");
  }
}

// Admin Power: Inspect Raw JSON Vault
const adminInspectRawVaultBtn = document.getElementById("adminInspectRawVaultBtn");
const rawVaultContainer = document.getElementById("rawVaultContainer");
const rawVaultPre = document.getElementById("rawVaultPre");
const closeRawVaultBtn = document.getElementById("closeRawVaultBtn");

if (adminInspectRawVaultBtn) {
  adminInspectRawVaultBtn.addEventListener("click", async () => {
    try {
      showToast("Inspecting Raw JSON Vault...", "📜");
      const res = await fetch("/api/admin/raw-vault?username=admin");
      if (!res.ok) throw new Error("Could not fetch raw vault");
      const data = await res.json();
      rawVaultPre.innerText = JSON.stringify(data, null, 2);
      rawVaultContainer.classList.remove("hidden");
    } catch (e) {
      showToast("Raw vault error: " + e.message, "✕");
    }
  });
}

if (closeRawVaultBtn) {
  closeRawVaultBtn.addEventListener("click", () => {
    rawVaultContainer.classList.add("hidden");
  });
}

// Admin Power: Purge Old Logs
const adminPurgeLogsBtn = document.getElementById("adminPurgeLogsBtn");
if (adminPurgeLogsBtn) {
  adminPurgeLogsBtn.addEventListener("click", async () => {
    if (!confirm("Confirm DRDO Protocol: Purge old activity logs and archive session telemetry?")) return;
    try {
      const res = await fetch("/api/admin/purge-logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_username: "admin" })
      });
      if (!res.ok) throw new Error("Purge failed");
      showToast("System Logs Cleaned & Reset!");
      await populateAdminAuditDashboard();
    } catch (e) {
      showToast("Purge failed: " + e.message, "✕");
    }
  });
}

// Admin Power: Decommission Operator Account
window.deleteOperatorAccount = async function(targetUsername) {
  if (!confirm(`Are you sure you want to decommission operator account '${targetUsername}'?`)) return;
  try {
    const res = await fetch(`/api/admin/user/${encodeURIComponent(targetUsername)}?admin_username=admin`, {
      method: "DELETE"
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Decommission failed");
    }
    showToast(`Operator '${targetUsername}' Decommissioned!`);
    await populateAdminAuditDashboard();
  } catch (e) {
    showToast("Error: " + e.message, "✕");
  }
};

// Admin Power: Toggle Deep Polar Cryo-Stress Override (-80°C)
function triggerCryoStressOverride() {
  if (!currentUser || currentUser.username !== "admin") {
    showToast("Access Denied: Only Chief Admin has Cryo-Stress Override clearance.", "🔒");
    return;
  }
  tempSlider.min = "-80";
  tempSlider.value = "-80";
  tempBadge.innerText = "-80";
  
  occupancySelect.value = "50";
  materialSelect.value = "Aerogel Insulation Composite";
  thicknessSlider.value = "350";
  thicknessBadge.innerText = "350";

  showToast("⚡ ADMIN POLAR OVERRIDE: -80°C Cryo-Freeze (50 Soldiers) Engaged!", "⚡");
  runSolver(false);
}

const adminToggleStressBtn = document.getElementById("adminToggleStressBtn");
if (adminToggleStressBtn) {
  adminToggleStressBtn.addEventListener("click", () => {
    triggerCryoStressOverride();
    adminModal.classList.remove("open");
  });
}

const adminPowerStressBtn = document.getElementById("adminPowerStressBtn");
if (adminPowerStressBtn) {
  adminPowerStressBtn.addEventListener("click", triggerCryoStressOverride);
}

// ---------------- NORMAL USER COMPARTMENTALIZED WORKSTATION ----------------
async function populateUserAccountWorkstation(username) {
  try {
    const res = await fetch(`/api/user/account?username=${encodeURIComponent(username)}`);
    if (!res.ok) throw new Error("Failed to load user account profile");
    const data = await res.json();

    const u = data.user;
    const isAdmin = data.is_admin;

    document.getElementById("accountUsername").innerText = u.username;
    document.getElementById("accountFullName").innerText = u.name;
    document.getElementById("accountRolePill").innerText = u.role;

    const modalTitle = document.getElementById("accountModalTitle");
    const modalSub = document.getElementById("accountModalSub");
    const stationTag = document.getElementById("accountStationTag");
    const clearanceText = document.getElementById("accountClearanceText");
    const sandboxNotice = document.getElementById("userSandboxNotice");

    if (isAdmin) {
      if (modalTitle) modalTitle.innerText = "Chief Administrator Workstation Profile";
      if (modalSub) modalSub.innerText = "Full Master Clearance — Root Access to All Tactical Subsystems";
      if (stationTag) stationTag.innerText = "Assigned Station: DRDO Central Defense Command";
      if (clearanceText) clearanceText.innerText = "DRDO Root Master (Whole System Access)";
      if (sandboxNotice) {
        sandboxNotice.style.display = "none";
      }
    } else {
      if (modalTitle) modalTitle.innerText = "My Operator Profile & Personal Workstation";
      if (modalSub) modalSub.innerText = "Personal session logs and individual simulation archive";
      if (stationTag) stationTag.innerText = "Assigned Station: Alpine Tactical Enclosure";
      if (clearanceText) clearanceText.innerText = "Standard Operator (Personal Sandbox Only)";
      if (sandboxNotice) {
        sandboxNotice.style.display = "flex";
      }
    }

    // 3 Personal KPIs
    document.getElementById("userMySessions").innerText = data.personal_metrics.my_total_logins;
    document.getElementById("userMySims").innerText = data.personal_metrics.my_total_simulations;
    document.getElementById("userMyReports").innerText = data.personal_metrics.my_total_reports;

    // Personal Logins Table
    const loginsTbody = document.getElementById("userLoginsTbody");
    loginsTbody.innerHTML = "";
    if (data.personal_logins.length === 0) {
      loginsTbody.innerHTML = "<tr><td colspan='4'>No sessions recorded for your account.</td></tr>";
    } else {
      data.personal_logins.forEach(log => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><small>${log.timestamp}</small></td>
          <td>${log.client}</td>
          <td>${log.role}</td>
          <td><span style="color:${log.remember_me ? '#10b981' : '#64748b'}">${log.remember_me ? '✓ Enabled' : 'No'}</span></td>
        `;
        loginsTbody.appendChild(tr);
      });
    }

    // Personal Activity Table
    const actTbody = document.getElementById("userActivityTbody");
    actTbody.innerHTML = "";
    if (data.personal_activities.length === 0) {
      actTbody.innerHTML = "<tr><td colspan='3'>You have not executed any thermal simulations yet.</td></tr>";
    } else {
      data.personal_activities.forEach(act => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><small>${act.timestamp}</small></td>
          <td><span class="comfort-badge-pill" style="font-size:0.65rem;padding:2px 6px;">${act.action}</span></td>
          <td><small>${act.details}</small></td>
        `;
        actTbody.appendChild(tr);
      });
    }
  } catch (err) {
    console.error("Personal workstation error:", err);
    showToast("Profile load error: " + err.message, "✕");
  }
}

async function populateReportsModal() {
  const list = document.getElementById("reportHistoryList");
  list.innerHTML = "<div>Fetching blueprint archive...</div>";
  try {
    const isUserAdmin = (currentUser && currentUser.username === "admin");
    let reports = [];
    if (isUserAdmin) {
      const res = await fetch("/api/admin/audit?username=admin");
      const data = await res.json();
      reports = data.reports_generated || [];
    } else {
      const res = await fetch(`/api/user/account?username=${encodeURIComponent(currentUser.username)}`);
      const data = await res.json();
      reports = data.personal_reports || [];
    }

    list.innerHTML = "";
    if (reports.length === 0) {
      list.innerHTML = "<p>No blueprint reports exported yet. Click 'DOWNLOAD EXECUTIVE PDF' on the dashboard to generate your first document.</p>";
      return;
    }
    reports.forEach(item => {
      const div = document.createElement("div");
      div.className = "report-item";
      div.innerHTML = `
        <div class="report-info">
          <strong>${item.material} (${item.thickness}) &bull; ${item.efficiency} Eff</strong>
          <span>Generated: ${item.timestamp} &bull; Load: ${item.heating_load} &bull; Fuel: ${item.diesel_liters}</span>
        </div>
        <button class="btn-report-download" onclick="downloadReportBtn.click()">Re-download</button>
      `;
      list.appendChild(div);
    });
  } catch (e) {
    list.innerHTML = "<p>Error loading reports archive.</p>";
  }
}

// ---------------- INITIALIZATION ----------------
window.addEventListener("DOMContentLoaded", () => {
  // Check if user has an active "Remember Me" session
  checkRememberedLogin();
});
