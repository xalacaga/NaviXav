"use strict";

const $ = (id) => document.getElementById(id);
const t = (key) => window.I18N.t(key);

const CONFIDENCE_CLASS = {
  "élevée": "high",
  "modérée": "medium",
  "faible": "low",
  "aucune": "none",
};

const SOURCE_LABEL = {
  simbrief: "SimBrief",
  moteur: "calculé",
  utilisateur: "imposé",
};

let currentPlan = null;
let currentChart = null;
let currentIcao = null;
let currentMapRole = null;
let liveTimer = null;
let simulatorTimer = null;
let activeRoutePointIndex = null;
let latestAircraft = null;
let flightGeometry = [];
let flightLog = [];
let flightRecording = true;
let lastFlightLogAt = 0;
let replayTimer = null;
let replayActive = false;
const siaRequests = new Map();
const officialAirportRequests = new Map();
const siaOverlayCandidates = new Map();
let siaOverlayKey = null;

const EARTH_RADIUS_M = 6378137;
const LIVE_INTERVAL_MS = 1000;
const FLIGHT_LOG_INTERVAL_MS = 5000;
const FLIGHT_LOG_MAX_POINTS = 3600;
const TERMINAL_COLLAPSED_KEY = "navixav-terminal-collapsed";

/* ------------------------------------------------------------------ utils */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function show(node, visible) {
  node.classList.toggle("hidden", !visible);
}

function setTerminalCollapsed(collapsed) {
  const terminal = $("terminal");
  const button = $("terminal-toggle");
  terminal.classList.toggle("collapsed", collapsed);
  button.textContent = collapsed ? t("expand") : t("collapse");
  button.setAttribute("aria-expanded", String(!collapsed));
}

function toggleTerminal() {
  const collapsed = !$("terminal").classList.contains("collapsed");
  localStorage.setItem(TERMINAL_COLLAPSED_KEY, String(collapsed));
  setTerminalCollapsed(collapsed);
}

function confidenceClass(choice) {
  return CONFIDENCE_CLASS[choice?.confidence] || "none";
}

function needsCheck(choice) {
  return choice?.value && ["modérée", "faible", "aucune"].includes(choice.confidence);
}

/* ----------------------------------------------------------------- status */

async function loadStatus() {
  const status = await fetch("/api/status").then((r) => r.json());

  $("footer-version").textContent = `NaviXav ${status.version}`;
  $("footer-source").textContent = `SimBrief ${status.simbrief_target} · METAR ${status.metar_source}`;

  if (!status.simbrief_configured) {
    $("empty-hint").textContent = t("no_simbrief");
  }
  if (status.demo_available) $("demo-toggle").disabled = false;
  return status;
}

async function checkForUpdates() {
  const button = $("update-install");
  try {
    const response = await fetch("/api/update/check", { cache: "no-store" });
    const update = await response.json();
    if (!response.ok || !update.available) return;
    button.dataset.version = update.latest_version;
    button.textContent = `${t("update_available")} ${update.latest_version}`;
    button.title = t("update_title");
    show(button, true);
  } catch (_error) {
    // Une coupure réseau ne doit jamais gêner le démarrage ou le vol.
  }
}

async function installAvailableUpdate() {
  const button = $("update-install");
  const version = button.dataset.version || "";
  if (!window.confirm(t("update_confirm").replace("{version}", version))) return;
  button.disabled = true;
  button.textContent = t("update_downloading");
  try {
    const response = await fetch("/api/update/install", {
      method: "POST",
      headers: { "X-NaviXav-Update": "install" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("update_failed"));
    button.textContent = t("update_restarting");
    showBanner("info", t("update_ready"), [t("update_restart_body")]);
  } catch (error) {
    button.disabled = false;
    button.textContent = `${t("update_available")} ${version}`;
    showBanner("error", t("update_failed"), [String(error)]);
  }
}

async function pollSimulatorStatus() {
  const indicator = $("sim-status");
  try {
    const status = await fetch("/api/simulator", { cache: "no-store" }).then((r) => r.json());
    indicator.classList.toggle("online", Boolean(status.connected));
    indicator.classList.toggle("offline", !status.connected);
    $("sim-status-text").textContent = status.connected ? t("sim_connected") : t("sim_offline");
    indicator.title = status.connected
      ? `Connexion directe active · ${status.source || "SimConnect"}`
      : (status.reason || "Microsoft Flight Simulator ne répond pas");
  } catch (_error) {
    indicator.classList.remove("online");
    indicator.classList.add("offline");
    $("sim-status-text").textContent = t("server_stopped");
  }
}

async function shutdownApplication() {
  const button = $("shutdown");
  button.disabled = true;
  button.textContent = t("stopping");
  try {
    const response = await fetch("/api/shutdown", { method: "POST" });
    if (!response.ok) throw new Error("Le serveur n’a pas accepté l’arrêt");
    clearInterval(simulatorTimer);
    document.body.innerHTML = "";
    const stopped = el("main", "empty");
    stopped.append(el("h2", null, t("stopped_title")), el("p", null, t("stopped_body")));
    document.body.append(stopped);
  } catch (error) {
    button.disabled = false;
    button.textContent = t("quit");
    showBanner("error", "Impossible d’arrêter NaviXav", [String(error)]);
  }
}

async function openSettings() {
  const message = $("settings-message");
  message.textContent = "";
  message.className = "settings-message";
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) throw new Error("Paramètres indisponibles");
    const values = await response.json();
    $("settings-pilot-id").value = values.simbrief_pilot_id || "";
    $("settings-username").value = values.simbrief_username || "";
    $("settings-metar").value = values.metar_source || "simbrief";
    $("settings-approaches").value = (values.approach_preference || []).join(", ");
    $("settings-tailwind").value = values.max_tailwind_kt;
    $("settings-crosswind").value = values.max_crosswind_kt;
    $("settings-runway-length").value = values.min_runway_length_ft;
    $("settings-rnp").checked = Boolean(values.aircraft_rnp_capable);
    $("settings-language").value = window.I18N.getLanguage();
    $("settings-dialog").showModal();
  } catch (error) {
    showBanner("error", "Impossible d’ouvrir les paramètres", [String(error)]);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const message = $("settings-message");
  message.textContent = t("saving");
  message.className = "settings-message";
  const payload = {
    simbrief_pilot_id: $("settings-pilot-id").value.trim(),
    simbrief_username: $("settings-username").value.trim(),
    // Vide : la base NaviXav garde son emplacement par défaut.
    navdata_store: "",
    metar_source: $("settings-metar").value,
    approach_preference: $("settings-approaches").value
      .split(",").map((item) => item.trim()).filter(Boolean),
    max_tailwind_kt: Number($("settings-tailwind").value),
    max_crosswind_kt: Number($("settings-crosswind").value),
    min_runway_length_ft: Number($("settings-runway-length").value),
    aircraft_rnp_capable: $("settings-rnp").checked,
  };
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Enregistrement refusé");
    message.textContent = t("saved");
    const status = await loadStatus();
    if (status.simbrief_configured) {
      $("demo-toggle").checked = false;
      await buildPlan();
    }
    setTimeout(() => $("settings-dialog").close(), 500);
  } catch (error) {
    message.textContent = String(error);
    message.className = "settings-message error";
  }
}

/* ------------------------------------------------------------------- plan */

async function buildPlan() {
  const button = $("refresh");
  button.disabled = true;
  button.querySelector("span").textContent = t("loading_plan");
  showBanner("info", t("cache_title"), [t("cache_body")]);

  try {
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        demo: $("demo-toggle").checked,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      showBanner("error", "Impossible de récupérer le plan", [payload.detail]);
      return;
    }
    currentPlan = payload;
    renderPlan(payload);
  } catch (error) {
    showBanner("error", "Erreur réseau", [String(error)]);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = t("complete");
  }
}

function showBanner(kind, title, lines) {
  const banner = $("banner");
  banner.className = `banner ${kind}`;
  banner.innerHTML = "";
  const body = el("div");
  body.append(el("strong", null, title));
  const list = el("ul");
  for (const line of lines.filter(Boolean)) list.append(el("li", null, line));
  if (list.childElementCount) body.append(list);
  banner.append(body);
  show(banner, true);
}

function hideBanner() {
  show($("banner"), false);
}

/* --------------------------------------------------------------- rendering */

function renderPlan(plan) {
  siaOverlayCandidates.clear();
  clearSiaMapOverlay();
  hideBanner();
  show($("empty"), false);
  for (const id of ["strip", "terminal", "tabs"]) show($(id), true);

  renderStrip(plan);
  renderTerminal(plan);
  renderConstraints(plan);
  renderFlightPanel(plan);
  renderDispatch(plan);
  renderAircraft(plan);
  renderOfficialCharts(plan);
  renderMcdu(plan);
  renderMapBar(plan);
  startLiveLoop();
  $("panel-raw").innerHTML = "";
  $("panel-raw").append(el("pre", null, JSON.stringify(plan, null, 2)));

  if (plan.warnings?.length) {
    showBanner("warn", "Avertissements", plan.warnings);
  }
  selectTab(document.querySelector(".tabs button.active")?.dataset.tab || "constraints");
}

function renderStrip(plan) {
  const strip = $("strip");
  strip.innerHTML = "";
  activeRoutePointIndex = null;

  const chip = (label, value, kind, routeIndex = null) => {
    const node = el("span", `chip ${kind}`);
    if (routeIndex !== null && routeIndex !== undefined) {
      node.dataset.routeIndex = String(routeIndex);
    }
    if (label) node.append(el("small", null, label));
    node.append(document.createTextNode(value));
    return node;
  };

  const dep = plan.departure;
  const arr = plan.arrival;
  const routePath = plan.enroute?.route_path || [];
  let pathCursor = 1;

  if (dep) {
    const originIndex = routePath[0]?.ident === dep.icao ? 0 : null;
    strip.append(chip(null, dep.icao, "apt", originIndex));
    if (dep.runway?.value) strip.append(chip("rwy", dep.runway.value, "proc"));
    if (dep.sid.value) strip.append(chip("sid", dep.sid.value, "proc"));
    if (dep.sid_transition.value) strip.append(chip("trans", dep.sid_transition.value, "wpt"));
  }
  for (const fix of plan.enroute.waypoints || []) {
    const routeIndex = routePath.findIndex(
      (point, index) => index >= pathCursor && point.ident === fix
    );
    if (routeIndex >= 0) pathCursor = routeIndex + 1;
    strip.append(chip(null, fix, "wpt", routeIndex >= 0 ? routeIndex : null));
  }
  if (arr) {
    if (arr.star_transition.value) strip.append(chip("trans", arr.star_transition.value, "wpt"));
    if (arr.star.value) strip.append(chip("star", arr.star.value, "proc"));
    if (arr.approach_transition.value) strip.append(chip("via", arr.approach_transition.value, "wpt"));
    if (arr.approach.value) strip.append(chip("appr", arr.approach.value, "proc"));
    if (arr.runway?.value) strip.append(chip("rwy", arr.runway.value, "proc"));
    const destinationIndex = routePath.findLastIndex(
      (point) => point.ident === arr.icao
    );
    strip.append(chip(
      null,
      arr.icao,
      "apt",
      destinationIndex >= 0 ? destinationIndex : null
    ));
  }
}

