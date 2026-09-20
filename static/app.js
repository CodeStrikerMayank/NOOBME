// ThermoShelter-AI Web Dashboard Client v2.0

// State variables
let currentParams = {
  thickness_mm: 250,
  ambient_temp: -10,
  material_name: "High-Performance Composite",
  target_temp: 21.0
};

let reportHistory = [
  { time: "Today 09:30", material: "High-Performance Composite", thickness: "250mm", eff: "90%", pmv: "+1.76" },
  { time: "Yesterday 16:45", material: "Aerogel", thickness: "180mm", eff: "94%", pmv: "+0.15" },
  { time: "Sep 18 11:20", material: "EPS Standard", thickness: "150mm", eff: "78%", pmv: "-0.40" }
];

// DOM elements
const thicknessSlider = document.getElementById("thicknessSlider");
const thicknessBadge = document.getElementById("thicknessBadge");
const tempSlider = document.getElementById("tempSlider");
const tempBadge = document.getElementById("tempBadge");
const materialSelect = document.getElementById("materialSelect");
const startSimBtn = document.getElementById("startSimBtn");
const simProgressBar = document.getElementById("simProgressBar");
const simStatusText = document.getElementById("simStatusText");
const downloadReportBtn = document.getElementById("downloadReportBtn");
const liveWeatherBtn = document.getElementById("liveWeatherBtn");

const efficiencyVal = document.getElementById("efficiencyVal");
const bridgeCountVal = document.getElementById("bridgeCountVal");
const heatingLoadVal = document.getElementById("heatingLoadVal");
const comfortStatusText = document.getElementById("comfortStatusText");
const pmvPpdText = document.getElementById("pmvPpdText");
const comfortBadge = document.getElementById("comfortBadge");

// Navigation buttons
const navDashboard = document.getElementById("navDashboard");
const navSolver = document.getElementById("navSolver");
const navHeatmaps = document.getElementById("navHeatmaps");
const navReports = document.getElementById("navReports");
const navAdmin = document.getElementById("navAdmin");
const navAccount = document.getElementById("navAccount");
const navAuth = document.getElementById("navAuth");
const profileBtn = document.getElementById("profileBtn");
const profileBtnName = document.getElementById("profileBtnName");
const notifBtn = document.getElementById("notifBtn");
const notifDropdown = document.getElementById("notifDropdown");

// Onboard Auth & Action elements
const headerAuthBtn = document.getElementById("headerAuthBtn");
const headerAuthText = document.getElementById("headerAuthText");
const headerAuthDot = document.getElementById("headerAuthDot");
const saveDesignBtn = document.getElementById("saveDesignBtn");

// Modals
const adminModal = document.getElementById("adminModal");
const reportsModal = document.getElementById("reportsModal");
const accountModal = document.getElementById("accountModal");
const authModal = document.getElementById("authModal");
const healthModal = document.getElementById("healthModal");
const healthStatusBtn = document.getElementById("healthStatusBtn");
const toastBox = document.getElementById("toastBox");

// Current Onboard User Session
let currentUser = JSON.parse(localStorage.getItem("thermo_user") || "null");

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

// ---------------- THREE.JS 3D VISUALIZATION ----------------
let scene, camera, renderer, controls, shelterGroup;

