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
let currentFlightTrail = [];
let currentFlightTrailPlanKey = "";
let lastCurrentFlightTrailAt = 0;
let flightLog = [];
let flightRecording = true;
let lastFlightLogAt = 0;
let activeFlightSummary = null;
let previousFlightSummarySample = null;
let lastFlightSummaryAt = 0;
let replayTimer = null;
let replayActive = false;
let replaySpeed = 1;
let replaySourceLabel = "";
let latestStatus = null;
const siaRequests = new Map();
const officialAirportRequests = new Map();
const siaOverlayCandidates = new Map();
let siaOverlayKey = null;

const EARTH_RADIUS_M = 6378137;
const LIVE_INTERVAL_MS = 1000;
const CURRENT_FLIGHT_TRAIL_INTERVAL_MS = 5000;
const CURRENT_FLIGHT_TRAIL_MAX_POINTS = 3600;
const FLIGHT_LOG_INTERVAL_MS = 5000;
const FLIGHT_LOG_MAX_POINTS = 3600;
const FLIGHT_LOG_INDEX_KEY = "navixav-flight-log-index";
const FLIGHT_REPLAY_BASE_MS = 300;
const FLIGHT_SUMMARY_KEY = "navixav-flight-summaries";
const FLIGHT_SUMMARY_INTERVAL_MS = 5000;
const FLIGHT_SUMMARY_MAX_ENTRIES = 100;
const APP_SESSION_ID = Date.now().toString(36);
const TERMINAL_COLLAPSED_KEY = "navixav-terminal-collapsed";
const ONBOARDING_KEY = "navixav-onboarded";
const DEFAULT_TRAIL_COLOR = "#22d3ee";

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
  latestStatus = status;

  $("footer-version").textContent = `NaviXav ${status.version}`;
  $("footer-source").textContent = `SimBrief ${status.simbrief_target} · METAR ${status.metar_source}`;

  if (!status.simbrief_configured) {
    $("empty-hint").textContent = t("no_simbrief");
  }
  if (status.demo_available) $("demo-toggle").disabled = false;
  document.body.classList.toggle("remote-client", Boolean(status.remote_client));
  show($("mobile-mode"), Boolean(status.remote_client));
  if ($("settings-lan-url")) {
    $("settings-lan-url").value = status.lan_url || "";
    show($("settings-lan-access"), Boolean(status.lan_url));
  }
  return status;
}

function refreshUpdateButtonText() {
  const button = $("update-install");
  const version = button.dataset.version;
  button.textContent = version
    ? `${t("update_available")} ${version}`
    : t("check_update");
  button.title = version ? t("update_title") : t("check_update_title");
}

async function checkForUpdates(manual = false) {
  const button = $("update-install");
  if (manual) {
    button.disabled = true;
    button.textContent = t("checking_update");
  }
  try {
    const response = await fetch("/api/update/check", { cache: "no-store" });
    const update = await response.json();
    if (!response.ok) throw new Error(update.error || t("update_check_failed"));
    if (update.error) throw new Error(update.error);
    if (update.available) {
      button.dataset.version = update.latest_version;
      button.classList.add("available");
      refreshUpdateButtonText();
      if (manual) {
        showBanner(
          "info",
          `${t("update_available")} ${update.latest_version}`,
          [t("update_click_to_install")]
        );
      }
      return;
    }
    delete button.dataset.version;
    button.classList.remove("available");
    refreshUpdateButtonText();
    if (manual) {
      showBanner("info", t("up_to_date"), [t("up_to_date_body")]);
    }
  } catch (error) {
    if (manual) {
      showBanner("error", t("update_check_failed"), [String(error)]);
    }
    // Une coupure réseau ne doit jamais gêner le démarrage ou le vol.
  } finally {
    button.disabled = false;
    refreshUpdateButtonText();
  }
}