function routePointForAircraft(aircraft) {
  const route = currentPlan?.enroute?.route_path || [];
  if (!aircraft || !route.length) return null;

  const latitude = Number(aircraft.latitude);
  const longitude = Number(aircraft.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

  const scaleX = EARTH_RADIUS_M * Math.cos(latitude * Math.PI / 180);
  const scaleY = EARTH_RADIUS_M;
  const relative = (point) => ({
    x: (Number(point.lon) - longitude) * Math.PI / 180 * scaleX,
    y: (Number(point.lat) - latitude) * Math.PI / 180 * scaleY,
  });

  let nearestPoint = { index: 0, distanceSquared: Infinity };
  route.forEach((point, index) => {
    const projected = relative(point);
    const distanceSquared = projected.x ** 2 + projected.y ** 2;
    if (distanceSquared < nearestPoint.distanceSquared) {
      nearestPoint = { index, distanceSquared };
    }
  });
  if (aircraft.on_ground && nearestPoint.distanceSquared <= 10_000 ** 2) {
    return nearestPoint.index;
  }
  if (route.length === 1) return 0;

  let nearestSegment = { index: 0, distanceSquared: Infinity };
  for (let index = 0; index < route.length - 1; index += 1) {
    const start = relative(route[index]);
    const end = relative(route[index + 1]);
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const lengthSquared = dx ** 2 + dy ** 2;
    const progress = lengthSquared
      ? Math.max(0, Math.min(1, -(start.x * dx + start.y * dy) / lengthSquared))
      : 0;
    const x = start.x + progress * dx;
    const y = start.y + progress * dy;
    const distanceSquared = x ** 2 + y ** 2;
    if (distanceSquared < nearestSegment.distanceSquared) {
      nearestSegment = { index, distanceSquared };
    }
  }
  return Math.min(nearestSegment.index + 1, route.length - 1);
}

function updateRouteStripProgress(aircraft) {
  const activeIndex = routePointForAircraft(aircraft);
  const strip = $("strip");
  for (const node of strip.querySelectorAll(".chip[data-route-index]")) {
    const index = Number(node.dataset.routeIndex);
    node.classList.toggle("route-passed", activeIndex !== null && index < activeIndex);
    node.classList.toggle("route-active", activeIndex !== null && index === activeIndex);
    node.classList.toggle("route-upcoming", activeIndex !== null && index > activeIndex);
    if (index === activeIndex) node.title = "Position actuelle de l’avion sur la route";
    else node.removeAttribute("title");
  }

  if (activeIndex === null || activeRoutePointIndex === activeIndex) {
    activeRoutePointIndex = activeIndex;
    return;
  }
  activeRoutePointIndex = activeIndex;
  const active = strip.querySelector(`.chip[data-route-index="${activeIndex}"]`);
  if (active) {
    strip.scrollTo({
      left: Math.max(0, active.offsetLeft - strip.clientWidth / 2 + active.clientWidth / 2),
      behavior: "smooth",
    });
  }
}

/* --------------------------------------------------------- suivi du vol */

function haversineNm(first, second) {
  const lat1 = Number(first.lat ?? first.latitude) * Math.PI / 180;
  const lat2 = Number(second.lat ?? second.latitude) * Math.PI / 180;
  const deltaLat = lat2 - lat1;
  const deltaLon = (
    Number(second.lon ?? second.longitude)
    - Number(first.lon ?? first.longitude)
  ) * Math.PI / 180;
  const value = Math.sin(deltaLat / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
  return (2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(value)))) / 1852;
}

function flightStagePaths(plan) {
  const route = plan.enroute?.route_path || [];
  const origin = route[0];
  const destination = route.at(-1);
  const sid = [...(plan.departure?.sid_path || [])];
  const star = [...(plan.arrival?.star_path || [])];
  const approach = [...(plan.arrival?.approach_path || [])];

  if (origin && sid.length) sid.unshift(origin);
  const departureEnd = sid.at(-1) || origin;
  const arrivalStart = star[0] || approach[0] || destination;
  const enroute = [
    departureEnd,
    ...route.slice(1, -1),
    arrivalStart,
  ].filter(Boolean).filter((point, index, points) => (
    index === 0
    || point.ident !== points[index - 1].ident
    || point.lat !== points[index - 1].lat
    || point.lon !== points[index - 1].lon
  ));
  if (star.length && approach.length) approach.unshift(star.at(-1));

  if (destination) {
    if (approach.length) approach.push(destination);
    else if (star.length) star.push(destination);
  }
  return [
    { stage: "sid", points: sid },
    { stage: "enroute", points: enroute },
    { stage: "star", points: star },
    { stage: "approach", points: approach },
  ].filter((segment) => segment.points.length);
}

function buildFlightGeometry(plan) {
  const geometry = [];
  for (const segment of flightStagePaths(plan)) {
    for (const point of segment.points) {
      if (!Number.isFinite(Number(point.lat)) || !Number.isFinite(Number(point.lon))) continue;
      const entry = {
        ident: point.ident || segment.stage,
        lat: Number(point.lat),
        lon: Number(point.lon),
        stage: segment.stage,
      };
      const previous = geometry[geometry.length - 1];
      if (
        previous
        && previous.ident === entry.ident
        && previous.lat === entry.lat
        && previous.lon === entry.lon
      ) {
        previous.stage = segment.stage;
        continue;
      }
      geometry.push(entry);
    }
  }
  return geometry;
}