function initThreeScene() {
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

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xfff5eb, 0.9);
  dirLight.position.set(15, 25, 12);
  dirLight.castShadow = true;
  scene.add(dirLight);

  const fillLight = new THREE.DirectionalLight(0xdbeafe, 0.4);
  fillLight.position.set(-10, 10, -10);
  scene.add(fillLight);

  // 3D Floor Grid & Axis Lines
  buildGridAndAxes();

  // Create architectural shelter model
  shelterGroup = new THREE.Group();
  scene.add(shelterGroup);
  buildShelterGeometry(-10, 20);

  // Hook camera presets
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
  const norm = Math.max(0, Math.min(1, (t + 20) / 40));
  let r = 0, g = 0, b = 0;
  if (norm < 0.25) {
    const f = norm / 0.25;
    r = 0.2 + 0.1 * f;
    g = 0.3 + 0.5 * f;
    b = 0.7 + 0.3 * f;
  } else if (norm < 0.5) {
    const f = (norm - 0.25) / 0.25;
    r = 0.3 + 0.5 * f;
    g = 0.8 + 0.2 * f;
    b = 1.0 - 0.7 * f;
  } else if (norm < 0.75) {
    const f = (norm - 0.5) / 0.25;
    r = 0.8 + 0.2 * f;
    g = 1.0 - 0.4 * f;
    b = 0.3 - 0.2 * f;
  } else {
    const f = (norm - 0.75) / 0.25;
    r = 1.0;
    g = 0.6 - 0.45 * f;
    b = 0.1 - 0.05 * f;
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

    setTimeout(() => { simProgressBar.style.width = "45%"; }, 100);
    setTimeout(() => { simProgressBar.style.width = "100%"; }, 250);
  }

  currentParams.thickness_mm = parseFloat(thicknessSlider.value);
  currentParams.ambient_temp = parseFloat(tempSlider.value);
  currentParams.material_name = materialSelect.value;

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
    efficiencyVal.innerText = `${r.thermal_efficiency}%`;
    bridgeCountVal.innerText = `${r.cold_bridge_count}`;
    heatingLoadVal.innerText = `${r.heating_load_kwh_day} kWh/day`;
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

    // Update 3D visual shelter model colors
    buildShelterGeometry(r.t_out, r.t_in);

    if (!isSilent) {
      simStatusText.innerText = "0.38s (Complete)";
      startSimBtn.style.opacity = "1";
      showToast(`Simulation Complete: ${r.thermal_efficiency}% Efficiency`);
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
  if (!currentUser) {
    showToast("Sign in or Sign up is compulsory to adjust parameters", "🔒");
    openAuthModal("tabLogin");
    return;
  }
  thicknessBadge.innerText = e.target.value;
  runSolver(true);
});

tempSlider.addEventListener("input", (e) => {
  if (!currentUser) {
    showToast("Sign in or Sign up is compulsory to adjust parameters", "🔒");
    openAuthModal("tabLogin");
    return;
  }
  const val = e.target.value;
  tempBadge.innerText = val > 0 ? `+${val}` : val;
  runSolver(true);
});

materialSelect.addEventListener("change", () => {
  if (!currentUser) {
    showToast("Sign in or Sign up is compulsory to select materials", "🔒");
    openAuthModal("tabLogin");
    return;
  }
  runSolver(true);
  showToast(`Material updated: ${materialSelect.value}`);
});

startSimBtn.addEventListener("click", () => {
  if (!currentUser) {
    showToast("Sign in or Sign up is compulsory to run simulation", "🔒");
    openAuthModal("tabLogin");
    return;
  }
  runSolver(false);
});