async function handleUpdateButton() {
  if ($("update-install").dataset.version) {
    await installAvailableUpdate();
  } else {
    await checkForUpdates(true);
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

async function openSimBriefPlanner() {
  const button = $("simbrief-create");
  button.disabled = true;
  try {
    const response = await fetch("/api/simbrief/new", {
      method: "POST",
      headers: { "X-NaviXav-External": "simbrief" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Ouverture impossible");
    showBanner("info", "SimBrief ouvert", [
      "Créez puis générez l’OFP dans SimBrief.",
      "Revenez ensuite dans NaviXav et cliquez sur « Importation du plan ».",
    ]);
  } catch (error) {
    showBanner("error", "Impossible d’ouvrir SimBrief", [String(error)]);
  } finally {
    button.disabled = false;
  }
}

async function openSupportPage() {
  const button = $("support-open");
  button.disabled = true;
  try {
    const response = await fetch("/api/support/open", {
      method: "POST",
      headers: { "X-NaviXav-External": "support" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("support_open_failed"));
  } catch (error) {
    showBanner("error", t("support_open_failed"), [String(error)]);
  } finally {
    button.disabled = false;
  }
}

/**
 * Aligne le champ couleur et son aperçu sur une teinte valide.
 *
 * Le champ natif refuse toute valeur hors « #rrggbb » et retombe alors sur du
 * noir : la teinte est normalisée avant d'être appliquée, et la ligne d'aperçu
 * reçoit la couleur exacte utilisée pour la trace sur la carte.
 */
function setTrailColorField(value) {
  const colour = /^#[0-9a-f]{6}$/i.test(String(value || ""))
    ? String(value)
    : DEFAULT_TRAIL_COLOR;
  const input = $("settings-trail-color");
  input.value = colour;
  input.closest(".color-field").style.setProperty("--trail-preview", colour);
  $("settings-trail-value").textContent = colour.toUpperCase();
  return colour;
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
    $("settings-basemap").value = values.map_basemap || "osm";
    setTrailColorField(values.map_trail_color);
    $("settings-lan-enabled").checked = Boolean(values.lan_enabled);
    show($("settings-lan-access"), Boolean(values.lan_enabled));
    $("settings-lan-url").value = latestStatus?.lan_url || "";
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
    map_basemap: $("settings-basemap").value,
    map_trail_color: $("settings-trail-color").value,
    lan_enabled: $("settings-lan-enabled").checked,
  };
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Enregistrement refusé");
    applyMapPreferences(result);
    message.textContent = result.lan_restart_required
      ? t("lan_restart_required")
      : t("saved");
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

/* ------------------------------------------------- premier lancement */

/**
 * Le premier lancement impose le choix de la langue et la saisie du compte
 * SimBrief. Un client distant (téléphone, tablette) parle à un poste déjà
 * configuré : seule la langue lui est demandée.
 */
function needsOnboarding(status) {
  if (status.remote_client) return !window.I18N.hasLanguage();
  if (localStorage.getItem(ONBOARDING_KEY)) return false;
  return !window.I18N.hasLanguage() || !status.simbrief_configured;
}

function welcomeNeedsSimbrief() {
  return !$("welcome-simbrief").classList.contains("hidden");
}

function welcomeIdentifiers() {
  return {
    simbrief_pilot_id: $("welcome-pilot-id").value.trim(),
    simbrief_username: $("welcome-username").value.trim(),
  };
}

function refreshWelcomeSubmit() {
  const { simbrief_pilot_id, simbrief_username } = welcomeIdentifiers();
  $("welcome-submit").disabled =
    welcomeNeedsSimbrief() && !simbrief_pilot_id && !simbrief_username;
}

function openWelcome(status) {
  show($("welcome-simbrief"), !status.simbrief_configured && !status.remote_client);
  show(
    $("welcome-demo"),
    welcomeNeedsSimbrief() && Boolean(status.demo_available)
  );
  if (!window.I18N.hasLanguage()) {
    $("welcome-language").value = window.I18N.suggestedLanguage();
  }
  const message = $("welcome-message");
  message.textContent = "";
  message.className = "settings-message";
  refreshWelcomeSubmit();
  $("welcome-dialog").showModal();
  $("welcome-language").focus();
}

function closeWelcome() {
  localStorage.setItem(ONBOARDING_KEY, "1");
  window.I18N.setLanguage($("welcome-language").value);
  $("welcome-dialog").close();
}

async function submitWelcome(event) {
  event.preventDefault();
  const message = $("welcome-message");
  const identifiers = welcomeIdentifiers();
  if (
    welcomeNeedsSimbrief()
    && !identifiers.simbrief_pilot_id
    && !identifiers.simbrief_username
  ) {
    message.textContent = t("welcome_need_id");
    message.className = "settings-message error";
    return;
  }
  if (!welcomeNeedsSimbrief()) {
    closeWelcome();
    return;
  }

  const button = $("welcome-submit");
  button.disabled = true;
  message.textContent = t("saving");
  message.className = "settings-message";
  try {
    // L'enregistrement remplace la totalité du fichier utilisateur : les
    // autres réglages sont relus puis renvoyés inchangés.
    const current = await fetch("/api/settings").then((r) => r.json());
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...current, ...identifiers, navdata_store: "" }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Enregistrement refusé");
    applyMapPreferences(result);
    closeWelcome();
    await initialiseApplication();
  } catch (error) {
    message.textContent = String(error);
    message.className = "settings-message error";
    button.disabled = false;
  }
}

async function skipWelcomeWithDemo() {
  closeWelcome();
  checkForUpdates();
  $("demo-toggle").checked = true;
  await buildPlan();
}

/* ------------------------------------------------------------------- plan */

async function buildPlan() {
  if (latestStatus?.remote_client) {
    await loadCurrentPlan();
    return;
  }

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

async function loadCurrentPlan() {
  const button = $("refresh");
  button.disabled = true;
  button.querySelector("span").textContent = t("loading_current_flight");

  try {
    const response = await fetch("/api/plan/current");
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 404) {
        showBanner("info", t("mobile_wait_title"), [t("mobile_wait_body")]);
      } else {
        showBanner("error", t("mobile_load_failed"), [payload.detail]);
      }
      return;
    }
    currentPlan = payload;
    renderPlan(payload);
  } catch (error) {
    showBanner("error", "Erreur réseau", [String(error)]);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = t("refresh_current_flight");
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
  const dismiss = el("button", "banner-close", "×");
  dismiss.type = "button";
  dismiss.title = t("close");
  dismiss.setAttribute("aria-label", t("close"));
  dismiss.addEventListener("click", hideBanner);
  banner.append(dismiss);
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

  // La progression du bandeau doit utiliser la route opérationnelle complète,
  // y compris les points de SID, STAR et d'approche.
  flightGeometry = buildFlightGeometry(plan);
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

  const chip = (label, value, kind, routeIndex = null, routeStage = null) => {
    const node = el("span", `chip ${kind}`);
    if (routeIndex !== null && routeIndex !== undefined) {
      node.dataset.routeIndex = String(routeIndex);
    }
    if (routeStage) node.dataset.routeStage = routeStage;
    if (label) node.append(el("small", null, label));
    node.append(document.createTextNode(value));
    return node;
  };

  const dep = plan.departure;
  const arr = plan.arrival;
  const geometryIndex = (ident, startAt = 0, fromEnd = false) => {
    if (!ident) return -1;
    if (fromEnd) {
      return flightGeometry.findLastIndex((point) => point.ident === ident);
    }
    return flightGeometry.findIndex(
      (point, index) => index >= startAt && point.ident === ident
    );
  };
  let geometryCursor = 1;
  const displayedFixes = new Set();
  const appendProcedureFixes = (points, excluded = []) => {
    const excludedFixes = new Set(excluded.filter(Boolean));
    for (const point of points || []) {
      const ident = point?.ident;
      if (!ident || displayedFixes.has(ident) || excludedFixes.has(ident)) continue;
      const index = geometryIndex(ident, geometryCursor);
      if (index < 0) continue;
      geometryCursor = index + 1;
      displayedFixes.add(ident);
      strip.append(chip(null, ident, "wpt", index));
    }
  };

  if (dep) {
    const originIndex = geometryIndex(dep.icao);
    strip.append(chip(null, dep.icao, "apt", originIndex));
    displayedFixes.add(dep.icao);
    if (dep.runway?.value) strip.append(chip("rwy", dep.runway.value, "proc"));
    if (dep.sid.value) strip.append(chip("sid", dep.sid.value, "proc", null, "sid"));
    appendProcedureFixes(
      dep.sid_path,
      [dep.icao, dep.sid_transition.value]
    );
    if (dep.sid_transition.value) {
      const index = geometryIndex(dep.sid_transition.value, geometryCursor);
      if (index >= 0) geometryCursor = index + 1;
      strip.append(chip(
        "trans",
        dep.sid_transition.value,
        "wpt",
        index >= 0 ? index : null
      ));
      displayedFixes.add(dep.sid_transition.value);
    }
  }
  for (const fix of plan.enroute.waypoints || []) {
    const index = geometryIndex(fix, geometryCursor);
    if (index >= 0) geometryCursor = index + 1;
    strip.append(chip(null, fix, "wpt", index >= 0 ? index : null));
    displayedFixes.add(fix);
  }
  if (arr) {
    if (arr.star_transition.value) {
      const index = geometryIndex(arr.star_transition.value, geometryCursor);
      if (index >= 0) geometryCursor = index + 1;
      strip.append(chip(
        "trans",
        arr.star_transition.value,
        "wpt",
        index >= 0 ? index : null
      ));
      displayedFixes.add(arr.star_transition.value);
    }
    if (arr.star.value) strip.append(chip("star", arr.star.value, "proc", null, "star"));
    appendProcedureFixes(
      arr.star_path,
      [arr.star_transition.value, arr.approach_transition.value, arr.icao]
    );
    if (arr.approach_transition.value) {
      const index = geometryIndex(arr.approach_transition.value, geometryCursor);
      if (index >= 0) geometryCursor = index + 1;
      strip.append(chip(
        "via",
        arr.approach_transition.value,
        "wpt",
        index >= 0 ? index : null
      ));
      displayedFixes.add(arr.approach_transition.value);
    }
    if (arr.approach.value) {
      strip.append(chip("appr", arr.approach.value, "proc", null, "approach"));
    }
    appendProcedureFixes(
      arr.approach_path,
      [arr.approach_transition.value, arr.icao]
    );
    if (arr.runway?.value) strip.append(chip("rwy", arr.runway.value, "proc"));
    const destinationIndex = geometryIndex(arr.icao, 0, true);
    strip.append(chip(
      null,
      arr.icao,
      "apt",
      destinationIndex >= 0 ? destinationIndex : null
    ));
  }
}

function routePointForAircraft(aircraft) {
  const route = flightGeometry;
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
  if (nearestSegment.distanceSquared > (50 * 1852) ** 2) return null;
  return Math.min(nearestSegment.index + 1, route.length - 1);
}

function updateRouteStripProgress(aircraft) {
  let activeIndex = routePointForAircraft(aircraft);
  if (activeIndex !== null && activeRoutePointIndex !== null) {
    // Un croisement de route ou deux segments proches ne doivent jamais faire
    // reculer la progression ni sauter toute une procédure en une seconde.
    activeIndex = Math.max(
      activeRoutePointIndex,
      Math.min(activeIndex, activeRoutePointIndex + 1)
    );
  }
  const strip = $("strip");
  for (const node of strip.querySelectorAll(".chip[data-route-index]")) {
    const index = Number(node.dataset.routeIndex);
    node.classList.toggle("route-passed", activeIndex !== null && index < activeIndex);
    node.classList.toggle("route-active", activeIndex !== null && index === activeIndex);
    node.classList.toggle("route-upcoming", activeIndex !== null && index > activeIndex);
    if (index === activeIndex) node.title = "Position actuelle de l’avion sur la route";
    else node.removeAttribute("title");
  }
  for (const node of strip.querySelectorAll(".chip[data-route-stage]")) {
    const stage = node.dataset.routeStage;
    const indexes = flightGeometry
      .map((point, index) => point.stage === stage ? index : -1)
      .filter((index) => index >= 0);
    if (!indexes.length || activeIndex === null) {
      node.classList.remove("route-passed", "route-active", "route-upcoming");
      continue;
    }
    const first = indexes[0];
    const last = indexes.at(-1);
    node.classList.toggle("route-passed", activeIndex > last);
    node.classList.toggle(
      "route-active",
      activeIndex >= first && activeIndex <= last
    );
    node.classList.toggle("route-upcoming", activeIndex < first);
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

function samePosition(first, second) {
  return Boolean(first) && Boolean(second)
    && first.lat === second.lat && first.lon === second.lon;
}

function flightStagePaths(plan) {
  // Le moteur ancre déjà les deux extrémités de la route sur les seuils des
  // pistes retenues : le tracé part donc de la piste de départ et s'arrête sur
  // celle d'arrivée, sans redoubler un point déjà fourni par la procédure.
  const route = plan.enroute?.route_path || [];
  const origin = route[0];
  const destination = route.at(-1);
  const cruise = route.slice(1, -1);
  const sid = [...(plan.departure?.sid_path || [])];
  const star = [...(plan.arrival?.star_path || [])];
  const approach = [...(plan.arrival?.approach_path || [])];

  if (origin && sid.length && !samePosition(origin, sid[0])) sid.unshift(origin);
  const departureEnd = sid.at(-1) || origin;
  const arrivalStart = star[0] || approach[0] || destination;
  // Sans point de croisière résolu, relier les deux aéroports inventerait une
  // route directe. On préfère ne rien tracer entre les procédures.
  const enroute = cruise.length
    ? [departureEnd, ...cruise, arrivalStart]
      .filter(Boolean).filter((point, index, points) => (
        index === 0
        || point.ident !== points[index - 1].ident
        || point.lat !== points[index - 1].lat
        || point.lon !== points[index - 1].lon
      ))
    : [];
  if (star.length && approach.length) approach.unshift(star.at(-1));

  if (destination) {
    if (approach.length) {
      if (!samePosition(destination, approach.at(-1))) approach.push(destination);
    } else if (star.length && !samePosition(destination, star.at(-1))) {
      star.push(destination);
    }
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

/* --------------------------------------------- configuration avion et alarmes */

/*
 * Deux garde-fous rendent ces alarmes utilisables en vol.
 *
 * Les capacités de la cellule d'abord : une règle qui dépend du train
 * rentrant, des volets ou des aérofreins n'est évaluée que si le simulateur a
 * confirmé que l'avion en possède. Sans cette information, la règle se taît
 * plutôt que de crier sur un train fixe.
 *
 * L'anti-rebond ensuite : une condition doit tenir quelques secondes avant de
 * lever une alarme, et disparaître un moment avant de l'éteindre. Sans cela,
 * chaque franchissement de seuil — 10 000 ft, 2 000 ft AGL — ferait clignoter
 * le bandeau.
 */

const ALERTS_STORAGE_KEY = "navixav-alerts-enabled";
const ALERT_RAISE_MS = 3000;
const ALERT_CORRECTION_MS = 750;
const ALERT_BANNER_MAX = 3;
const STD_PRESSURE_HPA = 1013.25;
const LBS_TO_KG = 0.45359237;
const SEVERITY_RANK = { danger: 0, warning: 1, info: 2 };

const LIGHT_LABELS = [
  ["landing", "LDG"],
  ["taxi", "TAXI"],
  ["strobe", "STRB"],
  ["nav", "NAV"],
  ["beacon", "BCN"],
  ["logo", "LOGO"],
  ["wing", "WING"],
];

let alertsEnabled = localStorage.getItem(ALERTS_STORAGE_KEY) !== "0";
let alertPhaseMemory = null;
const alertStates = new Map();

function finiteOr(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/** Réserve finale de l'OFP ramenée en kilogrammes, l'unité de SimConnect. */
function reserveFuelKg(plan) {
  const dispatch = plan?.dispatch || {};
  const reserve = finiteOr(dispatch.reserve_fuel, 0);
  if (!reserve) return null;
  return String(dispatch.units || "").toLowerCase().startsWith("lb")
    ? reserve * LBS_TO_KG
    : reserve;
}

function flightContext(aircraft, projection, phase, constraint) {
  const configuration = aircraft?.configuration || null;
  return {
    aircraft,
    configuration,
    capabilities: configuration?.capabilities || null,
    plan: currentPlan,
    projection,
    phase,
    constraint,
    onGround: Boolean(aircraft?.on_ground),
    groundSpeed: finiteOr(aircraft?.ground_speed_kt, 0),
    verticalSpeed: finiteOr(aircraft?.vertical_speed_fpm, 0),
    airspeed: finiteOr(aircraft?.indicated_airspeed_kt, 0),
    aglFt: finiteOr(aircraft?.height_above_ground_ft),
    // L'altitude indiquée est la seule comparable aux contraintes publiées.
    altitudeFt: finiteOr(
      configuration?.indicated_altitude_ft,
      finiteOr(aircraft?.altitude_ft)
    ),
  };
}

const ALERT_RULES = [
  {
    id: "parking_brake",
    severity: "danger",
    armed: (c) => !c.onGround || c.groundSpeed > 5,
    when: (c) => c.configuration.parking_brake === true,
  },
  {
    id: "gear_not_down",
    severity: "danger",
    needs: "retractable_gear",
    armed: (c) => (
      !c.onGround
      && c.aglFt !== null && c.aglFt < 2000
      && c.verticalSpeed < -300
      && (c.phase === "Approche" || c.phase === "Atterrissage")
    ),
    when: (c) => finiteOr(c.configuration.gear_extended_pct, 100) < 95,
  },
  {
    id: "gear_not_up",
    severity: "warning",
    needs: "retractable_gear",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt > 1000 && c.verticalSpeed > 300,
    when: (c) => finiteOr(c.configuration.gear_extended_pct, 0) > 5,
  },
  {
    id: "flaps_not_set",
    severity: "warning",
    needs: "flaps",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt < 3000 && c.phase === "Approche",
    when: (c) => c.configuration.flaps_handle_index === 0,
  },
  {
    id: "flaps_still_out",
    severity: "warning",
    needs: "flaps",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt > 3000 && c.phase === "Montée",
    when: (c) => finiteOr(c.configuration.flaps_handle_index, 0) > 0,
  },
  {
    id: "flaps_takeoff",
    severity: "warning",
    needs: "flaps",
    armed: (c) => c.onGround && c.phase === "Décollage",
    when: (c) => c.configuration.flaps_handle_index === 0,
  },
  {
    id: "spoilers_not_armed",
    severity: "warning",
    needs: "spoilers",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt < 2000 && c.phase === "Approche",
    when: (c) => c.configuration.spoilers_armed === false,
  },
  {
    id: "spoilers_out",
    severity: "warning",
    needs: "spoilers",
    armed: (c) => c.phase === "Montée",
    when: (c) => finiteOr(c.configuration.spoilers_handle_pct, 0) > 5,
  },
  {
    id: "strobe_off",
    severity: "warning",
    armed: (c) => !c.onGround || c.phase === "Décollage",
    when: (c) => c.configuration.lights?.strobe === false,
  },
  {
    id: "beacon_off",
    severity: "warning",
    armed: (c) => c.onGround,
    when: (c) => c.configuration.lights?.beacon === false,
  },
  {
    id: "nav_lights_off",
    severity: "info",
    armed: () => true,
    when: (c) => c.configuration.lights?.nav === false,
  },
  {
    id: "taxi_light_off",
    severity: "info",
    armed: (c) => c.onGround && c.groundSpeed > 3,
    when: (c) => c.configuration.lights?.taxi === false,
  },
  {
    id: "landing_lights_off",
    severity: "warning",
    armed: (c) => (
      !c.onGround
      && c.altitudeFt !== null && c.altitudeFt < 10000
      && (c.phase === "Descente" || c.phase === "Approche")
    ),
    when: (c) => c.configuration.lights?.landing === false,
  },
  {
    id: "landing_lights_on",
    severity: "info",
    armed: (c) => c.phase === "Croisière" && c.altitudeFt !== null && c.altitudeFt > 10000,
    when: (c) => c.configuration.lights?.landing === true,
  },
  {
    id: "std_not_set",
    severity: "warning",
    armed: (c) => {
      const transition = finiteOr(c.plan?.departure?.transition_altitude_ft);
      return (
        !c.onGround && c.phase === "Montée"
        && transition !== null && c.altitudeFt !== null
        && c.altitudeFt > transition
      );
    },
    when: (c) => {
      const setting = finiteOr(c.configuration.altimeter_hpa);
      return setting !== null && Math.abs(setting - STD_PRESSURE_HPA) > 0.5;
    },
  },
  {
    id: "qnh_not_set",
    severity: "warning",
    armed: (c) => {
      const level = finiteOr(c.plan?.arrival?.transition_level_ft);
      return (
        !c.onGround
        && (c.phase === "Descente" || c.phase === "Approche")
        && level !== null && c.altitudeFt !== null
        && c.altitudeFt < level
      );
    },
    when: (c) => {
      const setting = finiteOr(c.configuration.altimeter_hpa);
      return setting !== null && Math.abs(setting - STD_PRESSURE_HPA) <= 0.5;
    },
  },
  {
    id: "selected_altitude_above",
    severity: "danger",
    // Une altitude sélectionnée nulle signifie « non exposée par cet avion » :
    // c'est elle qui conditionne la règle, pas le maître du pilote automatique.
    armed: (c) => (
      Boolean(c.constraint?.altitudeFt)
      && c.constraint.distanceNm < 15
      && finiteOr(c.configuration.selected_altitude_ft, 0) > 0
    ),
    when: (c) => (
      finiteOr(c.configuration.selected_altitude_ft, 0) > c.constraint.altitudeFt + 100
    ),
    detail: (c) => `${Math.round(c.configuration.selected_altitude_ft)} ft / ${c.constraint.altitudeFt} ft`,
  },
  {
    id: "ils_mismatch",
    severity: "warning",
    armed: (c) => (
      Boolean(finiteOr(c.plan?.arrival?.ils_frequency_mhz))
      && (c.phase === "Descente" || c.phase === "Approche")
      && finiteOr(c.projection?.remainingNm, Infinity) < 25
    ),
    when: (c) => {
      const expected = finiteOr(c.plan.arrival.ils_frequency_mhz);
      const tuned = finiteOr(c.configuration.nav1_frequency_mhz, 0);
      return Math.abs(tuned - expected) > 0.005;
    },
    detail: (c) => (
      `${finiteOr(c.configuration.nav1_frequency_mhz, 0).toFixed(2)}`
      + ` / ${finiteOr(c.plan.arrival.ils_frequency_mhz).toFixed(2)}`
    ),
  },
  {
    id: "flap_overspeed",
    severity: "danger",
    armed: () => true,
    when: (c) => c.configuration.flap_speed_exceeded === true,
  },
  {
    id: "overspeed",
    severity: "danger",
    armed: () => true,
    when: (c) => c.configuration.overspeed_warning === true,
  },
  {
    id: "stall",
    severity: "danger",
    armed: (c) => !c.onGround,
    when: (c) => c.configuration.stall_warning === true,
  },
  {
    id: "anti_ice",
    severity: "warning",
    armed: (c) => {
      const temperature = finiteOr(c.configuration.total_air_temperature_c);
      return (
        !c.onGround && temperature !== null && temperature < 10
        && c.configuration.in_cloud === true
      );
    },
    when: (c) => c.configuration.engine_anti_ice === false,
  },
  {
    id: "fuel_below_reserve",
    severity: "danger",
    armed: (c) => !c.onGround && reserveFuelKg(c.plan) !== null,
    when: (c) => {
      const onboard = finiteOr(c.configuration.fuel_total_kg);
      return onboard !== null && onboard < reserveFuelKg(c.plan);
    },
    detail: (c) => `${Math.round(c.configuration.fuel_total_kg)} kg`,
  },
];

/** Motif d'inhibition globale, ou null si les alarmes doivent être évaluées. */
function alertsInhibition(context) {
  if (!alertsEnabled) return { key: "alerts_off" };
  if (replayActive) return { key: "alerts_replay" };
  if (!context.aircraft || !context.configuration) return { key: "alerts_no_data" };
  const rate = finiteOr(context.configuration.simulation_rate);
  if (rate !== null && Math.abs(rate - 1) > 0.05) {
    return { key: "alerts_rate", detail: `×${rate}` };
  }
  return null;
}

/** Règles en faute à cet instant, avant anti-rebond. */
function evaluateAlerts(context) {
  const hits = new Map();
  for (const rule of ALERT_RULES) {
    // Une capacité inconnue vaut absente : mieux vaut se taire que mentir.
    if (rule.needs && !context.capabilities?.[rule.needs]) continue;
    if (!rule.armed(context)) continue;
    if (!rule.when(context)) continue;
    let detail = "";
    try {
      detail = rule.detail ? rule.detail(context) : "";
    } catch (_error) {
      detail = "";
    }
    hits.set(rule.id, detail);
  }
  return hits;
}

/**
 * Applique l'anti-rebond et l'acquittement, et renvoie les alarmes à afficher.
 * Un changement de phase lève les acquittements : la situation a changé.
 */
function commitAlerts(hits, phase, now) {
  if (phase !== alertPhaseMemory) {
    alertPhaseMemory = phase;
    for (const state of alertStates.values()) state.acknowledged = false;
  }

  const active = [];
  for (const rule of ALERT_RULES) {
    let state = alertStates.get(rule.id);
    if (!state) {
      state = {
        firstSeen: 0,
        correctedAt: 0,
        active: false,
        acknowledged: false,
        detail: "",
      };
      alertStates.set(rule.id, state);
    }

    if (hits.has(rule.id)) {
      state.detail = hits.get(rule.id);
      state.correctedAt = 0;
      if (!state.firstSeen) state.firstSeen = now;
      if (!state.active && now - state.firstSeen >= ALERT_RAISE_MS) state.active = true;
    } else if (state.firstSeen) {
      if (!state.correctedAt) state.correctedAt = now;
      if (now - state.correctedAt >= ALERT_CORRECTION_MS) {
        // Une correction stable acquitte automatiquement l'alarme et la
        // réarme immédiatement pour une éventuelle nouvelle anomalie.
        state.firstSeen = 0;
        state.correctedAt = 0;
        state.active = false;
        state.acknowledged = false;
        state.detail = "";
      }
    }

    if (state.active && !state.acknowledged) {
      active.push({
        id: rule.id,
        severity: rule.severity,
        detail: state.detail,
        label: t(`alert_${rule.id}`),
        action: t(`alert_${rule.id}_action`),
      });
    }
  }

  active.sort((first, second) => SEVERITY_RANK[first.severity] - SEVERITY_RANK[second.severity]);
  return active;
}

function acknowledgeAlert(id) {
  const state = alertStates.get(id);
  if (state) state.acknowledged = true;
}

function resetAlertStates() {
  alertStates.clear();
  alertPhaseMemory = null;
}

function flightLogStorageKey(plan) {
  return [
    "navixav-flight-log",
    plan.departure?.icao || "----",
    plan.arrival?.icao || "----",
    plan.callsign || "flight",
    plan.demo
      ? `demo-${APP_SESSION_ID}`
      : plan.source?.simbrief_generated_at || APP_SESSION_ID,
  ].join(":");
}

function loadStoredFlightLog(key) {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function loadFlightLog(plan) {
  return loadStoredFlightLog(flightLogStorageKey(plan));
}

function saveFlightArchive(entries) {
  try {
    localStorage.setItem(FLIGHT_LOG_INDEX_KEY, JSON.stringify(entries));
  } catch (_error) {
    // Le vol reste enregistré même si son petit index ne peut pas être mis à jour.
  }
}

function flightArchiveEntry(plan, key, points) {
  return {
    key,
    departure: plan.departure?.icao || "----",
    arrival: plan.arrival?.icao || "----",
    callsign: plan.callsign || "",
    started_at: points[0]?.recorded_at || "",
    ended_at: points[points.length - 1]?.recorded_at || "",
    points: points.length,
    route_segments: flightStagePaths(plan).map((segment) => ({
      stage: segment.stage,
      points: segment.points.map((point) => ({
        ident: point.ident || segment.stage,
        lat: Number(point.lat),
        lon: Number(point.lon),
      })),
    })),
  };
}

function loadFlightArchive() {
  let entries = [];
  try {
    const parsed = JSON.parse(localStorage.getItem(FLIGHT_LOG_INDEX_KEY) || "[]");
    if (Array.isArray(parsed)) entries = parsed;
  } catch (_error) {
    entries = [];
  }
  entries = entries.filter(
    (entry) => entry && typeof entry.key === "string"
  );

  // Migration des journaux créés avant l'ajout du catalogue.
  const known = new Set(entries.map((entry) => entry.key));
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index) || "";
    if (!key.startsWith("navixav-flight-log:") || known.has(key)) continue;
    const points = loadStoredFlightLog(key);
    if (points.length < 2) continue;
    const parts = key.split(":");
    entries.push({
      key,
      departure: parts[1] || "----",
      arrival: parts[2] || "----",
      callsign: parts[3] || "",
      started_at: points[0]?.recorded_at || "",
      ended_at: points[points.length - 1]?.recorded_at || "",
      points: points.length,
    });
  }

  entries = entries
    .filter((entry) => entry?.key && localStorage.getItem(entry.key) !== null)
    .sort((first, second) => String(second.ended_at).localeCompare(String(first.ended_at)));
  saveFlightArchive(entries);
  return entries;
}

function updateFlightArchive(plan, key, points) {
  const entries = loadFlightArchive().filter((entry) => entry.key !== key);
  if (points.length >= 2) entries.push(flightArchiveEntry(plan, key, points));
  entries.sort(
    (first, second) => String(second.ended_at).localeCompare(String(first.ended_at))
  );
  saveFlightArchive(entries);
  renderFlightArchive();
}

function saveFlightLog() {
  if (!currentPlan) return;
  const key = flightLogStorageKey(currentPlan);
  if (!flightLog.length) {
    localStorage.removeItem(key);
    updateFlightArchive(currentPlan, key, flightLog);
    return;
  }
  try {
    localStorage.setItem(key, JSON.stringify(flightLog));
    updateFlightArchive(currentPlan, key, flightLog);
  } catch (_error) {
    // Conserver tout le trajet en espaçant les anciens relevés plutôt qu'en
    // supprimant le départ du vol.
    flightLog = flightLog.filter(
      (_point, index) => index % 2 === 0 || index === flightLog.length - 1
    );
    try {
      localStorage.setItem(key, JSON.stringify(flightLog));
      updateFlightArchive(currentPlan, key, flightLog);
    } catch (_secondError) {
      // Le suivi en direct continue même si le stockage local est indisponible.
    }
  }
}

function compactFlightLog() {
  if (flightLog.length <= FLIGHT_LOG_MAX_POINTS) return;
  flightLog = flightLog.filter(
    (_point, index) => index % 2 === 0 || index === flightLog.length - 1
  );
}

function flightTrailPoints(points) {
  const trail = [];
  let previous = null;
  for (const point of points) {
    const latitude = Number(point?.latitude);
    const longitude = Number(point?.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue;

    if (previous) {
      const elapsedMs = (
        Date.parse(point.recorded_at || "")
        - Date.parse(previous.recorded_at || "")
      );
      const elapsedHours = Number.isFinite(elapsedMs) && elapsedMs > 0
        ? elapsedMs / 3_600_000
        : 0;
      const speed = Math.max(
        50,
        finiteOr(previous.ground_speed_kt, 0),
        finiteOr(point.ground_speed_kt, 0)
      );
      const plausibleDistanceNm = elapsedHours
        ? Math.max(0.15, speed * elapsedHours * 4)
        : 2;
      const loopRestart = (
        previous.source === "Démonstration"
        && finiteOr(previous.ground_speed_kt, 0) < 1
        && finiteOr(point.ground_speed_kt, 0) > 1
      );
      if (loopRestart || haversineNm(previous, point) > plausibleDistanceNm) {
        trail.push(null);
      }
    }

    trail.push(projectToChart(latitude, longitude));
    previous = point;
  }
  return trail;
}

function syncMapTrail() {
  if (!currentChart) return;
  MAP.setTrail(flightTrailPoints(currentFlightTrail));
}

/**
 * Conserve uniquement en mémoire la trace du vol affiché.
 *
 * Cette liste n'est jamais écrite dans localStorage : elle disparaît à la
 * fermeture de NaviXav et ne constitue ni un historique ni un rejeu.
 */
function recordCurrentFlightTrail(aircraft) {
  if (!aircraft || !currentPlan) return;
  const planKey = flightSummaryPlanKey(currentPlan);
  if (planKey !== currentFlightTrailPlanKey) {
    currentFlightTrail = [];
    currentFlightTrailPlanKey = planKey;
    lastCurrentFlightTrailAt = 0;
  }

  const now = Date.now();
  if (now - lastCurrentFlightTrailAt < CURRENT_FLIGHT_TRAIL_INTERVAL_MS) return;
  lastCurrentFlightTrailAt = now;
  currentFlightTrail.push({
    latitude: aircraft.latitude,
    longitude: aircraft.longitude,
    ground_speed_kt: aircraft.ground_speed_kt,
    source: aircraft.source,
    recorded_at: new Date(now).toISOString(),
  });
  if (currentFlightTrail.length > CURRENT_FLIGHT_TRAIL_MAX_POINTS) {
    currentFlightTrail = currentFlightTrail.filter(
      (_point, index) => index % 2 === 0 || index === currentFlightTrail.length - 1
    );
  }
  syncMapTrail();
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
  compactFlightLog();
  saveFlightLog();
  syncMapTrail();
  updateRecorderStatus();
}

function updateRecorderStatus() {
  const status = $("flight-recorder-status");
  if (!status) return;
  const speed = String(replaySpeed).replace(".", ",");
  const mode = replayActive
    ? `rejeu ×${speed}${replaySourceLabel ? ` · ${replaySourceLabel}` : ""}`
    : flightRecording ? "enregistrement actif" : "en pause";
  status.textContent = `${mode} · ${flightLog.length} points`;
  const toggle = $("flight-record-toggle");
  if (toggle) toggle.textContent = flightRecording ? "Mettre en pause" : "Reprendre";
}

function stopFlightReplay() {
  if (replayTimer) clearInterval(replayTimer);
  replayTimer = null;
  replayActive = false;
  replaySourceLabel = "";
  syncMapTrail();
  updateRecorderStatus();
}

function startFlightReplay(points = flightLog, sourceLabel = "") {
  if (points.length < 2) return;
  stopFlightReplay();
  replayActive = true;
  replaySourceLabel = sourceLabel;
  if (currentChart) {
    MAP.setTrail(flightTrailPoints(points));
  }
  let index = 0;
  replayTimer = setInterval(() => {
    if (index >= points.length) {
      stopFlightReplay();
      return;
    }
    applyAircraftState(points[index], false);
    index += 1;
  }, Math.max(50, FLIGHT_REPLAY_BASE_MS / replaySpeed));
  updateRecorderStatus();
}

function currentDebriefRouteSegments() {
  return currentPlan
    ? flightStagePaths(currentPlan).map((segment) => ({
      stage: segment.stage,
      points: segment.points.map((point) => ({
        ident: point.ident || segment.stage,
        lat: Number(point.lat),
        lon: Number(point.lon),
      })),
    }))
    : null;
}

function projectAircraftOnDebriefPath(aircraft, routeSegments) {
  if (!Array.isArray(routeSegments) || !routeSegments.length) return null;
  const latitude = Number(aircraft?.latitude);
  const longitude = Number(aircraft?.longitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

  const scaleX = EARTH_RADIUS_M * Math.cos(latitude * Math.PI / 180);
  const scaleY = EARTH_RADIUS_M;
  const relative = (point) => ({
    x: (Number(point.lon) - longitude) * Math.PI / 180 * scaleX,
    y: (Number(point.lat) - latitude) * Math.PI / 180 * scaleY,
  });
  let best = null;
  for (const segment of routeSegments) {
    const points = (segment.points || []).filter((point) => (
      Number.isFinite(Number(point.lat)) && Number.isFinite(Number(point.lon))
    ));
    for (let index = 0; index < points.length - 1; index += 1) {
      const start = relative(points[index]);
      const end = relative(points[index + 1]);
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
        best = {
          distanceSquared,
          stage: segment.stage,
          activePoint: { ...points[index + 1], stage: segment.stage },
        };
      }
    }
  }
  return best
    ? {
      activePoint: best.activePoint,
      crossTrackNm: Math.sqrt(best.distanceSquared) / 1852,
    }
    : null;
}

function flightDebrief(points, routeSegments = currentDebriefRouteSegments()) {
  const samples = points.filter((point) => (
    Number.isFinite(Number(point?.latitude))
    && Number.isFinite(Number(point?.longitude))
  ));
  if (samples.length < 2) return null;

  let distanceNm = 0;
  let offRouteSeconds = 0;
  let maxDeviationNm = 0;
  let maxAltitudeFt = 0;
  const projections = [];

  for (let index = 0; index < samples.length; index += 1) {
    const point = samples[index];
    const projection = projectAircraftOnDebriefPath(point, routeSegments);
    projections.push(projection);
    maxAltitudeFt = Math.max(maxAltitudeFt, finiteOr(point.altitude_ft, 0));
    if (projection && !point.on_ground) {
      maxDeviationNm = Math.max(maxDeviationNm, projection.crossTrackNm);
      if (index && projection.crossTrackNm > 2) {
        const elapsed = (
          Date.parse(point.recorded_at || "")
          - Date.parse(samples[index - 1].recorded_at || "")
        ) / 1000;
        if (Number.isFinite(elapsed) && elapsed > 0 && elapsed < 60) {
          offRouteSeconds += elapsed;
        }
      }
    }
    if (!index) continue;
    const previous = samples[index - 1];
    const elapsedHours = (
      Date.parse(point.recorded_at || "")
      - Date.parse(previous.recorded_at || "")
    ) / 3_600_000;
    const leg = haversineNm(previous, point);
    const speed = Math.max(
      50,
      finiteOr(previous.ground_speed_kt, 0),
      finiteOr(point.ground_speed_kt, 0)
    );
    const plausible = Number.isFinite(elapsedHours) && elapsedHours > 0
      ? Math.max(0.15, speed * elapsedHours * 4)
      : 2;
    if (leg <= plausible) distanceNm += leg;
  }

  const events = [];
  const seen = new Set();
  const addEvent = (id, index, label, detail, severity = "info") => {
    if (seen.has(id) || index < 0) return;
    seen.add(id);
    events.push({ id, index, label, detail, severity });
  };

  for (let index = 1; index < samples.length; index += 1) {
    const previous = samples[index - 1];
    const point = samples[index];
    const projection = projections[index];
    if (previous.on_ground && !point.on_ground) {
      addEvent("takeoff", index, "Décollage", `${Math.round(point.ground_speed_kt || 0)} kt`);
    }
    if (
      !seen.has("descent")
      && !point.on_ground
      && finiteOr(point.vertical_speed_fpm, 0) < -500
      && finiteOr(point.altitude_ft, 0) < maxAltitudeFt - 1000
    ) {
      addEvent(
        "descent",
        index,
        "Début de descente",
        `${Math.round(point.altitude_ft || 0)} ft`
      );
    }
    if (
      !seen.has("approach")
      && !point.on_ground
      && projection?.activePoint?.stage === "approach"
    ) {
      addEvent(
        "approach",
        index,
        "Entrée en approche",
        projection?.activePoint?.ident || ""
      );
    }
    if (!previous.on_ground && point.on_ground) {
      addEvent("landing", index, "Toucher", `${Math.round(point.ground_speed_kt || 0)} kt`);
    }

    const configuration = point.configuration || {};
    if (configuration.overspeed_warning === true) {
      addEvent("overspeed", index, "Survitesse détectée", "Alarme simulateur", "danger");
    }
    if (configuration.stall_warning === true) {
      addEvent("stall", index, "Décrochage détecté", "Alarme simulateur", "danger");
    }
    if (configuration.flap_speed_exceeded === true) {
      addEvent(
        "flap_overspeed",
        index,
        "Limite volets dépassée",
        "Alarme simulateur",
        "danger"
      );
    }

    const onFinal = !point.on_ground
      && projection?.activePoint?.stage === "approach";
    const height = finiteOr(point.height_above_ground_ft);
    if (onFinal && height !== null && height <= 1000) {
      const gear = finiteOr(configuration.gear_extended_pct);
      if (gear !== null && gear < 95) {
        addEvent(
          "gear_below_1000",
          index,
          "Train non confirmé sous 1 000 ft",
          `${Math.round(gear)} %`,
          "warning"
        );
      }
      const verticalSpeed = finiteOr(point.vertical_speed_fpm, 0);
      if (verticalSpeed < -1200) {
        addEvent(
          "vertical_speed_below_1000",
          index,
          "Taux de descente élevé sous 1 000 ft",
          `${Math.round(verticalSpeed)} ft/min`,
          "warning"
        );
      }
      const airspeed = finiteOr(point.indicated_airspeed_kt);
      if (airspeed !== null && airspeed > 180) {
        addEvent(
          "speed_below_1000",
          index,
          "Vitesse élevée sous 1 000 ft",
          `${Math.round(airspeed)} kt`,
          "warning"
        );
      }
    }
  }

  const started = Date.parse(samples[0].recorded_at || "");
  const ended = Date.parse(samples.at(-1).recorded_at || "");
  return {
    samples,
    durationSeconds: Number.isFinite(started) && Number.isFinite(ended)
      ? Math.max(0, (ended - started) / 1000)
      : 0,
    distanceNm,
    offRouteSeconds,
    maxDeviationNm,
    maxAltitudeFt,
    routeAvailable: Array.isArray(routeSegments) && routeSegments.length > 0,
    events: events.sort((first, second) => first.index - second.index),
  };
}

function formatDebriefDuration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remaining = total % 60;
  return hours
    ? `${hours} h ${String(minutes).padStart(2, "0")} min`
    : `${minutes} min ${String(remaining).padStart(2, "0")} s`;
}

function renderFlightDebrief(
  points = flightLog,
  sourceLabel = "Vol courant",
  routeSegments = currentDebriefRouteSegments()
) {
  const container = $("flight-debrief-content");
  if (!container) return;
  container.innerHTML = "";
  const debrief = flightDebrief(points, routeSegments);
  if (!debrief) {
    container.append(el(
      "p",
      "flight-archive-empty",
      "Le débrief sera disponible après l’enregistrement d’au moins deux points."
    ));
    return;
  }

  const heading = el("div", "flight-debrief-heading");
  heading.append(
    el("strong", null, sourceLabel),
    el(
      "span",
      null,
      "Seuils indicatifs NaviXav : écart > 2 NM et vérifications sous 1 000 ft."
    )
  );
  container.append(heading);

  const stats = el("div", "flight-debrief-stats");
  for (const [label, value] of [
    ["Durée", formatDebriefDuration(debrief.durationSeconds)],
    ["Distance réelle", `${debrief.distanceNm.toFixed(1)} NM`],
    [
      "Écart maximal",
      debrief.routeAvailable ? `${debrief.maxDeviationNm.toFixed(1)} NM` : "—",
    ],
    [
      "Temps hors route",
      debrief.routeAvailable ? formatDebriefDuration(debrief.offRouteSeconds) : "—",
    ],
    ["Altitude maximale", `${Math.round(debrief.maxAltitudeFt)} ft`],
  ]) {
    const card = el("article", "flight-live-stat");
    card.append(el("div", "stat-label", label), el("div", "stat-value", value));
    stats.append(card);
  }
  container.append(stats);

  const timeline = el("div", "flight-debrief-timeline");
  if (!debrief.events.length) {
    timeline.append(el("p", "flight-archive-empty", "Aucun événement notable détecté."));
  }
  for (const event of debrief.events) {
    const row = el("button", "flight-debrief-event");
    row.type = "button";
    row.dataset.severity = event.severity;
    const time = debrief.samples[event.index]?.recorded_at;
    const description = el("span", "flight-debrief-event-body");
    description.append(
      el("strong", null, event.label),
      el(
        "span",
        null,
        [time ? new Date(time).toLocaleTimeString() : "", event.detail]
          .filter(Boolean)
          .join(" · ")
      )
    );
    row.append(el("span", "flight-debrief-event-mark", "▶"), description);
    row.title = "Rejouer cette séquence";
    row.addEventListener("click", () => {
      const start = Math.max(0, event.index - 6);
      const end = Math.min(debrief.samples.length, event.index + 13);
      startFlightReplay(
        debrief.samples.slice(start, end),
        `${sourceLabel} · ${event.label}`
      );
    });
    timeline.append(row);
  }
  container.append(timeline);
}

function renderFlightArchive() {
  const container = $("flight-archive-list");
  if (!container) return;
  container.innerHTML = "";
  const entries = loadFlightArchive();
  if (!entries.length) {
    container.append(el("p", "flight-archive-empty", "Aucun ancien vol enregistré."));
    return;
  }

  for (const entry of entries) {
    const row = el("article", "flight-archive-row");
    const description = el("div", "flight-archive-description");
    description.append(
      el("strong", null, `${entry.departure} → ${entry.arrival}`),
      el(
        "span",
        null,
        [
          entry.callsign,
          entry.ended_at ? new Date(entry.ended_at).toLocaleString() : "",
          `${entry.points} points`,
        ].filter(Boolean).join(" · ")
      )
    );
    const actions = el("div", "flight-archive-actions");
    const analyse = el("button", "icon-btn", "Débriefer");
    analyse.type = "button";
    analyse.addEventListener("click", () => {
      const sameRoute = (
        entry.departure === currentPlan?.departure?.icao
        && entry.arrival === currentPlan?.arrival?.icao
      );
      renderFlightDebrief(
        loadStoredFlightLog(entry.key),
        `${entry.departure} → ${entry.arrival}`,
        entry.route_segments || (sameRoute ? currentDebriefRouteSegments() : null)
      );
      $("flight-debrief")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    const replay = el("button", "icon-btn", "Rejouer");
    replay.type = "button";
    replay.addEventListener("click", () => {
      startFlightReplay(
        loadStoredFlightLog(entry.key),
        `${entry.departure} → ${entry.arrival}`
      );
    });
    actions.append(analyse, replay);
    row.append(description, actions);
    container.append(row);
  }
}

function flightSummaryPlanKey(plan) {
  return [
    plan.departure?.icao || "----",
    plan.arrival?.icao || "----",
    plan.callsign || "flight",
    plan.demo
      ? `demo-${APP_SESSION_ID}`
      : plan.source?.simbrief_generated_at || APP_SESSION_ID,
  ].join(":");
}

function loadFlightSummaries() {
  try {
    const parsed = JSON.parse(localStorage.getItem(FLIGHT_SUMMARY_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch (_error) {
    return [];
  }
}

function saveFlightSummaries(entries) {
  try {
    localStorage.setItem(
      FLIGHT_SUMMARY_KEY,
      JSON.stringify(entries.slice(0, FLIGHT_SUMMARY_MAX_ENTRIES))
    );
  } catch (_error) {
    // Le suivi du vol courant reste disponible même si le stockage est plein.
  }
}

function summaryDistance(points) {
  let distanceNm = 0;
  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const point = points[index];
    const elapsedHours = (
      Date.parse(point.recorded_at || "")
      - Date.parse(previous.recorded_at || "")
    ) / 3_600_000;
    const leg = haversineNm(previous, point);
    const speed = Math.max(
      50,
      finiteOr(previous.ground_speed_kt, 0),
      finiteOr(point.ground_speed_kt, 0)
    );
    const plausible = Number.isFinite(elapsedHours) && elapsedHours > 0
      ? Math.max(0.15, speed * elapsedHours * 4)
      : 2;
    if (leg <= plausible) distanceNm += leg;
  }
  return distanceNm;
}

function migrateDetailedFlightLogs() {
  const summaries = loadFlightSummaries();
  const existing = new Set(summaries.map((entry) => entry.id));
  let archive = [];
  try {
    const parsed = JSON.parse(localStorage.getItem(FLIGHT_LOG_INDEX_KEY) || "[]");
    if (Array.isArray(parsed)) archive = parsed;
  } catch (_error) {
    archive = [];
  }
  const archiveByKey = new Map(archive.map((entry) => [entry?.key, entry]));
  const legacyKeys = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index) || "";
    if (key.startsWith("navixav-flight-log:")) legacyKeys.push(key);
  }

  for (const key of legacyKeys) {
    const points = loadStoredFlightLog(key);
    const metadata = archiveByKey.get(key) || {};
    if (points.length >= 2 && !existing.has(`legacy:${key}`)) {
      const parts = key.split(":");
      const startedAt = metadata.started_at || points[0]?.recorded_at || "";
      const endedAt = metadata.ended_at || points.at(-1)?.recorded_at || "";
      summaries.push({
        id: `legacy:${key}`,
        departure: metadata.departure || parts[1] || "----",
        arrival: metadata.arrival || parts[2] || "----",
        callsign: metadata.callsign || parts[3] || "",
        started_at: startedAt,
        ended_at: endedAt,
        duration_seconds: Math.max(
          0,
          (Date.parse(endedAt) - Date.parse(startedAt)) / 1000 || 0
        ),
        distance_nm: summaryDistance(points),
        max_altitude_ft: points.reduce(
          (maximum, point) => Math.max(maximum, finiteOr(point.altitude_ft, 0)),
          0
        ),
      });
    }
    localStorage.removeItem(key);
  }
  localStorage.removeItem(FLIGHT_LOG_INDEX_KEY);
  summaries.sort(
    (first, second) => String(second.ended_at).localeCompare(String(first.ended_at))
  );
  saveFlightSummaries(summaries);
}

function purgeFlightHistory() {
  const legacyKeys = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index) || "";
    if (key.startsWith("navixav-flight-log:")) legacyKeys.push(key);
  }
  for (const key of legacyKeys) localStorage.removeItem(key);
  localStorage.removeItem(FLIGHT_LOG_INDEX_KEY);
  localStorage.removeItem(FLIGHT_SUMMARY_KEY);
  renderFlightSummaries();
}

function storeCompletedFlightSummary(summary) {
  const entries = loadFlightSummaries().filter((entry) => entry.id !== summary.id);
  entries.unshift(summary);
  saveFlightSummaries(entries);
  renderFlightSummaries();
}

function updateFlightSummary(aircraft) {
  if (!aircraft || !currentPlan) return;
  const now = Date.now();
  const previous = previousFlightSummarySample;
  const tookOff = previous?.on_ground === true && aircraft.on_ground === false;
  const landed = previous?.on_ground === false && aircraft.on_ground === true;

  if (!activeFlightSummary && (tookOff || aircraft.on_ground === false)) {
    const startedAt = new Date(now).toISOString();
    activeFlightSummary = {
      id: `${flightSummaryPlanKey(currentPlan)}:${now}`,
      plan_key: flightSummaryPlanKey(currentPlan),
      departure: currentPlan.departure?.icao || "----",
      arrival: currentPlan.arrival?.icao || "----",
      callsign: currentPlan.callsign || "",
      started_at: startedAt,
      ended_at: startedAt,
      duration_seconds: 0,
      distance_nm: 0,
      max_altitude_ft: Math.max(0, finiteOr(aircraft.altitude_ft, 0)),
      last_position: aircraft,
      last_sampled_at: startedAt,
    };
    lastFlightSummaryAt = 0;
  }

  const due = now - lastFlightSummaryAt >= FLIGHT_SUMMARY_INTERVAL_MS;
  if (activeFlightSummary && (due || landed)) {
    const sampledAt = new Date(now).toISOString();
    const previousPoint = {
      ...activeFlightSummary.last_position,
      recorded_at: activeFlightSummary.last_sampled_at,
    };
    const currentPoint = { ...aircraft, recorded_at: sampledAt };
    activeFlightSummary.distance_nm += summaryDistance([previousPoint, currentPoint]);
    activeFlightSummary.max_altitude_ft = Math.max(
      activeFlightSummary.max_altitude_ft,
      finiteOr(aircraft.altitude_ft, 0)
    );
    activeFlightSummary.ended_at = sampledAt;
    activeFlightSummary.duration_seconds = Math.max(
      0,
      (Date.parse(sampledAt) - Date.parse(activeFlightSummary.started_at)) / 1000
    );
    activeFlightSummary.last_position = aircraft;
    activeFlightSummary.last_sampled_at = sampledAt;
    lastFlightSummaryAt = now;
  }

  if (activeFlightSummary && landed) {
    const { plan_key, last_position, last_sampled_at, ...completed } = activeFlightSummary;
    storeCompletedFlightSummary(completed);
    activeFlightSummary = null;
    lastFlightSummaryAt = 0;
  }
  previousFlightSummarySample = aircraft;
}

function formatFlightSummaryDuration(seconds) {
  const totalMinutes = Math.max(0, Math.round(seconds / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? `${hours} h ${String(minutes).padStart(2, "0")}` : `${minutes} min`;
}

function renderFlightSummaries() {
  const container = $("flight-summary-list");
  if (!container) return;
  container.innerHTML = "";
  const entries = loadFlightSummaries();
  const purge = $("flight-summary-purge");
  if (purge) purge.disabled = entries.length === 0;
  if (!entries.length) {
    container.append(el("p", "flight-summary-empty", "Aucun vol terminé pour le moment."));
    return;
  }

  for (const entry of entries) {
    const row = el("article", "flight-summary-row");
    const heading = el("div", "flight-summary-heading");
    heading.append(
      el("strong", null, `${entry.departure} → ${entry.arrival}`),
      el(
        "span",
        null,
        [entry.callsign, entry.ended_at ? new Date(entry.ended_at).toLocaleString() : ""]
          .filter(Boolean)
          .join(" · ")
      )
    );
    const metrics = el("div", "flight-summary-metrics");
    for (const [label, value] of [
      ["Durée", formatFlightSummaryDuration(entry.duration_seconds || 0)],
      ["Distance", `${finiteOr(entry.distance_nm, 0).toFixed(1)} NM`],
      ["Altitude max.", `${Math.round(finiteOr(entry.max_altitude_ft, 0))} ft`],
    ]) {
      const metric = el("span");
      metric.append(el("small", null, label), el("b", null, value));
      metrics.append(metric);
    }
    row.append(heading, metrics);
    container.append(row);
  }
}

function liveValue(id, value, status = "") {
  const node = $(id);
  if (!node) return;
  node.textContent = value;
  node.closest(".flight-live-stat")?.setAttribute("data-status", status);
}

/* ------------------------------------------------- rendu de la configuration */

function describeGear(configuration, capabilities) {
  if (capabilities && !capabilities.retractable_gear) {
    return { text: t("cfg_gear_fixed"), status: "" };
  }
  const extended = finiteOr(configuration.gear_extended_pct);
  if (extended === null) return { text: "—", status: "" };
  if (extended >= 99) return { text: t("cfg_gear_down"), status: "good" };
  if (extended <= 1) return { text: t("cfg_gear_up"), status: "" };
  return { text: t("cfg_gear_transit"), status: "warning" };
}

function flapDetentLabels(aircraft, plan, positions) {
  const identity = [
    aircraft?.title,
    plan?.aircraft,
    plan?.aircraft_name,
  ].filter(Boolean).join(" ").toUpperCase();

  // SimConnect expose un index et un nombre de positions, mais pas le nom
  // inscrit à côté de chaque cran. Les profils connus ne sont appliqués que
  // lorsque le nombre de positions déclaré par l'avion correspond.
  const isAirbus = (
    identity.includes("AIRBUS")
    || /\bA(?:19|20|21|30|31|32|33|34|35|38)[A-Z0-9]*\b/.test(identity)
  );
  // Les avions Airbus exposent souvent deux états SimConnect pour le même
  // cran physique 1 : configuration 1 en vol et 1+F au sol. L'interface doit
  // afficher la position de la manette, pas le sous-état aérodynamique.
  if (isAirbus && positions >= 5) {
    return ["UP", "1", "1", "2", "3", "FULL"];
  }

  const isBoeing737 = (
    identity.includes("BOEING 737")
    || /\b(?:B73[3-9]|B3[789]M)\b/.test(identity)
  );
  if (isBoeing737 && positions === 9) {
    return ["UP", "1", "2", "5", "10", "15", "25", "30", "40"];
  }

  const isBoeing747 = (
    identity.includes("BOEING 747")
    || /\bB74[1-8]\b/.test(identity)
  );
  if (isBoeing747 && positions === 7) {
    return ["UP", "1", "5", "10", "20", "25", "30"];
  }

  const isOtherBoeingWidebody = (
    identity.includes("BOEING 757")
    || identity.includes("BOEING 767")
    || identity.includes("BOEING 777")
    || identity.includes("BOEING 787")
    || /\bB(?:75[2-3]|76[2-4]|77[A-Z0-9]|78[A-Z0-9])\b/.test(identity)
  );
  if (isOtherBoeingWidebody && positions === 7) {
    return ["UP", "1", "5", "15", "20", "25", "30"];
  }

  return null;
}

function describeFlaps(configuration, capabilities, aircraft, plan) {
  if (capabilities && !capabilities.flaps) {
    return { text: t("cfg_none"), status: "" };
  }
  const index = finiteOr(configuration.flaps_handle_index);
  if (index === null) return { text: "—", status: "" };
  const positions = finiteOr(capabilities?.flap_positions, 0);
  // MSFS compte la position lisse : quatre crans utiles sur cinq positions.
  const steps = positions > 1 ? positions - 1 : 0;
  if (index === 0) return { text: t("cfg_flaps_up"), status: "" };
  const detents = flapDetentLabels(aircraft, plan, positions);
  const extended = finiteOr(configuration.flaps_extended_pct);
  // Certains Airbus annoncent FULL sur le dernier index déclaré (4), d'autres
  // sur un index supplémentaire (5). L'extension réelle lève l'ambiguïté.
  const detent = (
    detents && extended !== null && extended >= 98
      ? "FULL"
      : detents?.[Math.round(index)]
  );
  return {
    text: detent || (
      extended !== null
        ? `${Math.round(extended)} %`
        : (steps ? `${index} / ${steps}` : String(index))
    ),
    status: "good",
  };
}

function describeSpoilers(configuration, capabilities) {
  const handle = finiteOr(configuration.spoilers_handle_pct);
  if (configuration.spoilers_armed === true) {
    return { text: t("cfg_spoilers_armed"), status: "good" };
  }
  if (handle !== null && handle > 5) {
    return { text: `${Math.round(handle)} %`, status: "warning" };
  }
  if (capabilities && !capabilities.spoilers) {
    return { text: t("cfg_none"), status: "" };
  }
  if (handle === null) return { text: "—", status: "" };
  return { text: t("cfg_spoilers_retracted"), status: "" };
}

function describeParkingBrake(configuration) {
  if (configuration.parking_brake === null || configuration.parking_brake === undefined) {
    return { text: "—", status: "" };
  }
  return configuration.parking_brake
    ? { text: t("cfg_brake_set"), status: "warning" }
    : { text: t("cfg_brake_released"), status: "good" };
}

function describeAltimeter(configuration) {
  const setting = finiteOr(configuration.altimeter_hpa);
  if (setting === null) return { text: "—", status: "" };
  const standard = Math.abs(setting - STD_PRESSURE_HPA) <= 0.5;
  return {
    text: standard ? "STD · 1013 hPa" : `QNH ${Math.round(setting)} hPa`,
    status: "",
  };
}

/*
 * Tous les avions ne câblent pas « AUTOPILOT MASTER » : un A320 modifié
 * annonce NAV tenu alors que le maître reste à faux. Les modes sont donc lus
 * un par un, sans exiger le maître au préalable.
 */
function describeAutopilot(configuration) {
  const modes = [];
  if (configuration.autopilot_master) modes.push("AP");
  if (configuration.autothrottle_active) modes.push("A/THR");
  if (configuration.autopilot_nav_lock) modes.push("NAV");
  if (configuration.autopilot_approach_hold) modes.push("APPR");
  if (configuration.autopilot_glideslope_hold) modes.push("G/S");
  if (!modes.length) return { text: t("cfg_ap_off"), status: "" };
  return { text: modes.join(" · "), status: "good" };
}

function describeSelectedAltitude(configuration) {
  const selected = finiteOr(configuration.selected_altitude_ft);
  if (selected === null || selected <= 0) return { text: "—", status: "" };
  return { text: `${Math.round(selected)} ft`, status: "" };
}

function describeFuel(configuration, plan) {
  const onboard = finiteOr(configuration.fuel_total_kg);
  if (onboard === null) return { text: "—", status: "" };
  const reserve = reserveFuelKg(plan);
  if (reserve === null) return { text: `${Math.round(onboard)} kg`, status: "" };
  const margin = onboard - reserve;
  return {
    text: `${Math.round(onboard)} kg`,
    status: margin < 0 ? "danger" : margin < reserve * 0.25 ? "warning" : "good",
  };
}

function describeWind(configuration) {
  const direction = finiteOr(configuration.wind_direction_deg);
  const speed = finiteOr(configuration.wind_speed_kt);
  if (direction === null || speed === null) return { text: "—", status: "" };
  return {
    text: `${String(Math.round(direction)).padStart(3, "0")}° / ${Math.round(speed)} kt`,
    status: "",
  };
}

function updateLights(configuration) {
  const container = $("flight-lights");
  if (!container) return;
  container.innerHTML = "";
  const lights = configuration?.lights || {};
  for (const [key, label] of LIGHT_LABELS) {
    const state = lights[key];
    const chip = el("span", "light-chip", label);
    // L'état ne repose pas sur la seule couleur : le texte reste lisible et
    // l'attribut est exposé aux lecteurs d'écran.
    chip.dataset.state = state === true ? "on" : state === false ? "off" : "unknown";
    chip.setAttribute(
      "aria-label",
      `${label} · ${t(state === true ? "cfg_light_on" : state === false ? "cfg_light_off" : "cfg_unknown")}`
    );
    container.append(chip);
  }
}

function updateConfigurationBlock(aircraft) {
  const section = $("flight-config");
  if (!section) return;
  const configuration = aircraft?.configuration || null;
  const capabilities = configuration?.capabilities || null;

  const unavailable = $("flight-config-unavailable");
  show(unavailable, !configuration);
  show($("flight-config-body"), Boolean(configuration));
  if (!configuration) return;

  const entries = [
    ["flight-cfg-gear", describeGear(configuration, capabilities)],
    [
      "flight-cfg-flaps",
      describeFlaps(configuration, capabilities, aircraft, currentPlan),
    ],
    ["flight-cfg-spoilers", describeSpoilers(configuration, capabilities)],
    ["flight-cfg-brake", describeParkingBrake(configuration)],
    ["flight-cfg-altimeter", describeAltimeter(configuration)],
    ["flight-cfg-autopilot", describeAutopilot(configuration)],
    ["flight-cfg-selected", describeSelectedAltitude(configuration)],
    ["flight-cfg-fuel", describeFuel(configuration, currentPlan)],
    ["flight-cfg-wind", describeWind(configuration)],
  ];
  for (const [id, description] of entries) {
    liveValue(id, description.text, description.status);
  }
  updateLights(configuration);
}

/* -------------------------------------------------------- rendu des alarmes */

function updateGlobalFlightAlert(active) {
  const warning = $("global-flight-alert");
  if (!warning) return;
  warning.innerHTML = "";
  if (!active.length) {
    show(warning, false);
    return;
  }

  const first = active[0];
  const master = t(first.severity === "danger" ? "master_warning" : "master_caution");
  const remaining = active.length > 1 ? ` · +${active.length - 1}` : "";
  warning.dataset.severity = first.severity;
  warning.append(el("span", "global-flight-alert-mark", "!"));
  const body = el("span", "global-flight-alert-body");
  body.append(el("strong", null, master));
  body.append(el("span", null, `${first.label}${remaining}`));
  warning.append(body);
  warning.setAttribute(
    "aria-label",
    `${master}. ${first.label}. ${t("tab_flight")}`
  );
  show(warning, true);
}

function updateAlertsDisplay(context) {
  const banner = $("flight-alerts");
  const master = $("flight-alert-master");
  if (!banner || !master) return;

  banner.innerHTML = "";
  const inhibition = alertsInhibition(context);
  if (inhibition) {
    resetAlertStates();
    updateGlobalFlightAlert([]);
    master.dataset.severity = "none";
    master.textContent = inhibition.detail
      ? `${t(inhibition.key)} ${inhibition.detail}`
      : t(inhibition.key);
    return;
  }

  const active = commitAlerts(
    evaluateAlerts(context),
    context.phase,
    performance.now()
  );

  if (!active.length) {
    updateGlobalFlightAlert([]);
    master.dataset.severity = "ok";
    master.textContent = t("alerts_none");
    return;
  }

  master.dataset.severity = active[0].severity;
  master.textContent = `${t(
    active[0].severity === "danger" ? "master_warning" : "master_caution"
  )} · ${active.length}`;
  updateGlobalFlightAlert(active);

  for (const alert of active.slice(0, ALERT_BANNER_MAX)) {
    const row = el("button", "flight-alert");
    row.type = "button";
    row.dataset.severity = alert.severity;
    row.title = t("alerts_ack_hint");
    row.append(el("span", "flight-alert-mark", alert.severity === "info" ? "i" : "!"));
    const body = el("span", "flight-alert-body");
    body.append(el("span", "flight-alert-label", alert.label));
    const action = alert.detail ? `${alert.action} · ${alert.detail}` : alert.action;
    body.append(el("span", "flight-alert-action", action));
    row.append(body);
    row.addEventListener("click", () => {
      acknowledgeAlert(alert.id);
      updateAlertsDisplay(context);
    });
    banner.append(row);
  }

  if (active.length > ALERT_BANNER_MAX) {
    banner.append(
      el("div", "flight-alert-more", `+${active.length - ALERT_BANNER_MAX}`)
    );
  }
}

function updateFlightPanel(aircraft) {
  const projection = projectAircraftOnFlightPath(aircraft);
  const phase = detectFlightPhase(aircraft, projection);
  const constraint = nextFlightConstraint(currentPlan, projection, aircraft || {});
  const descent = descentGuidance(currentPlan, aircraft, projection);

  updateConfigurationBlock(aircraft);
  updateAlertsDisplay(flightContext(aircraft, projection, phase, constraint));

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

function buildConfigurationSection() {
  const section = el("section", "flight-config");
  section.id = "flight-config";

  const head = el("div", "flight-config-head");
  const heading = el("div");
  heading.append(el("div", "card-kicker", t("cfg_kicker")));
  heading.append(el("h2", null, t("cfg_title")));
  head.append(heading);

  const switchLabel = el("label", "switch");
  const input = el("input");
  input.type = "checkbox";
  input.id = "flight-alerts-toggle";
  input.checked = alertsEnabled;
  input.addEventListener("change", () => {
    alertsEnabled = input.checked;
    localStorage.setItem(ALERTS_STORAGE_KEY, alertsEnabled ? "1" : "0");
    resetAlertStates();
    if (latestAircraft) updateFlightPanel(latestAircraft);
  });
  switchLabel.append(input);
  // La case elle-même est masquée : le rail et le curseur portent le rendu.
  const track = el("span", "switch-track");
  track.append(el("span", "switch-thumb"));
  switchLabel.append(track);
  switchLabel.append(el("span", "switch-label", t("alerts_toggle")));
  switchLabel.title = t("alerts_toggle_title");
  head.append(switchLabel);
  section.append(head);

  const unavailable = el("p", "flight-config-empty", t("alerts_no_data"));
  unavailable.id = "flight-config-unavailable";
  section.append(unavailable);

  const body = el("div");
  body.id = "flight-config-body";
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
  item(t("cfg_gear"), "flight-cfg-gear");
  item(t("cfg_flaps"), "flight-cfg-flaps");
  item(t("cfg_spoilers"), "flight-cfg-spoilers");
  item(t("cfg_brake"), "flight-cfg-brake");
  item(t("cfg_altimeter"), "flight-cfg-altimeter");
  item(t("cfg_autopilot"), "flight-cfg-autopilot");
  item(t("cfg_selected_altitude"), "flight-cfg-selected", t("cfg_selected_note"));
  item(t("cfg_fuel"), "flight-cfg-fuel", t("cfg_fuel_note"));
  item(t("cfg_wind"), "flight-cfg-wind", t("cfg_wind_note"));
  body.append(grid);

  const lightsBlock = el("div", "flight-lights-block");
  lightsBlock.append(el("div", "stat-label", t("cfg_lights")));
  const lights = el("div", "flight-lights");
  lights.id = "flight-lights";
  lightsBlock.append(lights);
  body.append(lightsBlock);

  section.append(body);
  return section;
}

function renderFlightPanel(plan) {
  migrateDetailedFlightLogs();
  if (activeFlightSummary?.plan_key !== flightSummaryPlanKey(plan)) {
    activeFlightSummary = null;
    previousFlightSummarySample = null;
    lastFlightSummaryAt = 0;
  }
  resetAlertStates();
  const panel = $("panel-flight");
  panel.innerHTML = "";
  const header = el("div", "flight-panel-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Guidage et progression"));
  title.append(el("h2", null, "Suivi du vol en temps réel"));
  header.append(title);
  const pills = el("div", "flight-panel-pills");
  const master = el("span", "flight-alert-pill", t("alerts_none"));
  master.id = "flight-alert-master";
  master.dataset.severity = "none";
  pills.append(master);
  const phase = el("span", "flight-phase-pill", "Hors connexion");
  phase.id = "flight-phase";
  pills.append(phase);
  header.append(pills);
  panel.append(header);

  const alerts = el("div", "flight-alerts");
  alerts.id = "flight-alerts";
  alerts.setAttribute("role", "status");
  alerts.setAttribute("aria-live", "polite");
  panel.append(alerts);

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

  panel.append(buildConfigurationSection());

  const journal = el("section", "flight-summary");
  const journalHead = el("div", "flight-summary-head");
  const journalTitle = el("div");
  journalTitle.append(el("div", "card-kicker", "Journal local"));
  journalTitle.append(el("h2", null, "Résumé des vols effectués"));
  const purge = el("button", "icon-btn", "Purger l’historique des vols");
  purge.id = "flight-summary-purge";
  purge.type = "button";
  purge.addEventListener("click", () => {
    if (!window.confirm("Supprimer définitivement tous les résumés de vol locaux ?")) return;
    purgeFlightHistory();
  });
  journalHead.append(journalTitle, purge);
  journal.append(journalHead);
  journal.append(el(
    "p",
    "flight-summary-note",
    "Seuls la durée, la distance et l’altitude maximale des vols terminés sont conservés."
  ));
  const summaryList = el("div", "flight-summary-list");
  summaryList.id = "flight-summary-list";
  journal.append(summaryList);
  panel.append(journal);
  renderFlightSummaries();
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

function aircraftFmsProfile(plan) {
  const code = String(plan.aircraft || "").trim().toUpperCase();
  const name = String(plan.aircraft_name || "").trim();
  if (
    /^(?:A30[06B]|A31[089]|A32[01]|A20N|A21N|A33[23789]|A34[2356]|A35[9K]|A388|BCS[13])$/.test(code)
    || /airbus/i.test(name)
  ) {
    return {
      kind: "airbus",
      label: "MCDU",
      init: "INIT A",
      weights: "INIT B",
      route: "F-PLN › EN ROUTE · VIA / TO",
      departure: "F-PLN › DEPARTURE",
      arrival: "F-PLN › ARRIVAL",
      radio: "RAD NAV",
      flightNumber: "FLT NBR",
      approachTransition: "VIA",
      starTransition: "TRANS",
    };
  }
  if (/^B(?:7[0-9A-Z]{2}|3[7-9X][0-9A-Z])$/.test(code) || /boeing/i.test(name)) {
    return {
      kind: "boeing",
      label: "CDU",
      init: "RTE 1",
      weights: "PERF INIT",
      route: "RTE · VIA / TO",
      departure: "DEP/ARR › DEPARTURE",
      arrival: "DEP/ARR › ARRIVAL",
      radio: "NAV RADIO",
      flightNumber: "FLT NO",
      approachTransition: "APPR TRANS",
      starTransition: "STAR TRANS",
    };
  }
  return {
    kind: "generic",
    label: "FMS",
    init: "FLIGHT PLAN",
    weights: "FLIGHT DATA",
    route: "ROUTE · VIA / TO",
    departure: "PROCEDURES › DEPARTURE",
    arrival: "PROCEDURES › ARRIVAL",
    radio: "RADIO NAV",
    flightNumber: "FLIGHT",
    approachTransition: "APPR TRANS",
    starTransition: "STAR TRANS",
  };
}

function renderMcdu(plan) {
  const panel = $("panel-mcdu");
  panel.innerHTML = "";
  const minima = loadMinima(plan);
  const profile = aircraftFmsProfile(plan);
  panel.append(siaApproachCard(plan));
  panel.append(minimaEditor(plan, minima));
  const profileHeader = el("div", "mcdu-profile");
  profileHeader.append(
    el("div", "card-kicker", `Fiche ${profile.label}`),
    el("h2", null, plan.aircraft_name || plan.aircraft || "Type d’avion inconnu"),
    el(
      "p",
      null,
      profile.kind === "generic"
        ? "Présentation FMS générique : vérifiez les libellés propres à l’avion."
        : `Présentation adaptée au système ${profile.label} de cet avion.`
    )
  );
  panel.append(profileHeader);
  const screen = el("div", "mcdu");
  const d = plan.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb" }[d.units] || d.units || "";
  const dep = plan.departure;
  const arr = plan.arrival;

  const pages = [
    mcduPage(profile.init, [
      mcduLine("FROM/TO", `${dep?.icao || "----"}/${arr?.icao || "----"}`),
      plan.alternate_icao && mcduLine("ALTN", plan.alternate_icao),
      plan.callsign && mcduLine(profile.flightNumber, plan.callsign),
      d.cost_index && mcduLine("COST INDEX", d.cost_index),
      plan.enroute.cruise_altitude_ft &&
        mcduLine("CRZ FL", `FL${Math.round(plan.enroute.cruise_altitude_ft / 100)}`),
    ]),
    mcduPage(profile.weights, [
      d.zfw && mcduLine("ZFW", kg(d.zfw, unit)),
      d.block_fuel && mcduLine("BLOCK", kg(d.block_fuel, unit)),
      d.taxi_fuel && mcduLine("TAXI", kg(d.taxi_fuel, unit)),
      d.trip_fuel && mcduLine("TRIP", kg(d.trip_fuel, unit)),
      d.reserve_fuel && mcduLine("RSV", kg(d.reserve_fuel, unit)),
      d.alternate_fuel && mcduLine("ALTN", kg(d.alternate_fuel, unit)),
    ]),
    dep &&
      mcduPage(profile.departure, [
        dep.runway && mcduLine("RWY", dep.runway.value || "—", null, needsCheck(dep.runway)),
        mcduLine("SID", dep.sid.value || "—", null, needsCheck(dep.sid)),
        mcduLine("TRANS", dep.sid_transition.value || "—", "sortie de la SID", needsCheck(dep.sid_transition)),
        dep.transition_altitude_ft && mcduLine("TRANS ALT", String(dep.transition_altitude_ft)),
      ]),
    plan.enroute.route_legs?.length &&
      mcduPage(profile.route, [
        ...plan.enroute.route_legs.map((leg) =>
          mcduLine(leg.via || "DCT", leg.to, leg.stage || null)
        ),
      ]),
    arr &&
      mcduPage(profile.arrival, [
        arr.runway && mcduLine("RWY", arr.runway.value || "—", null, needsCheck(arr.runway)),
        mcduLine("APPR", arr.approach.value || "—", null, needsCheck(arr.approach)),
        mcduLine(profile.approachTransition, arr.approach_transition.value || "—", "transition d'APPROCHE", needsCheck(arr.approach_transition)),
        mcduLine("STAR", arr.star.value || "—", null, needsCheck(arr.star)),
        mcduLine(profile.starTransition, arr.star_transition.value || "—", "entrée de STAR", needsCheck(arr.star_transition)),
        arr.transition_level_ft && mcduLine("TRANS LVL", String(arr.transition_level_ft)),
        arr.missed_approach_altitude_ft &&
          mcduLine("GA ALT", `${arr.missed_approach_altitude_ft} ft`, "remise de gaz"),
      ]),
    arr?.ils_frequency_mhz &&
      mcduPage(profile.radio, [
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
    syncMapTrail();
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

function applyMapPreferences(values) {
  MAP.configure({
    basemap: values?.map_basemap || "osm",
    trailColor: values?.map_trail_color || "#22d3ee",
  });
}

/**
 * Mémorise le fond choisi depuis la barre carte.
 *
 * Le PUT attend l'ensemble des réglages : on relit donc les valeurs courantes
 * avant de n'y remplacer que le fond. Un client distant n'écrit rien.
 */
async function persistBasemap(key) {
  if (latestStatus?.remote_client) return;
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) return;
    const values = await response.json();
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...values, map_basemap: key }),
    });
  } catch (error) {
    // Le fond reste appliqué à l'écran même si l'enregistrement échoue.
  }
}

async function loadMapPreferences(status = latestStatus) {
  if (status?.remote_client) {
    applyMapPreferences(status);
    return;
  }
  const response = await fetch("/api/settings");
  if (!response.ok) return;
  applyMapPreferences(await response.json());
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

function applyAircraftState(aircraft) {
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
  recordCurrentFlightTrail(aircraft);
  updateFlightSummary(aircraft);
}

async function pollLive() {
  if (!currentChart) return;

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
    applyAircraftState(aircraft);
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
  if (name === "map") window.requestAnimationFrame(() => MAP.resize());
}

function openActiveAlerts() {
  selectTab("flight");
  window.requestAnimationFrame(() => {
    const target = document.querySelector("#flight-alerts .flight-alert")
      || $("flight-alert-master");
    target?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto"
        : "smooth",
      block: "center",
    });
    if (target?.matches("button")) target.focus({ preventScroll: true });
  });
}

/* ------------------------------------------------------------------- init */

document.querySelector(".tabs").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-tab]");
  if (button) selectTab(button.dataset.tab);
});

$("refresh").addEventListener("click", buildPlan);
$("simbrief-create").addEventListener("click", openSimBriefPlanner);
$("support-open").addEventListener("click", openSupportPage);
$("demo-toggle").addEventListener("change", buildPlan);

$("map-fit").addEventListener("click", () => MAP.fit());
$("map-zoom-in").addEventListener("click", () => MAP.zoomIn());
$("map-zoom-out").addEventListener("click", () => MAP.zoomOut());
$("map-follow").addEventListener("click", () => MAP.toggleFollow());
$("map-basemap").addEventListener("click", () => MAP.toggleBasemap());
$("map-basemap-style").addEventListener("change", (event) => {
  const applied = MAP.setBasemap(event.target.value);
  $("settings-basemap").value = applied;
  persistBasemap(applied);
});
$("map-sia").addEventListener("click", () => toggleSiaMapOverlay());
$("sia-overlay-close").addEventListener("click", () => toggleSiaMapOverlay(false));
$("sia-opacity").addEventListener("input", (event) => {
  $("sia-map-frame").style.opacity = String(Number(event.target.value) / 100);
});
$("map-route").addEventListener("click", () => MAP.fitRoute());
$("settings-open").addEventListener("click", openSettings);
$("update-install").addEventListener("click", handleUpdateButton);
$("settings-close").addEventListener("click", () => $("settings-dialog").close());
$("settings-cancel").addEventListener("click", () => $("settings-dialog").close());
$("settings-form").addEventListener("submit", saveSettings);
$("settings-language").addEventListener("change", (event) => {
  window.I18N.setLanguage(event.target.value);
});
$("settings-trail-color").addEventListener("input", (event) => {
  setTrailColorField(event.target.value);
});
$("welcome-form").addEventListener("submit", submitWelcome);
$("welcome-demo").addEventListener("click", skipWelcomeWithDemo);
// Le premier lancement ne se contourne ni par Échap ni par un clic extérieur.
$("welcome-dialog").addEventListener("cancel", (event) => event.preventDefault());
$("welcome-language").addEventListener("change", (event) => {
  window.I18N.setLanguage(event.target.value);
});
for (const id of ["welcome-pilot-id", "welcome-username"]) {
  $(id).addEventListener("input", refreshWelcomeSubmit);
}
$("settings-lan-enabled").addEventListener("change", (event) => {
  show($("settings-lan-access"), event.target.checked);
});
$("settings-lan-copy").addEventListener("click", async () => {
  const value = $("settings-lan-url").value;
  if (!value) return;
  await navigator.clipboard.writeText(value);
  $("settings-message").textContent = t("lan_url_copied");
});
$("shutdown").addEventListener("click", shutdownApplication);
$("sim-status").addEventListener("click", pollSimulatorStatus);
$("terminal-toggle").addEventListener("click", toggleTerminal);
$("global-flight-alert").addEventListener("click", openActiveAlerts);

const storedTerminalState = localStorage.getItem(TERMINAL_COLLAPSED_KEY);
setTerminalCollapsed(
  storedTerminalState === null
    ? window.matchMedia("(max-width: 760px)").matches
    : storedTerminalState === "true"
);
window.I18N.apply();

window.addEventListener("navixav:languagechange", () => {
  setTerminalCollapsed(localStorage.getItem(TERMINAL_COLLAPSED_KEY) === "true");
  if (currentPlan) renderPlan(currentPlan);
  loadStatus().catch(() => {});
  pollSimulatorStatus();
  refreshUpdateButtonText();
});

pollSimulatorStatus();
simulatorTimer = setInterval(pollSimulatorStatus, 2500);

async function initialiseApplication() {
  try {
    $("demo-toggle").checked = false;
    const status = await loadStatus();
    await loadMapPreferences(status);
    if (needsOnboarding(status)) {
      openWelcome(status);
      return;
    }
    if (status.remote_client) {
      await loadCurrentPlan();
    } else {
      checkForUpdates();
      if (status.simbrief_configured) await buildPlan();
    }
  } catch (error) {
    showBanner("error", "Initialisation impossible", [String(error)]);
  }
}

initialiseApplication();