function projectAircraftOnFlightPath(aircraft) {
  if (!aircraft || flightGeometry.length < 2) return null;
  const latitude = Number(aircraft.latitude);
  const longitude = Number(aircraft.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

  const scaleX = EARTH_RADIUS_M * Math.cos(latitude * Math.PI / 180);
  const scaleY = EARTH_RADIUS_M;
  const relative = (point) => ({
    x: (point.lon - longitude) * Math.PI / 180 * scaleX,
    y: (point.lat - latitude) * Math.PI / 180 * scaleY,
  });
  let best = null;
  for (let index = 0; index < flightGeometry.length - 1; index += 1) {
    const start = relative(flightGeometry[index]);
    const end = relative(flightGeometry[index + 1]);
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const lengthSquared = dx ** 2 + dy ** 2;
    const progress = lengthSquared
      ? Math.max(0, Math.min(1, -(start.x * dx + start.y * dy) / lengthSquared))
      : 0;
    const x = start.x + progress * dx;
    const y = start.y + progress * dy;
    const distanceSquared = x ** 2 + y ** 2;
    if (!best || distanceSquared < best.distanceSquared) {
      best = { index, progress, distanceSquared };
    }
  }
  if (!best) return null;

  const segmentLength = haversineNm(
    flightGeometry[best.index],
    flightGeometry[best.index + 1]
  );
  let remainingNm = segmentLength * (1 - best.progress);
  for (let index = best.index + 1; index < flightGeometry.length - 1; index += 1) {
    remainingNm += haversineNm(flightGeometry[index], flightGeometry[index + 1]);
  }
  return {
    segmentIndex: best.index,
    segmentProgress: best.progress,
    activeIndex: best.index + 1,
    activePoint: flightGeometry[best.index + 1],
    crossTrackNm: Math.sqrt(best.distanceSquared) / 1852,
    distanceToActiveNm: segmentLength * (1 - best.progress),
    remainingNm,
  };
}

function distanceFromProjectionToIndex(projection, targetIndex) {
  if (!projection || targetIndex <= projection.segmentIndex) return 0;
  let distance = haversineNm(
    flightGeometry[projection.segmentIndex],
    flightGeometry[projection.segmentIndex + 1]
  ) * (1 - projection.segmentProgress);
  for (let index = projection.segmentIndex + 1; index < targetIndex; index += 1) {
    distance += haversineNm(flightGeometry[index], flightGeometry[index + 1]);
  }
  return distance;
}

function constraintAltitudeFt(text, currentAltitude) {
  const values = String(text || "").match(/\d[\d ]*/g)
    ?.map((value) => Number(value.replaceAll(" ", "")))
    .filter(Number.isFinite) || [];
  if (!values.length) return null;
  if (String(text).startsWith("entre") && values.length >= 2) {
    const low = Math.min(...values);
    const high = Math.max(...values);
    if (currentAltitude < low) return low;
    if (currentAltitude > high) return high;
    return Math.round(currentAltitude);
  }
  return values[0];
}

function nextFlightConstraint(plan, projection, aircraft) {
  if (!projection) return null;
  const groups = [
    ["sid", plan.departure?.sid_constraints || []],
    ["star", plan.arrival?.star_constraints || []],
    ["approach", plan.arrival?.approach_constraints || []],
  ];
  const candidates = [];
  for (const [stage, rows] of groups) {
    let cursor = 0;
    for (const row of rows) {
      if (!row.is_fix) continue;
      const index = flightGeometry.findIndex(
        (point, pointIndex) => (
          pointIndex >= cursor
          && point.stage === stage
          && point.ident === row.label
        )
      );
      if (index < 0) continue;
      cursor = index + 1;
      if (index < projection.activeIndex || (!row.altitude && !row.speed)) continue;
      candidates.push({
        ...row,
        stage,
        pathIndex: index,
        distanceNm: distanceFromProjectionToIndex(projection, index),
        altitudeFt: constraintAltitudeFt(row.altitude, Number(aircraft.altitude_ft || 0)),
      });
    }
  }
  candidates.sort((first, second) => first.pathIndex - second.pathIndex);
  return candidates[0] || null;
}

function detectFlightPhase(aircraft, projection) {
  if (!aircraft) return "Hors connexion";
  const speed = Number(aircraft.ground_speed_kt || 0);
  const verticalSpeed = Number(aircraft.vertical_speed_fpm || 0);
  if (aircraft.on_ground) {
    if (projection?.remainingNm < 5) return speed > 35 ? "Atterrissage" : "Roulage arrivée";
    return speed > 45 ? "Décollage" : "Roulage départ";
  }
  if (projection?.activePoint?.stage === "approach" || projection?.remainingNm < 25) {
    return "Approche";
  }
  if (verticalSpeed > 300) return "Montée";
  if (verticalSpeed < -300) return "Descente";
  const cruise = Number(currentPlan?.enroute?.cruise_altitude_ft || 0);
  if (cruise && Math.abs(Number(aircraft.altitude_ft) - cruise) < 1200) return "Croisière";
  return "En route";
}

function descentGuidance(plan, aircraft, projection) {
  if (!aircraft || !projection) return null;
  const currentAltitude = Number(aircraft.altitude_ft || 0);
  const interceptText = plan.arrival?.glide_intercept_altitude;
  const targetAltitude = constraintAltitudeFt(interceptText, currentAltitude) || 3000;
  const finalDistance = Number(plan.arrival?.final_approach_distance_nm || 8);
  const distanceToIntercept = Math.max(0, projection.remainingNm - finalDistance);
  const altitudeToLose = Math.max(0, currentAltitude - targetAltitude);
  const descentDistance = altitudeToLose / 318;
  const todInNm = distanceToIntercept - descentDistance;
  const groundSpeed = Math.max(120, Number(aircraft.ground_speed_kt || 0));
  const requiredVsFpm = -Math.round((groundSpeed * 318) / 60 / 50) * 50;
  const expectedAltitude = Math.min(
    Number(plan.enroute?.cruise_altitude_ft || Infinity),
    targetAltitude + distanceToIntercept * 318
  );
  return {
    targetAltitude,
    todInNm,
    requiredVsFpm,
    expectedAltitude,
    profileDeltaFt: Math.round(currentAltitude - expectedAltitude),
  };
}

function flightLogStorageKey(plan) {
  return [
    "navixav-flight-log",
    plan.departure?.icao || "----",
    plan.arrival?.icao || "----",
    plan.callsign || "flight",
    plan.source?.simbrief_generated_at || "session",
  ].join(":");
}

function loadFlightLog(plan) {
  try {
    const parsed = JSON.parse(localStorage.getItem(flightLogStorageKey(plan)) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function saveFlightLog() {
  if (!currentPlan) return;
  try {
    localStorage.setItem(flightLogStorageKey(currentPlan), JSON.stringify(flightLog));
  } catch (_error) {
    flightLog = flightLog.slice(-Math.floor(FLIGHT_LOG_MAX_POINTS / 2));
  }
}

function recordFlightPoint(aircraft) {
  if (!flightRecording || replayActive || !aircraft) return;
  const now = Date.now();
  if (now - lastFlightLogAt < FLIGHT_LOG_INTERVAL_MS) return;
  lastFlightLogAt = now;
  flightLog.push({
    ...aircraft,
    recorded_at: new Date(now).toISOString(),
  });
  if (flightLog.length > FLIGHT_LOG_MAX_POINTS) flightLog.shift();
  saveFlightLog();
  updateRecorderStatus();
}

function updateRecorderStatus() {
  const status = $("flight-recorder-status");
  if (!status) return;
  const mode = replayActive ? "rejeu" : flightRecording ? "enregistrement actif" : "en pause";
  status.textContent = `${mode} · ${flightLog.length} points`;
  const toggle = $("flight-record-toggle");
  if (toggle) toggle.textContent = flightRecording ? "Mettre en pause" : "Reprendre";
}

function stopFlightReplay() {
  if (replayTimer) clearInterval(replayTimer);
  replayTimer = null;
  replayActive = false;
  updateRecorderStatus();
}

function startFlightReplay() {
  if (flightLog.length < 2) return;
  stopFlightReplay();
  replayActive = true;
  let index = 0;
  replayTimer = setInterval(() => {
    if (index >= flightLog.length) {
      stopFlightReplay();
      return;
    }
    applyAircraftState(flightLog[index], false);
    index += 1;
  }, 300);
  updateRecorderStatus();
}

function liveValue(id, value, status = "") {
  const node = $(id);
  if (!node) return;
  node.textContent = value;
  node.closest(".flight-live-stat")?.setAttribute("data-status", status);
}

function updateFlightPanel(aircraft) {
  const projection = projectAircraftOnFlightPath(aircraft);
  const phase = detectFlightPhase(aircraft, projection);
  const constraint = nextFlightConstraint(currentPlan, projection, aircraft || {});
  const descent = descentGuidance(currentPlan, aircraft, projection);

  liveValue("flight-phase", phase);
  liveValue(
    "flight-next-fix",
    projection?.activePoint?.ident || "—",
    projection ? "good" : ""
  );
  liveValue(
    "flight-next-distance",
    projection ? `${projection.distanceToActiveNm.toFixed(1)} NM` : "—"
  );
  const deviation = projection?.crossTrackNm;
  liveValue(
    "flight-deviation",
    deviation !== undefined ? `${deviation.toFixed(1)} NM` : "—",
    deviation > 5 ? "danger" : deviation > 2 ? "warning" : "good"
  );
  liveValue(
    "flight-remaining",
    projection ? `${projection.remainingNm.toFixed(0)} NM` : "—"
  );
  liveValue(
    "flight-ground-speed",
    aircraft?.ground_speed_kt !== null && aircraft?.ground_speed_kt !== undefined
      ? `${Math.round(aircraft.ground_speed_kt)} kt`
      : "—"
  );
  liveValue(
    "flight-air-speed",
    aircraft?.indicated_airspeed_kt !== null
      && aircraft?.indicated_airspeed_kt !== undefined
      ? `${Math.round(aircraft.indicated_airspeed_kt)} kt`
      : "—"
  );
  liveValue(
    "flight-next-constraint",
    constraint
      ? `${constraint.label} · ${[constraint.altitude, constraint.speed].filter(Boolean).join(" · ")}`
      : "Aucune"
  );
  liveValue(
    "flight-constraint-distance",
    constraint ? `${constraint.distanceNm.toFixed(1)} NM` : "—"
  );

  let requiredVs = null;
  if (constraint?.altitudeFt && constraint.distanceNm > 0.2 && aircraft) {
    const minutes = constraint.distanceNm / Math.max(60, Number(aircraft.ground_speed_kt || 0)) * 60;
    requiredVs = Math.round(
      (constraint.altitudeFt - Number(aircraft.altitude_ft || 0)) / minutes / 50
    ) * 50;
  }
  liveValue(
    "flight-required-vs",
    requiredVs !== null ? `${requiredVs > 0 ? "+" : ""}${requiredVs} ft/min` : "—"
  );

  if (descent) {
    const todText = descent.todInNm > 2
      ? `dans ${descent.todInNm.toFixed(0)} NM`
      : descent.todInNm >= -2
        ? "maintenant"
        : `dépassé de ${Math.abs(descent.todInNm).toFixed(0)} NM`;
    liveValue("flight-tod", todText, descent.todInNm < -2 ? "warning" : "good");
    liveValue("flight-descent-vs", `${descent.requiredVsFpm} ft/min`);
    const verticalSpeed = Number(aircraft?.vertical_speed_fpm || 0);
    const profileActive = (
      phase === "Descente"
      || phase === "Approche"
      || verticalSpeed < -300
      || descent.todInNm <= 2
    );
    if (!profileActive) {
      const waiting = descent.todInNm > 2
        ? `En attente du TOD · ${descent.todInNm.toFixed(0)} NM`
        : "Profil disponible en descente";
      liveValue("flight-vertical-profile", waiting);
    } else {
      const delta = descent.profileDeltaFt;
      // Une marge de 500 ft évite une alerte instable due à l'arrondi du
      // profil 3°, au QNH et aux points de procédure rapprochés.
      liveValue(
        "flight-vertical-profile",
        Math.abs(delta) <= 500
          ? "Profil correct"
          : delta > 0
            ? `Trop haut de ${Math.abs(delta)} ft`
            : `Trop bas de ${Math.abs(delta)} ft`,
        Math.abs(delta) <= 500 ? "good" : Math.abs(delta) <= 1200 ? "warning" : "danger"
      );
    }
  } else {
    for (const id of ["flight-tod", "flight-descent-vs", "flight-vertical-profile"]) {
      liveValue(id, "—");
    }
  }
}

function renderFlightPanel(plan) {
  flightGeometry = buildFlightGeometry(plan);
  flightLog = loadFlightLog(plan);
  lastFlightLogAt = 0;
  stopFlightReplay();
  const panel = $("panel-flight");
  panel.innerHTML = "";
  const header = el("div", "flight-panel-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Guidage et progression"));
  title.append(el("h2", null, "Suivi du vol en temps réel"));
  header.append(title);
  const phase = el("span", "flight-phase-pill", "Hors connexion");
  phase.id = "flight-phase";
  header.append(phase);
  panel.append(header);

  const grid = el("div", "flight-live-grid");
  const item = (label, id, note = "") => {
    const node = el("article", "flight-live-stat");
    node.append(el("div", "stat-label", label));
    const value = el("div", "stat-value", "—");
    value.id = id;
    node.append(value);
    if (note) node.append(el("div", "stat-note", note));
    grid.append(node);
  };
  item("Prochain point", "flight-next-fix");
  item("Distance du point", "flight-next-distance");
  item("Écart latéral", "flight-deviation", "Distance par rapport au segment actif");
  item("Distance restante", "flight-remaining");
  item(t("ground_speed"), "flight-ground-speed", t("ground_speed_note"));
  item(t("air_speed"), "flight-air-speed", t("air_speed_note"));
  item("Prochaine contrainte", "flight-next-constraint");
  item("Distance contrainte", "flight-constraint-distance");
  item("Taux requis", "flight-required-vs", "Pour respecter la prochaine altitude");
  item("Top of Descent", "flight-tod");
  item("Profil vertical", "flight-vertical-profile", "Évalué à partir du TOD");
  item("Descente indicative", "flight-descent-vs", "Base 3° · à confirmer");
  panel.append(grid);

  const recorder = el("section", "flight-recorder");
  const recorderHead = el("div");
  recorderHead.append(el("div", "card-kicker", "Journal local"));
  recorderHead.append(el("h2", null, "Enregistrement et rejeu"));
  const recorderStatus = el("span", "badge");
  recorderStatus.id = "flight-recorder-status";
  const recorderTop = el("div", "flight-recorder-head");
  recorderTop.append(recorderHead, recorderStatus);
  recorder.append(recorderTop);
  const actions = el("div", "flight-recorder-actions");
  const toggle = el("button", "icon-btn");
  toggle.id = "flight-record-toggle";
  toggle.type = "button";
  toggle.addEventListener("click", () => {
    flightRecording = !flightRecording;
    updateRecorderStatus();
  });
  const replay = el("button", "btn-primary", "Rejouer");
  replay.type = "button";
  replay.addEventListener("click", startFlightReplay);
  const stop = el("button", "icon-btn", "Arrêter le rejeu");
  stop.type = "button";
  stop.addEventListener("click", stopFlightReplay);
  const clear = el("button", "icon-btn", "Effacer le journal");
  clear.type = "button";
  clear.addEventListener("click", () => {
    stopFlightReplay();
    flightLog = [];
    saveFlightLog();
    updateRecorderStatus();
  });
  actions.append(toggle, replay, stop, clear);
  recorder.append(actions);
  panel.append(recorder);
  updateRecorderStatus();
  updateFlightPanel(latestAircraft);
}

function choiceRow(label, choice, note) {
  const row = el("div", "row");
  row.append(el("span", "row-label", label));

  const value = el("span", `row-value${choice.value ? "" : " empty"}`, choice.value || "—");
  row.append(value);
  row.append(el("span", `dot ${confidenceClass(choice)}`));

  const reason = [SOURCE_LABEL[choice.source] || choice.source, choice.reason]
    .filter(Boolean)
    .join(" · ");
  const parts = [note, reason].filter(Boolean).join(" — ");
  if (parts) row.append(el("span", "row-reason", parts));
  return row;
}

function terminalCard(block, kicker, extraRows) {
  const card = document.createDocumentFragment();

  const head = el("div", "card-head");
  const left = el("div");
  left.append(el("div", "card-kicker", kicker));
  left.append(el("div", "card-icao", block.icao));
  left.append(el("div", "card-name", block.name || ""));
  head.append(left);

  const right = el("div", "card-weather");
  right.append(
    el("div", "card-wind", windLabel(block.wind)),
    el("div", "card-qnh", qnhLabel(block.wind))
  );
  head.append(right);
  card.append(head);

  if (block.wind?.raw_metar) {
    card.append(el("div", "card-metar", block.wind.raw_metar));
  }

  const rows = el("div", "rows");
  if (block.runway) {
    rows.append(choiceRow("Piste", block.runway, runwayNote(block.runway)));
  }
  for (const [label, choice, note] of extraRows) {
    rows.append(choiceRow(label, choice, note));
  }
  card.append(rows);
  return card;
}

function windLabel(wind) {
  if (!wind) return "";
  if (wind.variable) return `VRB ${wind.speed_kt ?? 0} kt`;
  if (wind.direction_deg === null || wind.direction_deg === undefined) {
    return wind.speed_kt === 0 ? "calme" : "vent inconnu";
  }
  const gust = wind.gust_kt ? `G${wind.gust_kt}` : "";
  return `${String(wind.direction_deg).padStart(3, "0")}°/${wind.speed_kt}${gust} kt`;
}

function qnhLabel(wind) {
  if (wind?.qnh_hpa !== null && wind?.qnh_hpa !== undefined) {
    return `QNH ${Math.round(wind.qnh_hpa)} hPa`;
  }
  return "QNH —";
}

function runwayNote(runway) {
  const bits = [];
  if (runway.headwind_kt !== null && runway.headwind_kt !== undefined) {
    const sign = runway.headwind_kt >= 0 ? "+" : "";
    bits.push(`face ${sign}${Math.round(runway.headwind_kt)} kt`);
  }
  if (runway.crosswind_kt !== null && runway.crosswind_kt !== undefined) {
    bits.push(`trav. ${Math.round(runway.crosswind_kt)} kt`);
  }
  if (runway.length_ft) bits.push(`${Math.round(runway.length_ft).toLocaleString("fr-FR")} ft`);
  if (runway.ils_ident) bits.push(`ILS ${runway.ils_ident}`);
  return bits.join(" · ");
}

function renderTerminal(plan) {
  const departure = $("card-departure");
  departure.innerHTML = "";
  if (plan.departure) {
    departure.append(
      terminalCard(plan.departure, "Départ", [
        ["SID", plan.departure.sid, ""],
        ["Transition", plan.departure.sid_transition, "sortie de la SID"],
      ])
    );
    if (plan.departure.transition_altitude_ft) {
      departure.append(
        el("span", "badge", `Altitude de transition ${plan.departure.transition_altitude_ft} ft`)
      );
    }
  }

  const route = $("card-route");
  route.innerHTML = "";
  route.append(el("div", "card-kicker", "Route"));
  route.append(el("div", "route-text", plan.atc_route || "—"));
  const meta = el("div", "route-meta");
  if (plan.enroute.cruise_altitude_ft) {
    meta.append(el("span", "badge", `FL${Math.round(plan.enroute.cruise_altitude_ft / 100)}`));
  }
  if (plan.aircraft) meta.append(el("span", "badge", plan.aircraft));
  if (plan.callsign) meta.append(el("span", "badge", plan.callsign));
  if (plan.alternate_icao) meta.append(el("span", "badge", `ALTN ${plan.alternate_icao}`));
  if (plan.dispatch?.route_distance_nm) {
    meta.append(el("span", "badge", `${plan.dispatch.route_distance_nm} NM`));
  }
  route.append(meta);

  const arrival = $("card-arrival");
  arrival.innerHTML = "";
  if (plan.arrival) {
    arrival.append(
      terminalCard(plan.arrival, "Arrivée", [
        ["STAR", plan.arrival.star, ""],
        ["Transition", plan.arrival.star_transition, "entrée de STAR — TRANS au MCDU"],
        ["Approche", plan.arrival.approach, ""],
        ["Trans. app.", plan.arrival.approach_transition, "transition d'approche — VIA au MCDU"],
      ])
    );
    const badges = el("div", "route-meta");
    if (plan.arrival.ils_frequency_mhz) {
      badges.append(el("span", "badge", `ILS ${plan.arrival.ils_frequency_mhz.toFixed(2)} MHz`));
    }
    if (plan.arrival.missed_approach_altitude_ft) {
      badges.append(el("span", "badge", `Remise de gaz ${plan.arrival.missed_approach_altitude_ft} ft`));
    }
    if (plan.arrival.transition_level_ft) {
      badges.append(el("span", "badge", `Niveau de transition ${plan.arrival.transition_level_ft} ft`));
    }
    if (badges.childElementCount) arrival.append(badges);
  }
}

/* ----------------------------------------------------------- constraints */

function constraintTable(title, rows) {
  const wrapper = el("div");
  wrapper.append(el("div", "section-title", title));
  if (!rows?.length) {
    wrapper.append(el("p", "stat-note", "Aucune contrainte publiée."));
    return wrapper;
  }
  const table = el("table");
  const head = el("thead");
  const headRow = el("tr");
  for (const label of ["Repère", "Altitude", "Vitesse"]) headRow.append(el("th", null, label));
  head.append(headRow);
  table.append(head);

  const body = el("tbody");
  for (const row of rows) {
    const line = el("tr");
    line.append(el("td", `fix${row.is_fix ? "" : " segment"}`, row.label));
    line.append(el("td", "constraint", row.altitude || "—"));
    line.append(el("td", "constraint", row.speed || "—"));
    body.append(line);
  }
  table.append(body);
  wrapper.append(table);
  return wrapper;
}

function altitudeInstruction(altitude) {
  if (!altitude) return "";
  if (altitude.startsWith("≥ ")) {
    return `Ne pas descendre sous ${altitude.slice(2)}`;
  }
  if (altitude.startsWith("≤ ")) {
    return `Être à ou sous ${altitude.slice(2)}`;
  }
  if (altitude.startsWith("entre ")) {
    return `Rester ${altitude}`;
  }
  return `Maintenir ${altitude}`;
}

function approachProfile(arrival) {
  const wrapper = el("div", "approach-profile");
  const head = el("div", "approach-profile-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Profil vertical"));
  title.append(el(
    "h2",
    null,
    `${arrival.approach?.value || "Approche"}${arrival.runway?.value ? ` · RWY ${arrival.runway.value}` : ""}`
  ));
  head.append(title);
  if (arrival.ils_frequency_mhz) {
    head.append(el("span", "badge", `ILS ${arrival.ils_frequency_mhz.toFixed(2)} MHz`));
  }
  wrapper.append(head);

  if (arrival.ils_ident || arrival.glide_intercept_altitude) {
    const briefing = el("div", "final-briefing");
    const items = [
      ["ILS", [
        arrival.ils_ident,
        arrival.ils_frequency_mhz ? `${arrival.ils_frequency_mhz.toFixed(2)} MHz` : null,
      ].filter(Boolean).join(" · ")],
      ["Axe LOC", arrival.ils_course_deg !== null && arrival.ils_course_deg !== undefined
        ? `${String(Math.round(arrival.ils_course_deg)).padStart(3, "0")}°`
        : null],
      ["Pente", arrival.glide_slope_deg
        ? `${Number(arrival.glide_slope_deg).toFixed(2)}°`
        : null],
      ["Interception", arrival.glide_intercept_altitude],
      ["Point", arrival.glide_intercept_fix],
      ["Finale", arrival.final_approach_distance_nm
        ? `${arrival.final_approach_distance_nm.toFixed(1)} NM`
        : null],
    ];
    for (const [label, value] of items) {
      if (!value) continue;
      const item = el("div", label === "Interception" ? "final-item primary" : "final-item");
      item.append(el("span", null, label));
      item.append(el("strong", null, value));
      briefing.append(item);
    }
    wrapper.append(briefing);

    if (arrival.glide_intercept_altitude) {
      wrapper.append(el(
        "p",
        "intercept-explanation",
        `${altitudeInstruction(arrival.glide_intercept_altitude)} à ${arrival.glide_intercept_fix || "l’interception"} pour établir la finale publiée.`
      ));
    }
  }

  const rows = (arrival.approach_constraints || []).filter((row) => row.altitude);
  if (rows.length) {
    const flow = el("div", "altitude-flow");
    rows.forEach((row, index) => {
      if (index) flow.append(el("span", "altitude-arrow", "→"));
      const step = el("div", "altitude-step");
      step.append(el("span", "altitude-fix", row.label));
      step.append(el("strong", null, row.altitude));
      step.append(el("small", null, altitudeInstruction(row.altitude)));
      if (row.speed) step.append(el("small", "altitude-speed", row.speed));
      flow.append(step);
    });
    wrapper.append(flow);
  } else {
    wrapper.append(el(
      "p",
      "stat-note",
      "Aucune contrainte d’altitude publiée dans la base pour cette approche."
    ));
  }

  if (arrival.missed_approach_altitude_ft) {
    const missed = el("div", "missed-altitude");
    missed.append(el("span", null, "En remise de gaz, monter vers"));
    missed.append(el("strong", null, `${arrival.missed_approach_altitude_ft} ft`));
    wrapper.append(missed);
  }
  wrapper.append(el(
    "p",
    "approach-caution",
    "Les minima officiels sont recherchés dans la fiche MCDU. Toujours confirmer la carte SIA, la catégorie avion et les conditions applicables."
  ));
  return wrapper;
}

function renderConstraints(plan) {
  const panel = $("panel-constraints");
  panel.innerHTML = "";
  if (plan.arrival) panel.append(approachProfile(plan.arrival));
  if (plan.departure) {
    panel.append(
      constraintTable(
        `SID ${plan.departure.sid.value || ""}`.trim(),
        plan.departure.sid_constraints
      )
    );
  }
  if (plan.arrival) {
    panel.append(
      constraintTable(`STAR ${plan.arrival.star.value || ""}`.trim(), plan.arrival.star_constraints)
    );
    panel.append(
      constraintTable(
        `Approche ${plan.arrival.approach.value || ""}`.trim(),
        plan.arrival.approach_constraints
      )
    );
  }
}

/* -------------------------------------------------------------- dispatch */

function stat(label, value, note, fill) {
  if (value === null || value === undefined || value === "") return null;
  const node = el("div", "stat");
  node.append(el("div", "stat-label", label));
  node.append(el("div", "stat-value", value));
  if (note) node.append(el("div", "stat-note", note));
  if (fill !== undefined && fill !== null) {
    const meter = el("div", `meter${fill > 1 ? " over" : ""}`);
    const bar = el("span");
    bar.style.width = `${Math.min(100, Math.round(fill * 100))}%`;
    meter.append(bar);
    node.append(meter);
  }
  return node;
}

function kg(value, unit) {
  if (value === null || value === undefined) return null;
  return `${value.toLocaleString("fr-FR")} ${unit}`;
}

function hhmm(seconds) {
  if (!seconds) return null;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return hours ? `${hours} h ${String(minutes).padStart(2, "0")}` : `${minutes} min`;
}

function group(title, nodes) {
  const present = nodes.filter(Boolean);
  if (!present.length) return null;
  const wrapper = el("div");
  wrapper.append(el("div", "section-title", title));
  const grid = el("div", "stat-grid");
  for (const node of present) grid.append(node);
  wrapper.append(grid);
  return wrapper;
}

function renderDispatch(plan) {
  const panel = $("panel-dispatch");
  panel.innerHTML = "";
  const d = plan.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb", kgs: "kg", lbs: "lb" }[d.units] || d.units || "";

  if (!Object.keys(d).length) {
    panel.append(el("p", "stat-note", "Aucune donnée de dispatch dans cet OFP."));
    return;
  }

  const ratioOf = (value, max) => (value && max ? value / max : null);

  const blocks = [
    group("Masses", [
      stat("Passagers", d.passengers, d.bags ? `${d.bags} bagages` : null),
      stat("Charge marchande", kg(d.payload, unit), d.cargo ? `dont ${kg(d.cargo, unit)} de fret` : null),
      stat("ZFW", kg(d.zfw, unit), d.max_zfw ? `max ${kg(d.max_zfw, unit)}` : null, ratioOf(d.zfw, d.max_zfw)),
      stat("Décollage", kg(d.takeoff_weight, unit), d.max_takeoff_weight ? `max ${kg(d.max_takeoff_weight, unit)}` : null, ratioOf(d.takeoff_weight, d.max_takeoff_weight)),
      stat("Atterrissage", kg(d.landing_weight, unit), d.max_landing_weight ? `max ${kg(d.max_landing_weight, unit)}` : null, ratioOf(d.landing_weight, d.max_landing_weight)),
    ]),
    group("Carburant", [
      stat("Bloc", kg(d.block_fuel, unit), d.max_tanks ? `capacité ${kg(d.max_tanks, unit)}` : null, ratioOf(d.block_fuel, d.max_tanks)),
      stat("Étape", kg(d.trip_fuel, unit)),
      stat("Roulage", kg(d.taxi_fuel, unit)),
      stat("Imprévus", kg(d.contingency_fuel, unit)),
      stat("Dégagement", kg(d.alternate_fuel, unit)),
      stat("Réserve finale", kg(d.reserve_fuel, unit)),
      stat("Restant à l'arrivée", kg(d.landing_fuel, unit)),
      stat("Conso horaire", kg(d.average_fuel_flow, `${unit}/h`)),
    ]),
    group("Profil", [
      stat("Cost index", d.cost_index),
      stat("Croisière", d.cruise_profile),
      stat(
        "Vent moyen",
        d.average_wind_direction && d.average_wind_speed
          ? `${d.average_wind_direction}°/${d.average_wind_speed} kt`
          : null,
        d.average_wind_component ? `composante ${d.average_wind_component} kt` : null
      ),
      stat("Écart ISA", d.average_temperature_dev ? `${d.average_temperature_dev} °C` : null),
      stat("Tropopause", d.tropopause_ft ? `FL${Math.round(d.tropopause_ft / 100)}` : null),
    ]),
    group("Distances et temps", [
      stat("Distance route", d.route_distance_nm ? `${d.route_distance_nm} NM` : null),
      stat("Distance air", d.air_distance_nm ? `${d.air_distance_nm} NM` : null),
      stat("Orthodromie", d.great_circle_distance_nm ? `${d.great_circle_distance_nm} NM` : null),
      stat("Temps de vol", hhmm(d.time_enroute_s)),
      stat("Temps bloc", hhmm(d.block_time_s)),
    ]),
    group("Dégagement", [
      stat("Terrain", plan.alternate_icao),
      stat("Distance", d.alternate_distance_nm ? `${d.alternate_distance_nm} NM` : null),
      stat("Temps", hhmm(d.alternate_time_s)),
      stat("Carburant", kg(d.alternate_burn, unit)),
      stat("Niveau", d.alternate_altitude_ft ? `FL${Math.round(d.alternate_altitude_ft / 100)}` : null),
    ]),
    group("Avion", [
      stat("Immatriculation", d.registration),
      stat("SELCAL", d.selcal),
      stat("Équipement", d.equipment),
    ]),
  ].filter(Boolean);

  for (const block of blocks) panel.append(block);

  if (d.alternate_metar) {
    const wrapper = el("div");
    wrapper.append(el("div", "section-title", "METAR dégagement"));
    wrapper.append(el("div", "card-metar", d.alternate_metar));
    panel.append(wrapper);
  }
  if (d.atc_flightplan_text) {
    const wrapper = el("div");
    wrapper.append(el("div", "section-title", "Plan de vol OACI"));
    wrapper.append(el("pre", null, d.atc_flightplan_text));
    panel.append(wrapper);
  }
}

/* --------------------------------------------------------------- aircraft */

function renderAircraft(plan) {
  const panel = $("panel-aircraft");
  panel.innerHTML = "";
  const d = plan.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb", kgs: "kg", lbs: "lb" }[d.units] || d.units || "";

  const identity = el("div", "aircraft-identity");
  const mark = el("div", "aircraft-mark", plan.aircraft || "—");
  const title = el("div");
  title.append(el("div", "card-kicker", "Appareil utilisé"));
  title.append(el("h2", null, plan.aircraft_name || plan.aircraft || "Type inconnu"));
  const badges = el("div", "route-meta");
  if (plan.callsign) badges.append(el("span", "badge", `Vol ${plan.callsign}`));
  if (d.registration) badges.append(el("span", "badge", d.registration));
  title.append(badges);
  identity.append(mark, title);
  panel.append(identity);

  const blocks = [
    group("Identification", [
      stat("Type OACI", plan.aircraft),
      stat("Modèle", plan.aircraft_name),
      stat("Immatriculation", d.registration),
      stat("Indicatif", plan.callsign),
      stat("SELCAL", d.selcal),
    ]),
    group("Équipement de bord", [
      stat("Équipement OACI", d.equipment, "codes déclarés dans le plan de vol SimBrief"),
      stat("Profil de montée", d.climb_profile),
      stat("Profil de croisière", d.cruise_profile),
      stat("Profil de descente", d.descent_profile),
      stat("Cost index", d.cost_index),
    ]),
    group("Masses et capacité", [
      stat("Masse à vide", kg(d.oew, unit)),
      stat("MZFW", kg(d.max_zfw, unit)),
      stat("MTOW", kg(d.max_takeoff_weight, unit)),
      stat("MLW", kg(d.max_landing_weight, unit)),
      stat("Capacité carburant", kg(d.max_tanks, unit)),
      stat("Passagers prévus", d.passengers),
    ]),
  ].filter(Boolean);

  for (const block of blocks) panel.append(block);
}

/* ------------------------------------------------------------------ mcdu */

function mcduLine(label, value, note, warn) {
  const line = el("div", "mcdu-line");
  line.append(el("span", "mcdu-label", label));
  const right = el("span");
  right.append(el("span", warn ? "mcdu-warn" : "mcdu-value", value + (warn ? "  ⚠" : "")));
  if (note) right.append(el("span", "mcdu-note", `   ${note}`));
  line.append(right);
  return line;
}

function mcduPage(title, lines) {
  const present = lines.filter(Boolean);
  if (!present.length) return null;
  const page = document.createDocumentFragment();
  page.append(el("div", "mcdu-title", title));
  for (const line of present) page.append(line);
  page.append(el("div", null, " "));
  return page;
}

function minimaStorageKey(plan) {
  const arrival = plan.arrival || {};
  return [
    "navixav-minima",
    arrival.icao || "",
    arrival.runway?.value || "",
    arrival.approach?.value || "",
  ].join(":");
}

function loadMinima(plan) {
  try {
    return JSON.parse(localStorage.getItem(minimaStorageKey(plan)) || "{}");
  } catch (_error) {
    return {};
  }
}

function siaRequestKey(plan) {
  const arrival = plan.arrival || {};
  return [
    arrival.icao || "",
    arrival.runway?.value || "",
    arrival.approach?.value || "",
  ].join(":");
}

function fetchSiaApproach(plan) {
  const key = siaRequestKey(plan);
  if (siaRequests.has(key)) return siaRequests.get(key);
  const arrival = plan.arrival || {};
  const params = new URLSearchParams({
    icao: arrival.icao || "",
    runway: arrival.runway?.value || "",
    approach: arrival.approach?.value || "",
  });
  const request = fetch(`/api/charts/approach?${params}`).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Carte officielle indisponible.");
    return payload;
  });
  siaRequests.set(key, request);
  request.catch(() => siaRequests.delete(key));
  return request;
}