// Download PDF Report
downloadReportBtn.addEventListener("click", async () => {
  if (!currentUser) {
    showToast("Sign in or Sign up is compulsory to download blueprint reports", "🔒");
    openAuthModal("tabLogin");
    return;
  }
  try {
    downloadReportBtn.style.opacity = "0.7";
    showToast("Generating Blueprint PDF...", "⏳");

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
    a.download = `ThermoShelter_Blueprint_${currentParams.material_name.replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    // Add to history
    reportHistory.unshift({
      time: "Just now",
      material: currentParams.material_name,
      thickness: `${currentParams.thickness_mm}mm`,
      eff: efficiencyVal.innerText,
      pmv: pmvPpdText.innerText.split('|')[0].trim()
    });

    showToast("PDF Blueprint Downloaded Successfully!");
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
    showToast("Fetching Open-Meteo Alpine Climate...", "☁");
    const res = await fetch("/api/live-climate?lat=28.6139&lon=77.2090");
    if (!res.ok) throw new Error("Weather API failed");
    const data = await res.json();

    const roundedTemp = Math.round(data.temperature);
    tempSlider.value = roundedTemp;
    tempBadge.innerText = roundedTemp > 0 ? `+${roundedTemp}` : roundedTemp;
    
    await runSolver(false);
    liveWeatherBtn.innerHTML = `<span>✓ Synced (${roundedTemp}°C)</span>`;
    showToast(`Open-Meteo Synced: ${roundedTemp}°C`);

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

navDashboard.addEventListener("click", () => {
  setActiveNav(navDashboard);
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

navReports.addEventListener("click", () => {
  setActiveNav(navReports);
  populateReportsModal();
  reportsModal.classList.add("open");
});

navAdmin.addEventListener("click", async () => {
  setActiveNav(navAdmin);
  await populateAdminMaterials();
  adminModal.classList.add("open");
});

navAccount.addEventListener("click", () => {
  setActiveNav(navAccount);
  accountModal.classList.add("open");
});

profileBtn.addEventListener("click", () => {
  accountModal.classList.add("open");
});

// Onboard Auth Navigation & Button Click Handlers
if (navAuth) {
  navAuth.addEventListener("click", () => {
    setActiveNav(navAuth);
    openAuthModal(currentUser ? "tabDesigns" : "tabLogin");
  });
}

if (headerAuthBtn) {
  headerAuthBtn.addEventListener("click", () => {
    openAuthModal(currentUser ? "tabDesigns" : "tabLogin");
  });
}

if (saveDesignBtn) {
  saveDesignBtn.addEventListener("click", () => {
    if (!currentUser) {
      showToast("Please log in to save blueprints to onboard store", "🔒");
      openAuthModal("tabLogin");
    } else {
      openAuthModal("tabDesigns");
      setTimeout(() => {
        const inp = document.getElementById("designNameInput");
        if (inp) inp.focus();
      }, 200);
    }
  });
}

// Render Health & Keep-Awake Modal Listeners
if (healthStatusBtn && healthModal) {
  healthStatusBtn.addEventListener("click", () => {
    healthModal.classList.add("open");
    fetchHealthStatus();
  });
}

const copyHealthUrlBtn = document.getElementById("copyHealthUrlBtn");
if (copyHealthUrlBtn) {
  copyHealthUrlBtn.addEventListener("click", () => {
    const input = document.getElementById("healthCheckUrlInput");
    if (input) {
      navigator.clipboard.writeText(input.value);
      showToast("Copied Health URL to clipboard!", "📋");
      copyHealthUrlBtn.innerHTML = `<span>✓ Copied</span>`;
      setTimeout(() => {
        copyHealthUrlBtn.innerHTML = `
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <span>Copy URL</span>
        `;
      }, 2500);
    }
  });
}

async function fetchHealthStatus() {
  const statusEl = document.getElementById("healthModalStatus");
  const uptimeEl = document.getElementById("healthModalUptime");
  const pingsEl = document.getElementById("healthModalPings");
  const envEl = document.getElementById("healthModalEnv");
  const urlInput = document.getElementById("healthCheckUrlInput");

  if (urlInput) {
    urlInput.value = `${window.location.origin}/health`;
  }

  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();

    if (statusEl) statusEl.innerText = data.status.toUpperCase();
    if (uptimeEl) uptimeEl.innerText = data.uptime_formatted;
    if (pingsEl) pingsEl.innerText = data.pings_received;
    if (envEl) envEl.innerText = data.environment === "render" ? "Render Web Service" : "Local Fast-API";
  } catch (err) {
    if (statusEl) {
      statusEl.innerText = "OFFLINE";
      statusEl.className = "store-stat-val";
      statusEl.style.color = "#dc2626";
    }
  }
}

// ---------------- 24/7 BROWSER KEEP-ALIVE PULSE ----------------
// Pings /api/health every 5 minutes while this tab or a monitor tab is open
// Render free tier sleeps after 15m; a 5m pulse prevents it from sleeping!
setInterval(() => {
  fetch("/api/health")
    .then(res => res.json())
    .then(data => {
      const pulseText = document.getElementById("clientPulseText");
      if (pulseText) {
        const timeStr = new Date().toLocaleTimeString();
        pulseText.innerText = `● Client Pulse: Sent at ${timeStr} (Next in 5m)`;
      }
    })
    .catch(() => {});
}, 300000); // 300,000 ms = 5 minutes

notifBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  notifDropdown.classList.toggle("show");
});

window.addEventListener("click", () => {
  notifDropdown.classList.remove("show");
});

// Close modals
document.querySelectorAll(".modal-close, .modal-overlay").forEach(el => {
  el.addEventListener("click", (e) => {
    if (e.target === el || e.target.classList.contains("modal-close")) {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("open"));
    }
  });
});

async function populateAdminMaterials() {
  const tbody = document.getElementById("adminMaterialsBody");
  tbody.innerHTML = "<tr><td colspan='5'>Loading database...</td></tr>";
  try {
    const res = await fetch("/api/materials");
    const data = await res.json();
    tbody.innerHTML = "";
    Object.entries(data).forEach(([name, props]) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${name}</strong></td>
        <td>${props.k.toFixed(3)}</td>
        <td>${props.density} kg/m³</td>
        <td>${props.cost_index.toFixed(2)}x</td>
        <td><small>${props.source}</small></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan='5'>Error: ${err.message}</td></tr>`;
  }
}

function populateReportsModal() {
  const list = document.getElementById("reportHistoryList");
  list.innerHTML = "";
  reportHistory.forEach(item => {
    const div = document.createElement("div");
    div.className = "report-item";
    div.innerHTML = `
      <div class="report-info">
        <strong>${item.material} (${item.thickness})</strong>
        <span>Generated: ${item.time} | Efficiency: ${item.eff} | Comfort: ${item.pmv}</span>
      </div>
      <button class="btn-report-download" onclick="downloadReportBtn.click()">Download PDF</button>
    `;
    list.appendChild(div);
  });
}

// ---------------- ONBOARD AUTH & DATA STORE LOGIC ----------------

function openAuthModal(defaultTabId = "tabLogin") {
  if (authModal) {
    authModal.classList.add("open");
    switchAuthTab(defaultTabId);
    fetchOnboardUsers();
    if (currentUser) {
      refreshUserProfile();
    }
  }
}

function switchAuthTab(targetPaneId) {
  document.querySelectorAll(".auth-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.target === targetPaneId);
  });
  document.querySelectorAll(".auth-tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === targetPaneId);
  });

  if (targetPaneId === "tabStore") {
    fetchOnboardUsers();
  }
}

// Tab Button Clicks
document.querySelectorAll(".auth-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const target = btn.dataset.target;
    switchAuthTab(target);
  });
});

// Switch links inside forms
const switchToSignupBtn = document.getElementById("switchToSignupBtn");
if (switchToSignupBtn) {
  switchToSignupBtn.addEventListener("click", () => switchAuthTab("tabSignup"));
}

const switchToLoginBtn = document.getElementById("switchToLoginBtn");
if (switchToLoginBtn) {
  switchToLoginBtn.addEventListener("click", () => switchAuthTab("tabLogin"));
}

const emptyStateLoginBtn = document.getElementById("emptyStateLoginBtn");
if (emptyStateLoginBtn) {
  emptyStateLoginBtn.addEventListener("click", () => switchAuthTab("tabLogin"));
}

// 1-Click Demo Presets
const presetAdminBtn = document.getElementById("presetAdminBtn");
if (presetAdminBtn) {
  presetAdminBtn.addEventListener("click", () => {
    document.getElementById("loginUsername").value = "admin";
    document.getElementById("loginPassword").value = "admin123";
    showToast("Filled demo admin credentials", "🔑");
  });
}

const presetEngineerBtn = document.getElementById("presetEngineerBtn");
if (presetEngineerBtn) {
  presetEngineerBtn.addEventListener("click", () => {
    document.getElementById("loginUsername").value = "engineer";
    document.getElementById("loginPassword").value = "engineer123";
    showToast("Filled demo engineer credentials", "⚡");
  });
}