function clearSiaMapOverlay(key) {
  if (key && siaOverlayKey === key) return;
  siaOverlayKey = null;
  $("map-sia").classList.add("hidden");
  $("map-sia").classList.remove("active");
  $("map-sia").setAttribute("aria-pressed", "false");
  $("sia-map-overlay").classList.add("hidden");
  $("sia-map-frame").removeAttribute("src");
}

function officialProviderName(data) {
  if (data?.provider === "sia") return "SIA";
  if (data?.provider === "faa") return "FAA";
  if (data?.provider === "enaire") return "ENAIRE";
  if (data?.provider === "lvnl") return "LVNL";
  return String(data?.provider || "AIS").toUpperCase();
}

function syncSiaMapOverlay() {
  const candidate = siaOverlayCandidates.get(currentMapRole);
  if (!candidate?.chart?.georeferenced) {
    clearSiaMapOverlay();
    return;
  }
  const key = `${currentMapRole}:${currentIcao}:${candidate.chart.filename}`;
  if (siaOverlayKey !== key) {
    toggleSiaMapOverlay(false);
    siaOverlayKey = key;
    $("sia-map-frame").src = candidate.pdf_url;
  }
  const provider = officialProviderName(candidate);
  $("map-sia").textContent = `Calque ${provider}`;
  $("map-sia").title = `Afficher la carte ${provider} géoréférencée de cet aérodrome`;
  $("sia-overlay-title").textContent = `Calque ${provider}`;
  $("map-sia").classList.remove("hidden");
}

function setSiaMapCandidate(role, icao, data) {
  const key = String(role || "").toLowerCase();
  const airport = String(icao || "").toUpperCase();
  if (!key || !airport) return;
  if (data?.chart?.georeferenced) siaOverlayCandidates.set(key, data);
  else siaOverlayCandidates.delete(key);
  if (currentMapRole === key && currentIcao === airport) syncSiaMapOverlay();
}

function toggleSiaMapOverlay(forceVisible) {
  if (!siaOverlayKey) return;
  const overlay = $("sia-map-overlay");
  const visible = forceVisible ?? overlay.classList.contains("hidden");
  overlay.classList.toggle("hidden", !visible);
  $("map-sia").classList.toggle("active", visible);
  $("map-sia").setAttribute("aria-pressed", String(visible));
}

function siaApproachCard(plan) {
  const wrapper = el("section", "sia-card");
  const head = el("div", "sia-card-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Source officielle"));
  title.append(el("h2", null, "Carte d’approche officielle"));
  head.append(title);
  const status = el("span", "badge", "Recherche…");
  head.append(status);
  wrapper.append(head);
  const content = el("div", "sia-card-content");
  content.append(el("p", "stat-note", "Recherche de la carte correspondant à l’approche sélectionnée."));
  wrapper.append(content);

  const arrival = plan.arrival;
  if (!arrival?.icao || !arrival?.runway?.value || !arrival?.approach?.value) {
    status.textContent = "Plan incomplet";
    content.innerHTML = "";
    content.append(el("p", "stat-note", "Aucune approche d’arrivée ne permet de rechercher une carte."));
    return wrapper;
  }

  fetchSiaApproach(plan).then((data) => {
    if (currentPlan !== plan) return;
    setSiaMapCandidate("arrival", arrival.icao, data);
    status.textContent = `${officialProviderName(data)} · AIRAC ${data.chart.effective_date}`;
    content.innerHTML = "";
    content.append(el("p", "sia-chart-title", data.chart.title.replaceAll("_", " ")));

    if (data.minima) {
      const values = el("div", "sia-minima-values");
      values.append(
        stat("Catégorie", data.minima.category),
        stat("RADIO / DH", `${data.minima.dh_ft} ft`),
        stat("BARO / DA", `${data.minima.altitude_ft} ft`),
        stat("RVR", `${data.minima.rvr_m} m`)
      );
      content.append(values);

      const use = el("button", "btn-primary", "Valider ces valeurs pour le MCDU");
      use.type = "button";
      use.addEventListener("click", () => {
        localStorage.setItem(minimaStorageKey(plan), JSON.stringify({
          ...data.minima,
          source: data.source,
          chart_title: data.chart.title,
          effective_date: data.chart.effective_date,
        }));
        renderMcdu(plan);
      });
      content.append(use);
    } else {
      content.append(el(
        "p",
        "approach-caution",
        "La carte officielle a été trouvée, mais ses minima n’ont pas pu être extraits avec une confiance suffisante. Les saisir après lecture de la carte."
      ));
    }

    const details = el("details", "sia-chart-preview");
    details.append(el("summary", null, "Afficher la carte officielle"));
    const frame = el("iframe");
    frame.src = data.pdf_url;
    frame.title = `Carte ${officialProviderName(data)} ${data.chart.title}`;
    frame.loading = "lazy";
    details.append(frame);
    content.append(details);
    content.append(el(
      "p",
      "approach-caution",
      "Extraction automatique à confirmer : vérifier la variante d’approche, la catégorie avion, les NOTAM et les consignes ATC."
    ));
  }).catch((error) => {
    status.textContent = "Indisponible";
    content.innerHTML = "";
    content.append(el("p", "stat-note", String(error.message || error)));
  });
  return wrapper;
}