// Login Submission
const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = document.getElementById("loginUsername").value.trim();
    const p = document.getElementById("loginPassword").value;
    const submitBtn = document.getElementById("loginSubmitBtn");

    if (!u || !p) {
      showToast("Please enter both username and password", "✕");
      return;
    }

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = "<span>Authenticating...</span>";

      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      currentUser = data.user;
      localStorage.setItem("thermo_user", JSON.stringify(currentUser));
      updateAuthUI();
      showToast(`Welcome back, ${currentUser.name}!`, "✓");
      switchAuthTab("tabDesigns");
      fetchOnboardUsers();
    } catch (err) {
      showToast(err.message, "✕");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Authenticate & Connect</span><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>`;
    }
  });
}

// Sign Up Submission
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("signupName").value.trim();
    const username = document.getElementById("signupUsername").value.trim();
    const role = document.getElementById("signupRole").value;
    const password = document.getElementById("signupPassword").value;
    const submitBtn = document.getElementById("signupSubmitBtn");

    if (!name || !username || !password) {
      showToast("Please fill all required registration fields", "✕");
      return;
    }

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = "<span>Registering in Onboard System...</span>";

      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          username: username,
          role: role,
          password: password
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Sign up failed");
      }

      currentUser = data.user;
      localStorage.setItem("thermo_user", JSON.stringify(currentUser));
      updateAuthUI();
      showToast(`User created & saved to onboard store!`, "✓");
      switchAuthTab("tabDesigns");
      fetchOnboardUsers();
    } catch (err) {
      showToast(err.message, "✕");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Register & Sign In</span><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>`;
    }
  });
}

// Log Out Handler
const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    currentUser = null;
    localStorage.removeItem("thermo_user");
    updateAuthUI();
    showToast("Logged out. Operating in Guest mode.", "ℹ");
    switchAuthTab("tabLogin");
  });
}

// Fetch and Render Onboard Data Store Users
async function fetchOnboardUsers() {
  const tbody = document.getElementById("storeTableBody");
  const storeUserCountBadge = document.getElementById("storeUserCountBadge");
  const storeStatTotalUsers = document.getElementById("storeStatTotalUsers");
  const storeStatTotalDesigns = document.getElementById("storeStatTotalDesigns");

  if (!tbody) return;

  try {
    const res = await fetch("/api/auth/users");
    if (!res.ok) throw new Error("Failed to load onboard users");
    const users = await res.json();

    let totalDesigns = 0;
    tbody.innerHTML = "";

    users.forEach(u => {
      totalDesigns += (u.designs_count || 0);
      const isCurrent = currentUser && currentUser.username === u.username;
      const initial = (u.name || u.username || "U").charAt(0).toUpperCase();

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>
          <div class="user-badge-cell">
            <div class="user-cell-avatar">${initial}</div>
            <div>
              <strong>${u.name}</strong>
              ${isCurrent ? '<small style="color: #059669; font-weight:700; display:block;">(Active Session)</small>' : ''}
            </div>
          </div>
        </td>
        <td><code>${u.username}</code></td>
        <td><span class="role-tag">${u.role}</span></td>
        <td><strong>${u.designs_count || 0}</strong> saved</td>
        <td><small style="color: var(--text-muted);">${u.created_at ? u.created_at.split("T")[0] : "System"}</small></td>
        <td>
          ${isCurrent 
            ? '<span style="color:#059669; font-weight:700; font-size:0.75rem;">Connected</span>' 
            : `<button class="btn-switch-user" onclick="quickFillAndSwitchUser('${u.username}')">Select User</button>`
          }
        </td>
      `;
      tbody.appendChild(tr);
    });

    if (storeStatTotalUsers) storeStatTotalUsers.innerText = users.length;
    if (storeStatTotalDesigns) storeStatTotalDesigns.innerText = totalDesigns;
    if (storeUserCountBadge) storeUserCountBadge.innerText = users.length;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #dc2626;">Error loading onboard store: ${err.message}</td></tr>`;
  }
}

// Quick switch user helper
window.quickFillAndSwitchUser = function(username) {
  document.getElementById("loginUsername").value = username;
  document.getElementById("loginPassword").value = username === "admin" ? "admin123" : (username === "engineer" ? "engineer123" : "");
  switchAuthTab("tabLogin");
  showToast(`Selected user '${username}'. Enter password to connect.`, "👤");
};

// Refresh User Profile from Onboard Storage
async function refreshUserProfile() {
  if (!currentUser || !currentUser.username) return;
  try {
    const res = await fetch(`/api/auth/user/${encodeURIComponent(currentUser.username)}`);
    if (!res.ok) return;
    const data = await res.json();
    currentUser = data.user;
    localStorage.setItem("thermo_user", JSON.stringify(currentUser));
    updateAuthUI();
  } catch (err) {
    console.warn("Could not sync user profile:", err);
  }
}

// Save Active Model to Onboard Profile
const saveCurrentModelBtn = document.getElementById("saveCurrentModelBtn");
if (saveCurrentModelBtn) {
  saveCurrentModelBtn.addEventListener("click", async () => {
    if (!currentUser) {
      showToast("Please log in first", "🔒");
      switchAuthTab("tabLogin");
      return;
    }

    const designNameInput = document.getElementById("designNameInput");
    const customName = designNameInput.value.trim() || 
      `${materialSelect.value} (${thicknessSlider.value}mm @ ${tempSlider.value}°C)`;

    const params = {
      thickness_mm: parseFloat(thicknessSlider.value),
      ambient_temp: parseFloat(tempSlider.value),
      material_name: materialSelect.value,
      target_temp: currentParams.target_temp || 21.0
    };

    const results = {
      efficiency: efficiencyVal ? efficiencyVal.innerText : "N/A",
      heating_load: heatingLoadVal ? heatingLoadVal.innerText : "N/A",
      comfort: comfortStatusText ? comfortStatusText.innerText : "N/A",
      pmv: pmvPpdText ? pmvPpdText.innerText : "N/A"
    };

    try {
      saveCurrentModelBtn.disabled = true;
      saveCurrentModelBtn.innerText = "Saving to Onboard Store...";

      const res = await fetch("/api/auth/save-design", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: currentUser.username,
          design_name: customName,
          parameters: params,
          results: results
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to save design");

      if (!currentUser.designs) currentUser.designs = [];
      currentUser.designs.unshift(data.design);
      localStorage.setItem("thermo_user", JSON.stringify(currentUser));

      designNameInput.value = "";
      updateAuthUI();
      fetchOnboardUsers();
      showToast(`Saved '${customName}' to onboard storage!`, "✓");
    } catch (err) {
      showToast(err.message, "✕");
    } finally {
      saveCurrentModelBtn.disabled = false;
      saveCurrentModelBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
          <polyline points="17 21 17 13 7 13 7 21"/>
          <polyline points="7 3 7 8 15 8"/>
        </svg>
        <span>Save Active Model</span>
      `;
    }
  });
}

// Load a Saved Blueprint into Solver
window.loadSavedBlueprint = function(designIndex) {
  if (!currentUser || !currentUser.designs || !currentUser.designs[designIndex]) return;
  const d = currentUser.designs[designIndex];
  const p = d.parameters || {};

  if (p.thickness_mm) {
    thicknessSlider.value = p.thickness_mm;
    thicknessBadge.innerText = p.thickness_mm;
  }
  if (p.ambient_temp !== undefined) {
    tempSlider.value = p.ambient_temp;
    tempBadge.innerText = p.ambient_temp > 0 ? `+${p.ambient_temp}` : p.ambient_temp;
  }
  if (p.material_name) {
    materialSelect.value = p.material_name;
  }

  runSolver(false);
  authModal.classList.remove("open");
  showToast(`Loaded '${d.name}' into 3D Solver`, "📐");
};

// Delete a Saved Blueprint from Onboard Store
window.deleteSavedBlueprint = async function(designId) {
  if (!currentUser || !currentUser.username) return;
  if (!confirm("Are you sure you want to remove this blueprint from the onboard system?")) return;

  try {
    const res = await fetch(`/api/auth/user/${encodeURIComponent(currentUser.username)}/design/${encodeURIComponent(designId)}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Failed to delete design");

    currentUser.designs = (currentUser.designs || []).filter(d => d.id !== designId);
    localStorage.setItem("thermo_user", JSON.stringify(currentUser));
    updateAuthUI();
    fetchOnboardUsers();
    showToast("Blueprint removed from onboard store", "🗑");
  } catch (err) {
    showToast(err.message, "✕");
  }
};

// Refresh Refresh button
const refreshStoreBtn = document.getElementById("refreshStoreBtn");
if (refreshStoreBtn) {
  refreshStoreBtn.addEventListener("click", () => {
    fetchOnboardUsers();
    showToast("Onboard store synchronized", "✓");
  });
}

// Quick Preset Helper for 1-Click Login
async function loginWithPreset(username, password) {
  try {
    showToast(`Connecting as ${username}...`, "🔑");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Authentication failed");

    currentUser = data.user;
    localStorage.setItem("thermo_user", JSON.stringify(currentUser));
    updateAuthUI();
    showToast(`Operator connected: ${currentUser.name}! System Unlocked.`, "✓");
    runSolver(false);
    fetchOnboardUsers();
    if (authModal) authModal.classList.remove("open");
  } catch (err) {
    showToast(err.message, "✕");
  }
}

// Wire Compulsory Lock Overlay Buttons
const lockDemoAdminBtn = document.getElementById("lockDemoAdminBtn");
if (lockDemoAdminBtn) {
  lockDemoAdminBtn.addEventListener("click", () => loginWithPreset("admin", "admin123"));
}

const lockDemoEngineerBtn = document.getElementById("lockDemoEngineerBtn");
if (lockDemoEngineerBtn) {
  lockDemoEngineerBtn.addEventListener("click", () => loginWithPreset("engineer", "engineer123"));
}

const lockLoginBtn = document.getElementById("lockLoginBtn");
if (lockLoginBtn) {
  lockLoginBtn.addEventListener("click", () => openAuthModal("tabLogin"));
}

const lockSignupBtn = document.getElementById("lockSignupBtn");
if (lockSignupBtn) {
  lockSignupBtn.addEventListener("click", () => openAuthModal("tabSignup"));
}

// Update Active User UI across Dashboard
function updateAuthUI() {
  const headerAuthText = document.getElementById("headerAuthText");
  const headerAuthDot = document.getElementById("headerAuthDot");
  const profileBtnName = document.getElementById("profileBtnName");
  const userDesignsCountBadge = document.getElementById("userDesignsCountBadge");
  const designsLoggedOutView = document.getElementById("designsLoggedOutView");
  const designsLoggedInView = document.getElementById("designsLoggedInView");
  const bannerAvatar = document.getElementById("bannerAvatar");
  const bannerUserName = document.getElementById("bannerUserName");
  const bannerUserRole = document.getElementById("bannerUserRole");
  const bannerUserMeta = document.getElementById("bannerUserMeta");
  const blueprintCountTag = document.getElementById("blueprintCountTag");
  const blueprintsGrid = document.getElementById("blueprintsGrid");
  const dashboardLockOverlay = document.getElementById("dashboardLockOverlay");

  if (currentUser) {
    // Unlocked Dashboard State
    if (dashboardLockOverlay) dashboardLockOverlay.style.display = "none";

    const initial = (currentUser.name || currentUser.username || "U").charAt(0).toUpperCase();
    if (headerAuthText) headerAuthText.innerText = currentUser.name.split(" ")[0];
    if (headerAuthDot) {
      headerAuthDot.className = "auth-status-dot online";
      headerAuthDot.title = "Connected to Onboard System";
    }
    if (profileBtnName) profileBtnName.innerText = currentUser.name.split(" ")[0];

    if (designsLoggedOutView) designsLoggedOutView.style.display = "none";
    if (designsLoggedInView) designsLoggedInView.style.display = "block";

    if (bannerAvatar) bannerAvatar.innerText = initial;
    if (bannerUserName) bannerUserName.innerText = currentUser.name;
    if (bannerUserRole) bannerUserRole.innerText = currentUser.role || "Operator";
    if (bannerUserMeta) bannerUserMeta.innerText = `User ID: ${currentUser.username} | Target: data/onboard_users.json`;

    const designs = currentUser.designs || [];
    if (userDesignsCountBadge) userDesignsCountBadge.innerText = designs.length;
    if (blueprintCountTag) blueprintCountTag.innerText = `${designs.length} saved in onboard store`;

    if (blueprintsGrid) {
      if (designs.length === 0) {
        blueprintsGrid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted); background: var(--pill-bg); border-radius: 8px;">
            No custom blueprints saved yet. Use the "Save Active Model" button above to preserve your current 3D shelter configuration.
          </div>
        `;
      } else {
        blueprintsGrid.innerHTML = "";
        designs.forEach((d, idx) => {
          const p = d.parameters || {};
          const r = d.results || {};
          const card = document.createElement("div");
          card.className = "blueprint-card";
          card.innerHTML = `
            <div class="blueprint-header">
              <div>
                <strong>${d.name}</strong>
                <span class="blueprint-time">${d.saved_at || "Recent"}</span>
              </div>
              <span class="role-tag">${p.material_name || "Composite"}</span>
            </div>
            <div class="blueprint-stats">
              <div class="blueprint-stat-item">
                <span>Thickness:</span> <strong>${p.thickness_mm || 250}mm</strong>
              </div>
              <div class="blueprint-stat-item">
                <span>Ambient:</span> <strong>${p.ambient_temp !== undefined ? p.ambient_temp : -10}°C</strong>
              </div>
              <div class="blueprint-stat-item">
                <span>Efficiency:</span> <strong>${r.efficiency || "N/A"}</strong>
              </div>
              <div class="blueprint-stat-item">
                <span>Heating Load:</span> <strong>${r.heating_load || "N/A"}</strong>
              </div>
            </div>
            <div class="blueprint-actions">
              <button class="btn-load-blueprint" onclick="loadSavedBlueprint(${idx})">Load into Solver</button>
              <button class="btn-delete-blueprint" onclick="deleteSavedBlueprint('${d.id}')" title="Delete Blueprint">🗑</button>
            </div>
          `;
          blueprintsGrid.appendChild(card);
        });
      }
    }
  } else {
    // Locked Dashboard State (Sign In / Sign Up Compulsory)
    if (dashboardLockOverlay) dashboardLockOverlay.style.display = "flex";

    if (headerAuthText) headerAuthText.innerText = "Login / Sign Up";
    if (headerAuthDot) {
      headerAuthDot.className = "auth-status-dot offline";
      headerAuthDot.title = "Authentication Compulsory";
    }
    if (profileBtnName) profileBtnName.innerText = "Profile";

    if (designsLoggedOutView) designsLoggedOutView.style.display = "flex";
    if (designsLoggedInView) designsLoggedInView.style.display = "none";
    if (userDesignsCountBadge) userDesignsCountBadge.innerText = "0";
  }
}

// Initialize on page load
// The main dashboard is the page, but authentication is compulsory to use it.
window.addEventListener("DOMContentLoaded", () => {
  initThreeScene();
  updateAuthUI();
  fetchOnboardUsers();

  if (currentUser) {
    runSolver(true);
  } else {
    // Show compulsory auth modal and lock overlay
    openAuthModal("tabLogin");
    showToast("Operator sign in or sign up is compulsory to use the system", "🔒");
  }
});