function fetchOfficialAirport(icao) {
  const key = String(icao || "").toUpperCase();
  if (officialAirportRequests.has(key)) return officialAirportRequests.get(key);
  const request = fetch(`/api/charts/airport/${encodeURIComponent(key)}`).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Catalogue officiel indisponible.");
    return payload;
  });
  officialAirportRequests.set(key, request);
  request.catch(() => officialAirportRequests.delete(key));
  return request;
}

function normaliseChartText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "");
}

function preferredOfficialChartIndex(charts, role, airport) {
  const runway = normaliseChartText(airport?.runway?.value);
  const sid = normaliseChartText(airport?.sid?.value);
  const star = normaliseChartText(airport?.star?.value);
  const approach = String(airport?.approach?.value || "").toUpperCase();
  const approachType = ["ILS", "RNP", "RNAV", "LOC", "VOR", "NDB"]
    .find((kind) => approach.includes(kind));
  const approachVariant = approach.match(/\b(?:ILS|RNP|RNAV|LOC|VOR|NDB)\s+([XYZ])\b/)?.[1];

  const scores = charts.map((chart) => {
    const title = normaliseChartText(
      `${chart.title} ${chart.filename} ${chart.procedure_ident || ""}`
    );
    let score = 0;
    if (role === "Départ") {
      if (chart.category === "Départs SID") score += 120;
      if (chart.category === "Aérodrome et roulage") score += 30;
      if (sid && title.includes(sid)) score += 220;
    } else {
      if (chart.category === "Approches IAC") score += 150;
      if (chart.category === "Arrivées STAR") score += 70;
      if (chart.category === "Aérodrome et roulage") score += 20;
      if (star && title.includes(star)) score += 120;
      if (approachType && title.includes(approachType)) score += 90;
      if (approachVariant && title.includes(`${approachType}${approachVariant}`)) score += 45;
    }
    if (runway && (
      title.includes(`RWY${runway}`)
      || title.includes(`R${runway}`)
      || title.includes(`I${runway}`)
    )) score += 100;
    return score;
  });
  return scores.reduce(
    (best, score, index) => score > scores[best] ? index : best,
    0
  );
}

function officialAirportLibrary(icao, role, mapRole, airport, plan) {
  const card = el("article", "sia-airport-library");
  const head = el("div", "sia-library-head");
  const heading = el("div");
  heading.append(el("div", "card-kicker", role), el("h2", null, icao));
  const status = el("span", "badge", "Chargement…");
  head.append(heading, status);
  card.append(head, el("p", "stat-note", "Recherche des publications officielles en vigueur."));

  fetchOfficialAirport(icao).then((data) => {
    if (currentPlan !== plan) return;
    card.replaceChildren(head);
    status.textContent = `${officialProviderName(data)} · AIRAC ${data.effective_date}`;
    if (!data.charts.length) {
      card.append(el("p", "stat-note", "Aucun document publié pour cet aérodrome."));
      return;
    }

    const controls = el("div", "sia-document-controls");
    const field = el("label", "field");
    field.append(el("span", null, "Document"));
    const select = el("select");
    const groups = new Map();
    data.charts.forEach((chart, index) => {
      if (!groups.has(chart.category)) {
        const group = document.createElement("optgroup");
        group.label = chart.category;
        groups.set(chart.category, group);
        select.append(group);
      }
      const option = el("option", null, chart.title.replaceAll("_", " "));
      option.value = String(index);
      groups.get(chart.category).append(option);
    });
    select.value = String(preferredOfficialChartIndex(data.charts, role, airport));
    field.append(select);

    const actions = el("div", "sia-document-actions");
    const display = el("button", "btn-primary", "Afficher le PDF");
    display.type = "button";
    const external = el("a", "icon-btn", "Ouvrir dans un nouvel onglet");
    external.target = "_blank";
    external.rel = "noopener";
    actions.append(display, external);
    controls.append(field, actions);

    const availability = el("p", "stat-note");
    const frame = el("iframe", "sia-document-frame hidden");
    frame.loading = "lazy";

    const updateSelection = () => {
      const chart = data.charts[Number(select.value)];
      external.href = chart.pdf_url;
      setSiaMapCandidate(mapRole, icao, {
        provider: data.provider,
        source: data.source,
        chart,
        pdf_url: chart.pdf_url,
      });
      availability.textContent = chart.georeferenced
        ? `Calque disponible lorsque la carte affiche ${role.toLowerCase()} ${icao}.`
        : `PDF ${officialProviderName(data)} consultable. Aucun calque proposé : ce document n’a pas de géoréférencement validé.`;
      if (!frame.classList.contains("hidden")) {
        frame.src = chart.pdf_url;
        frame.title = `Carte ${officialProviderName(data)} ${chart.title}`;
      }
    };
    select.addEventListener("change", updateSelection);
    display.addEventListener("click", () => {
      const chart = data.charts[Number(select.value)];
      frame.src = chart.pdf_url;
      frame.title = `Carte ${officialProviderName(data)} ${chart.title}`;
      frame.classList.remove("hidden");
    });
    card.append(controls, availability, frame);
    updateSelection();
  }).catch((error) => {
    status.textContent = "Indisponible";
    card.append(el("p", "stat-note", String(error.message || error)));
  });
  return card;
}

function renderOfficialCharts(plan) {
  const panel = $("panel-sia");
  panel.innerHTML = "";
  const intro = el("div", "section-head");
  const title = el("div");
  title.append(
    el("div", "card-kicker", "Sources AIS nationales officielles · FAA d-TPP"),
    el("h2", null, "Cartes des aérodromes du vol")
  );
  intro.append(title);
  panel.append(
    intro,
    el("p", "stat-note", "Le document proposé par défaut correspond au plan courant. Vous pouvez ensuite choisir un autre PDF du départ ou de l’arrivée. Le calque n’apparaît que pour un document géoréférencé et pour l’aérodrome actuellement affiché.")
  );
  const grid = el("div", "sia-library-grid");
  for (const [role, mapRole, airport] of [
    ["Départ", "departure", plan.departure],
    ["Arrivée", "arrival", plan.arrival],
  ]) {
    const icao = airport?.icao;
    if (!icao) continue;
    grid.append(officialAirportLibrary(icao, role, mapRole, airport, plan));
  }
  if (!grid.childElementCount) {
    grid.append(el("p", "stat-note", "Chargez un plan contenant un départ et une arrivée."));
  }
  panel.append(grid);
}

function minimaEditor(plan, minima) {
  const wrapper = el("form", "minima-editor");
  const header = el("div", "minima-editor-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Minima de la carte"));
  title.append(el("h2", null, "Valeurs à saisir dans le MCDU"));
  header.append(title);
  if (minima.source) header.append(el("span", "badge", "SIA confirmé"));
  wrapper.append(header);

  const fields = el("div", "minima-fields");
  const field = (label, id, type = "number", placeholder = "") => {
    const node = el("label", "field");
    node.append(el("span", null, label));
    const input = el("input");
    input.id = id;
    input.type = type;
    input.placeholder = placeholder;
    if (type === "number") input.min = "0";
    node.append(input);
    fields.append(node);
    return input;
  };

  const category = field("Catégorie", "minima-category", "text", "CAT I, CAT III, LOC…");
  const modeLabel = el("label", "field");
  modeLabel.append(el("span", null, "Champ MCDU"));
  const mode = el("select");
  mode.id = "minima-mode";
  for (const [value, label] of [["RADIO", "RADIO (DH)"], ["BARO", "BARO (DA/MDA)"]]) {
    const option = el("option", null, label);
    option.value = value;
    mode.append(option);
  }
  modeLabel.append(mode);
  fields.append(modeLabel);
  const dh = field("DH / hauteur radio (ft)", "minima-dh", "number", "ex. 100");
  const altitude = field("DA ou MDA barométrique (ft)", "minima-altitude", "number", "ex. 588");
  const rvr = field("RVR / visibilité (m)", "minima-rvr", "number", "ex. 300");

  category.value = minima.category || "";
  mode.value = minima.mode || (plan.arrival?.approach?.value?.includes("ILS") ? "RADIO" : "BARO");
  dh.value = minima.dh_ft || "";
  altitude.value = minima.altitude_ft || "";
  rvr.value = minima.rvr_m || "";
  wrapper.append(fields);

  const actions = el("div", "minima-actions");
  actions.append(el(
    "p",
    "approach-caution",
    "Recopier les valeurs de la carte correspondant à la catégorie avion et à l’équipement disponible."
  ));
  const save = el("button", "btn-primary", "Mémoriser ces minima");
  save.type = "submit";
  actions.append(save);
  wrapper.append(actions);

  wrapper.addEventListener("submit", (event) => {
    event.preventDefault();
    localStorage.setItem(minimaStorageKey(plan), JSON.stringify({
      category: category.value.trim(),
      mode: mode.value,
      dh_ft: Number(dh.value) || null,
      altitude_ft: Number(altitude.value) || null,
      rvr_m: Number(rvr.value) || null,
    }));
    renderMcdu(plan);
  });
  return wrapper;
}

function renderMcdu(plan) {
  const panel = $("panel-mcdu");
  panel.innerHTML = "";
  const minima = loadMinima(plan);
  panel.append(siaApproachCard(plan));
  panel.append(minimaEditor(plan, minima));
  const screen = el("div", "mcdu");
  const d = plan.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb" }[d.units] || d.units || "";
  const dep = plan.departure;
  const arr = plan.arrival;

  const pages = [
    mcduPage("INIT A", [
      mcduLine("FROM/TO", `${dep?.icao || "----"}/${arr?.icao || "----"}`),
      plan.alternate_icao && mcduLine("ALTN", plan.alternate_icao),
      plan.callsign && mcduLine("FLT NBR", plan.callsign),
      d.cost_index && mcduLine("COST INDEX", d.cost_index),
      plan.enroute.cruise_altitude_ft &&
        mcduLine("CRZ FL", `FL${Math.round(plan.enroute.cruise_altitude_ft / 100)}`),
    ]),
    mcduPage("INIT B", [
      d.zfw && mcduLine("ZFW", kg(d.zfw, unit)),
      d.block_fuel && mcduLine("BLOCK", kg(d.block_fuel, unit)),
      d.taxi_fuel && mcduLine("TAXI", kg(d.taxi_fuel, unit)),
      d.trip_fuel && mcduLine("TRIP", kg(d.trip_fuel, unit)),
      d.reserve_fuel && mcduLine("RSV", kg(d.reserve_fuel, unit)),
      d.alternate_fuel && mcduLine("ALTN", kg(d.alternate_fuel, unit)),
    ]),
    dep &&
      mcduPage("F-PLN › DEPARTURE", [
        dep.runway && mcduLine("RWY", dep.runway.value || "—", null, needsCheck(dep.runway)),
        mcduLine("SID", dep.sid.value || "—", null, needsCheck(dep.sid)),
        mcduLine("TRANS", dep.sid_transition.value || "—", "sortie de la SID", needsCheck(dep.sid_transition)),
        dep.transition_altitude_ft && mcduLine("TRANS ALT", String(dep.transition_altitude_ft)),
      ]),
    plan.enroute.route_legs?.length &&
      mcduPage("F-PLN › EN ROUTE · VIA / TO", [
        ...plan.enroute.route_legs.map((leg) =>
          mcduLine(leg.via || "DCT", leg.to, leg.stage || null)
        ),
      ]),
    arr &&
      mcduPage("F-PLN › ARRIVAL", [
        arr.runway && mcduLine("RWY", arr.runway.value || "—", null, needsCheck(arr.runway)),
        mcduLine("APPR", arr.approach.value || "—", null, needsCheck(arr.approach)),
        mcduLine("VIA", arr.approach_transition.value || "—", "transition d'APPROCHE", needsCheck(arr.approach_transition)),
        mcduLine("STAR", arr.star.value || "—", null, needsCheck(arr.star)),
        mcduLine("TRANS", arr.star_transition.value || "—", "entrée de STAR", needsCheck(arr.star_transition)),
        arr.transition_level_ft && mcduLine("TRANS LVL", String(arr.transition_level_ft)),
        arr.missed_approach_altitude_ft &&
          mcduLine("GA ALT", `${arr.missed_approach_altitude_ft} ft`, "remise de gaz"),
      ]),
    arr?.ils_frequency_mhz &&
      mcduPage("RAD NAV", [
        mcduLine("ILS", `${arr.ils_frequency_mhz.toFixed(2)} / ${arr.ils_ident || ""}`),
        arr.ils_course_deg !== null && arr.ils_course_deg !== undefined &&
          mcduLine("CRS", `${String(Math.round(arr.ils_course_deg)).padStart(3, "0")}°`),
      ]),
    arr &&
      mcduPage("PERF APPR", [
        arr.wind && mcduLine("WIND", windLabel(arr.wind)),
        arr.wind?.qnh_hpa && mcduLine("QNH", `${Math.round(arr.wind.qnh_hpa)} hPa`),
        minima.category && mcduLine("CAT", minima.category),
        minima.mode === "RADIO" && minima.dh_ft &&
          mcduLine("RADIO", `${minima.dh_ft} ft`, "DH carte"),
        minima.mode === "BARO" && minima.altitude_ft &&
          mcduLine("BARO", `${minima.altitude_ft} ft`, "DA/MDA carte"),
        minima.rvr_m && mcduLine("RVR", `${minima.rvr_m} m`),
        arr.missed_approach_altitude_ft &&
          mcduLine("GA ALT", `${arr.missed_approach_altitude_ft} ft`),
      ]),
  ].filter(Boolean);

  for (const page of pages) screen.append(page);

  const toConfirm = [];
  const check = (label, choice) => { if (needsCheck(choice)) toConfirm.push(label); };
  if (dep) {
    check("piste départ", dep.runway);
    check("SID", dep.sid);
    check("TRANS départ", dep.sid_transition);
  }
  if (arr) {
    check("piste arrivée", arr.runway);
    check("APPR", arr.approach);
    check("VIA", arr.approach_transition);
    check("STAR", arr.star);
    check("TRANS arrivée", arr.star_transition);
  }
  if (toConfirm.length) {
    screen.append(el("div", "mcdu-warn", `À confirmer à l'ATIS : ${toConfirm.join(", ")}`));
  }

  panel.append(screen);
}

/* ------------------------------------------------------------------ carte */

function renderMapBar(plan) {
  const bar = $("map-airports");
  bar.innerHTML = "";

  const entries = [];
  if (plan.departure) {
    entries.push({
      icao: plan.departure.icao,
      runway: plan.departure.runway?.value || null,
      role: "départ",
      mapRole: "departure",
    });
  }
  if (plan.arrival) {
    entries.push({
      icao: plan.arrival.icao,
      runway: plan.arrival.runway?.value || null,
      role: "arrivée",
      mapRole: "arrival",
    });
  }

  for (const entry of entries) {
    const button = el("button", "airport-btn");
    button.dataset.mapRole = entry.mapRole;
    button.textContent = entry.icao;
    button.append(el("small", null, entry.runway ? `${entry.role} · ${entry.runway}` : entry.role));
    button.addEventListener("click", () => loadChart(entry.icao, entry.runway, entry.mapRole));
    bar.append(button);
  }

  if (entries.length) loadChart(entries[0].icao, entries[0].runway, entries[0].mapRole);
}

async function loadChart(icao, runway, mapRole) {
  for (const button of document.querySelectorAll(".airport-btn")) {
    button.classList.toggle(
      "active",
      button.textContent.startsWith(icao) && button.dataset.mapRole === mapRole
    );
  }

  const params = new URLSearchParams();
  if (runway) params.set("runway", runway);

  try {
    const response = await fetch(`/api/chart/${icao}?${params}`);
    if (!response.ok) {
      const payload = await response.json();
      showBanner("error", `Plan de ${icao} indisponible`, [payload.detail]);
      return;
    }
    currentChart = await response.json();
    currentIcao = icao;
    currentMapRole = mapRole;
    syncSiaMapOverlay();
    MAP.setChart(currentChart);
    const routeSegments = flightStagePaths(currentPlan).map((segment) => ({
      stage: segment.stage,
      points: segment.points.map((point) => {
        const projected = projectToChart(point.lat, point.lon);
        return { ...projected, ident: point.ident, via: point.via };
      }),
    }));
    MAP.setRouteSegments(routeSegments);
    MAP.resize();
    updateHud(null);

    if (currentChart.geometry_source) {
      showBanner("warn", "Géométrie du terrain empruntée", [
        `La base sélectionnée ne contient pas le tracé du sol ; le plan provient de « ${currentChart.geometry_source} ». Les procédures, elles, restent celles de la base choisie.`,
      ]);
    }
  } catch (error) {
    showBanner("error", "Erreur réseau", [String(error)]);
  }
}

/** Projette une position géographique dans le repère local du plan. */
function projectToChart(latitude, longitude) {
  const origin = currentChart.origin;
  const x =
    ((longitude - origin.lon) * Math.PI / 180) *
    EARTH_RADIUS_M *
    Math.cos((origin.lat * Math.PI) / 180);
  const y = ((latitude - origin.lat) * Math.PI / 180) * EARTH_RADIUS_M;
  return { x, y };
}

function setLiveState(online, text) {
  const pill = $("live-pill");
  pill.classList.toggle("online", online);
  $("live-text").textContent = text;
}

function updateHud(aircraft) {
  const hud = $("map-hud");
  hud.innerHTML = "";
  hud.append(el("div", "hud-title", currentChart ? `${currentChart.icao} · ${currentChart.name}` : "—"));

  if (!aircraft) {
    hud.append(el("div", null, "avion non localisé"));
    if (currentChart?.highlight_runway) {
      const line = el("div");
      line.append(document.createTextNode("piste retenue "));
      line.append(el("b", null, currentChart.highlight_runway));
      hud.append(line);
    }
    return;
  }

  const rows = [
    ["cap", aircraft.heading_true_deg !== null && aircraft.heading_true_deg !== undefined
      ? `${String(Math.round(aircraft.heading_true_deg)).padStart(3, "0")}°` : "—"],
    ["sol", aircraft.ground_speed_kt !== null && aircraft.ground_speed_kt !== undefined
      ? `${Math.round(aircraft.ground_speed_kt)} kt` : "—"],
    ["alt", aircraft.altitude_ft !== null && aircraft.altitude_ft !== undefined
      ? `${Math.round(aircraft.altitude_ft)} ft` : "—"],
    ["état", aircraft.on_ground ? "au sol" : "en vol"],
  ];
  for (const [label, value] of rows) {
    const line = el("div");
    line.append(document.createTextNode(`${label} `));
    line.append(el("b", null, value));
    hud.append(line);
  }
  if (currentChart?.highlight_runway) {
    const line = el("div");
    line.append(document.createTextNode("piste "));
    line.append(el("b", null, currentChart.highlight_runway));
    hud.append(line);
  }
}

function applyAircraftState(aircraft, shouldRecord = true) {
  latestAircraft = aircraft;
  if (currentChart) {
    const point = projectToChart(aircraft.latitude, aircraft.longitude);
    MAP.setAircraft({
      x: point.x,
      y: point.y,
      heading: aircraft.heading_true_deg,
    });
  }
  updateHud(aircraft);
  updateRouteStripProgress(aircraft);
  updateFlightPanel(aircraft);
  if (shouldRecord) recordFlightPoint(aircraft);
}

async function pollLive() {
  if (replayActive || !currentChart) return;

  const params = new URLSearchParams({
    demo: $("demo-toggle").checked ? "1" : "0",
    icao: currentIcao || "",
  });
  if (currentChart.highlight_runway) params.set("runway", currentChart.highlight_runway);

  try {
    const data = await fetch(`/api/live?${params}`).then((r) => r.json());
    if (!data.connected) {
      setLiveState(false, data.reason || "Simulateur non connecté");
      MAP.clearAircraft();
      updateHud(null);
      updateRouteStripProgress(null);
      latestAircraft = null;
      updateFlightPanel(null);
      return;
    }
    const aircraft = data.aircraft;
    setLiveState(true, `${aircraft.source} · en direct`);
    applyAircraftState(aircraft, true);
  } catch (error) {
    setLiveState(false, "Erreur de liaison");
    updateRouteStripProgress(null);
    updateFlightPanel(null);
  }
}

function startLiveLoop() {
  if (liveTimer) return;
  pollLive();
  liveTimer = setInterval(pollLive, LIVE_INTERVAL_MS);
}

/* ------------------------------------------------------------------ tabs */

function selectTab(name) {
  for (const button of document.querySelectorAll(".tabs button")) {
    button.classList.toggle("active", button.dataset.tab === name);
  }
  for (const key of ["map", "flight", "constraints", "dispatch", "aircraft", "sia", "mcdu", "raw"]) {
    show($(`panel-${key}`), key === name);
  }
  // Le canvas doit être mesuré une fois visible, sinon il reste à zéro.
  if (name === "map") MAP.resize();
}

/* ------------------------------------------------------------------- init */

document.querySelector(".tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (button) selectTab(button.dataset.tab);
});

$("refresh").addEventListener("click", buildPlan);
$("demo-toggle").addEventListener("change", buildPlan);

$("map-fit").addEventListener("click", () => MAP.fit());
$("map-zoom-in").addEventListener("click", () => MAP.zoomIn());
$("map-zoom-out").addEventListener("click", () => MAP.zoomOut());
$("map-follow").addEventListener("click", () => MAP.toggleFollow());
$("map-basemap").addEventListener("click", () => MAP.toggleBasemap());
$("map-ground").addEventListener("click", () => MAP.toggleGroundDetails());
$("map-sia").addEventListener("click", () => toggleSiaMapOverlay());
$("sia-overlay-close").addEventListener("click", () => toggleSiaMapOverlay(false));
$("sia-opacity").addEventListener("input", (event) => {
  $("sia-map-frame").style.opacity = String(Number(event.target.value) / 100);
});
$("map-route").addEventListener("click", () => MAP.fitRoute());
$("settings-open").addEventListener("click", openSettings);
$("update-install").addEventListener("click", installAvailableUpdate);
$("settings-close").addEventListener("click", () => $("settings-dialog").close());
$("settings-cancel").addEventListener("click", () => $("settings-dialog").close());
$("settings-form").addEventListener("submit", saveSettings);
$("settings-language").addEventListener("change", (event) => {
  window.I18N.setLanguage(event.target.value);
});
$("shutdown").addEventListener("click", shutdownApplication);
$("sim-status").addEventListener("click", pollSimulatorStatus);
$("terminal-toggle").addEventListener("click", toggleTerminal);

setTerminalCollapsed(localStorage.getItem(TERMINAL_COLLAPSED_KEY) === "true");
window.I18N.apply();

window.addEventListener("navixav:languagechange", () => {
  setTerminalCollapsed(localStorage.getItem(TERMINAL_COLLAPSED_KEY) === "true");
  if (currentPlan) renderPlan(currentPlan);
  loadStatus().catch(() => {});
  pollSimulatorStatus();
});

pollSimulatorStatus();
simulatorTimer = setInterval(pollSimulatorStatus, 2500);

async function initialiseApplication() {
  try {
    $("demo-toggle").checked = false;
    const status = await loadStatus();
    checkForUpdates();
    if (status.simbrief_configured) await buildPlan();
  } catch (error) {
    showBanner("error", "Initialisation impossible", [String(error)]);
  }
}

initialiseApplication();
