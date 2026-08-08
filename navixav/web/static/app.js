"use strict";

const $ = (id) => document.getElementById(id);
const t = (key) => window.I18N.t(key);
const displayLocale = () => window.I18N.getLanguage();
const tf = (key, values = {}) => Object.entries(values).reduce(
  (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
  t(key)
);
/* Libellés que le service compose en français, traduits à l'affichage. */
const constraintText = (value) => window.I18N.constraintText(value);
const groundLabel = (value) => window.I18N.groundLabel(value);
const chartCategory = (value) => window.I18N.chartCategory(value);

/** Localises explanations produced by the planner while preserving identifiers. */
function plannerText(value) {
  const text = String(value || "");
  if (!text || displayLocale() === "fr") return text;
  const exact = new Map([
    ["piste planifiée par SimBrief", t("reason_runway_simbrief")],
    ["SID donnée par SimBrief et validée en base", t("reason_sid_simbrief_validated")],
    ["STAR donnée par SimBrief et validée en base", t("reason_star_simbrief_validated")],
    ["et confirmée par le vent", t("reason_wind_confirmed")],
    ["point d'entrée de la STAR", t("reason_star_entry")],
    ["enchaîne avec la route", t("reason_star_route")],
    ["RNP requis, avion qualifié", t("reason_rnp_qualified")],
    ["transition la plus proche de la fin de la STAR", t("reason_transition_nearest_star")],
    ["transition imposée", t("reason_transition_forced")],
    ["piste imposée", t("source_forced")],
    ["approche imposée", t("source_forced")],
    ["SID imposée", t("source_forced")],
    ["STAR imposée", t("source_forced")],
    ["forcée, non vérifiée", "user-selected, not verified"],
    ["aucune SID en base", "no SID in the database"],
    ["aucune STAR en base", "no STAR in the database"],
    ["aucune approche en base", "no approach in the database"],
    ["transition partant du point de sortie de la STAR", "transition starting at the STAR exit point"],
    ["aucune transition publiée : guidage radar attendu", "no published transition: radar vectors expected"],
    ["première transition publiée, aucun lien avec la STAR", "first published transition, no connection with the STAR"],
    ["première transition publiée, aucun lien avec la route", "first published transition, no connection with the route"],
    ["aucune STAR retenue", "no STAR selected"],
    ["aucune SID retenue", "no SID selected"],
    ["publiée pour une autre piste", "published for another runway"],
    ["transition rejoignant le premier point en route", "transition connecting to the first en-route waypoint"],
    ["transition la plus proche du premier point en route", "transition nearest to the first en-route waypoint"],
    ["transition partant du dernier point en route", "transition starting at the last en-route waypoint"],
    ["transition la plus proche du dernier point en route", "transition nearest to the last en-route waypoint"],
    ["première transition publiée", "first published transition"],
    ["point de sortie de la SID", "SID exit point"],
    ["SID sans point de sortie identifiable", "SID with no identifiable exit point"],
    ["STAR sans point d'entrée", "STAR with no entry point"],
    ["rejoint la route", "connects with the route"],
    ["variante guidage radar (entrée sur repère d'interception)", "radar-vector variant (entry at the intercept fix)"],
    ["vent indisponible : piste la plus longue retenue", "wind unavailable: longest runway selected"],
    ["aucun lien avec le premier point en route", "no connection with the first en-route waypoint"],
    ["aucun lien avec le dernier point en route", "no connection with the last en-route waypoint"],
  ]);
  return text.split(" ; ").map((part) => {
    if (exact.has(part)) return exact.get(part);
    let match = part.match(/^type (.+) selon la préférence$/);
    if (match) return tf("reason_approach_type", { type: match[1] });
    match = part.match(/^(.+) à ([\d,.]+) NM de (.+)$/);
    if (match) return tf("reason_fix_distance", { fix: match[1], distance: match[2], target: match[3] });
    match = part.match(/^(sortie|entrée) sur (.+)$/);
    if (match) return `${match[1] === "sortie" ? "exit" : "entry"} at ${match[2]}`;
    match = part.match(/^aucune (SID|STAR) publiée pour la piste (.+)$/);
    if (match) return `no ${match[1]} published for runway ${match[2]}`;
    match = part.match(/^transition publiée (vers|depuis) (.+)$/);
    if (match) return `published transition ${match[1] === "vers" ? "to" : "from"} ${match[2]}`;
    match = part.match(/^choix serré entre (.+) et (.+)$/);
    if (match) return `close choice between ${match[1]} and ${match[2]}`;
    match = part.match(/^meilleure composante de vent de face \(([+-]?\d+) kt, traversier (\d+) kt\)$/);
    if (match) return `best headwind component (${match[1]} kt, crosswind ${match[2]} kt)`;
    match = part.match(/^écartées faute de qualification RNP : (.+)$/);
    if (match) return `excluded because the aircraft is not RNP-qualified: ${match[1]}`;
    match = part.match(/^configuration préférentielle(?: \((.+)\))?$/);
    if (match) return `preferred configuration${match[1] ? ` (${match[1]})` : ""}`;
    match = part.match(/^piste planifiée par SimBrief( et confirmée par le vent)?$/);
    if (match) return [t("reason_runway_simbrief"), match[1] ? t("reason_wind_confirmed") : ""].filter(Boolean).join(" ");
    return part;
  }).join("; ");
}

function warningText(value) {
  const text = String(value || "");
  if (!text || displayLocale() === "fr") return text;
  const rules = [
    [/^(.+) absent de la base de navigation\.$/, "$1 is missing from the navigation database."],
    [/^Aucune piste de départ déterminable à (.+)\.$/, "No departure runway can be determined at $1."],
    [/^Aucune piste d'arrivée déterminable à (.+)\.$/, "No arrival runway can be determined at $1."],
    [/^Aucune SID publiée pour (.+) dans la base\.$/, "No SID is published for $1 in the database."],
    [/^Aucune STAR publiée pour (.+) dans la base\.$/, "No STAR is published for $1 in the database."],
    [/^Aucune procédure d'approche publiée pour (.+)\.$/, "No approach procedure is published for $1."],
    [/^Aucune STAR n'est publiée pour la piste (.+) ; arrivée directe vers l'approche\.$/, "No STAR is published for runway $1; direct arrival to the approach."],
    [/^Aucune SID n'est publiée pour la piste (.+) ; départ en guidage radar\.$/, "No SID is published for runway $1; radar-vectored departure."],
    [/^La STAR « (.+) » n'est pas publiée pour la piste (.+) : elle mène à l'IAF d'une autre piste\.$/, "STAR “$1” is not published for runway $2: it leads to another runway’s IAF."],
    [/^La SID « (.+) » n'est pas publiée pour la piste (.+) : elle part d'un autre seuil\.$/, "SID “$1” is not published for runway $2: it starts from another threshold."],
    [/^La STAR (.+) se termine sur (.+), qui n'ouvre aucune approche de la piste (.+) : prévoir un guidage radar vers l'axe\.$/, "STAR $1 ends at $2, which starts no approach for runway $3: expect radar vectors to the final course."],
    [/^(SID|STAR) forcée « (.+) » introuvable en base\.$/, "User-selected $1 “$2” was not found in the database."],
    [/^La (SID|STAR) SimBrief « (.+) » n'est pas publiée pour la piste (.+)\.$/, "SimBrief $1 “$2” is not published for runway $3."],
    [/^Aucune approche publiée pour la piste (.+)\.$/, "No approach is published for runway $1."],
    [/^Approche forcée « (.+) » introuvable\.$/, "User-selected approach “$1” was not found."],
    [/^Piste forcée « (.+) » inconnue à (.+)\.$/, "User-selected runway “$1” is unknown at $2."],
    [/^Piste SimBrief « (.+) » inconnue à (.+)\.$/, "SimBrief runway “$1” is unknown at $2."],
    [/^(.+) : la piste (.+) prévue par SimBrief est hors limites \((.+)\)\.$/, "$1: runway $2 planned by SimBrief is outside the configured limits ($3)."],
    [/^METAR indisponible pour (.+) ; repli sur l'OFP SimBrief\.$/, "METAR unavailable for $1; using the SimBrief OFP instead."],
    [/^Aucun METAR pour (.+) : sélection de piste dégradée\.$/, "No METAR for $1: runway selection has reduced confidence."],
    [/^Cycles AIRAC différents : SimBrief (.+) contre navdata locale (.+)\. Une procédure peut avoir changé de nom ou disparu\.$/, "AIRAC cycle mismatch: SimBrief $1 versus local navdata $2. A procedure may have been renamed or removed."],
  ];
  for (const [pattern, replacement] of rules) {
    if (pattern.test(text)) return text.replace(pattern, replacement);
  }
  if (text.startsWith("L'avion est déclaré non RNP")) {
    return "The aircraft is declared non-RNP, but this airport does not publish RNP requirements. Check the approach chart.";
  }
  if (text.startsWith("Avion déclaré non RNP")) {
    return text.replace("Avion déclaré non RNP", "Aircraft declared non-RNP")
      .replace("écartée(s)", "excluded").replace("Régler", "Enable").replace("si c'est inexact", "if this is incorrect");
  }
  return plannerText(text);
}

const CONFIDENCE_CLASS = {
  "élevée": "high",
  "modérée": "medium",
  "faible": "low",
  "aucune": "none",
};

const SOURCE_LABEL = {
  simbrief: "SimBrief",
  moteur: "source_computed",
  utilisateur: "source_forced",
};

let currentPlan = null;
let plannerOverrides = {};
let currentChart = null;
let currentIcao = null;
let currentMapRole = null;
let currentTaxiPlan = null;
let currentTaxiGuidance = null;
let automaticTaxiRouteKey = null;
let automaticTaxiRoutePending = false;
let taxiRouteRevision = 0;
let taxiRouteRequestController = null;
let liveTimer = null;
let simulatorTimer = null;
let weatherTimer = null;
let weatherRefreshInFlight = false;
let weatherRefreshState = "idle";
let weatherLastUpdatedAt = null;
let activeRoutePointIndex = null;
let latestAircraft = null;
let flightGeometry = [];
let flightRouteTotalNm = 0;
let currentFlightTrail = [];
let currentFlightTrailPlanKey = "";
let lastCurrentFlightTrailAt = 0;
let flightLog = [];
let flightRecording = true;
let lastFlightLogAt = 0;
let activeFlightSummary = null;
let previousFlightSummarySample = null;
let lastFlightSummaryAt = 0;
let flightEvents = [];
let flightEventSequence = 0;
let flightEventsPlanKey = "";
let flightEventsRenderKey = "";
const flightEventStates = new Map();
const collapsedFlightEventGroups = new Set();
let dispatchLive = null;
let dispatchLiveRenderedAt = 0;
let replayTimer = null;
let replayActive = false;
let replaySpeed = 1;
let replaySourceLabel = "";
let latestStatus = null;
let currentProcedures = null;
let selectedProcedurePhase = null;
let procedureAircraftKey = "";
const siaRequests = new Map();
const officialAirportRequests = new Map();
const siaOverlayCandidates = new Map();
let siaOverlayKey = null;

const EARTH_RADIUS_M = 6378137;
const LIVE_INTERVAL_MS = 1000;
const WEATHER_REFRESH_INTERVAL_MS = 5 * 60 * 1000;
const CURRENT_FLIGHT_TRAIL_INTERVAL_MS = 5000;
const CURRENT_FLIGHT_TRAIL_MAX_POINTS = 3600;
const FLIGHT_LOG_INTERVAL_MS = 5000;
const FLIGHT_LOG_MAX_POINTS = 3600;
const FLIGHT_LOG_INDEX_KEY = "navixav-flight-log-index";
const FLIGHT_REPLAY_BASE_MS = 300;
const FLIGHT_SUMMARY_KEY = "navixav-flight-summaries";
const FLIGHT_SUMMARY_INTERVAL_MS = 5000;
const FLIGHT_SUMMARY_MAX_ENTRIES = 100;
const PROCEDURE_PROGRESS_PREFIX = "navixav-procedure-progress";
/* Chronologie du vol : un changement doit tenir avant d'entrer au journal, et
   le journal conservé avec le résumé reste court pour ne pas saturer le
   stockage local d'un pilote qui garde cent vols. */
const FLIGHT_EVENT_CONFIRM_MS = 800;
const FLIGHT_EVENT_MAX = 200;
const FLIGHT_EVENT_STORED_MAX = 60;
const DISPATCH_LIVE_KEY = "navixav-dispatch-live";
const DISPATCH_LIVE_INTERVAL_MS = 2000;
const DISPATCH_SAMPLE_INTERVAL_S = 5;
const DISPATCH_FLOW_WINDOW_S = 5 * 60;
const DISPATCH_GAP_MS = 15000;
const APP_SESSION_ID = Date.now().toString(36);
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
  const label = button.querySelector(".toolbar-label");
  const version = button.dataset.version;
  label.textContent = version
    ? `${t("update_available")} ${version}`
    : t("check_update");
  button.title = version ? t("update_title") : t("check_update_title");
}

async function checkForUpdates(manual = false) {
  const button = $("update-install");
  const label = button.querySelector(".toolbar-label");
  if (manual) {
    button.disabled = true;
    label.textContent = t("checking_update");
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
  const label = button.querySelector(".toolbar-label");
  const version = button.dataset.version || "";
  if (!window.confirm(t("update_confirm").replace("{version}", version))) return;
  button.disabled = true;
  label.textContent = t("update_downloading");
  try {
    const response = await fetch("/api/update/install", {
      method: "POST",
      headers: { "X-NaviXav-Update": "install" },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("update_failed"));
    label.textContent = t("update_restarting");
    showBanner("info", t("update_ready"), [t("update_restart_body")]);
  } catch (error) {
    button.disabled = false;
    label.textContent = `${t("update_available")} ${version}`;
    showBanner("error", t("update_failed"), [String(error)]);
  }
}

/* ------------------------------------------------------ journal des versions */

/** Journal complet, livré avec l'application et lu sans réseau.
 *
 * Le texte des puces reste celui du dépôt, en anglais : il décrit trente et une
 * versions déjà publiées, qu'aucune traduction ne réécrira. Seuls le cadre et
 * les intitulés de rubrique suivent la langue de l'interface.
 */
function changelogKindLabel(section) {
  const key = `changelog_kind_${section.kind}`;
  const label = t(key);
  return label === key ? (section.title || "") : label;
}

function changelogDate(value) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(displayLocale(), {
    year: "numeric", month: "long", day: "numeric",
  });
}

function renderChangelog(data) {
  const body = $("changelog-body");
  body.innerHTML = "";
  const releases = data?.releases || [];
  if (!releases.length) {
    body.append(el("p", "changelog-note", t("changelog_empty")));
    return;
  }
  for (const release of releases) {
    const block = el("section", "changelog-release");
    const head = el("div", "changelog-release-head");
    head.append(el("span", "changelog-version", release.version));
    if (release.date) head.append(el("span", "changelog-date", changelogDate(release.date)));
    // Repérer la version installée évite de chercher où l'on en est.
    if (release.version === data.version) {
      head.append(el("span", "badge changelog-current", t("changelog_installed")));
    }
    block.append(head);
    for (const section of release.sections || []) {
      const label = changelogKindLabel(section);
      if (label) block.append(el("div", `changelog-kind kind-${section.kind}`, label));
      const list = el("ul", "changelog-items");
      for (const item of section.items || []) list.append(el("li", null, item));
      block.append(list);
    }
    body.append(block);
  }
}

async function openChangelog() {
  const dialog = $("changelog-dialog");
  const body = $("changelog-body");
  body.innerHTML = "";
  body.append(el("p", "changelog-note", t("changelog_loading")));
  dialog.showModal();
  try {
    const data = await fetch("/api/changelog", { cache: "no-store" }).then((r) => r.json());
    renderChangelog(data);
  } catch (error) {
    body.innerHTML = "";
    body.append(el("p", "changelog-note", `${t("changelog_failed")} — ${error}`));
  }
}

async function pollSimulatorStatus() {
  const indicator = $("sim-status");
  try {
    const status = await fetch("/api/simulator", { cache: "no-store" }).then((r) => r.json());
    const paused = Boolean(status.connected && status.paused);
    indicator.classList.toggle("online", Boolean(status.connected) && !paused);
    indicator.classList.toggle("paused", paused);
    indicator.classList.toggle("offline", !status.connected);
    $("sim-status-text").textContent = paused
      ? t("sim_paused")
      : (status.connected ? t("sim_connected") : t("sim_offline"));
    indicator.title = status.connected
      ? (paused
        ? tf("sim_paused_title", { source: status.source || "SimConnect" })
        : tf("sim_connected_title", { source: status.source || "SimConnect" }))
      : (status.reason || t("sim_no_answer"));
  } catch (_error) {
    indicator.classList.remove("online", "paused");
    indicator.classList.add("offline");
    $("sim-status-text").textContent = t("server_stopped");
  }
}

async function shutdownApplication() {
  const button = $("shutdown");
  const label = button.querySelector(".toolbar-label");
  button.disabled = true;
  label.textContent = t("stopping");
  try {
    const response = await fetch("/api/shutdown", { method: "POST" });
    if (!response.ok) throw new Error(t("err_shutdown_refused"));
    clearInterval(simulatorTimer);
    document.body.innerHTML = "";
    const stopped = el("main", "empty");
    stopped.append(el("h2", null, t("stopped_title")), el("p", null, t("stopped_body")));
    document.body.append(stopped);
  } catch (error) {
    button.disabled = false;
    label.textContent = t("quit");
    showBanner("error", t("err_shutdown"), [String(error)]);
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
    if (!response.ok) throw new Error(payload.detail || t("simbrief_open_failed"));
    showBanner("info", t("simbrief_opened"), [
      t("simbrief_open_step"),
      t("simbrief_return_step"),
    ]);
  } catch (error) {
    showBanner("error", t("simbrief_open_failed"), [String(error)]);
  } finally {
    button.disabled = false;
  }
}

async function openSupportPage(event) {
  const button = event?.currentTarget || $("support-open");
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

function renderAircraftSurvey(report) {
  const covered = report.covered || [];
  const missing = report.missing || [];
  $("aircraft-covered-count").textContent = covered.length;
  $("aircraft-missing-count").textContent = missing.length;
  const renderList = (targetId, items, missingAircraft) => {
    const target = $(targetId);
    target.replaceChildren();
    if (!items.length) {
      target.append(el("p", "aircraft-survey-empty", t("aircraft_none")));
      return;
    }
    for (const aircraft of items) {
      const row = el("div", "aircraft-survey-item");
      const copy = el("span");
      copy.append(el("strong", "", aircraft.label));
      const detail = missingAircraft
        ? [aircraft.icao, aircraft.has_checklist ? t("aircraft_checklist") : t("aircraft_no_checklist")].filter(Boolean).join(" · ")
        : [aircraft.icao, aircraft.aircraft, t(`aircraft_maturity_${aircraft.maturity}`)].filter(Boolean).join(" · ");
      copy.append(el("small", "", detail));
      row.append(copy);
      if (missingAircraft) {
        const button = el("button", "icon-btn", t("aircraft_scaffold"));
        button.type = "button";
        button.addEventListener("click", () => scaffoldAircraft(aircraft, button));
        row.append(button);
      }
      target.append(row);
    }
  };
  renderList("aircraft-covered-list", covered, false);
  renderList("aircraft-missing-list", missing, true);
  const folders = report.folders || [];
  $("aircraft-survey-status").textContent = folders.length
    ? tf("aircraft_found", { count: report.total || 0 })
    : t("aircraft_folder_not_found");
  $("aircraft-survey-status").className = "aircraft-survey-status";
}

async function loadAircraftSurvey() {
  const status = $("aircraft-survey-status");
  status.textContent = t("aircraft_scanning");
  status.className = "aircraft-survey-status";
  const community = $("settings-aircraft-community").value.trim();
  try {
    const query = community ? `?community=${encodeURIComponent(community)}` : "";
    const response = await fetch(`/api/aircraft/survey${query}`);
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || t("aircraft_scan_failed"));
    if (!community && report.folders?.length) {
      $("settings-aircraft-community").placeholder = report.folders.join(" · ");
    }
    renderAircraftSurvey(report);
  } catch (error) {
    status.textContent = String(error);
    status.className = "aircraft-survey-status error";
  }
}

async function browseAircraftFolder() {
  const button = $("aircraft-folder-browse");
  button.disabled = true;
  try {
    const response = await fetch("/api/aircraft/select-folder", {
      method: "POST",
      headers: { "X-NaviXav-Aircraft": "browse" },
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || t("aircraft_browse_failed"));
    if (report.cancelled) return;
    $("settings-aircraft-community").value = report.selected_path || "";
    renderAircraftSurvey(report);
  } catch (error) {
    const status = $("aircraft-survey-status");
    status.textContent = String(error);
    status.className = "aircraft-survey-status error";
  } finally {
    button.disabled = false;
  }
}

async function scaffoldAircraft(aircraft, button) {
  button.disabled = true;
  button.textContent = t("aircraft_scaffolding");
  try {
    const response = await fetch("/api/aircraft/scaffold", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-NaviXav-Aircraft": "scaffold",
      },
      body: JSON.stringify({
        label: aircraft.label,
        package: aircraft.package,
        community_path: $("settings-aircraft-community").value.trim(),
      }),
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.detail || t("aircraft_scaffold_failed"));
    renderAircraftSurvey(report);
    $("aircraft-survey-status").textContent = tf("aircraft_scaffolded", {
      label: report.created?.label || aircraft.label,
    });
  } catch (error) {
    const status = $("aircraft-survey-status");
    status.textContent = String(error);
    status.className = "aircraft-survey-status error";
    button.disabled = false;
    button.textContent = t("aircraft_scaffold");
  }
}

async function openSettings() {
  const message = $("settings-message");
  message.textContent = "";
  message.className = "settings-message";
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) throw new Error(t("err_settings_unavailable"));
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
    $("settings-taxi-speed").value = values.taxi_speed_limit_kt;
    $("settings-taxi-turn-speed").value = values.taxi_turn_speed_limit_kt;
    $("settings-taxi-alarm").checked = values.taxi_speed_alarm_sound !== false;
    $("settings-lan-enabled").checked = Boolean(values.lan_enabled);
    $("settings-aircraft-community").value = values.aircraft_community_path || "";
    show($("settings-lan-access"), Boolean(values.lan_enabled));
    $("settings-lan-url").value = latestStatus?.lan_url || "";
    $("settings-language").value = window.I18N.getLanguage();
    $("settings-theme").value = window.THEME.getPreference();
    $("settings-dialog").showModal();
    loadAircraftSurvey();
  } catch (error) {
    showBanner("error", t("err_settings_open"), [String(error)]);
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
    taxi_speed_limit_kt: Number($("settings-taxi-speed").value),
    taxi_turn_speed_limit_kt: Number($("settings-taxi-turn-speed").value),
    taxi_speed_alarm_sound: $("settings-taxi-alarm").checked,
    aircraft_community_path: $("settings-aircraft-community").value.trim(),
    lan_enabled: $("settings-lan-enabled").checked,
  };
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || t("err_save_refused"));
    applyMapPreferences(result);
    applyTaxiSpeedPreferences(result);
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
    if (!response.ok) throw new Error(result.detail || t("err_save_refused"));
    applyMapPreferences(result);
    applyTaxiSpeedPreferences(result);
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

function resetDemoSession() {
  const planKey = flightSummaryPlanKey(currentPlan);
  currentFlightTrail = [];
  currentFlightTrailPlanKey = planKey;
  lastCurrentFlightTrailAt = 0;
  MAP.setTrail([]);
  resetFlightEvents();
  flightEventsPlanKey = planKey;
  activeFlightSummary = null;
  previousFlightSummarySample = null;
  lastFlightSummaryAt = 0;
  dispatchLive = emptyDispatchLive(planKey);
  dispatchLiveRenderedAt = 0;
  updateRouteStripProgress(null);
  renderFlightPanel(currentPlan);
}

async function restartCurrentPlanDemo() {
  if (!currentPlan) return false;
  try {
    const response = await fetch("/api/demo/restart", { method: "POST" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("demo_restart_failed"));
    resetDemoSession();
    await pollLive();
    return true;
  } catch (error) {
    $("demo-toggle").checked = false;
    showBanner("error", t("demo_restart_failed"), [String(error)]);
    return false;
  }
}

async function toggleDemoMode() {
  if ($("demo-toggle").checked) {
    if (currentPlan) await restartCurrentPlanDemo();
    else await buildPlan();
    return;
  }
  if (currentPlan?.demo && latestStatus?.simbrief_configured) {
    await buildPlan(null, false);
  } else {
    await pollLive();
  }
}

async function refreshPlanOrDemo() {
  if ($("demo-toggle").checked && currentPlan) {
    await restartCurrentPlanDemo();
    return;
  }
  await buildPlan();
}

async function buildPlan(nextOverride = null, demoOfp = null) {
  if (latestStatus?.remote_client) {
    await loadCurrentPlan();
    return;
  }

  if (nextOverride) {
    plannerOverrides = { ...plannerOverrides, ...nextOverride };
  } else {
    plannerOverrides = {};
  }

  const button = $("refresh");
  button.disabled = true;
  button.querySelector("span").textContent = t("loading_plan");
  showBanner("info", t("cache_title"), [t("cache_body")]);

  try {
    const useBundledDemo = demoOfp ?? (
      nextOverride && currentPlan ? Boolean(currentPlan.demo) : $("demo-toggle").checked
    );
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        demo: useBundledDemo,
        ...plannerOverrides,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      showBanner("error", t("err_plan_fetch"), [payload.detail]);
      return;
    }
    currentPlan = payload;
    renderPlan(payload);
  } catch (error) {
    showBanner("error", t("err_network"), [String(error)]);
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
    showBanner("error", t("err_network"), [String(error)]);
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

function procedureIdentity(data = currentProcedures) {
  const aircraft = data?.aircraft;
  if (!aircraft) return "";
  return `${aircraft.id}:${aircraft.variant || "default"}`;
}

function procedureProgressKey(data = currentProcedures) {
  const flight = currentPlan ? flightSummaryPlanKey(currentPlan) : "no-plan";
  return `${PROCEDURE_PROGRESS_PREFIX}:${flight}:${procedureIdentity(data)}`;
}

function procedureManualProgress(data = currentProcedures) {
  try {
    return JSON.parse(sessionStorage.getItem(procedureProgressKey(data)) || "{}") || {};
  } catch (_error) {
    return {};
  }
}

function saveProcedureManualProgress(progress) {
  sessionStorage.setItem(procedureProgressKey(), JSON.stringify(progress));
}

function procedureStepKey(phase, step) {
  return `${phase.id}:${step.id}`;
}

function procedureStepComplete(phase, step, progress) {
  if (step.mode === "info") return true;
  if (step.mode === "auto") {
    return step.status === "complete"
      || (step.status === "unknown" && progress[procedureStepKey(phase, step)] === true);
  }
  return progress[procedureStepKey(phase, step)] === true;
}

function procedurePhaseStats(phase, progress) {
  const required = phase.steps.filter((step) => step.mode !== "info");
  const complete = required.filter((step) => procedureStepComplete(phase, step, progress));
  return { complete: complete.length, total: required.length, done: complete.length === required.length };
}

function inferredProcedurePhase(aircraft) {
  if (!aircraft) return null;
  const speed = Number(aircraft.ground_speed_kt || 0);
  const agl = finiteOr(aircraft.height_above_ground_ft);
  const key = detectFlightPhaseKey(aircraft, projectAircraftOnFlightPath(aircraft));
  if (key === "phase_takeoff") return "takeoff";
  if (key === "phase_taxi_in") return "after_landing";
  if (key === "phase_landing") return "landing";
  if (key === "phase_approach") return "approach";
  if (key === "phase_descent") return "descent";
  if (key === "phase_cruise") return "cruise";
  if (key === "phase_climb") return agl !== null && agl < 1500 ? "after_takeoff" : "climb";
  if (aircraft.on_ground && speed >= 5) return "taxi";
  return null;
}

function procedureNote(note) {
  if (!note || typeof note !== "object") return "";
  const language = window.I18N.getLanguage();
  return note[language] || note.en || note.fr || "";
}

function procedureSourceText(value) {
  const source = String(value || "");
  const family = source.match(
    /^Procédures normales de la famille (.+?), représentation normalisée\. Aucune SOP compagnie, aucun extrait de FCOM\.$/
  );
  if (family) return tf("procedure_source_family", { family: family[1] });
  const manual = source.match(
    /^(.+?), section 4 — procédures normales, représentation normalisée\.$/
  );
  if (manual) return tf("procedure_source_manual", { manual: manual[1] });
  return source;
}

const PROCEDURE_PHASE_ICON_PATHS = {
  before_start: "M12 2v7m-4.7-4.4A8 8 0 1 0 16.7 4.6",
  start: "M12 4a8 8 0 1 0 7.4 5M18 3v6h-6M12 8v4l3 2",
  after_start: "M4 12l5 5L20 6M4 4h7M4 20h16",
  taxi: "M3 19h3c4 0 4-14 9-14h6M17 2l4 3-4 3M10 19h11",
  before_takeoff: "M4 3v18M8 3v18M13 5h8M13 9h8M13 13h8M13 17h8",
  takeoff: "M3 20h18M5 17 19 5M10 13l-5-1M15 9l1 5",
  after_takeoff: "M4 18 18 4M12 4h6v6M4 21h16",
  climb: "M4 18l6-6 4 3 6-8M15 7h5v5",
  cruise: "M3 12h18M8 8l-4 4 4 4M16 8l4 4-4 4",
  descent: "M4 6l6 6 4-3 6 8M15 17h5v-5",
  approach: "M3 4l7 16M21 4l-7 16M7 12h10M5 17h14",
  landing: "M3 20h18M5 5l14 12M10 10l-5 1M15 14l1-5",
  after_landing: "M3 4v7c0 5 4 9 9 9h9M17 17l4 3-4 3M8 4v7",
  shutdown: "M12 2v9M7 5.5a8 8 0 1 0 10 0",
};

function procedurePhaseMark(phase) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", PROCEDURE_PHASE_ICON_PATHS[phase] || PROCEDURE_PHASE_ICON_PATHS.cruise);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.7");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

function renderProcedurePanel(data = currentProcedures, aircraft = latestAircraft) {
  const panel = $("panel-procedures");
  panel.replaceChildren();
  if (!data?.available) {
    const empty = el("div", "procedure-empty");
    empty.append(el("div", "procedure-empty-icon", "✓"));
    empty.append(el("h2", null, t("procedure_unavailable_title")));
    empty.append(el("p", null, t(
      data?.reason === "procedures_unavailable"
        ? "procedure_unavailable_body"
        : "procedure_aircraft_uncovered"
    )));
    panel.append(empty);
    return;
  }

  const identity = procedureIdentity(data);
  if (identity !== procedureAircraftKey) {
    procedureAircraftKey = identity;
    selectedProcedurePhase = null;
  }
  const progress = procedureManualProgress(data);
  const phases = data.phases || [];
  if (!selectedProcedurePhase || !phases.some((phase) => phase.id === selectedProcedurePhase)) {
    selectedProcedurePhase = (
      phases.find((phase) => !procedurePhaseStats(phase, progress).done) || phases[0]
    )?.id || null;
  }
  const inferred = inferredProcedurePhase(aircraft);
  const header = el("header", "procedure-header");
  const heading = el("div", "procedure-aircraft");
  const aircraftMark = el("span", "procedure-aircraft-mark");
  aircraftMark.append(planeMark());
  const aircraftCopy = el("div", "procedure-aircraft-copy");
  aircraftCopy.append(el("div", "card-kicker", t("procedure_kicker")));
  aircraftCopy.append(el("h2", null, data.aircraft.model || data.aircraft.family));
  const variant = [data.aircraft.manufacturer, data.aircraft.variant_label].filter(Boolean).join(" · ");
  if (variant) aircraftCopy.append(el("p", null, variant));
  heading.append(aircraftMark, aircraftCopy);
  header.append(heading);
  const badges = el("div", "procedure-badges");
  badges.append(el(
    "span",
    `procedure-badge maturity-${data.aircraft.maturity}`,
    t(`procedure_maturity_${data.aircraft.maturity}`)
  ));
  badges.append(el(
    "span",
    `procedure-badge ${aircraft ? "is-live" : ""}`,
    aircraft ? t("procedure_live") : t("procedure_offline")
  ));
  header.append(badges);
  panel.append(header);

  const flow = el("nav", "procedure-flow");
  flow.setAttribute("aria-label", t("procedure_phase_flow"));
  phases.forEach((phase, index) => {
    const stats = procedurePhaseStats(phase, progress);
    const button = el("button", "procedure-phase");
    button.type = "button";
    button.title = t(`procedure_phase_${phase.phase}`);
    button.classList.toggle("active", phase.id === selectedProcedurePhase);
    button.classList.toggle("done", stats.done);
    button.classList.toggle("detected", phase.phase === inferred);
    button.setAttribute(
      "aria-current",
      phase.id === selectedProcedurePhase ? "step" : "false"
    );
    if (phase.phase === inferred) button.dataset.liveLabel = t("live");
    const phaseMark = el("span", "procedure-phase-mark");
    phaseMark.append(procedurePhaseMark(phase.phase));
    const phaseCopy = el("span", "procedure-phase-copy");
    phaseCopy.append(el("strong", null, t(`procedure_phase_${phase.phase}`)));
    phaseCopy.append(el("small", null, `${stats.complete}/${stats.total}`));
    button.append(phaseMark, phaseCopy);
    button.append(el("span", "procedure-phase-index", stats.done ? "✓" : String(index + 1)));
    button.addEventListener("click", () => {
      selectedProcedurePhase = phase.id;
      renderProcedurePanel(currentProcedures, latestAircraft);
    });
    flow.append(button);
  });
  panel.append(flow);

  const phase = phases.find((item) => item.id === selectedProcedurePhase) || phases[0];
  if (!phase) return;
  const stats = procedurePhaseStats(phase, progress);
  const workspace = el("section", "procedure-workspace");
  const phaseHead = el("div", "procedure-workspace-head");
  const phaseTitle = el("div", "procedure-workspace-title");
  const workspaceMark = el("span", "procedure-workspace-mark");
  workspaceMark.append(procedurePhaseMark(phase.phase));
  const phaseTitleCopy = el("div");
  phaseTitleCopy.append(el("div", "card-kicker", t(`procedure_phase_${phase.phase}`)));
  phaseTitleCopy.append(el("h3", null, phase.title));
  phaseTitle.append(workspaceMark, phaseTitleCopy);
  phaseHead.append(phaseTitle);
  const phaseProgress = el("div", "procedure-progress-copy");
  phaseProgress.append(el("strong", null, tf("procedure_progress", stats)));
  const meter = el("span", "procedure-progress-meter");
  const fill = el("i");
  fill.style.width = `${stats.total ? (stats.complete / stats.total) * 100 : 100}%`;
  meter.append(fill);
  phaseProgress.append(meter);
  phaseHead.append(phaseProgress);
  workspace.append(phaseHead);

  const list = el("div", "procedure-checklist");
  let previousGroup = "";
  for (const step of phase.steps) {
    const group = String(step.group || "");
    if (group && group !== previousGroup) {
      list.append(el("div", "procedure-group", group.replaceAll("_", " ").toUpperCase()));
    }
    previousGroup = group;
    const key = procedureStepKey(phase, step);
    const complete = procedureStepComplete(phase, step, progress);
    const canConfirm = step.mode === "manual" || step.status === "unknown";
    const row = el("button", `procedure-step mode-${step.mode}`);
    row.type = "button";
    row.classList.toggle("complete", complete);
    row.classList.toggle("unknown", step.status === "unknown" && !complete);
    row.classList.toggle("pending", step.status === "pending");
    row.disabled = !canConfirm;
    row.setAttribute("aria-pressed", String(complete));
    row.append(el("span", "procedure-check", complete ? "✓" : step.mode === "info" ? "i" : ""));
    const text = el("span", "procedure-step-copy");
    text.append(el("strong", "procedure-challenge", step.title));
    text.append(el("span", "procedure-leader"));
    text.append(el("span", "procedure-expected", step.expected || ""));
    const note = procedureNote(step.note);
    if (note) text.append(el("small", "procedure-note", note));
    row.append(text);
    const state = step.mode === "auto"
      ? step.status === "complete" ? "procedure_confirmed_auto"
        : step.status === "unknown" ? "procedure_confirm_manual"
          : "procedure_waiting_sim"
      : `procedure_mode_${step.mode}`;
    row.append(el("span", "procedure-step-mode", t(state)));
    if (canConfirm) {
      row.addEventListener("click", () => {
        progress[key] = !complete;
        saveProcedureManualProgress(progress);
        renderProcedurePanel(currentProcedures, latestAircraft);
      });
    }
    list.append(row);
  }
  workspace.append(list);

  const actions = el("footer", "procedure-actions");
  const reset = el("button", "icon-btn", t("procedure_reset"));
  reset.type = "button";
  reset.addEventListener("click", () => {
    sessionStorage.removeItem(procedureProgressKey());
    selectedProcedurePhase = phases[0]?.id || null;
    renderProcedurePanel(currentProcedures, latestAircraft);
  });
  actions.append(reset);
  const nextIndex = phases.indexOf(phase) + 1;
  if (nextIndex < phases.length) {
    const next = el("button", "btn-primary", `${t("procedure_next")} →`);
    next.type = "button";
    next.addEventListener("click", () => {
      selectedProcedurePhase = phases[nextIndex].id;
      renderProcedurePanel(currentProcedures, latestAircraft);
    });
    actions.append(next);
  }
  workspace.append(actions);
  panel.append(workspace);
  if (data.source) {
    panel.append(el(
      "p",
      "procedure-source",
      `${t("procedure_source")} · ${procedureSourceText(data.source)}`
    ));
  }
}

function updateProcedures(data, aircraft = latestAircraft) {
  currentProcedures = data || { available: false, reason: "aircraft_not_covered", phases: [] };
  renderProcedurePanel(currentProcedures, aircraft);
}

async function loadProceduresForPlan(plan = currentPlan) {
  const title = plan?.aircraft_name || plan?.aircraft || "";
  try {
    const response = await fetch(`/api/aircraft/procedures?title=${encodeURIComponent(title)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || t("procedure_load_failed"));
    updateProcedures(data, latestAircraft);
  } catch (_error) {
    updateProcedures({ available: false, reason: "procedures_unavailable", phases: [] });
  }
}

function renderPlan(plan) {
  siaOverlayCandidates.clear();
  clearSiaMapOverlay();
  hideBanner();
  show($("empty"), false);
  for (const id of ["strip", "tabs", "module-menu-toggle"]) show($(id), true);

  // La progression du bandeau doit utiliser la route opérationnelle complète,
  // y compris les points de SID, STAR et d'approche.
  flightGeometry = buildFlightGeometry(plan);
  flightRouteTotalNm = routeLengthNm(flightGeometry);
  renderStrip(plan);
  renderTerminal(plan);
  renderConstraints(plan);
  renderFlightPanel(plan);
  renderDispatch(plan);
  renderAircraft(plan);
  loadProceduresForPlan(plan);
  renderOfficialCharts(plan);
  renderMcdu(plan);
  renderWeather(plan);
  renderMapBar(plan);
  startLiveLoop();
  startWeatherLoop();

  if (plan.warnings?.length) {
    showBanner("warn", t("warnings"), plan.warnings.map(warningText));
  }
  selectTab(document.querySelector(".tabs button.active")?.dataset.tab || "constraints");
}

function renderStrip(plan) {
  const strip = $("strip");
  strip.innerHTML = "";
  strip.setAttribute("aria-label", t("route_title"));
  activeRoutePointIndex = null;

  const chip = (label, value, kind, routeIndex = null, routeStage = null) => {
    const fragment = document.createDocumentFragment();
    if (strip.childElementCount) fragment.append(el("span", "strip-sep"));
    const node = el("span", `chip ${kind}`);
    if (routeIndex !== null && routeIndex !== undefined) {
      node.dataset.routeIndex = String(routeIndex);
    }
    if (routeStage) node.dataset.routeStage = routeStage;
    if (label) node.append(el("small", null, label));
    node.append(document.createTextNode(value));
    fragment.append(node);
    return fragment;
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
  window.requestAnimationFrame(updateStripOverflowState);
}

function updateStripOverflowState() {
  const strip = $("strip");
  const maximum = Math.max(0, strip.scrollWidth - strip.clientWidth);
  strip.classList.toggle("can-scroll", maximum > 2);
  strip.classList.toggle("at-start", strip.scrollLeft <= 2);
  strip.classList.toggle("at-end", strip.scrollLeft >= maximum - 2);
}

function initialiseStripScrolling() {
  const strip = $("strip");
  let pointerId = null;
  let pointerX = 0;
  let scrollStart = 0;

  strip.addEventListener("scroll", updateStripOverflowState, { passive: true });
  strip.addEventListener("wheel", (event) => {
    if (!strip.classList.contains("can-scroll")) return;
    const movement = Math.abs(event.deltaX) > Math.abs(event.deltaY)
      ? event.deltaX
      : event.deltaY;
    if (!movement) return;
    const before = strip.scrollLeft;
    const maximum = strip.scrollWidth - strip.clientWidth;
    strip.scrollLeft = Math.max(0, Math.min(maximum, before + movement));
    if (strip.scrollLeft === before) return;
    event.preventDefault();
  }, { passive: false });
  strip.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || !strip.classList.contains("can-scroll")) return;
    pointerId = event.pointerId;
    pointerX = event.clientX;
    scrollStart = strip.scrollLeft;
    strip.classList.add("is-dragging");
    strip.setPointerCapture(pointerId);
  });
  strip.addEventListener("pointermove", (event) => {
    if (event.pointerId !== pointerId) return;
    strip.scrollLeft = scrollStart - (event.clientX - pointerX);
  });
  const finishDrag = (event) => {
    if (event.pointerId !== pointerId) return;
    pointerId = null;
    strip.classList.remove("is-dragging");
  };
  strip.addEventListener("pointerup", finishDrag);
  strip.addEventListener("pointercancel", finishDrag);
  strip.addEventListener("keydown", (event) => {
    if (!strip.classList.contains("can-scroll")) return;
    const distance = Math.max(160, strip.clientWidth * 0.45);
    if (event.key === "ArrowLeft") strip.scrollBy({ left: -distance, behavior: "smooth" });
    else if (event.key === "ArrowRight") strip.scrollBy({ left: distance, behavior: "smooth" });
    else if (event.key === "Home") strip.scrollTo({ left: 0, behavior: "smooth" });
    else if (event.key === "End") strip.scrollTo({ left: strip.scrollWidth, behavior: "smooth" });
    else return;
    event.preventDefault();
  });
  new ResizeObserver(updateStripOverflowState).observe(strip);
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

/** Longueur totale de la route opérationnelle, calculée une fois par plan. */
function routeLengthNm(geometry) {
  let total = 0;
  for (let index = 0; index < geometry.length - 1; index += 1) {
    total += haversineNm(geometry[index], geometry[index + 1]);
  }
  return total;
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

/*
 * La phase est déterminée sous forme de clé de traduction, jamais de libellé.
 * La chronologie du vol la conserve telle quelle : un vol enregistré en
 * français se relit en anglais sans réécrire l'historique.
 */
function detectFlightPhaseKey(aircraft, projection) {
  if (!aircraft) return "phase_offline";
  const speed = Number(aircraft.ground_speed_kt || 0);
  const verticalSpeed = Number(aircraft.vertical_speed_fpm || 0);
  if (aircraft.on_ground) {
    if (projection?.remainingNm < 5) return speed > 35 ? "phase_landing" : "phase_taxi_in";
    return speed > 45 ? "phase_takeoff" : "phase_taxi_out";
  }
  if (projection?.activePoint?.stage === "approach" || projection?.remainingNm < 25) {
    return "phase_approach";
  }
  if (verticalSpeed > 300) return "phase_climb";
  if (verticalSpeed < -300) return "phase_descent";
  // Le niveau de croisière du plan est un niveau de vol : le comparer à
  // l'altitude vraie faisait perdre la croisière dès que l'air s'écartait de
  // l'atmosphère standard.
  const cruise = Number(currentPlan?.enroute?.cruise_altitude_ft || 0);
  if (cruise && Math.abs(finiteOr(standardAltitude(aircraft), 0) - cruise) < 1200) {
    return "phase_cruise";
  }
  return "phase_enroute";
}

function detectFlightPhase(aircraft, projection) {
  return t(detectFlightPhaseKey(aircraft, projection));
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
      && (c.phase === t("phase_approach") || c.phase === t("phase_landing"))
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
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt < 3000 && c.phase === t("phase_approach"),
    when: (c) => c.configuration.flaps_handle_index === 0,
  },
  {
    id: "flaps_still_out",
    severity: "warning",
    needs: "flaps",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt > 3000 && c.phase === t("phase_climb"),
    when: (c) => finiteOr(c.configuration.flaps_handle_index, 0) > 0,
  },
  {
    id: "flaps_takeoff",
    severity: "warning",
    needs: "flaps",
    armed: (c) => c.onGround && c.phase === t("phase_takeoff"),
    when: (c) => c.configuration.flaps_handle_index === 0,
  },
  {
    id: "spoilers_not_armed",
    severity: "warning",
    needs: "spoilers",
    armed: (c) => !c.onGround && c.aglFt !== null && c.aglFt < 2000 && c.phase === t("phase_approach"),
    when: (c) => c.configuration.spoilers_armed === false,
  },
  {
    id: "spoilers_out",
    severity: "warning",
    needs: "spoilers",
    armed: (c) => c.phase === t("phase_climb"),
    when: (c) => finiteOr(c.configuration.spoilers_handle_pct, 0) > 5,
  },
  {
    id: "strobe_off",
    severity: "warning",
    armed: (c) => !c.onGround || c.phase === t("phase_takeoff"),
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
      && (c.phase === t("phase_descent") || c.phase === t("phase_approach"))
    ),
    when: (c) => c.configuration.lights?.landing === false,
  },
  {
    id: "landing_lights_on",
    severity: "info",
    armed: (c) => c.phase === t("phase_cruise") && c.altitudeFt !== null && c.altitudeFt > 10000,
    when: (c) => c.configuration.lights?.landing === true,
  },
  {
    id: "std_not_set",
    severity: "warning",
    armed: (c) => {
      const transition = finiteOr(c.plan?.departure?.transition_altitude_ft);
      return (
        !c.onGround && c.phase === t("phase_climb")
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
        && (c.phase === t("phase_descent") || c.phase === t("phase_approach"))
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
      && (c.phase === t("phase_descent") || c.phase === t("phase_approach"))
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
      const plausibleDistanceNm = plausibleLegNm(previous, point);
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

/**
 * Distance maximale crédible entre deux relevés, au-delà de laquelle le
 * segment vient d'une téléportation (rechargement, slew) et non d'un vol.
 *
 * Le vol de démonstration est exempté : il comprime le temps, sa position
 * avance donc plus vite que la vitesse sol annoncée sans jamais sauter.
 */
function plausibleLegNm(previous, point) {
  if (previous?.source === "Démonstration") return Infinity;
  const elapsedMs = (
    Date.parse(point.recorded_at || "") - Date.parse(previous.recorded_at || "")
  );
  const elapsedHours = Number.isFinite(elapsedMs) && elapsedMs > 0
    ? elapsedMs / 3_600_000
    : 0;
  const speed = Math.max(
    50,
    finiteOr(previous.ground_speed_kt, 0),
    finiteOr(point.ground_speed_kt, 0)
  );
  return elapsedHours ? Math.max(0.15, speed * elapsedHours * 4) : 2;
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
    ? `${t("recorder_replay")} ×${speed}${replaySourceLabel ? ` · ${replaySourceLabel}` : ""}`
    : flightRecording ? t("recorder_active") : t("recorder_paused");
  status.textContent = `${mode} · ${flightLog.length} ${t("points")}`;
  const toggle = $("flight-record-toggle");
  if (toggle) toggle.textContent = flightRecording ? t("pause") : t("resume");
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
    const leg = haversineNm(previous, point);
    if (leg <= plausibleLegNm(previous, point)) distanceNm += leg;
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
      addEvent("takeoff", index, t("event_takeoff"), `${Math.round(point.ground_speed_kt || 0)} kt`);
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
        t("event_descent"),
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
        t("event_approach"),
        projection?.activePoint?.ident || ""
      );
    }
    if (!previous.on_ground && point.on_ground) {
      addEvent("landing", index, t("event_touchdown"), `${Math.round(point.ground_speed_kt || 0)} kt`);
    }

    const configuration = point.configuration || {};
    if (configuration.overspeed_warning === true) {
      addEvent("overspeed", index, t("event_overspeed"), t("simulator_alert"), "danger");
    }
    if (configuration.stall_warning === true) {
      addEvent("stall", index, t("event_stall"), t("simulator_alert"), "danger");
    }
    if (configuration.flap_speed_exceeded === true) {
      addEvent(
        "flap_overspeed",
        index,
        t("event_flap_overspeed"),
        t("simulator_alert"),
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
          t("event_gear_1000"),
          `${Math.round(gear)} %`,
          "warning"
        );
      }
      const verticalSpeed = finiteOr(point.vertical_speed_fpm, 0);
      if (verticalSpeed < -1200) {
        addEvent(
          "vertical_speed_below_1000",
          index,
          t("event_descent_rate_1000"),
          `${Math.round(verticalSpeed)} ft/min`,
          "warning"
        );
      }
      const airspeed = finiteOr(point.indicated_airspeed_kt);
      if (airspeed !== null && airspeed > 180) {
        addEvent(
          "speed_below_1000",
          index,
          t("event_speed_1000"),
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
  sourceLabel = t("current_flight"),
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
      t("debrief_waiting")
    ));
    return;
  }

  const heading = el("div", "flight-debrief-heading");
  heading.append(
    el("strong", null, sourceLabel),
    el(
      "span",
      null,
      t("debrief_thresholds")
    )
  );
  container.append(heading);

  const stats = el("div", "flight-debrief-stats");
  for (const [label, value] of [
    [t("duration"), formatDebriefDuration(debrief.durationSeconds)],
    [t("actual_distance"), `${debrief.distanceNm.toFixed(1)} NM`],
    [
      t("max_deviation"),
      debrief.routeAvailable ? `${debrief.maxDeviationNm.toFixed(1)} NM` : "—",
    ],
    [
      t("off_route_time"),
      debrief.routeAvailable ? formatDebriefDuration(debrief.offRouteSeconds) : "—",
    ],
    [t("maximum_altitude"), `${Math.round(debrief.maxAltitudeFt)} ft`],
  ]) {
    const card = el("article", "flight-live-stat");
    card.append(el("div", "stat-label", label), el("div", "stat-value", value));
    stats.append(card);
  }
  container.append(stats);

  const timeline = el("div", "flight-debrief-timeline");
  if (!debrief.events.length) {
    timeline.append(el("p", "flight-archive-empty", t("no_notable_event")));
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
        [time ? new Date(time).toLocaleTimeString(displayLocale()) : "", event.detail]
          .filter(Boolean)
          .join(" · ")
      )
    );
    row.append(el("span", "flight-debrief-event-mark", "▶"), description);
    row.title = t("replay_sequence");
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
    container.append(el("p", "flight-archive-empty", t("no_archived_flight")));
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
          entry.ended_at ? new Date(entry.ended_at).toLocaleString(displayLocale()) : "",
          `${entry.points} points`,
        ].filter(Boolean).join(" · ")
      )
    );
    const actions = el("div", "flight-archive-actions");
    const analyse = el("button", "icon-btn", t("debrief"));
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
    const replay = el("button", "icon-btn", t("replay"));
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
    if (haversineNm(previous, point) <= plausibleLegNm(previous, point)) {
      distanceNm += haversineNm(previous, point);
    }
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
    // La chronologie commence au roulage, avant que le résumé n'existe : elle
    // est rattachée entière au vol terminé, pas seulement depuis le décollage.
    completed.events = storedFlightEvents();
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
    container.append(el("p", "flight-summary-empty", t("no_completed_flights")));
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
        [entry.callsign, entry.ended_at ? new Date(entry.ended_at).toLocaleString(displayLocale()) : ""]
          .filter(Boolean)
          .join(" · ")
      )
    );
    const metrics = el("div", "flight-summary-metrics");
    for (const [label, value] of [
      [t("duration"), formatFlightSummaryDuration(entry.duration_seconds || 0)],
      [t("distance"), `${finiteOr(entry.distance_nm, 0).toFixed(1)} NM`],
      [t("max_altitude"), `${Math.round(finiteOr(entry.max_altitude_ft, 0))} ft`],
    ]) {
      const metric = el("span");
      metric.append(el("small", null, label), el("b", null, value));
      metrics.append(metric);
    }
    row.append(heading, metrics);

    // Les vols enregistrés avant cette version n'ont pas de chronologie : le
    // bouton n'apparaît que lorsqu'il y a quelque chose à rejouer.
    const events = Array.isArray(entry.events) ? entry.events : [];
    if (events.length) {
      const timeline = el("div", "flight-summary-events hidden");
      const toggle = el("button", "icon-btn", t("events_replay"));
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      toggle.addEventListener("click", () => {
        const opened = timeline.classList.contains("hidden");
        if (opened && !timeline.childElementCount) {
          const endedAt = Date.parse(entry.ended_at) || Date.now();
          timeline.append(flightEventGroups(flightEventSegments(events, endedAt)));
        }
        show(timeline, opened);
        toggle.setAttribute("aria-expanded", opened ? "true" : "false");
      });
      heading.append(toggle);
      row.append(timeline);
    }
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
  // Deux familles d'Airbus coexistent, et c'est le nombre de positions
  // déclarées qui les sépare. Certains exposent deux états SimConnect pour le
  // même cran physique 1 — configuration 1 en vol, 1+F au sol — et annoncent
  // donc six positions ; l'interface affiche alors la position de la manette,
  // pas le sous-état aérodynamique. Les autres s'en tiennent aux cinq crans
  // réels. Appliquer la table à six entrées à ces derniers décalait tout
  // au-dessus du cran 1 : la manette sur 2 s'affichait « 1 ».
  if (isAirbus && positions >= 6) {
    return ["0", "1", "1", "2", "3", "FULL"];
  }
  if (isAirbus && positions === 5) {
    return ["0", "1", "2", "3", "FULL"];
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
  const detents = flapDetentLabels(aircraft, plan, positions);
  if (index === 0) {
    // Le premier cran porte le marquage du constructeur : « 0 » chez Airbus.
    // Là où il vaut UP, c'est le libellé traduit qui reste affiché.
    const retracted = detents?.[0];
    return {
      text: retracted && retracted !== "UP" ? retracted : t("cfg_flaps_up"),
      status: "",
    };
  }
  const extended = finiteOr(configuration.flaps_extended_pct);
  // Le marquage suit toujours l'index résolu par la source temps réel. Utiliser
  // une ancienne extension physique à 100 % maintenait abusivement FULL
  // pendant toute la rentrée des volets.
  const detent = detents?.[Math.round(index)];
  if (detent) return { text: detent, status: "good" };

  // Avion sans profil connu — et il y en aura toujours. Le rang de la manette
  // reste lisible sur n'importe quelle aile, et l'angle mesuré dit ce que ce
  // cran vaut : c'est d'ailleurs le marquage même de la plupart des leviers
  // hors Airbus. Le pourcentage ne sert que si l'angle manque.
  const angle = finiteOr(configuration.flaps_angle_deg);
  const position = steps ? `${index} / ${steps}` : String(index);
  const measured = angle !== null && angle >= 1
    ? `${Math.round(angle)}°`
    : (extended !== null ? `${Math.round(extended)} %` : null);
  return {
    text: [position, measured].filter(Boolean).join(" · "),
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

/* ------------------------------------------------------ chronologie du vol */

/*
 * La chronologie n'observe rien de plus que le bloc de configuration : elle
 * compare deux états successifs et retient ce qui a changé. Trois règles la
 * rendent lisible en vol.
 *
 * L'anti-rebond d'abord : un cran de volets traverse plusieurs positions
 * pendant sa course, et un levier relâché oscille. Un changement n'entre au
 * journal qu'après être resté stable, comme pour les alarmes.
 *
 * Le premier échantillon ensuite : la configuration trouvée à l'ouverture du
 * plan n'est pas un changement. Seule la phase ouvre la chronologie, pour lui
 * donner une origine ; le reste est mémorisé en silence.
 *
 * Les clés enfin : un événement conserve la clé de traduction et ses valeurs
 * brutes, jamais un libellé. Un vol enregistré en français se relit en
 * anglais, et les marquages constructeur — UP, FULL, FL350 — ne bougent pas.
 */

const FLIGHT_EVENT_LIGHT_KEYS = {
  landing: "evt_light_landing",
  taxi: "evt_light_taxi",
  strobe: "evt_light_strobe",
  nav: "evt_light_nav",
  beacon: "evt_light_beacon",
  logo: "evt_light_logo",
  wing: "evt_light_wing",
};

/** Marquage inscrit sur le levier de volets, à défaut le rang de la manette. */
function flapMarking(aircraft, index) {
  const rank = Math.round(finiteOr(index, 0));
  const capabilities = aircraft?.configuration?.capabilities || null;
  const detents = flapDetentLabels(
    aircraft,
    currentPlan,
    finiteOr(capabilities?.flap_positions, 0)
  );
  return detents?.[rank] || (rank === 0 ? "UP" : String(rank));
}

/** Piste retenue pour le décollage ou l'atterrissage, sans invention. */
function flightEventRunway(landed) {
  const planned = landed
    ? currentPlan?.arrival?.runway?.value
    : currentPlan?.departure?.runway?.value;
  return String(planned || currentChart?.highlight_runway || "").trim();
}

function flightEventWind(aircraft) {
  const direction = finiteOr(aircraft?.configuration?.wind_direction_deg);
  const speed = finiteOr(aircraft?.configuration?.wind_speed_kt);
  if (direction === null || speed === null) return "";
  return `${String(Math.round(direction)).padStart(3, "0")}°/${Math.round(speed)} kt`;
}

function flightEventAltitude(aircraft) {
  const altitude = standardAltitude(aircraft);
  if (altitude === null) return "";
  const transition = finiteOr(
    currentPlan?.departure?.transition_altitude_ft,
    finiteOr(currentPlan?.arrival?.transition_level_ft, 5000)
  );
  return altitude >= transition
    ? `FL${String(Math.round(altitude / 100)).padStart(3, "0")}`
    : `${Math.round(altitude)} ft`;
}

/* Une phase se lit avec la grandeur qui la définit : le taux en montée et en
   descente, la vitesse au sol et au décollage, le niveau partout ailleurs. */
function flightEventPhaseValue(phaseKey, aircraft) {
  if (phaseKey === "phase_climb" || phaseKey === "phase_descent") {
    const rate = finiteOr(aircraft?.vertical_speed_fpm);
    if (rate !== null) {
      const rounded = Math.round(rate / 50) * 50;
      return `${rounded > 0 ? "+" : ""}${rounded} ft/min`;
    }
  }
  if (["phase_takeoff", "phase_landing", "phase_taxi_out", "phase_taxi_in"].includes(phaseKey)) {
    const speed = finiteOr(
      aircraft?.indicated_airspeed_kt,
      finiteOr(aircraft?.ground_speed_kt)
    );
    if (speed !== null) return `${Math.round(speed)} kt`;
  }
  return flightEventAltitude(aircraft);
}

/*
 * Un observateur lit une valeur discrète et stable — jamais un pourcentage qui
 * bouge en continu — puis décrit la transition. `read` rend `null` quand le
 * simulateur ne publie pas la donnée : rien n'est alors observé, et surtout
 * rien n'est inventé sur un avion à train fixe ou sans aérofreins.
 */
const FLIGHT_EVENT_WATCHERS = [
  {
    key: "phase",
    kind: "phase",
    read: (_aircraft, phaseKey) => phaseKey || null,
    describe: (_previous, value, aircraft) => ({
      key: "evt_phase",
      value: flightEventPhaseValue(value, aircraft),
    }),
  },
  {
    key: "ground",
    kind: "runway",
    read: (aircraft) => (
      aircraft?.on_ground === true || aircraft?.on_ground === false
        ? Boolean(aircraft.on_ground)
        : null
    ),
    describe: (_previous, landed, aircraft) => {
      const runway = flightEventRunway(landed);
      const base = landed ? "evt_landing" : "evt_takeoff";
      return {
        key: runway ? `${base}_runway` : base,
        params: { runway },
        value: flightEventWind(aircraft),
      };
    },
  },
  {
    key: "gear",
    kind: "config",
    read: (aircraft) => {
      const configuration = aircraft?.configuration;
      if (!configuration) return null;
      if (configuration.capabilities && !configuration.capabilities.retractable_gear) {
        return null;
      }
      const extended = finiteOr(configuration.gear_extended_pct);
      if (extended === null) return null;
      if (extended >= 99) return "down";
      if (extended <= 1) return "up";
      return "transit";
    },
    describe: (_previous, value) => ({
      key: `evt_gear_${value}`,
      value: value === "down" ? "DOWN" : value === "up" ? "UP" : "",
    }),
  },
  {
    key: "flaps",
    kind: "config",
    read: (aircraft) => {
      const configuration = aircraft?.configuration;
      if (!configuration) return null;
      if (configuration.capabilities && !configuration.capabilities.flaps) return null;
      const index = finiteOr(configuration.flaps_handle_index);
      return index === null ? null : Math.round(index);
    },
    describe: (previous, value, aircraft) => {
      const angle = finiteOr(aircraft?.configuration?.flaps_angle_deg);
      const marking = flapMarking(aircraft, value);
      const measured = angle !== null && angle >= 1 ? `${Math.round(angle)}°` : marking;
      if (value === 0) return { key: "evt_flaps_up", value: marking };
      return {
        key: "evt_flaps_set",
        params: { from: flapMarking(aircraft, previous ?? 0), to: marking },
        value: measured,
      };
    },
  },
  {
    key: "spoilers",
    kind: "config",
    read: (aircraft) => {
      const configuration = aircraft?.configuration;
      if (!configuration) return null;
      if (configuration.spoilers_armed === true) return "armed";
      if (configuration.capabilities && !configuration.capabilities.spoilers) return null;
      const handle = finiteOr(configuration.spoilers_handle_pct);
      if (handle === null) return null;
      return handle > 5 ? "extended" : "retracted";
    },
    describe: (_previous, value, aircraft) => ({
      key: `evt_spoilers_${value}`,
      value: value === "extended"
        ? `${Math.round(finiteOr(aircraft?.configuration?.spoilers_handle_pct, 0))} %`
        : "",
    }),
  },
  {
    key: "brake",
    kind: "config",
    read: (aircraft) => {
      const parking = aircraft?.configuration?.parking_brake;
      return parking === true || parking === false ? parking : null;
    },
    describe: (_previous, value) => ({
      key: value ? "evt_brake_set" : "evt_brake_released",
    }),
  },
  {
    key: "autopilot",
    kind: "auto",
    read: (aircraft) => {
      if (!aircraft?.configuration) return null;
      // Les modes sont des sigles de cockpit : ils ne se traduisent pas et
      // font donc une valeur stable, comparable d'un échantillon au suivant.
      const description = describeAutopilot(aircraft.configuration);
      return description.status === "good" ? description.text : "";
    },
    // Les modes tiennent dans la colonne de droite : les répéter dans le
    // libellé écrivait deux fois la même chose sur la même ligne.
    describe: (_previous, value) => (
      value ? { key: "evt_ap_modes", value } : { key: "evt_ap_off" }
    ),
  },
  ...Object.entries(FLIGHT_EVENT_LIGHT_KEYS).map(([light, labelKey]) => ({
    key: `light:${light}`,
    kind: "lights",
    read: (aircraft) => {
      const state = aircraft?.configuration?.lights?.[light];
      return state === true || state === false ? state : null;
    },
    describe: (_previous, value) => ({
      key: value ? "evt_light_on" : "evt_light_off",
      params: { light: labelKey },
    }),
  })),
];

function resetFlightEvents() {
  flightEvents = [];
  flightEventSequence = 0;
  flightEventStates.clear();
  collapsedFlightEventGroups.clear();
  flightEventsRenderKey = "";
}

function appendFlightEvent(watcher, previous, value, aircraft, occurredAt) {
  const description = watcher.describe(previous, value, aircraft);
  if (!description) return;
  flightEventSequence += 1;
  flightEvents.push({
    id: flightEventSequence,
    at: new Date(occurredAt).toISOString(),
    phase: flightEventStates.get("phase")?.value || "phase_offline",
    kind: watcher.kind,
    key: description.key,
    params: description.params || {},
    value: description.value || "",
  });
  if (flightEvents.length > FLIGHT_EVENT_MAX) {
    flightEvents.splice(0, flightEvents.length - FLIGHT_EVENT_MAX);
  }
}

function updateFlightEvents(aircraft, phaseKey) {
  if (!aircraft || !currentPlan) return;
  const now = Date.now();
  for (const watcher of FLIGHT_EVENT_WATCHERS) {
    const value = watcher.read(aircraft, phaseKey);
    if (value === null || value === undefined) continue;
    const state = flightEventStates.get(watcher.key);
    if (!state) {
      flightEventStates.set(watcher.key, { value, pending: value, since: now });
      if (watcher.kind === "phase") appendFlightEvent(watcher, null, value, aircraft, now);
      continue;
    }
    if (value === state.value || value !== state.pending) {
      state.pending = value;
      state.since = now;
      continue;
    }
    if (now - state.since < FLIGHT_EVENT_CONFIRM_MS) continue;
    const previous = state.value;
    // L'heure retenue est celle du premier échantillon qui portait la nouvelle
    // valeur, pas celle de sa confirmation : la chronologie doit coïncider avec
    // le vol, pas avec le délai que s'accorde l'anti-rebond.
    const observedAt = state.since;
    state.value = value;
    state.since = now;
    appendFlightEvent(watcher, previous, value, aircraft, observedAt);
  }
}

/* Le journal conservé avec le résumé garde d'abord les jalons — phases,
   décollage, atterrissage — puis complète avec la configuration la plus
   récente. Un vol de trois heures tient ainsi dans quelques kilo-octets. */
function storedFlightEvents() {
  if (flightEvents.length <= FLIGHT_EVENT_STORED_MAX) return flightEvents.slice();
  const isMilestone = (event) => event.kind === "phase" || event.kind === "runway";
  const milestones = flightEvents.filter(isMilestone);
  const room = Math.max(0, FLIGHT_EVENT_STORED_MAX - milestones.length);
  const kept = new Set(
    flightEvents.filter((event) => !isMilestone(event)).slice(-room).map((event) => event.id)
  );
  return flightEvents
    .filter((event) => isMilestone(event) || kept.has(event.id))
    .slice(-FLIGHT_EVENT_STORED_MAX);
}

function flightEventLabel(event) {
  if (event.kind === "phase") return tf("evt_phase", { phase: t(event.phase) });
  const params = { ...(event.params || {}) };
  if (params.light) params.light = t(params.light);
  return tf(event.key, params);
}

function formatFlightEventClock(milliseconds) {
  // L'heure d'un vol se lit sur vingt-quatre heures dans toutes les langues :
  // un « 08:36:54 AM » ne se compare à aucune horloge de cockpit.
  return new Date(milliseconds).toLocaleTimeString(displayLocale(), {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatFlightEventDuration(seconds) {
  const total = Math.max(0, Math.round(seconds));
  return total < 60 ? `${total} s` : formatFlightSummaryDuration(total);
}

/** Découpe la chronologie en segments de phase, du plus ancien au plus récent. */
function flightEventSegments(events, endedAt) {
  const segments = [];
  for (const event of events) {
    const last = segments.at(-1);
    if (last && last.phase === event.phase) {
      last.events.push(event);
      continue;
    }
    segments.push({ phase: event.phase, from: Date.parse(event.at), events: [event] });
  }
  for (const [index, segment] of segments.entries()) {
    segment.to = Math.max(segment.from, segments[index + 1]?.from ?? endedAt);
  }
  return segments;
}

/*
 * Le ruban donne au vol sa forme d'ensemble : chaque phase occupe la largeur
 * du temps qu'elle a duré, et chaque événement y laisse une marque à sa place.
 * C'est ce que la liste seule ne montre jamais — une montée deux fois plus
 * longue que prévu se voit avant d'être lue.
 */
function renderFlightEventRibbon(node, segments) {
  node.innerHTML = "";
  if (!segments.length) {
    node.append(el("p", "flight-events-ribbon-empty", t("events_waiting")));
    return;
  }
  for (const [index, segment] of segments.entries()) {
    const span = Math.max(1, segment.to - segment.from);
    const cell = el("div", "flight-events-phase");
    // L'échelle est compressée en racine carrée. Proportionnelle au temps, une
    // croisière d'une heure réduisait le décollage à quelques pixels et son
    // nom à une lettre ; la racine garde l'ordre des durées lisible tout en
    // laissant une phase brève occuper une place où elle se lit encore.
    cell.style.flexGrow = String(Math.sqrt(span / 1000));
    if (index === segments.length - 1) cell.dataset.current = "true";
    cell.title = `${t(segment.phase)} · ${formatFlightEventDuration(span / 1000)}`;
    cell.append(el("span", "flight-events-phase-name", t(segment.phase)));
    const track = el("span", "flight-events-phase-track");
    for (const event of segment.events) {
      const tick = el("span", "flight-events-tick");
      tick.dataset.kind = event.kind;
      const ratio = (Date.parse(event.at) - segment.from) / span;
      tick.style.left = `${Math.min(100, Math.max(0, ratio * 100))}%`;
      tick.title = `${formatFlightEventClock(Date.parse(event.at))} · ${flightEventLabel(event)}`;
      track.append(tick);
    }
    cell.append(track);
    node.append(cell);
  }
}

/** Journal groupé par phase, du plus récent au plus ancien. */
function flightEventGroups(segments) {
  const fragment = document.createDocumentFragment();
  for (const segment of [...segments].reverse()) {
    const group = el("div", "flight-events-group");
    const groupId = `${segment.phase}:${segment.from}`;
    const collapsed = collapsedFlightEventGroups.has(groupId);
    if (collapsed) group.classList.add("is-collapsed");

    const head = el("button", "flight-events-group-head");
    head.type = "button";
    head.setAttribute("aria-expanded", collapsed ? "false" : "true");
    head.append(el("span", "flight-events-group-name", t(segment.phase)));
    head.append(el(
      "span",
      "flight-events-group-meta",
      `${formatFlightEventClock(segment.from)} · ${formatFlightEventDuration((segment.to - segment.from) / 1000)}`
    ));
    head.addEventListener("click", () => {
      const hidden = group.classList.toggle("is-collapsed");
      head.setAttribute("aria-expanded", hidden ? "false" : "true");
      if (hidden) collapsedFlightEventGroups.add(groupId);
      else collapsedFlightEventGroups.delete(groupId);
    });
    group.append(head);

    const body = el("div", "flight-events-group-body");
    for (const event of [...segment.events].reverse()) {
      const row = el("div", "flight-events-row");
      row.dataset.kind = event.kind;
      const occurredAt = Date.parse(event.at);
      const time = el("time", "flight-events-time", formatFlightEventClock(occurredAt));
      time.dateTime = event.at;
      // La marque ne porte pas d'information seule : le libellé dit toujours
      // ce qui a changé, la forme ne fait que trier l'œil.
      const mark = el("span", "flight-events-mark");
      mark.setAttribute("aria-hidden", "true");
      row.append(time, mark, el("span", "flight-events-label", flightEventLabel(event)));
      if (event.value) row.append(el("span", "flight-events-value", event.value));
      body.append(row);
    }
    group.append(body);
    fragment.append(group);
  }
  return fragment;
}

function renderFlightEvents() {
  const ribbon = $("flight-events-ribbon");
  const list = $("flight-events-list");
  if (!ribbon || !list) return;
  const segments = flightEventSegments(flightEvents, Date.now());
  renderFlightEventRibbon(ribbon, segments);

  const count = $("flight-events-count");
  if (count) count.textContent = String(flightEvents.length);

  // La liste ne se reconstruit qu'à l'arrivée d'un événement ou au changement
  // de langue : sans cela, chaque seconde effacerait le défilement en cours.
  const renderKey = `${displayLocale()}:${flightEvents.length}:${flightEvents.at(-1)?.id || 0}`;
  if (renderKey === flightEventsRenderKey) return;
  flightEventsRenderKey = renderKey;
  list.innerHTML = "";
  if (!flightEvents.length) {
    list.append(el("p", "flight-events-empty", t("events_empty")));
    return;
  }
  list.append(flightEventGroups(segments));
}

function buildFlightEventsSection() {
  const section = el("section", "flight-events");
  const head = el("div", "flight-events-head");
  const heading = el("div");
  heading.append(el("div", "card-kicker", t("events_kicker")));
  heading.append(el("h2", null, t("events_title")));
  head.append(heading);
  const count = el("span", "flight-events-count", "0");
  count.id = "flight-events-count";
  count.title = t("events_count_title");
  head.append(count);
  section.append(head);

  const ribbon = el("div", "flight-events-ribbon");
  ribbon.id = "flight-events-ribbon";
  ribbon.setAttribute("aria-label", t("events_ribbon_label"));
  section.append(ribbon);

  const list = el("div", "flight-events-list");
  list.id = "flight-events-list";
  list.setAttribute("role", "log");
  list.setAttribute("aria-live", "polite");
  section.append(list);
  return section;
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

/* ------------------------------------------- progression graphique du vol */

const SVG_NS = "http://www.w3.org/2000/svg";

/** Silhouette d'avion vue de dessus, nez vers le haut puis pivotée en CSS. */
function planeMark() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute(
    "d",
    "M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"
  );
  path.setAttribute("fill", "currentColor");
  svg.append(path);
  return svg;
}

function progressTime(id, label, extraClass = "") {
  const node = el("div", `flight-progress-time${extraClass ? ` ${extraClass}` : ""}`);
  node.append(el("span", "flight-progress-time-label", label));
  const value = el("span", "flight-progress-time-value", "—");
  value.id = id;
  node.append(value);
  return node;
}

function progressAirport(block, role, extraClass) {
  const airport = el("div", `flight-progress-airport${extraClass ? ` ${extraClass}` : ""}`);
  airport.append(el("div", "flight-progress-role", role));
  airport.append(el("div", "flight-progress-icao", block?.icao || "----"));
  if (block?.name) airport.append(el("div", "flight-progress-name", block.name));
  return airport;
}

/**
 * Bandeau « départ → arrivée » : l'avion avance sur la ligne au rythme de la
 * distance parcourue, avec le temps écoulé, prévu et restant sous la ligne.
 */
function buildFlightProgressSection(plan) {
  const section = el("section", "flight-progress");
  section.append(progressAirport(plan.departure, t("progress_departure"), ""));

  const middle = el("div", "flight-progress-middle");

  const track = el("div", "flight-progress-track");
  track.id = "flight-progress-track";
  track.setAttribute("role", "img");
  track.append(el("span", "flight-progress-dot"));
  const done = el("span", "flight-progress-done");
  track.append(done);
  const plane = el("span", "flight-progress-plane");
  const altitude = el("span", "flight-progress-altitude", "—");
  altitude.id = "flight-progress-altitude";
  plane.append(altitude);
  plane.append(planeMark());
  track.append(plane);
  track.append(el("span", "flight-progress-dot is-end"));
  middle.append(track);

  const caption = el("div", "flight-progress-caption", "—");
  caption.id = "flight-progress-caption";
  middle.append(caption);

  const times = el("div", "flight-progress-times");
  times.append(progressTime("flight-progress-elapsed", t("time_elapsed")));
  times.append(progressTime("flight-progress-total", t("total_ete"), "is-center"));
  times.append(progressTime("flight-progress-remaining", t("time_remaining"), "is-right"));
  middle.append(times);

  section.append(middle);
  section.append(progressAirport(plan.arrival, t("progress_arrival"), "is-right"));
  return section;
}

/**
 * Altitude courante affichée au-dessus de l'avion, en niveau de vol au-dessus
 * de l'altitude de transition et en pieds en dessous, avec la tendance
 * verticale. La transition retenue suit la phase : celle du départ tant que
 * l'avion n'a pas dépassé la mi-route, celle de l'arrivée ensuite.
 */
/**
 * Altitude dont se déduit le niveau de vol : celle de l'atmosphère standard.
 *
 * SimConnect publie aussi l'altitude vraie, mais elle ne fait niveau de vol
 * qu'en atmosphère standard : par air chaud elle dépasse la pression de plus
 * de mille pieds, et FL330 s'affichait FL342. Le simulateur peut refuser le
 * bloc de configuration ; l'altitude vraie reste alors le seul repli.
 */
function standardAltitude(aircraft) {
  return finiteOr(
    aircraft?.configuration?.pressure_altitude_ft,
    finiteOr(aircraft?.altitude_ft)
  );
}

function progressAltitudeLabel(aircraft, ratio) {
  const altitude = standardAltitude(aircraft);
  if (altitude === null) return "—";
  const transition = finiteOr(
    ratio !== null && ratio >= 0.5
      ? currentPlan?.arrival?.transition_level_ft
      : currentPlan?.departure?.transition_altitude_ft,
    5000
  );
  const text = altitude >= transition
    ? `FL${String(Math.round(altitude / 100)).padStart(3, "0")}`
    : `${Math.round(altitude).toLocaleString(displayLocale())} ft`;
  const verticalSpeed = finiteOr(aircraft?.vertical_speed_fpm, 0);
  const trend = verticalSpeed > 300 ? " ↑" : verticalSpeed < -300 ? " ↓" : "";
  return `${text}${trend}`;
}

function updateFlightProgress(aircraft, projection, remainingSeconds, plannedEteSeconds) {
  const track = $("flight-progress-track");
  if (!track) return;

  const elapsedSeconds = activeFlightSummary
    ? Math.max(0, (Date.now() - Date.parse(activeFlightSummary.started_at)) / 1000)
    : 0;

  // La distance parcourue reste la référence ; sans projection utilisable on
  // retombe sur le rapport entre le temps écoulé et la prévision SimBrief.
  let ratio = null;
  if (projection && flightRouteTotalNm > 0) {
    ratio = (flightRouteTotalNm - projection.remainingNm) / flightRouteTotalNm;
  } else if (elapsedSeconds && plannedEteSeconds) {
    ratio = elapsedSeconds / plannedEteSeconds;
  }

  const percent = ratio === null ? 0 : Math.min(100, Math.max(0, ratio * 100));
  track.style.setProperty("--flight-progress", `${percent.toFixed(2)}%`);
  track.dataset.state = !aircraft ? "offline" : ratio === null ? "unknown" : "live";
  track.setAttribute(
    "aria-label",
    `${t("progress_departure")} ${currentPlan?.departure?.icao || "----"} → `
      + `${t("progress_arrival")} ${currentPlan?.arrival?.icao || "----"} · `
      + `${Math.round(percent)} %`
  );

  liveValue("flight-progress-altitude", progressAltitudeLabel(aircraft, ratio));
  const caption = projection
    ? `${projection.remainingNm.toFixed(0)} NM ${t("progress_before_arrival")}`
    : plannedEteSeconds
      ? `${hhmm(plannedEteSeconds)} ${t("progress_planned_suffix")}`
      : "—";
  liveValue(
    "flight-progress-caption",
    ratio === null ? caption : `${caption} · ${Math.round(percent)} %`
  );
  liveValue("flight-progress-elapsed", hhmm(elapsedSeconds) || "—");
  liveValue("flight-progress-total", hhmm(plannedEteSeconds) || "—");
  liveValue("flight-progress-remaining", hhmm(remainingSeconds) || "—");
}

function updateFlightPanel(aircraft) {
  const projection = projectAircraftOnFlightPath(aircraft);
  const phaseKey = detectFlightPhaseKey(aircraft, projection);
  const phase = t(phaseKey);
  const constraint = nextFlightConstraint(currentPlan, projection, aircraft || {});
  const descent = descentGuidance(currentPlan, aircraft, projection);

  updateConfigurationBlock(aircraft);
  updateFlightEvents(aircraft, phaseKey);
  renderFlightEvents();
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

  // Temps de vol prévu par SimBrief, puis temps restant estimé sur la vitesse
  // sol réelle. Sous 40 kt la division devient instable : avant le décollage on
  // retombe sur la prévision SimBrief, et après l'arrivée on n'affiche plus rien.
  const plannedEteSeconds = Number(currentPlan?.dispatch?.time_enroute_s || 0);
  const groundSpeedKt = Number(aircraft?.ground_speed_kt || 0);
  const arrived = projection ? projection.remainingNm <= 5 : false;
  let remainingSeconds = null;
  if (projection && groundSpeedKt >= 40) {
    remainingSeconds = (projection.remainingNm / groundSpeedKt) * 3600;
  } else if (plannedEteSeconds && !arrived && (!aircraft || aircraft.on_ground)) {
    remainingSeconds = plannedEteSeconds;
  }
  updateFlightProgress(aircraft, projection, remainingSeconds, plannedEteSeconds);

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
      : t("none")
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
      ? tf("tod_in", { distance: descent.todInNm.toFixed(0) })
      : descent.todInNm >= -2
        ? t("tod_now")
        : tf("tod_passed", { distance: Math.abs(descent.todInNm).toFixed(0) });
    liveValue("flight-tod", todText, descent.todInNm < -2 ? "warning" : "good");
    liveValue("flight-descent-vs", `${descent.requiredVsFpm} ft/min`);
    const verticalSpeed = Number(aircraft?.vertical_speed_fpm || 0);
    const profileActive = (
      phase === t("phase_descent")
      || phase === t("phase_approach")
      || verticalSpeed < -300
      || descent.todInNm <= 2
    );
    if (!profileActive) {
      const waiting = descent.todInNm > 2
        ? tf("profile_waiting", { distance: descent.todInNm.toFixed(0) })
        : t("profile_available_descent");
      liveValue("flight-vertical-profile", waiting);
    } else {
      const delta = descent.profileDeltaFt;
      // Une marge de 500 ft évite une alerte instable due à l'arrondi du
      // profil 3°, au QNH et aux points de procédure rapprochés.
      liveValue(
        "flight-vertical-profile",
        Math.abs(delta) <= 500
          ? t("profile_correct")
          : delta > 0
            ? tf("profile_high", { distance: Math.abs(delta) })
            : tf("profile_low", { distance: Math.abs(delta) }),
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
  // La chronologie ne suit que le plan : un changement de langue reconstruit
  // le panneau sans effacer ce que le vol en cours a déjà enregistré.
  if (flightEventsPlanKey !== flightSummaryPlanKey(plan)) {
    resetFlightEvents();
    flightEventsPlanKey = flightSummaryPlanKey(plan);
  }
  flightEventsRenderKey = "";
  resetAlertStates();
  const panel = $("panel-flight");
  panel.innerHTML = "";
  const header = el("div", "flight-panel-head");
  const title = el("div");
  title.append(el("div", "card-kicker", t("flight_guidance")));
  title.append(el("h2", null, t("flight_tracking_title")));
  header.append(title);
  const pills = el("div", "flight-panel-pills");
  const master = el("span", "flight-alert-pill", t("alerts_none"));
  master.id = "flight-alert-master";
  master.dataset.severity = "none";
  pills.append(master);
  const phase = el("span", "flight-phase-pill", t("phase_offline"));
  phase.id = "flight-phase";
  pills.append(phase);
  header.append(pills);
  panel.append(header);

  const alerts = el("div", "flight-alerts");
  alerts.id = "flight-alerts";
  alerts.setAttribute("role", "status");
  alerts.setAttribute("aria-live", "polite");
  panel.append(alerts);

  panel.append(buildFlightProgressSection(plan));

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
  item(t("flight_next_fix"), "flight-next-fix");
  item(t("flight_fix_distance"), "flight-next-distance");
  item(t("flight_lateral_deviation"), "flight-deviation", t("flight_lateral_deviation_note"));
  item(t("flight_remaining_distance"), "flight-remaining");
  item(t("ground_speed"), "flight-ground-speed", t("ground_speed_note"));
  item(t("air_speed"), "flight-air-speed", t("air_speed_note"));
  item(t("flight_next_constraint"), "flight-next-constraint");
  item(t("flight_constraint_distance"), "flight-constraint-distance");
  item(t("flight_required_rate"), "flight-required-vs", t("flight_required_rate_note"));
  item("Top of Descent", "flight-tod");
  item(t("flight_vertical_profile"), "flight-vertical-profile", t("flight_vertical_profile_note"));
  item(t("flight_descent_rate"), "flight-descent-vs", t("flight_descent_rate_note"));
  panel.append(grid);

  panel.append(buildConfigurationSection());
  panel.append(buildFlightEventsSection());

  const journal = el("section", "flight-summary");
  const journalHead = el("div", "flight-summary-head");
  const journalTitle = el("div");
  journalTitle.append(el("div", "card-kicker", t("local_journal")));
  journalTitle.append(el("h2", null, t("flight_summaries")));
  const purge = el("button", "icon-btn", t("purge_history"));
  purge.id = "flight-summary-purge";
  purge.type = "button";
  purge.addEventListener("click", () => {
    if (!window.confirm(t("purge_history_confirm"))) return;
    purgeFlightHistory();
  });
  journalHead.append(journalTitle, purge);
  journal.append(journalHead);
  journal.append(el(
    "p",
    "flight-summary-note",
    t("flight_summary_note")
  ));
  const summaryList = el("div", "flight-summary-list");
  summaryList.id = "flight-summary-list";
  journal.append(summaryList);
  panel.append(journal);
  renderFlightSummaries();
  updateFlightPanel(latestAircraft);
}

const PLANNER_OVERRIDE_DEPENDENCIES = {
  departure_runway: ["sid", "sid_transition"],
  sid: ["sid_transition"],
  arrival_runway: ["star", "star_transition", "approach", "approach_transition"],
  star: ["star_transition", "approach", "approach_transition"],
  approach: ["approach_transition"],
};

// Sentinelle du choix « automatique » : elle ne peut pas être vide, sinon le
// menu la confondrait avec son intitulé d'invite, ni ressembler à un identifiant
// de procédure. Elle repasse la main au moteur en effaçant la surcharge.
const PLANNER_OVERRIDE_AUTO = "__auto__";

// Le bouton doit désigner sa liste par `aria-controls` : chaque ligne a donc
// besoin d'un identifiant qui lui est propre, y compris après un nouveau rendu.
let choiceSelectSequence = 0;

/** Crayon discret : un choix se corrige, il ne se réclame pas. */
function pencilMark() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute(
    "d",
    "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 "
    + "0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
  );
  path.setAttribute("fill", "currentColor");
  svg.append(path);
  return svg;
}

async function applyPlannerOverride(field, value) {
  for (const dependent of PLANNER_OVERRIDE_DEPENDENCIES[field] || []) {
    delete plannerOverrides[dependent];
  }
  if (value === null) {
    delete plannerOverrides[field];
    await buildPlan({ ...plannerOverrides });
    return;
  }
  await buildPlan({ [field]: value });
}

function alternativeLabel(alternative) {
  const details = [];
  if (Number.isFinite(alternative.headwind_kt)) {
    const sign = alternative.headwind_kt >= 0 ? "+" : "";
    details.push(tf("headwind_short", { wind: `${sign}${Math.round(alternative.headwind_kt)}` }));
  }
  if (Number.isFinite(alternative.crosswind_kt)) {
    details.push(tf("crosswind_short", { wind: Math.round(alternative.crosswind_kt) }));
  }
  return [alternative.value, ...details].join(" · ");
}

function choiceRow(label, choice, note, overrideField = null) {
  const sourceKey = SOURCE_LABEL[choice.source];
  const source = sourceKey && sourceKey !== "SimBrief" ? t(sourceKey) : (sourceKey || choice.source);
  const reason = [source, plannerText(choice.reason)]
    .filter(Boolean)
    .join(" · ");
  const parts = [note, reason].filter(Boolean).join(" — ");
  const confidence = t(`confidence_${confidenceClass(choice)}`);
  const confidenceDescription = [confidence, parts].filter(Boolean).join(" — ");

  // Un choix vide n'a pas de valeur à cadrer : un tiret sur une ligne et son
  // explication sur la suivante occupent la hauteur d'une procédure réelle pour
  // dire qu'il n'y en a pas. L'explication tient donc lieu de valeur, sur une
  // seule ligne resserrée.
  const empty = !choice.value;
  const row = el("div", `row${empty ? " row-empty" : ""}`);
  row.append(el("span", "row-label", label));
  row.append(el(
    "span",
    `row-value${empty ? " empty" : ""}`,
    empty ? (parts || "—") : choice.value
  ));

  const dot = el("span", `dot ${confidenceClass(choice)}`);
  dot.setAttribute("role", "img");
  dot.setAttribute("aria-label", confidenceDescription);
  dot.title = confidenceDescription;
  const actions = el("span", "row-actions");
  actions.append(dot);
  row.append(actions);
  if (parts && !empty) row.append(el("span", "row-reason", parts));

  const alternatives = (choice.alternatives || []).filter(
    (alternative) => alternative?.value && !alternative.disqualified
  );
  // Le sélecteur n'est pas réservé aux rattrapages : le moteur propose, le
  // pilote dispose. Il s'ouvre dès qu'une autre procédure publiée existe, y
  // compris sur un choix sûr, et aussi quand le moteur n'a rien retenu — une
  // STAR publiée pour une autre piste n'est plus enchaînée d'office, mais elle
  // reste imposable par qui sait pourquoi il la veut.
  if (overrideField && alternatives.length && !latestStatus?.remote_client) {
    const overridden = Boolean(plannerOverrides[overrideField]);
    const select = el("select", "choice-select hidden");
    select.id = `choice-select-${++choiceSelectSequence}`;
    select.setAttribute("aria-label", tf("change_choice", { label }));
    select.title = tf("change_choice", { label });
    const prompt = el("option", null, t("change_choice_action"));
    prompt.value = "";
    prompt.selected = true;
    select.append(prompt);
    for (const alternative of alternatives) {
      const option = el("option", null, alternativeLabel(alternative));
      option.value = alternative.value;
      select.append(option);
    }
    // Une surcharge doit rester réversible : sans cette entrée, un choix imposé
    // ne peut plus être rendu au moteur sans refaire le plan complet.
    if (overridden) {
      const auto = el("option", null, t("reset_choice_action"));
      auto.value = PLANNER_OVERRIDE_AUTO;
      select.append(auto);
    }
    select.addEventListener("change", async () => {
      if (!select.value) return;
      const next = select.value === PLANNER_OVERRIDE_AUTO ? null : select.value;
      select.disabled = true;
      try {
        await applyPlannerOverride(overrideField, next);
      } finally {
        select.disabled = false;
      }
    });

    // Un panneau de vol se lit d'abord, il ne se règle qu'ensuite : le crayon
    // reste en retrait tant qu'on ne survole pas la ligne, et n'ouvre la liste
    // que si on le demande. Un choix déjà imposé le garde allumé, sinon rien
    // ne distinguerait une valeur calculée d'une valeur forcée.
    const toggle = el("button", `choice-edit${overridden ? " overridden" : ""}`);
    toggle.type = "button";
    toggle.setAttribute("aria-controls", select.id);
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", tf("change_choice", { label }));
    toggle.title = tf("change_choice", { label });
    toggle.append(pencilMark());
    toggle.addEventListener("click", () => {
      const opened = select.classList.contains("hidden");
      show(select, opened);
      toggle.setAttribute("aria-expanded", String(opened));
      toggle.classList.toggle("active", opened);
      if (opened) select.focus();
    });
    actions.append(toggle);
    row.append(select);
  }
  return row;
}

function terminalCard(block, kicker, runwayOverrideField, extraRows) {
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
    rows.append(choiceRow(t("runway"), block.runway, runwayNote(block.runway), runwayOverrideField));
  }
  for (const [label, choice, note, overrideField] of extraRows) {
    rows.append(choiceRow(label, choice, note, overrideField));
  }
  card.append(rows);
  return card;
}

function windLabel(wind) {
  if (!wind) return "";
  if (wind.variable) return `VRB ${wind.speed_kt ?? 0} kt`;
  if (wind.direction_deg === null || wind.direction_deg === undefined) {
    return wind.speed_kt === 0 ? t("wind_calm") : t("wind_unknown");
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
    bits.push(tf("headwind_short", { wind: `${sign}${Math.round(runway.headwind_kt)}` }));
  }
  if (runway.crosswind_kt !== null && runway.crosswind_kt !== undefined) {
    bits.push(tf("crosswind_short", { wind: Math.round(runway.crosswind_kt) }));
  }
  if (runway.length_ft) bits.push(`${Math.round(runway.length_ft).toLocaleString(displayLocale())} ft`);
  if (runway.ils_ident) bits.push(`ILS ${runway.ils_ident}`);
  return bits.join(" · ");
}

/** Ligne de transition, tue si la procédure dont elle dépend n'existe pas.
 *
 * Sans SID il n'y a pas de sortie de SID, sans STAR il n'y a pas d'entrée de
 * STAR : la ligne ne dirait rien de plus que celle du dessus, sur un panneau où
 * la place se compte.
 */
function transitionRows(procedure, transition, label, note, overrideField) {
  if (!procedure.value) return [];
  return [[label, transition, note, overrideField]];
}

function renderTerminal(plan) {
  const departure = $("card-departure");
  departure.innerHTML = "";
  if (plan.departure) {
    departure.append(
      terminalCard(plan.departure, t("departure_title"), "departure_runway", [
        ["SID", plan.departure.sid, "", "sid"],
        ...transitionRows(
          plan.departure.sid, plan.departure.sid_transition,
          t("transition"), t("sid_exit_note"), "sid_transition",
        ),
      ])
    );
    if (plan.departure.transition_altitude_ft) {
      departure.append(
        el("span", "badge", tf("transition_altitude", { altitude: plan.departure.transition_altitude_ft }))
      );
    }
  }

  const route = $("card-route");
  route.innerHTML = "";
  route.append(el("div", "card-kicker", t("route_title")));
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
      terminalCard(plan.arrival, t("arrival_title"), "arrival_runway", [
        ["STAR", plan.arrival.star, "", "star"],
        ...transitionRows(
          plan.arrival.star, plan.arrival.star_transition,
          t("transition"), t("star_entry_note"), "star_transition",
        ),
        [t("approach"), plan.arrival.approach, "", "approach"],
        ...transitionRows(
          plan.arrival.approach, plan.arrival.approach_transition,
          t("approach_transition_short"), t("approach_transition_note"),
          "approach_transition",
        ),
      ])
    );
    const badges = el("div", "route-meta");
    if (plan.arrival.ils_frequency_mhz) {
      badges.append(el("span", "badge", `ILS ${plan.arrival.ils_frequency_mhz.toFixed(2)} MHz`));
    }
    if (plan.arrival.missed_approach_altitude_ft) {
      badges.append(el("span", "badge", tf("missed_approach", { altitude: plan.arrival.missed_approach_altitude_ft })));
    }
    if (plan.arrival.transition_level_ft) {
      badges.append(el("span", "badge", tf("transition_level", { altitude: plan.arrival.transition_level_ft })));
    }
    if (badges.childElementCount) arrival.append(badges);
  }
}

/* ----------------------------------------------------------- constraints */

function constraintTable(title, rows) {
  const wrapper = el("div");
  wrapper.append(el("div", "section-title", title));
  if (!rows?.length) {
    wrapper.append(el("p", "stat-note", t("cst_empty")));
    return wrapper;
  }
  const table = el("table");
  const head = el("thead");
  const headRow = el("tr");
  for (const key of ["cst_fix", "cst_altitude", "cst_speed"]) headRow.append(el("th", null, t(key)));
  head.append(headRow);
  table.append(head);

  const body = el("tbody");
  for (const row of rows) {
    const line = el("tr");
    line.append(el("td", `fix${row.is_fix ? "" : " segment"}`, row.label));
    line.append(el("td", "constraint", constraintText(row.altitude) || "—"));
    line.append(el("td", "constraint", constraintText(row.speed) || "—"));
    body.append(line);
  }
  table.append(body);
  wrapper.append(table);
  return wrapper;
}

function altitudeInstruction(altitude) {
  if (!altitude) return "";
  if (altitude.startsWith("≥ ")) {
    return tf("cst_not_below", { altitude: altitude.slice(2) });
  }
  if (altitude.startsWith("≤ ")) {
    return tf("cst_at_or_below", { altitude: altitude.slice(2) });
  }
  if (altitude.startsWith("entre ")) {
    return tf("cst_stay", { altitude: constraintText(altitude) });
  }
  return tf("cst_maintain", { altitude });
}

function approachProfile(arrival) {
  const wrapper = el("div", "approach-profile");
  const head = el("div", "approach-profile-head");
  const title = el("div");
  title.append(el("div", "card-kicker", t("vprof_kicker")));
  title.append(el(
    "h2",
    null,
    `${arrival.approach?.value || t("vprof_approach")}${arrival.runway?.value ? ` · RWY ${arrival.runway.value}` : ""}`
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
      [t("vprof_loc"), arrival.ils_course_deg !== null && arrival.ils_course_deg !== undefined
        ? `${String(Math.round(arrival.ils_course_deg)).padStart(3, "0")}°`
        : null],
      [t("vprof_slope"), arrival.glide_slope_deg
        ? `${Number(arrival.glide_slope_deg).toFixed(2)}°`
        : null],
      [t("vprof_intercept"), constraintText(arrival.glide_intercept_altitude), true],
      [t("vprof_point"), arrival.glide_intercept_fix],
      [t("vprof_final"), arrival.final_approach_distance_nm
        ? `${arrival.final_approach_distance_nm.toFixed(1)} NM`
        : null],
    ];
    for (const [label, value, primary] of items) {
      if (!value) continue;
      const item = el("div", primary ? "final-item primary" : "final-item");
      item.append(el("span", null, label));
      item.append(el("strong", null, value));
      briefing.append(item);
    }
    wrapper.append(briefing);

    if (arrival.glide_intercept_altitude) {
      wrapper.append(el(
        "p",
        "intercept-explanation",
        tf("vprof_intercept_note", {
          instruction: altitudeInstruction(arrival.glide_intercept_altitude),
          fix: arrival.glide_intercept_fix || t("vprof_intercept_fallback"),
        })
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
      step.append(el("strong", null, constraintText(row.altitude)));
      step.append(el("small", null, altitudeInstruction(row.altitude)));
      if (row.speed) step.append(el("small", "altitude-speed", constraintText(row.speed)));
      flow.append(step);
    });
    wrapper.append(flow);
  } else {
    wrapper.append(el("p", "stat-note", t("vprof_empty")));
  }

  if (arrival.missed_approach_altitude_ft) {
    const missed = el("div", "missed-altitude");
    missed.append(el("span", null, t("vprof_missed")));
    missed.append(el("strong", null, `${arrival.missed_approach_altitude_ft} ft`));
    wrapper.append(missed);
  }
  wrapper.append(el("p", "approach-caution", t("vprof_caution")));
  return wrapper;
}

function renderConstraints(plan) {
  const panel = $("panel-constraints");
  panel.innerHTML = "";
  if (plan.arrival) panel.append(approachProfile(plan.arrival));
  if (plan.departure) {
    panel.append(
      constraintTable(
        tf("cst_sid", { procedure: plan.departure.sid.value || "" }).trim(),
        plan.departure.sid_constraints
      )
    );
  }
  if (plan.arrival) {
    panel.append(
      constraintTable(
        tf("cst_star", { procedure: plan.arrival.star.value || "" }).trim(),
        plan.arrival.star_constraints
      )
    );
    panel.append(
      constraintTable(
        tf("cst_approach", { procedure: plan.arrival.approach.value || "" }).trim(),
        plan.arrival.approach_constraints
      )
    );
  }
}

/* -------------------------------------------------------------- dispatch */

/**
 * Tuile de dispatch.
 *
 * `live` ajoute une seconde ligne alimentée par SimConnect : la tuile survit
 * alors à l'absence de valeur OFP, puisque le relevé réel garde un sens même
 * quand SimBrief n'a pas fourni la prévision correspondante.
 */
function stat(label, value, note, fill, live) {
  const missing = value === null || value === undefined || value === "";
  if (missing && !live) return null;
  const node = el("div", "stat");
  node.append(el("div", "stat-label", label));
  node.append(el("div", "stat-value", missing ? "—" : value));
  if (note) node.append(el("div", "stat-note", note));
  if (fill !== undefined && fill !== null) {
    const meter = el("div", `meter${fill > 1 ? " over" : ""}`);
    const bar = el("span");
    bar.style.width = `${Math.min(100, Math.round(fill * 100))}%`;
    meter.append(bar);
    node.append(meter);
  }
  if (live) node.append(dispatchLiveRow(live.id, live.label));
  return node;
}

/** Ligne « réel » d'une tuile de dispatch, remplie par `updateDispatchLive`. */
function dispatchLiveRow(id, label) {
  const row = el("div", "stat-live");
  row.id = id;
  row.append(el("span", "stat-live-label", label));
  row.append(el("span", "stat-live-value", "—"));
  row.append(el("span", "stat-live-delta", ""));
  return row;
}

/** Tuile sans équivalent OFP : la valeur principale vient du simulateur. */
function liveOnlyStat(label, id, note) {
  const node = el("div", "stat");
  node.append(el("div", "stat-label", label));
  const value = el("div", "stat-value", "—");
  value.id = id;
  node.append(value);
  if (note) node.append(el("div", "stat-note", note));
  return node;
}

function kg(value, unit) {
  if (value === null || value === undefined) return null;
  return `${value.toLocaleString(displayLocale())} ${unit}`;
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

/* ------------------------------------------------- suivi dispatch en direct */

/*
 * Le dispatch de l'OFP est une prévision figée au moment de la génération.
 * Ce suivi lui superpose ce que le simulateur mesure réellement : carburant
 * embarqué, consommation, masses et temps écoulés. Rien n'est renvoyé au
 * serveur, tout est calculé à partir de `/api/live`.
 *
 * Le temps est compté en secondes simulées — horloge murale multipliée par le
 * taux de simulation — sans quoi un vol accéléré donnerait une consommation
 * horaire plusieurs fois trop élevée.
 */

function emptyDispatchLive(planKey) {
  return {
    plan_key: planKey,
    block_fuel_kg: null,
    off_block_sim_s: null,
    takeoff_sim_s: null,
    takeoff_weight_kg: null,
    landing_sim_s: null,
    landing_fuel_kg: null,
    landing_weight_kg: null,
    flow_kg_per_h: null,
    sim_seconds: 0,
    sampled_at: null,
    samples: [],
    seen_on_ground: false,
    airborne: false,
  };
}

function loadDispatchLive(planKey) {
  try {
    const parsed = JSON.parse(localStorage.getItem(DISPATCH_LIVE_KEY) || "null");
    if (parsed && parsed.plan_key === planKey) {
      return { ...emptyDispatchLive(planKey), ...parsed, sampled_at: null };
    }
  } catch (_error) {
    // Un suivi illisible n'empêche pas d'en démarrer un neuf.
  }
  return emptyDispatchLive(planKey);
}

function saveDispatchLive() {
  try {
    localStorage.setItem(DISPATCH_LIVE_KEY, JSON.stringify(dispatchLive));
  } catch (_error) {
    // Le suivi reste utilisable en mémoire même si le stockage est plein.
  }
}

/** Consommation horaire moyenne sur la fenêtre glissante, en kg/h. */
function dispatchFuelFlow(samples) {
  if (samples.length < 2) return null;
  const first = samples[0];
  const last = samples.at(-1);
  const seconds = last.sim_s - first.sim_s;
  const burned = first.fuel_kg - last.fuel_kg;
  if (seconds < 60 || burned <= 0) return null;
  return (burned / seconds) * 3600;
}

/** Intègre un état SimConnect dans le suivi : jalons, fenêtre de consommation. */
function ingestDispatchSample(aircraft) {
  if (!currentPlan || !aircraft) return;
  const planKey = flightSummaryPlanKey(currentPlan);
  if (!dispatchLive || dispatchLive.plan_key !== planKey) {
    dispatchLive = loadDispatchLive(planKey);
  }
  const state = dispatchLive;

  const now = Date.now();
  const rate = finiteOr(aircraft.configuration?.simulation_rate, 1) || 1;
  const elapsedMs = state.sampled_at ? now - state.sampled_at : 0;
  // Fenêtre masquée, simulateur en pause, reconnexion : au-delà de quelques
  // secondes de trou l'échantillonnage n'est plus exploitable.
  if (elapsedMs > DISPATCH_GAP_MS) state.samples = [];
  else if (elapsedMs > 0) state.sim_seconds += (elapsedMs / 1000) * rate;
  state.sampled_at = now;

  const fuelKg = finiteOr(aircraft.configuration?.fuel_total_kg);
  const weightKg = finiteOr(aircraft.configuration?.total_weight_kg);
  const onGround = aircraft.on_ground === true;
  const groundSpeedKt = finiteOr(aircraft.ground_speed_kt, 0);

  if (onGround) {
    state.seen_on_ground = true;
    // Avitaillement : au sol, le plein le plus élevé devient le carburant bloc.
    if (fuelKg !== null && (state.block_fuel_kg === null || fuelKg > state.block_fuel_kg + 1)) {
      state.block_fuel_kg = fuelKg;
      state.samples = [];
    }
    if (state.off_block_sim_s === null && groundSpeedKt > 3) {
      state.off_block_sim_s = state.sim_seconds;
    }
  }

  // Les jalons ne sont pris que si le vol a été suivi depuis le sol : démarrer
  // NaviXav en croisière ne doit pas inventer une heure de décollage.
  if (!onGround && !state.airborne) {
    state.airborne = true;
    // Remise en l'air après un poser : les valeurs d'arrivée capturées ne
    // décrivent plus la fin du vol, les projections reprennent la main.
    state.landing_sim_s = null;
    state.landing_fuel_kg = null;
    state.landing_weight_kg = null;
    if (state.takeoff_sim_s === null && state.seen_on_ground) {
      state.takeoff_sim_s = state.sim_seconds;
      state.takeoff_weight_kg = weightKg;
    }
  } else if (onGround && state.airborne) {
    state.airborne = false;
    state.landing_sim_s = state.sim_seconds;
    state.landing_fuel_kg = fuelKg;
    state.landing_weight_kg = weightKg;
  }

  const last = state.samples.at(-1);
  if (fuelKg !== null && (!last || state.sim_seconds - last.sim_s >= DISPATCH_SAMPLE_INTERVAL_S)) {
    // Une remontée de niveau en vol signale un changement d'appareil ou un
    // repositionnement : la moyenne repart de zéro plutôt que de mentir.
    if (last && fuelKg > last.fuel_kg + 1) state.samples = [];
    state.samples.push({ sim_s: state.sim_seconds, fuel_kg: fuelKg });
    while (
      state.samples.length > 2
      && state.sim_seconds - state.samples[0].sim_s > DISPATCH_FLOW_WINDOW_S
    ) {
      state.samples.shift();
    }
    state.flow_kg_per_h = dispatchFuelFlow(state.samples);
    saveDispatchLive();
  }
}

function setDispatchLiveCell(id, value, delta = "", status = "") {
  const node = $(id);
  if (!node) return;
  const valueNode = node.querySelector(".stat-live-value") || node;
  valueNode.textContent = value === null || value === undefined || value === "" ? "—" : value;
  const deltaNode = node.querySelector(".stat-live-delta");
  if (deltaNode) deltaNode.textContent = delta || "";
  node.closest(".stat")?.setAttribute("data-live-status", status);
}

function dispatchDelta(actual, planned, unit) {
  if (actual === null || actual === undefined) return "";
  const reference = finiteOr(planned);
  if (reference === null) return "";
  const delta = Math.round(actual - reference);
  if (!delta) return `= ${t("dispatch_as_planned")}`;
  return `${delta > 0 ? "+" : "−"}${Math.abs(delta).toLocaleString(displayLocale())} ${unit}`;
}

/**
 * Recalcule les valeurs réelles et les projections du panneau Dispatch.
 *
 * `aircraft` vaut null quand le simulateur est absent : les relevés instantanés
 * et les projections repassent à « — », les jalons déjà capturés restent.
 */
function renderDispatchLiveCells(aircraft) {
  const d = currentPlan?.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb", kgs: "kg", lbs: "lb" }[d.units] || d.units || "";
  const pounds = String(d.units || "").toLowerCase().startsWith("lb");
  const toUnit = (valueKg) => (valueKg === null || valueKg === undefined
    ? null
    : Math.round(pounds ? valueKg / LBS_TO_KG : valueKg));
  const state = dispatchLive;

  const configuration = aircraft?.configuration || {};
  const fuelKg = finiteOr(configuration.fuel_total_kg);
  const weightKg = finiteOr(configuration.total_weight_kg);
  const projection = aircraft ? projectAircraftOnFlightPath(aircraft) : null;
  const groundSpeedKt = finiteOr(aircraft?.ground_speed_kt, 0);
  const landed = Boolean(state?.landing_sim_s !== null && state?.landing_sim_s !== undefined);

  const badge = $("dispatch-live-state");
  if (badge) {
    let key = "dispatch_live_waiting";
    if (aircraft && landed && aircraft.on_ground) key = "dispatch_live_arrived";
    else if (aircraft && !aircraft.on_ground) key = "dispatch_live_airborne";
    else if (aircraft) key = "dispatch_live_ground";
    badge.textContent = t(key);
  }

  // Temps restant estimé sur la vitesse sol réelle, comme l'onglet Suivi du vol.
  const remainingSeconds = projection && groundSpeedKt >= 40
    ? (projection.remainingNm / groundSpeedKt) * 3600
    : null;

  const flowKgPerH = finiteOr(state?.flow_kg_per_h);
  let landingFuelKg = landed ? finiteOr(state?.landing_fuel_kg) : null;
  if (landingFuelKg === null && fuelKg !== null && remainingSeconds !== null && flowKgPerH !== null) {
    landingFuelKg = Math.max(0, fuelKg - flowKgPerH * (remainingSeconds / 3600));
  }

  const blockFuel = toUnit(state?.block_fuel_kg);
  const onboard = toUnit(fuelKg);
  const burned = state?.block_fuel_kg !== null && state?.block_fuel_kg !== undefined && fuelKg !== null
    ? toUnit(Math.max(0, state.block_fuel_kg - fuelKg))
    : null;
  const flow = toUnit(flowKgPerH);
  const landingFuel = toUnit(landingFuelKg);

  setDispatchLiveCell("dispatch-live-block", kg(blockFuel, unit), dispatchDelta(blockFuel, d.block_fuel, unit));
  setDispatchLiveCell("dispatch-live-onboard", kg(onboard, unit));
  setDispatchLiveCell("dispatch-live-burn", kg(burned, unit));
  setDispatchLiveCell("dispatch-live-flow", kg(flow, `${unit}/h`), dispatchDelta(flow, d.average_fuel_flow, `${unit}/h`));

  // Le carburant projeté à l'arrivée est le chiffre qui décide d'un déroutement :
  // sous la réserve finale il est rouge, sous réserve + dégagement il alerte.
  const reserve = finiteOr(d.reserve_fuel);
  const alternate = finiteOr(d.alternate_fuel, 0);
  let landingFuelStatus = "";
  if (landingFuel !== null && reserve !== null) {
    if (landingFuel < reserve) landingFuelStatus = "danger";
    else if (landingFuel < reserve + alternate) landingFuelStatus = "warning";
    else landingFuelStatus = "good";
  }
  setDispatchLiveCell(
    "dispatch-live-landing-fuel",
    kg(landingFuel, unit),
    dispatchDelta(landingFuel, d.landing_fuel, unit),
    landingFuelStatus
  );

  const takeoffWeight = toUnit(state?.takeoff_weight_kg);
  setDispatchLiveCell(
    "dispatch-live-tow",
    kg(takeoffWeight, unit),
    dispatchDelta(takeoffWeight, d.takeoff_weight, unit),
    takeoffWeight !== null && d.max_takeoff_weight && takeoffWeight > d.max_takeoff_weight ? "danger" : ""
  );

  let landingWeightKg = landed ? finiteOr(state?.landing_weight_kg) : null;
  if (landingWeightKg === null && weightKg !== null && fuelKg !== null && landingFuelKg !== null) {
    landingWeightKg = weightKg - (fuelKg - landingFuelKg);
  }
  const landingWeight = toUnit(landingWeightKg);
  const maxLanding = finiteOr(d.max_landing_weight);
  let landingWeightStatus = "";
  if (landingWeight !== null && maxLanding) {
    if (landingWeight > maxLanding) landingWeightStatus = "danger";
    else if (landingWeight > maxLanding * 0.98) landingWeightStatus = "warning";
    else landingWeightStatus = "good";
  }
  setDispatchLiveCell(
    "dispatch-live-ldw",
    kg(landingWeight, unit),
    dispatchDelta(landingWeight, d.landing_weight, unit),
    landingWeightStatus
  );

  const simNow = finiteOr(state?.sim_seconds, 0);
  const endSim = landed ? state.landing_sim_s : simNow;
  const airborneSeconds = state?.takeoff_sim_s === null || state?.takeoff_sim_s === undefined
    ? null
    : Math.max(0, endSim - state.takeoff_sim_s);
  const blockSeconds = state?.off_block_sim_s === null || state?.off_block_sim_s === undefined
    ? null
    : Math.max(0, endSim - state.off_block_sim_s);

  // Temps de vol total estimé : ce qui est déjà volé plus ce qui reste.
  let eteDelta = "";
  if (airborneSeconds !== null && remainingSeconds !== null && d.time_enroute_s) {
    const minutes = Math.round((airborneSeconds + remainingSeconds - d.time_enroute_s) / 60);
    eteDelta = minutes ? `${minutes > 0 ? "+" : "−"}${Math.abs(minutes)} min` : `= ${t("dispatch_as_planned")}`;
  }
  setDispatchLiveCell("dispatch-live-ete", airborneSeconds === null ? null : hhmm(airborneSeconds), eteDelta);
  setDispatchLiveCell("dispatch-live-block-time", blockSeconds === null ? null : hhmm(blockSeconds));

  const remainingNm = projection ? Math.round(projection.remainingNm) : null;
  const flownNm = remainingNm !== null && d.route_distance_nm
    ? Math.max(0, d.route_distance_nm - remainingNm)
    : null;
  setDispatchLiveCell(
    "dispatch-live-distance",
    remainingNm === null ? null : `${remainingNm.toLocaleString(displayLocale())} NM`,
    flownNm === null ? "" : `${t("dispatch_flown")} ${flownNm.toLocaleString(displayLocale())} NM`
  );
}

/**
 * Point d'entrée appelé à chaque relevé live.
 *
 * L'échantillonnage suit la boucle à 1 Hz — une moyenne de consommation a
 * besoin de points réguliers — mais le panneau n'est repeint que toutes les
 * deux secondes, largement assez pour lire des masses et un carburant.
 */
function updateDispatchLive(aircraft) {
  if (!$("dispatch-live-state")) return;
  ingestDispatchSample(aircraft);
  const now = Date.now();
  if (now - dispatchLiveRenderedAt < DISPATCH_LIVE_INTERVAL_MS) return;
  dispatchLiveRenderedAt = now;
  renderDispatchLiveCells(aircraft);
}

function renderDispatch(plan) {
  const panel = $("panel-dispatch");
  panel.innerHTML = "";
  const d = plan.dispatch || {};
  const unit = { KGS: "kg", LBS: "lb", kgs: "kg", lbs: "lb" }[d.units] || d.units || "";

  if (!Object.keys(d).length) {
    panel.append(el("p", "stat-note", t("dsp_empty")));
    return;
  }

  const head = el("div", "dispatch-live-head");
  const heading = el("div");
  heading.append(el("div", "section-title", t("dispatch_live_title")));
  heading.append(el("div", "stat-note", t("dispatch_live_hint")));
  const badge = el("span", "badge", t("dispatch_live_waiting"));
  badge.id = "dispatch-live-state";
  head.append(heading, badge);
  panel.append(head);

  const ratioOf = (value, max) => (value && max ? value / max : null);
  const maxNote = (value) => (value ? t("dsp_max").replace("{value}", kg(value, unit)) : null);

  const blocks = [
    group(t("dsp_group_weights"), [
      stat(t("dsp_passengers"), d.passengers, d.bags ? t("dsp_bags").replace("{value}", d.bags) : null),
      stat(t("dsp_payload"), kg(d.payload, unit), d.cargo ? t("dsp_cargo_note").replace("{value}", kg(d.cargo, unit)) : null),
      stat("ZFW", kg(d.zfw, unit), maxNote(d.max_zfw), ratioOf(d.zfw, d.max_zfw)),
      stat(t("dsp_takeoff"), kg(d.takeoff_weight, unit), maxNote(d.max_takeoff_weight), ratioOf(d.takeoff_weight, d.max_takeoff_weight), { id: "dispatch-live-tow", label: t("dispatch_actual") }),
      stat(t("dsp_landing"), kg(d.landing_weight, unit), maxNote(d.max_landing_weight), ratioOf(d.landing_weight, d.max_landing_weight), { id: "dispatch-live-ldw", label: t("dispatch_projected") }),
    ]),
    group(t("dsp_group_fuel"), [
      stat(t("dsp_block"), kg(d.block_fuel, unit), d.max_tanks ? t("dsp_capacity_note").replace("{value}", kg(d.max_tanks, unit)) : null, ratioOf(d.block_fuel, d.max_tanks), { id: "dispatch-live-block", label: t("dispatch_loaded") }),
      liveOnlyStat(t("dsp_onboard"), "dispatch-live-onboard", t("dispatch_onboard_note")),
      stat(t("dsp_trip"), kg(d.trip_fuel, unit), null, null, { id: "dispatch-live-burn", label: t("dispatch_burned") }),
      stat(t("dsp_taxi"), kg(d.taxi_fuel, unit)),
      stat(t("dsp_contingency"), kg(d.contingency_fuel, unit)),
      stat(t("dsp_alternate_fuel"), kg(d.alternate_fuel, unit)),
      stat(t("dsp_reserve"), kg(d.reserve_fuel, unit)),
      stat(t("dsp_landing_fuel"), kg(d.landing_fuel, unit), null, null, { id: "dispatch-live-landing-fuel", label: t("dispatch_projected") }),
      stat(t("dsp_fuel_flow"), kg(d.average_fuel_flow, `${unit}/h`), null, null, { id: "dispatch-live-flow", label: t("dispatch_measured") }),
    ]),
    group(t("dsp_group_profile"), [
      // « Cost index » se lit tel quel dans toutes les langues du cockpit.
      stat("Cost index", d.cost_index),
      stat(t("dsp_cruise"), d.cruise_profile),
      stat(
        t("dsp_average_wind"),
        d.average_wind_direction && d.average_wind_speed
          ? `${d.average_wind_direction}°/${d.average_wind_speed} kt`
          : null,
        d.average_wind_component
          ? t("dsp_wind_component").replace("{value}", d.average_wind_component)
          : null
      ),
      stat(t("dsp_isa_deviation"), d.average_temperature_dev ? `${d.average_temperature_dev} °C` : null),
      stat(t("wx_tropopause"), d.tropopause_ft ? `FL${Math.round(d.tropopause_ft / 100)}` : null),
    ]),
    group(t("dsp_group_distances"), [
      stat(t("dsp_route_distance"), d.route_distance_nm ? `${d.route_distance_nm} NM` : null, null, null, { id: "dispatch-live-distance", label: t("dispatch_remaining") }),
      stat(t("dsp_air_distance"), d.air_distance_nm ? `${d.air_distance_nm} NM` : null),
      stat(t("dsp_great_circle"), d.great_circle_distance_nm ? `${d.great_circle_distance_nm} NM` : null),
      stat(t("dsp_time_enroute"), hhmm(d.time_enroute_s), null, null, { id: "dispatch-live-ete", label: t("dispatch_elapsed") }),
      stat(t("dsp_block_time"), hhmm(d.block_time_s), null, null, { id: "dispatch-live-block-time", label: t("dispatch_elapsed") }),
    ]),
    group(t("dsp_group_alternate"), [
      stat(t("dsp_alternate_airport"), plan.alternate_icao),
      stat(t("dsp_distance"), d.alternate_distance_nm ? `${d.alternate_distance_nm} NM` : null),
      stat(t("dsp_time"), hhmm(d.alternate_time_s)),
      stat(t("dsp_fuel"), kg(d.alternate_burn, unit)),
      stat(t("dsp_level"), d.alternate_altitude_ft ? `FL${Math.round(d.alternate_altitude_ft / 100)}` : null),
    ]),
    group(t("dsp_group_aircraft"), [
      stat(t("dsp_registration"), d.registration),
      stat("SELCAL", d.selcal),
      stat(t("dsp_equipment"), d.equipment),
    ]),
  ].filter(Boolean);

  for (const block of blocks) panel.append(block);

  if (d.alternate_metar) {
    const wrapper = el("div");
    wrapper.append(el("div", "section-title", t("dsp_alternate_metar")));
    wrapper.append(el("div", "card-metar", d.alternate_metar));
    panel.append(wrapper);
  }
  if (d.atc_flightplan_text) {
    const wrapper = el("div");
    wrapper.append(el("div", "section-title", t("dsp_atc_flightplan")));
    wrapper.append(el("pre", null, d.atc_flightplan_text));
    panel.append(wrapper);
  }

  // Le panneau vient d'être reconstruit : le prochain relevé le remplit sans
  // attendre la fenêtre de deux secondes.
  dispatchLiveRenderedAt = 0;
  renderDispatchLiveCells(latestAircraft);
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
  title.append(el("div", "card-kicker", t("acf_kicker")));
  title.append(el("h2", null, plan.aircraft_name || plan.aircraft || t("acf_unknown_type")));
  const badges = el("div", "route-meta");
  if (plan.callsign) badges.append(el("span", "badge", t("acf_flight").replace("{value}", plan.callsign)));
  if (d.registration) badges.append(el("span", "badge", d.registration));
  title.append(badges);
  identity.append(mark, title);
  panel.append(identity);

  const blocks = [
    group(t("acf_group_identification"), [
      stat(t("acf_icao_type"), plan.aircraft),
      stat(t("acf_model"), plan.aircraft_name),
      stat(t("dsp_registration"), d.registration),
      stat(t("acf_callsign"), plan.callsign),
      stat("SELCAL", d.selcal),
    ]),
    group(t("acf_group_equipment"), [
      stat(t("acf_icao_equipment"), d.equipment, t("acf_equipment_note")),
      stat(t("acf_climb_profile"), d.climb_profile),
      stat(t("acf_cruise_profile"), d.cruise_profile),
      stat(t("acf_descent_profile"), d.descent_profile),
      stat("Cost index", d.cost_index),
    ]),
    group(t("acf_group_weights"), [
      stat(t("acf_oew"), kg(d.oew, unit)),
      stat("MZFW", kg(d.max_zfw, unit)),
      stat("MTOW", kg(d.max_takeoff_weight, unit)),
      stat("MLW", kg(d.max_landing_weight, unit)),
      stat(t("acf_fuel_capacity"), kg(d.max_tanks, unit)),
      stat(t("acf_planned_passengers"), d.passengers),
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
  $("map-sia").textContent = tf("chart_overlay", { provider });
  $("map-sia").title = tf("chart_overlay_title", { provider });
  $("sia-overlay-title").textContent = tf("chart_overlay", { provider });
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
  title.append(el("div", "card-kicker", t("sia_kicker")));
  title.append(el("h2", null, t("sia_title")));
  head.append(title);
  const status = el("span", "badge", t("sia_searching_badge"));
  head.append(status);
  wrapper.append(head);
  const content = el("div", "sia-card-content");
  content.append(el("p", "stat-note", t("sia_searching")));
  wrapper.append(content);

  const arrival = plan.arrival;
  if (!arrival?.icao || !arrival?.runway?.value || !arrival?.approach?.value) {
    status.textContent = t("sia_incomplete");
    content.innerHTML = "";
    content.append(el("p", "stat-note", t("sia_no_approach")));
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
        stat(t("min_category"), data.minima.category),
        stat("RADIO / DH", `${data.minima.dh_ft} ft`),
        stat("BARO / DA", `${data.minima.altitude_ft} ft`),
        stat("RVR", `${data.minima.rvr_m} m`)
      );
      content.append(values);

      const use = el("button", "btn-primary", t("sia_use_values"));
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
      content.append(el("p", "approach-caution", t("sia_minima_unreadable")));
    }

    const details = el("details", "sia-chart-preview");
    details.append(el("summary", null, t("sia_show_chart")));
    const frame = el("iframe");
    frame.src = data.pdf_url;
    frame.title = tf("chart_frame_title", {
      provider: officialProviderName(data),
      title: data.chart.title,
    });
    frame.loading = "lazy";
    details.append(frame);
    content.append(details);
    content.append(el("p", "approach-caution", t("sia_extraction_caution")));
  }).catch((error) => {
    status.textContent = t("chart_unavailable");
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
    if (!response.ok) throw new Error(payload.detail || t("chart_catalogue_unavailable"));
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

/*
 * `role` vaut « departure » ou « arrival » : le classement se fait sur les
 * rubriques que le service publie, jamais sur le libellé affiché, qui change
 * avec la langue.
 */
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
    if (role === "departure") {
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

function officialAirportLibrary(icao, role, airport, plan) {
  const roleLabel = t(role === "departure" ? "departure" : "arrival");
  const card = el("article", "sia-airport-library");
  const head = el("div", "sia-library-head");
  const heading = el("div");
  heading.append(el("div", "card-kicker", roleLabel), el("h2", null, icao));
  const status = el("span", "badge", t("chart_loading"));
  head.append(heading, status);
  card.append(head, el("p", "stat-note", t("chart_searching")));

  fetchOfficialAirport(icao).then((data) => {
    if (currentPlan !== plan) return;
    card.replaceChildren(head);
    status.textContent = `${officialProviderName(data)} · AIRAC ${data.effective_date}`;
    if (!data.charts.length) {
      card.append(el("p", "stat-note", t("chart_none")));
      return;
    }

    const controls = el("div", "sia-document-controls");
    const field = el("label", "field");
    field.append(el("span", null, t("chart_document")));
    const select = el("select");
    const groups = new Map();
    data.charts.forEach((chart, index) => {
      if (!groups.has(chart.category)) {
        const group = document.createElement("optgroup");
        group.label = chartCategory(chart.category);
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
    const display = el("button", "btn-primary", t("chart_show_pdf"));
    display.type = "button";
    const external = el("a", "icon-btn", t("chart_open_tab"));
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
      setSiaMapCandidate(role, icao, {
        provider: data.provider,
        source: data.source,
        chart,
        pdf_url: chart.pdf_url,
      });
      availability.textContent = chart.georeferenced
        ? tf("chart_overlay_available", { role: roleLabel.toLowerCase(), icao })
        : tf("chart_overlay_missing", { provider: officialProviderName(data) });
      if (!frame.classList.contains("hidden")) {
        frame.src = chart.pdf_url;
        frame.title = tf("chart_frame_title", {
          provider: officialProviderName(data),
          title: chart.title,
        });
      }
    };
    select.addEventListener("change", updateSelection);
    display.addEventListener("click", () => {
      const chart = data.charts[Number(select.value)];
      card.classList.add("pdf-open");
      frame.src = chart.pdf_url;
      frame.title = tf("chart_frame_title", {
        provider: officialProviderName(data),
        title: chart.title,
      });
      frame.classList.remove("hidden");
    });
    card.append(controls, availability, frame);
    updateSelection();
  }).catch((error) => {
    status.textContent = t("chart_unavailable");
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
    el("div", "card-kicker", t("chart_kicker")),
    el("h2", null, t("chart_title"))
  );
  intro.append(title);
  panel.append(intro, el("p", "stat-note", t("chart_intro")));
  const grid = el("div", "sia-library-grid");
  for (const [role, airport] of [
    ["departure", plan.departure],
    ["arrival", plan.arrival],
  ]) {
    const icao = airport?.icao;
    if (!icao) continue;
    grid.append(officialAirportLibrary(icao, role, airport, plan));
  }
  if (!grid.childElementCount) {
    grid.append(el("p", "stat-note", t("chart_need_plan")));
  }
  panel.append(grid);
}

function minimaEditor(plan, minima) {
  const wrapper = el("form", "minima-editor");
  const header = el("div", "minima-editor-head");
  const title = el("div");
  title.append(el("div", "card-kicker", t("min_kicker")));
  title.append(el("h2", null, t("min_title")));
  header.append(title);
  if (minima.source) header.append(el("span", "badge", t("min_confirmed")));
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

  const category = field(
    t("min_category"), "minima-category", "text", t("min_category_placeholder")
  );
  const modeLabel = el("label", "field");
  modeLabel.append(el("span", null, t("min_field")));
  const mode = el("select");
  mode.id = "minima-mode";
  for (const [value, label] of [["RADIO", "RADIO (DH)"], ["BARO", "BARO (DA/MDA)"]]) {
    const option = el("option", null, label);
    option.value = value;
    mode.append(option);
  }
  modeLabel.append(mode);
  fields.append(modeLabel);
  const dh = field(t("min_dh"), "minima-dh", "number", "ex. 100");
  const altitude = field(t("min_altitude"), "minima-altitude", "number", "ex. 588");
  const rvr = field(t("min_rvr"), "minima-rvr", "number", "ex. 300");

  category.value = minima.category || "";
  mode.value = minima.mode || (plan.arrival?.approach?.value?.includes("ILS") ? "RADIO" : "BARO");
  dh.value = minima.dh_ft || "";
  altitude.value = minima.altitude_ft || "";
  rvr.value = minima.rvr_m || "";
  wrapper.append(fields);

  const actions = el("div", "minima-actions");
  actions.append(el("p", "approach-caution", t("min_note")));
  const save = el("button", "btn-primary", t("min_save"));
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
    el("div", "card-kicker", tf("mcdu_kicker", { system: profile.label })),
    el("h2", null, plan.aircraft_name || plan.aircraft || t("mcdu_unknown_aircraft")),
    el(
      "p",
      null,
      profile.kind === "generic"
        ? t("mcdu_generic_note")
        : tf("mcdu_profile_note", { system: profile.label })
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
        mcduLine("TRANS", dep.sid_transition.value || "—", t("mcdu_sid_exit"), needsCheck(dep.sid_transition)),
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
        mcduLine(profile.approachTransition, arr.approach_transition.value || "—", t("mcdu_approach_transition"), needsCheck(arr.approach_transition)),
        mcduLine("STAR", arr.star.value || "—", null, needsCheck(arr.star)),
        mcduLine(profile.starTransition, arr.star_transition.value || "—", t("mcdu_star_entry"), needsCheck(arr.star_transition)),
        arr.transition_level_ft && mcduLine("TRANS LVL", String(arr.transition_level_ft)),
        arr.missed_approach_altitude_ft &&
          mcduLine("GA ALT", `${arr.missed_approach_altitude_ft} ft`, t("mcdu_missed")),
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
          mcduLine("RADIO", `${minima.dh_ft} ft`, t("mcdu_chart_dh")),
        minima.mode === "BARO" && minima.altitude_ft &&
          mcduLine("BARO", `${minima.altitude_ft} ft`, t("mcdu_chart_da")),
        minima.rvr_m && mcduLine("RVR", `${minima.rvr_m} m`),
        arr.missed_approach_altitude_ft &&
          mcduLine("GA ALT", `${arr.missed_approach_altitude_ft} ft`),
      ]),
  ].filter(Boolean);

  for (const page of pages) screen.append(page);

  const toConfirm = [];
  const check = (label, choice) => { if (needsCheck(choice)) toConfirm.push(label); };
  if (dep) {
    check(t("mcdu_departure_runway"), dep.runway);
    check("SID", dep.sid);
    check(t("mcdu_departure_transition"), dep.sid_transition);
  }
  if (arr) {
    check(t("mcdu_arrival_runway"), arr.runway);
    check("APPR", arr.approach);
    check("VIA", arr.approach_transition);
    check("STAR", arr.star);
    check(t("mcdu_arrival_transition"), arr.star_transition);
  }
  if (toConfirm.length) {
    screen.append(el("div", "mcdu-warn", tf("mcdu_confirm", { items: toConfirm.join(", ") })));
  }

  panel.append(screen);
}

/* ------------------------------------------------------------------ carte */

function renderMapBar(plan) {
  // La carte et le plan de roulage montrent le même terrain : les deux barres
  // portent les mêmes boutons, et changer d'aérodrome depuis l'une suit dans
  // l'autre.
  const bars = [$("map-airports"), $("ground-airports")].filter(Boolean);
  for (const bar of bars) bar.innerHTML = "";

  const entries = [];
  if (plan.departure) {
    entries.push({
      icao: plan.departure.icao,
      runway: plan.departure.runway?.value || null,
      role: t("departure"),
      mapRole: "departure",
    });
  }
  if (plan.arrival) {
    entries.push({
      icao: plan.arrival.icao,
      runway: plan.arrival.runway?.value || null,
      role: t("arrival"),
      mapRole: "arrival",
    });
  }

  for (const bar of bars) {
    for (const entry of entries) {
      const button = el("button", "airport-btn");
      button.dataset.mapRole = entry.mapRole;
      button.textContent = entry.icao;
      button.append(el("small", null, entry.runway ? `${entry.role} · ${entry.runway}` : entry.role));
      button.addEventListener("click", () => loadChart(entry.icao, entry.runway, entry.mapRole));
      bar.append(button);
    }
  }

  if (entries.length) loadChart(entries[0].icao, entries[0].runway, entries[0].mapRole);
}

async function loadChart(icao, runway, mapRole) {
  cancelPendingTaxiRoute();
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
      showBanner("error", tf("chart_unavailable", { icao }), [t("network_error")]);
      return;
    }
    currentChart = await response.json();
    currentIcao = icao;
    currentMapRole = mapRole;
    currentTaxiPlan = null;
    currentTaxiGuidance = null;
    automaticTaxiRouteKey = null;
    syncSiaMapOverlay();
    MAP.setChart(currentChart);
    // Le plan de roulage reçoit le terrain brut, en mètres locaux : il n'a ni
    // tuiles ni route de vol avec lesquelles s'aligner.
    GROUND.setChart(currentChart);
    GROUND.onParkingSelect(requestTaxiRoute);
    updateGroundHud();
    maybeRequestAutomaticTaxiRoute(latestAircraft);
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
      showBanner("warn", t("borrowed_geometry"), [
        tf("borrowed_geometry_body", { source: currentChart.geometry_source }),
      ]);
    }
  } catch (error) {
    showBanner("error", t("network_error"), [String(error)]);
  }
}

function cancelPendingTaxiRoute() {
  taxiRouteRevision += 1;
  taxiRouteRequestController?.abort();
  taxiRouteRequestController = null;
}

/**
 * Projette une position géographique dans le repère monde de la carte.
 *
 * La conversion appartient à `map.js` : route, trace, avion et fond de carte
 * doivent partager exactement la même, sous peine de dériver entre eux.
 */
function projectToChart(latitude, longitude) {
  return MAP.project(latitude, longitude);
}

/**
 * Itinéraire de roulage vers le poste cliqué sur le plan.
 *
 * Le sens découle du rôle du terrain affiché : au départ on va du poste à la
 * piste, à l'arrivée on en revient. La piste est celle que le plan a retenue,
 * déjà mise en évidence — l'utilisateur n'a donc rien à saisir.
 */
async function requestTaxiRoute(parking) {
  const runway = currentChart?.highlight_runway;
  if (!currentIcao || !runway) {
    showBanner("warn", t("taxi_no_runway"), [t("taxi_no_runway_body")]);
    return;
  }

  const params = new URLSearchParams({
    parking,
    runway,
    direction: currentMapRole === "arrival" ? "arrival" : "departure",
  });
  taxiRouteRequestController?.abort();
  const controller = new AbortController();
  taxiRouteRequestController = controller;
  const revision = ++taxiRouteRevision;
  currentTaxiGuidance = null;
  try {
    const response = await fetch(`/api/ground/${currentIcao}/route?${params}`, {
      signal: controller.signal,
    });
    const payload = await response.json();
    if (revision !== taxiRouteRevision) return;
    if (!response.ok) {
      clearTaxiPlan();
      showBanner("warn", t("taxi_unavailable"), [t("taxi_unavailable_body")]);
      return;
    }
    currentTaxiPlan = payload;
    currentTaxiGuidance = null;
    GROUND.setPlan(payload);
    GROUND.fitPlan();
    updateGroundHud();
  } catch (error) {
    if (error?.name === "AbortError") return;
    showBanner("error", t("network_error"), [String(error)]);
  } finally {
    if (taxiRouteRequestController === controller) {
      taxiRouteRequestController = null;
    }
  }
}

/**
 * Propose le roulage depuis le poste où se trouve réellement l'avion.
 *
 * La proposition automatique ne concerne que le départ : à l'arrivée, la
 * position sur la piste ne permet pas de deviner le poste souhaité. Au-delà
 * de 180 m d'un parking, aucune supposition n'est faite.
 */
function maybeRequestAutomaticTaxiRoute(aircraft) {
  if (
    currentTaxiPlan || automaticTaxiRoutePending
    || currentMapRole !== "departure" || !aircraft?.on_ground
  ) return;
  const nearest = GROUND.nearestParking(aircraft);
  if (!nearest || nearest.distance_m > 180) return;
  const key = `${currentIcao}:${currentChart?.highlight_runway}:${nearest.label}`;
  if (automaticTaxiRouteKey === key) return;

  automaticTaxiRouteKey = key;
  automaticTaxiRoutePending = true;
  requestTaxiRoute(nearest.label).finally(() => {
    automaticTaxiRoutePending = false;
  });
}

function clearTaxiPlan() {
  cancelPendingTaxiRoute();
  currentTaxiPlan = null;
  currentTaxiGuidance = null;
  GROUND.setPlan(null);
  updateGroundHud();
}

/**
 * Suit le roulage au fil des positions et reprend l'itinéraire si besoin.
 *
 * L'itinéraire est recalculé côté service à chaque interrogation, sans état de
 * session : le réseau y étant en cache, le calcul complet coûte quelques
 * millisecondes, bien moins que la seconde qui sépare deux positions.
 *
 * Une erreur reste muette. Le guidage au sol est un confort : le signaler
 * chaque seconde couvrirait l'écran de bandeaux pour une information que le
 * pilote lit déjà sur le tracé.
 */
async function pollTaxiGuidance(aircraft) {
  if (!currentTaxiPlan || !currentIcao || taxiRouteRequestController) return;
  // En vol, il n'y a plus rien à guider au sol.
  if (!aircraft?.on_ground) {
    if (currentTaxiGuidance) {
      currentTaxiGuidance = null;
      updateGroundHud();
    }
    return;
  }

  const requestedPlan = currentTaxiPlan;
  const revision = taxiRouteRevision;
  const params = new URLSearchParams({
    parking: requestedPlan.parking.label,
    runway: requestedPlan.runway,
    direction: requestedPlan.direction,
    latitude: aircraft.latitude,
    longitude: aircraft.longitude,
  });
  try {
    const response = await fetch(`/api/ground/${currentIcao}/guidance?${params}`);
    if (!response.ok) return;
    const data = await response.json();
    if (
      revision !== taxiRouteRevision || currentTaxiPlan !== requestedPlan
      || taxiRouteRequestController
    ) return;
    currentTaxiGuidance = data.guidance;
    // Le tracé n'est remplacé que s'il a changé : le redéposer à chaque
    // seconde ramènerait la progression à zéro.
    if (data.recomputed) {
      currentTaxiPlan = data.plan;
      GROUND.setPlan(data.plan);
    }
    GROUND.setProgress(data.guidance?.fix?.travelled_m ?? 0);
    updateGroundHud();
  } catch (error) {
    currentTaxiGuidance = null;
  }
}

/**
 * Bandeau du plan de roulage : la consigne du moment, puis le chemin.
 *
 * Il est distinct de celui de la carte, qui affiche cap, vitesse et altitude.
 * Au sol, aucune de ces valeurs n'aide à trouver sa piste.
 */
function updateGroundHud() {
  const hud = $("ground-hud");
  if (!hud) return;
  hud.innerHTML = "";
  hud.append(el(
    "div", "ground-title",
    currentChart ? `${currentChart.icao} · ${currentChart.name}` : "—"
  ));

  if (!currentChart) {
    hud.append(el("div", "ground-hint", t("ground_load_plan")));
    return;
  }
  if (!currentTaxiPlan) {
    const line = el("div");
    line.append(document.createTextNode(`${t("runway_selected")} `));
    line.append(el("b", null, currentChart.highlight_runway || "—"));
    hud.append(line);
    hud.append(el(
      "div", "ground-hint",
      t("ground_click_parking")
    ));
    return;
  }

  const guidance = currentTaxiGuidance;
  if (guidance) {
    const kind = guidance.arrived
      ? "done"
      : (!guidance.on_route && "lost") || (guidance.hold_short && "hold") || "go";
    let announcement = null;
    if (guidance.arrived) announcement = t("taxi_arrived");
    else if (!guidance.on_route) announcement = t("taxi_off_route");
    else if (guidance.hold_short && guidance.distance_to_hold_m <= 250) {
      announcement = tf("taxi_hold_short", { runway: guidance.hold_short });
    } else if (guidance.next_name && guidance.distance_to_next_m <= 250) {
      const key = guidance.next_turn === "left"
        ? "taxi_turn_left"
        : guidance.next_turn === "right" ? "taxi_turn_right" : "taxi_continue";
      announcement = tf(key, { taxiway: guidance.next_name });
    }
    if (announcement) hud.append(el("div", `ground-call is-${kind}`, announcement));
  }

  const heading = el("div");
  heading.append(document.createTextNode(
    `${currentTaxiPlan.direction === "arrival" ? t("ground_to") : t("ground_from")} `
  ));
  heading.append(el("b", null, groundLabel(currentTaxiPlan.parking?.label) || "—"));
  heading.append(document.createTextNode(
    currentTaxiPlan.direction === "arrival" ? "" : ` · ${t("runway")} ${currentTaxiPlan.runway}`
  ));
  hud.append(heading);

  hud.append(el(
    "div",
    "ground-steps",
    currentTaxiPlan.summary.map(groundLabel).join(" › ")
  ));
  // Une fois le roulage commencé, c'est la distance restante qui compte.
  hud.append(el("div", null, guidance
    ? tf("metres_remaining", { distance: Math.round(guidance.remaining_m) })
    : `${Math.round(currentTaxiPlan.distance_m)} m`));
}

/* ------------------------------------------------ vitesse au roulage */

/*
 * La vitesse sol du plan de roulage, et l'alarme qui va avec.
 *
 * Aucun règlement ne fixe une vitesse de roulage universelle : les consignes
 * d'exploitation tournent autour de 25 kt en ligne droite et de 10 kt dès
 * qu'il faut tourner, s'arrêter avant une piste ou approcher un poste. Les
 * deux valeurs sont donc des réglages, pas une limite publiée, et le bandeau
 * affiche toujours celle qu'il applique — une alarme dont on ignore le seuil
 * n'apprend rien.
 *
 * Deux garde-fous évitent de crier pour rien. La piste d'abord : le décollage
 * et l'atterrissage s'y font à des vitesses qui n'ont aucun rapport avec le
 * roulage, et c'est la géométrie du terrain qui le dit, jamais la vitesse
 * elle-même — la déduire de la vitesse ferait taire l'alarme exactement quand
 * elle se justifie le plus. Le maintien ensuite : le dépassement doit tenir une
 * seconde avant le premier bip, sans quoi une bosse de piste le déclencherait.
 */

// Sous la limite, la bande où l'on prévient avant d'alarmer.
const TAXI_CAUTION_RATIO = 0.9;
// Distance à partir de laquelle la limite de virage s'applique déjà.
const TAXI_TURN_ZONE_M = 150;
// En deçà, l'avion manœuvre au pas : rien à signaler.
const TAXI_SPEED_FLOOR_KT = 2;
const TAXI_ALARM_HOLD_MS = 1000;
const TAXI_ALARM_REPEAT_MS = { caution: 3000, over: 1000 };

const taxiSpeedLimits = { straight: 25, turn: 10, sound: true };
let taxiAlarmContext = null;
let taxiAlarmLevel = null;
let taxiAlarmSince = 0;
let taxiAlarmLastBeep = 0;

function applyTaxiSpeedPreferences(values) {
  taxiSpeedLimits.straight = finiteOr(values?.taxi_speed_limit_kt, 25);
  taxiSpeedLimits.turn = Math.min(
    taxiSpeedLimits.straight,
    finiteOr(values?.taxi_turn_speed_limit_kt, 10)
  );
  taxiSpeedLimits.sound = values?.taxi_speed_alarm_sound !== false;
  syncTaxiAlarmButton();
}

/** Limite applicable ici : celle des virages dès qu'il faut ralentir. */
function taxiSpeedLimitKt(guidance) {
  const straight = taxiSpeedLimits.straight;
  const turn = Math.min(taxiSpeedLimits.turn, straight);
  if (!guidance) return straight;
  if (guidance.arrived) return turn;
  const toHold = finiteOr(guidance.distance_to_hold_m);
  if (guidance.hold_short && toHold !== null && toHold <= TAXI_TURN_ZONE_M) return turn;
  const toNext = finiteOr(guidance.distance_to_next_m);
  const turning = guidance.next_turn === "left" || guidance.next_turn === "right";
  if (turning && toNext !== null && toNext <= TAXI_TURN_ZONE_M) return turn;
  return straight;
}

/**
 * État de la vitesse au sol, ou null s'il n'y a rien à afficher.
 *
 * Le niveau « runway » affiche la vitesse sans limite ni alarme : sur la
 * piste, la vitesse de roulage ne s'applique plus.
 */
function taxiSpeedState(aircraft, guidance) {
  if (!aircraft?.on_ground || aircraft.paused) return null;
  const speed = finiteOr(aircraft.ground_speed_kt);
  if (speed === null) return null;
  if (GROUND.onRunway(aircraft)) return { speed, limit: null, level: "runway" };

  const limit = taxiSpeedLimitKt(guidance);
  let level = "ok";
  if (speed >= TAXI_SPEED_FLOOR_KT) {
    if (speed > limit) level = "over";
    else if (speed >= limit * TAXI_CAUTION_RATIO) level = "caution";
  }
  return { speed, limit, level };
}

/**
 * Bip d'alarme, synthétisé plutôt que chargé.
 *
 * Un fichier son ajouterait un actif au paquet, une latence au premier
 * déclenchement et un chemin à corriger dans l'installateur, pour deux notes.
 */
function taxiAlarmBeep(level) {
  if (!taxiSpeedLimits.sound) return;
  try {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    taxiAlarmContext = taxiAlarmContext || new Audio();
    if (taxiAlarmContext.state === "suspended") taxiAlarmContext.resume();
    const start = taxiAlarmContext.currentTime;
    const oscillator = taxiAlarmContext.createOscillator();
    const gain = taxiAlarmContext.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = level === "over" ? 880 : 587;
    // Attaque et extinction douces : un créneau brut claque dans le casque.
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.09, start + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.18);
    oscillator.connect(gain).connect(taxiAlarmContext.destination);
    oscillator.start(start);
    oscillator.stop(start + 0.2);
  } catch (_error) {
    // Sans sortie audio utilisable, l'alarme reste visuelle.
  }
}

function driveTaxiSpeedAlarm(level, now = Date.now()) {
  if (level !== taxiAlarmLevel) {
    taxiAlarmLevel = level;
    taxiAlarmSince = level === "caution" || level === "over" ? now : 0;
    taxiAlarmLastBeep = 0;
  }
  if (!taxiAlarmSince || now - taxiAlarmSince < TAXI_ALARM_HOLD_MS) return;
  if (taxiAlarmLastBeep && now - taxiAlarmLastBeep < TAXI_ALARM_REPEAT_MS[level]) return;
  taxiAlarmLastBeep = now;
  taxiAlarmBeep(level);
}

/**
 * Bandeau de vitesse du plan de roulage.
 *
 * Il vit hors du bandeau de guidage, réécrit à chaque position : reconstruire
 * ses nœuds une fois par seconde relancerait le clignotement du dépassement à
 * chaque fois, et il ne clignoterait jamais.
 */
function renderTaxiSpeed(aircraft) {
  const node = $("ground-speed");
  if (!node) return;
  const state = taxiSpeedState(aircraft, currentTaxiGuidance);
  if (!state) {
    show(node, false);
    driveTaxiSpeedAlarm("ok");
    return;
  }
  if (!node.childElementCount) {
    const readout = el("div", "ground-speed-readout");
    readout.append(
      el("span", "ground-speed-label", t("ground_short")),
      el("b", "ground-speed-value"),
      el("span", "ground-speed-unit", "kt")
    );
    node.append(readout, el("div", "ground-speed-limit"));
  }
  node.querySelector(".ground-speed-label").textContent = t("ground_short");
  node.querySelector(".ground-speed-value").textContent = String(Math.round(state.speed));
  // Le dépassement est dit en toutes lettres : une couleur seule laisserait un
  // pilote daltonien devant un chiffre qui n'a l'air de rien.
  const key = state.level === "over" ? "taxi_speed_over" : "taxi_speed_limit";
  node.querySelector(".ground-speed-limit").textContent = state.limit === null
    ? t("taxi_speed_runway")
    : tf(key, { limit: state.limit });
  node.className = `ground-speed is-${state.level}`;
  show(node, true);
  driveTaxiSpeedAlarm(state.level);
}

function syncTaxiAlarmButton() {
  const button = $("ground-alarm");
  if (!button) return;
  button.classList.toggle("active", taxiSpeedLimits.sound);
  button.setAttribute("aria-pressed", String(taxiSpeedLimits.sound));
}

/**
 * Coupe ou rétablit le bip depuis la barre du plan de roulage.
 *
 * Le réglage est le même que celui des paramètres : deux interrupteurs pour
 * une seule alarme laisseraient croire qu'on peut la couper à moitié.
 */
async function toggleTaxiAlarmSound() {
  taxiSpeedLimits.sound = !taxiSpeedLimits.sound;
  syncTaxiAlarmButton();
  if (latestStatus?.remote_client) return;
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) return;
    const values = await response.json();
    await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...values, taxi_speed_alarm_sound: taxiSpeedLimits.sound }),
    });
  } catch (error) {
    // Le choix reste appliqué à l'écran même si l'enregistrement échoue.
  }
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
    applyTaxiSpeedPreferences(status);
    return;
  }
  const response = await fetch("/api/settings");
  if (!response.ok) return;
  const values = await response.json();
  applyMapPreferences(values);
  applyTaxiSpeedPreferences(values);
}

function setLiveState(online, text, paused = false) {
  // Les deux vues portent le même état : passer de l'une à l'autre ne doit pas
  // laisser croire que le simulateur a été perdu.
  for (const [pill, label] of [
    [$("live-pill"), $("live-text")],
    [$("ground-live-pill"), $("ground-live-text")],
  ]) {
    if (!pill) continue;
    pill.classList.toggle("online", online && !paused);
    pill.classList.toggle("paused", online && paused);
    if (label) label.textContent = text;
  }
}

function updateHud(aircraft) {
  const hud = $("map-hud");
  hud.innerHTML = "";
  hud.append(el("div", "hud-title", currentChart ? `${currentChart.icao} · ${currentChart.name}` : "—"));

  if (!aircraft) {
    hud.append(el("div", null, t("aircraft_not_located")));
    if (currentChart?.highlight_runway) {
      const line = el("div");
      line.append(document.createTextNode(`${t("runway_selected")} `));
      line.append(el("b", null, currentChart.highlight_runway));
      hud.append(line);
    }
    return;
  }

  const heading = finiteOr(aircraft.heading_true_deg);
  const groundSpeed = finiteOr(aircraft.ground_speed_kt);
  const verticalSpeed = finiteOr(aircraft.vertical_speed_fpm);
  const airspeed = finiteOr(aircraft.indicated_airspeed_kt);
  const temperature = finiteOr(aircraft.configuration?.total_air_temperature_c);
  const rows = [
    [t("heading_short"), heading !== null ? `${String(Math.round(heading)).padStart(3, "0")}°` : "—"],
    [t("ground_short"), groundSpeed !== null ? `${Math.round(groundSpeed)} kt` : "—"],
    ["IAS", airspeed !== null ? `${Math.round(airspeed)} kt` : "—"],
    [t("altitude_short"), progressAltitudeLabel(aircraft, null)],
  ];
  // Le variomètre n'a de sens qu'en vol, et le bruit au sol le rendrait
  // illisible : il n'apparaît que si la trajectoire monte ou descend.
  if (!aircraft.on_ground && verticalSpeed !== null && Math.abs(verticalSpeed) >= 50) {
    const rounded = Math.round(verticalSpeed / 50) * 50;
    rows.push(["Vz", `${rounded > 0 ? "+" : ""}${rounded} ft/min`]);
  }
  if (temperature !== null) rows.push([t("temperature_short"), `${Math.round(temperature)} °C`]);
  rows.push([t("phase"), detectFlightPhase(aircraft, projectAircraftOnFlightPath(aircraft))]);

  for (const [label, value] of rows) {
    const line = el("div");
    line.append(document.createTextNode(`${label} `));
    line.append(el("b", null, value));
    hud.append(line);
  }
  if (currentChart?.highlight_runway) {
    const line = el("div");
    line.append(document.createTextNode(`${t("runway")} `));
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
    // Le plan de roulage reçoit la position telle quelle : il la projette
    // lui-même dans le repère local du terrain.
    GROUND.setAircraft(aircraft);
    maybeRequestAutomaticTaxiRoute(aircraft);
  }
  updateHud(aircraft);
  // La vitesse au sol suit chaque position, avec ou sans itinéraire chargé.
  renderTaxiSpeed(aircraft);
  updateRouteStripProgress(aircraft);
  updateFlightPanel(aircraft);
  updateDispatchLive(aircraft);
  recordCurrentFlightTrail(aircraft);
  updateFlightSummary(aircraft);
}

async function pollLive() {
  if (!currentChart) return;

  const params = new URLSearchParams({
    demo: $("demo-toggle").checked ? "1" : "0",
    icao: currentIcao || "",
    aircraft: currentPlan?.aircraft_name || currentPlan?.aircraft || "",
  });
  if (currentChart.highlight_runway) params.set("runway", currentChart.highlight_runway);

  try {
    const data = await fetch(`/api/live?${params}`).then((r) => r.json());
    if (!data.connected) {
      setLiveState(false, t("sim_disconnected"));
      MAP.clearAircraft();
      GROUND.clearAircraft();
      updateHud(null);
      renderTaxiSpeed(null);
      updateGroundHud();
      updateRouteStripProgress(null);
      latestAircraft = null;
      updateFlightPanel(null);
      updateDispatchLive(null);
      renderProcedurePanel(currentProcedures, null);
      return;
    }
    const aircraft = data.aircraft;
    const source = aircraft.source === "Démonstration" ? t("demo") : aircraft.source;
    setLiveState(
      true,
      aircraft.paused ? t("sim_paused") : `${source} · ${t("live")}`,
      Boolean(aircraft.paused),
    );
    applyAircraftState(aircraft);
    updateProcedures(data.procedures, aircraft);
    pollTaxiGuidance(aircraft);
  } catch (error) {
    setLiveState(false, t("connection_error"));
    updateRouteStripProgress(null);
    updateFlightPanel(null);
    updateDispatchLive(null);
    renderProcedurePanel(currentProcedures, null);
  }
}

function startLiveLoop() {
  if (liveTimer) return;
  pollLive();
  liveTimer = setInterval(pollLive, LIVE_INTERVAL_MS);
}

/* ---------------------------------------------------------------- weather */

/* Les catégories de vol restent en notation OACI/FAA : elles ne se traduisent
   pas, un pilote les lit telles quelles sur toutes les cartes. */
const FLIGHT_CATEGORY_CLASS = {
  VFR: "cat-vfr",
  MVFR: "cat-mvfr",
  IFR: "cat-ifr",
  LIFR: "cat-lifr",
};

function metres(value) {
  if (value === null || value === undefined) return null;
  if (value >= 9999) return "≥ 10 km";
  if (value >= 1000) return `${(value / 1000).toLocaleString(displayLocale(), {
    maximumFractionDigits: 1,
  })} km`;
  return `${value} m`;
}

function feet(value) {
  if (value === null || value === undefined) return null;
  return `${value.toLocaleString(displayLocale())} ft`;
}

function celsius(value) {
  if (value === null || value === undefined) return null;
  return `${value} °C`;
}

function windText(wind) {
  if (!wind) return null;
  if (wind.variable) return `VRB ${wind.speed_kt ?? 0} kt`;
  if (wind.direction_deg === null || wind.direction_deg === undefined) {
    return wind.speed_kt === 0 ? t("wind_calm") : null;
  }
  const gust = wind.gust_kt ? ` G${wind.gust_kt}` : "";
  return `${String(wind.direction_deg).padStart(3, "0")}° / ${wind.speed_kt}${gust} kt`;
}

function cloudsText(clouds) {
  if (!clouds?.length) return null;
  return clouds
    .map((layer) => {
      const convective = layer.convective ? ` ${layer.convective}` : "";
      return `${layer.cover}${convective} ${layer.height_ft.toLocaleString(displayLocale())} ft`;
    })
    .join(" · ");
}

/* Un âge de 10 000 min ne se lit pas : au-delà de l'heure, on change d'unité. */
function observedAgo(minutes) {
  if (minutes < 60) return t("observed_ago_minutes").replace("{value}", minutes);
  if (minutes < 48 * 60) {
    return t("observed_ago_hours").replace("{value}", Math.round(minutes / 60));
  }
  return t("observed_ago_days").replace("{value}", Math.floor(minutes / (24 * 60)));
}

function categoryBadge(category) {
  if (!category) return null;
  return el("span", `wx-cat ${FLIGHT_CATEGORY_CLASS[category] || ""}`.trim(), category);
}

/** Bloc repliable qui garde le brut accessible sans encombrer le briefing. */
function rawToggle(label, text) {
  if (!text) return null;
  const details = el("details", "wx-raw");
  details.append(el("summary", null, label));
  details.append(el("pre", null, text));
  return details;
}

function weatherCondition(report) {
  const phenomena = (report.phenomena || []).map((item) => item.code).join(" ");
  if (/TS/.test(phenomena)) return { kind: "thunder", symbol: "ϟ", label: t("wx_condition_thunder") };
  if (/(SN|SG|PL|IC)/.test(phenomena)) return { kind: "snow", symbol: "❄", label: t("wx_condition_snow") };
  if (/(RA|DZ|SH)/.test(phenomena)) return { kind: "rain", symbol: "☂", label: t("wx_condition_rain") };
  if (/(FG|BR|HZ|FU)/.test(phenomena)) return { kind: "fog", symbol: "≋", label: t("wx_condition_fog") };
  if ((report.clouds || []).some((layer) => ["BKN", "OVC", "VV"].includes(layer.cover))) {
    return { kind: "cloud", symbol: "☁", label: t("wx_condition_cloudy") };
  }
  return { kind: "clear", symbol: "☀", label: t("wx_condition_clear") };
}

function weatherMeter(label, value, maximum, textValue, fullWhenMissing = false) {
  const item = el("div", "wx-meter");
  const head = el("div", "wx-meter-head");
  head.append(el("span", null, label), el("strong", null, textValue || "—"));
  const track = el("div", "wx-meter-track");
  const fill = el("span", "wx-meter-fill");
  const percent = value === null || value === undefined
    ? (fullWhenMissing ? 100 : 0)
    : Math.max(0, Math.min(100, (value / maximum) * 100));
  fill.style.width = `${percent}%`;
  track.append(fill);
  item.append(head, track);
  return item;
}

function weatherVisual(report) {
  const visual = el("div", "wx-visual");
  const condition = weatherCondition(report);
  const sky = el("div", `wx-sky wx-sky-${condition.kind}`);
  const symbol = el("span", "wx-sky-symbol", condition.symbol);
  symbol.setAttribute("aria-hidden", "true");
  sky.append(symbol, el("span", "wx-sky-label", condition.label));

  const dial = el("div", `wx-wind-dial${report.wind?.variable ? " variable" : ""}`);
  dial.title = windText(report.wind) || t("wx_wind_unknown");
  dial.setAttribute("aria-label", dial.title);
  dial.style.setProperty(
    "--wind-direction",
    `${report.wind?.direction_deg ?? 0}deg`
  );
  dial.append(el("span", "wx-wind-north", "N"));
  if (report.wind?.direction_deg !== null && report.wind?.direction_deg !== undefined) {
    dial.append(el("span", "wx-wind-arrow", "➤"));
  }
  const speed = el("strong", "wx-wind-speed", report.wind?.speed_kt ?? "—");
  speed.append(el("small", null, "kt"));
  dial.append(speed);

  const meters = el("div", "wx-visual-meters");
  meters.append(
    weatherMeter(
      t("wx_visibility"),
      report.visibility_m,
      10000,
      report.cavok ? "CAVOK" : metres(report.visibility_m),
      report.cavok
    ),
    weatherMeter(
      t("wx_ceiling"),
      report.ceiling_ft,
      3000,
      feet(report.ceiling_ft) || t("wx_no_ceiling"),
      report.ceiling_ft === null || report.ceiling_ft === undefined
    )
  );
  visual.append(sky, dial, meters);
  return visual;
}

function weatherAirport(report, kicker) {
  const card = el("article", "wx-card");

  const head = el("div", "wx-head");
  const identity = el("div");
  identity.append(el("div", "card-kicker", kicker));
  identity.append(el("div", "card-icao", report.icao));
  if (report.name) identity.append(el("div", "card-name", report.name));
  head.append(identity);

  const status = el("div", "wx-status");
  const badge = categoryBadge(report.flight_category);
  if (badge) status.append(badge);
  if (report.age_minutes !== null && report.age_minutes !== undefined) {
    status.append(
      el("div", `wx-age${report.stale ? " stale" : ""}`, observedAgo(report.age_minutes))
    );
  }
  if (report.source) {
    status.append(el("div", "wx-source", report.source === "awc" ? "aviationweather.gov" : "SimBrief"));
  }
  head.append(status);
  card.append(head);

  if (!report.raw_metar) {
    card.append(el("p", "stat-note", t("weather_unavailable")));
    return card;
  }

  card.append(weatherVisual(report));

  const grid = el("div", "stat-grid");
  for (const node of [
    stat(t("wx_wind"), windText(report.wind)),
    stat(t("wx_visibility"), report.cavok ? "CAVOK" : metres(report.visibility_m)),
    stat(t("wx_ceiling"), feet(report.ceiling_ft) || (report.clouds.length ? t("wx_no_ceiling") : null),
      cloudsText(report.clouds)),
    stat(
      t("wx_temperature"),
      celsius(report.temperature_c),
      report.dew_point_c !== null && report.dew_point_c !== undefined
        ? `${t("wx_dew_point")} ${report.dew_point_c} °C`
        : null
    ),
    stat(
      t("wx_qnh"),
      report.qnh_hpa ? `${report.qnh_hpa} hPa` : null,
      report.altimeter_inhg ? `${report.altimeter_inhg.toFixed(2)} inHg` : null
    ),
  ]) {
    if (node) grid.append(node);
  }
  card.append(grid);

  if (report.phenomena?.length) {
    const row = el("div", "wx-phenomena");
    for (const item of report.phenomena) {
      const chip = el("span", "wx-phenomenon");
      chip.append(el("strong", null, item.code));
      chip.append(document.createTextNode(` ${item.label}`));
      row.append(chip);
    }
    card.append(row);
  }

  if (report.notes?.length) {
    const list = el("ul", "wx-notes");
    for (const note of report.notes) list.append(el("li", null, note));
    card.append(list);
  }

  if (report.taf_periods?.length) {
    const taf = el("div", "wx-taf");
    taf.append(el("div", "section-title", t("wx_taf")));
    for (const period of report.taf_periods) {
      const row = el("div", "wx-taf-row");
      const head = el("div", "wx-taf-head");
      head.append(el("span", "wx-taf-kind", period.kind === "base" ? t("wx_taf_base") : period.kind));
      const window = [period.from_time, period.to_time].filter(Boolean).join(" → ");
      if (window) head.append(el("span", "wx-taf-window", window));
      const periodBadge = categoryBadge(period.flight_category);
      if (periodBadge) head.append(periodBadge);
      row.append(head);
      row.append(el("div", "wx-taf-raw", period.raw));
      taf.append(row);
    }
    card.append(taf);
  }

  const raws = el("div", "wx-raws");
  for (const node of [
    rawToggle(t("wx_raw_metar"), report.raw_metar),
    rawToggle(t("wx_raw_taf"), report.raw_taf),
  ]) {
    if (node) raws.append(node);
  }
  if (raws.children.length) card.append(raws);
  return card;
}

function weatherEnroute(enroute) {
  const card = el("article", "wx-card");
  const head = el("div", "wx-head");
  const identity = el("div");
  identity.append(el("div", "card-kicker", t("wx_enroute")));
  identity.append(el("div", "card-icao", t("wx_cruise")));
  head.append(identity);
  if (enroute.cruise_altitude_ft) {
    const status = el("div", "wx-status");
    status.append(el("div", "wx-level", `FL${Math.round(enroute.cruise_altitude_ft / 100)}`));
    head.append(status);
  }
  card.append(head);

  const grid = el("div", "stat-grid");
  const component = enroute.wind_component_kt;
  for (const node of [
    stat(
      t("wx_wind"),
      enroute.wind_direction_deg !== null && enroute.wind_direction_deg !== undefined
        ? `${String(enroute.wind_direction_deg).padStart(3, "0")}° / ${enroute.wind_speed_kt} kt`
        : null,
      component !== null && component !== undefined
        ? `${component > 0 ? "+" : ""}${component} kt ${
            component < 0 ? t("wx_headwind") : t("wx_tailwind")
          }`
        : null
    ),
    stat(t("wx_oat"), celsius(enroute.outside_air_temperature_c),
      enroute.temperature_dev_c !== null && enroute.temperature_dev_c !== undefined
        ? `ISA ${enroute.temperature_dev_c > 0 ? "+" : ""}${enroute.temperature_dev_c}`
        : null),
    stat(t("wx_tropopause"), enroute.tropopause_ft
      ? `FL${Math.round(enroute.tropopause_ft / 100)}`
      : null),
  ]) {
    if (node) grid.append(node);
  }
  if (!grid.children.length) {
    card.append(el("p", "stat-note", t("wx_enroute_unavailable")));
    return card;
  }
  card.append(grid);

  if (enroute.notes?.length) {
    const list = el("ul", "wx-notes");
    for (const note of enroute.notes) list.append(el("li", null, note));
    card.append(list);
  }
  return card;
}

function weatherUpdatedLabel(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return tf("wx_updated_at", {
    value: new Intl.DateTimeFormat(displayLocale(), {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(parsed),
  });
}

function renderWeatherToolbar(panel) {
  const toolbar = el("div", "wx-toolbar");
  const live = el("div", "wx-live");
  live.setAttribute("aria-live", "polite");
  live.append(el("span", `wx-live-dot ${weatherRefreshState}`));

  const labels = {
    loading: t("wx_refreshing"),
    error: t("wx_refresh_failed"),
    off: t("wx_live_off"),
    partial: t("wx_live_partial"),
    idle: t("wx_live_ready"),
  };
  const text = el("div");
  text.append(el("strong", null, labels[weatherRefreshState] || labels.idle));
  const updated = weatherUpdatedLabel(weatherLastUpdatedAt);
  if (updated) text.append(el("small", null, updated));
  live.append(text);

  const button = el("button", "icon-btn wx-refresh", t("wx_refresh"));
  button.type = "button";
  button.disabled = weatherRefreshInFlight || latestStatus?.metar_source !== "live";
  button.addEventListener("click", () => refreshWeather());
  toolbar.append(live, button);
  panel.append(toolbar);
}

async function refreshWeather({ silent = false } = {}) {
  if (!currentPlan || weatherRefreshInFlight) return;
  weatherRefreshInFlight = true;
  weatherRefreshState = "loading";
  renderWeather(currentPlan);
  try {
    const response = await fetch("/api/weather/current", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || t("wx_refresh_failed"));
    currentPlan.weather = payload.weather || currentPlan.weather;
    weatherLastUpdatedAt = payload.refreshed_at;
    weatherRefreshState = !payload.enabled
      ? "off"
      : payload.live
        ? (payload.partial ? "partial" : "idle")
        : "error";
  } catch (error) {
    weatherRefreshState = "error";
    if (!silent) console.warn("Weather refresh failed", error);
  } finally {
    weatherRefreshInFlight = false;
    renderWeather(currentPlan);
  }
}

function startWeatherLoop() {
  if (weatherTimer) clearInterval(weatherTimer);
  weatherTimer = null;
  weatherLastUpdatedAt = null;
  if (latestStatus?.metar_source !== "live") {
    weatherRefreshState = "off";
    renderWeather(currentPlan);
    return;
  }
  weatherRefreshState = "idle";
  void refreshWeather({ silent: true });
  weatherTimer = setInterval(
    () => refreshWeather({ silent: true }),
    WEATHER_REFRESH_INTERVAL_MS
  );
}

function renderWeather(plan) {
  const panel = $("panel-weather");
  panel.innerHTML = "";
  renderWeatherToolbar(panel);

  const weather = plan.weather || {};
  const grid = el("div", "wx-grid");

  // L'ordre suit le vol : départ, croisière, arrivée, puis dégagement.
  if (weather.departure) grid.append(weatherAirport(weather.departure, t("wx_departure")));
  grid.append(weatherEnroute(weather.enroute || {}));
  if (weather.arrival) grid.append(weatherAirport(weather.arrival, t("wx_arrival")));
  if (weather.alternate) grid.append(weatherAirport(weather.alternate, t("wx_alternate")));

  if (!grid.children.length) {
    panel.append(el("p", "stat-note", t("weather_unavailable")));
    return;
  }
  panel.append(grid);
  panel.append(
    el("p", "wx-disclaimer", t("wx_disclaimer"))
  );
}

/* ------------------------------------------------------------------ tabs */

const MOBILE_MODULE_MENU = window.matchMedia("(max-width: 760px)");

function setModuleMenuOpen(open, restoreFocus = false) {
  const tabs = $("tabs");
  const toggle = $("module-menu-toggle");
  const isOpen = Boolean(
    open && MOBILE_MODULE_MENU.matches && !tabs.classList.contains("hidden")
  );
  tabs.classList.toggle("mobile-open", isOpen);
  toggle.setAttribute("aria-expanded", String(isOpen));
  toggle.querySelector("span").textContent = t(
    isOpen ? "module_menu_close" : "module_menu"
  );
  show($("module-menu-backdrop"), isOpen);
  document.body.classList.toggle("module-menu-open", isOpen);
  if (isOpen) {
    window.requestAnimationFrame(() => {
      if (tabs.classList.contains("mobile-open")) {
        tabs.querySelector("button.active")?.focus({ preventScroll: true });
      }
    });
  } else if (restoreFocus) {
    toggle.focus({ preventScroll: true });
  }
}

function selectTab(name, scrollToModule = false) {
  const restoreMenuFocus = $("module-menu-toggle").getAttribute("aria-expanded") === "true";
  for (const button of document.querySelectorAll(".tabs button")) {
    button.classList.toggle("active", button.dataset.tab === name);
  }
  show($("terminal"), name === "terminal");
  for (const key of ["map", "ground", "procedures", "flight", "constraints", "dispatch", "aircraft", "sia", "mcdu", "weather"]) {
    show($(`panel-${key}`), key === name);
  }
  // Le canvas doit être mesuré une fois visible, sinon il reste à zéro.
  if (name === "map") window.requestAnimationFrame(() => MAP.resize());
  if (name === "ground") window.requestAnimationFrame(() => GROUND.resize());
  setModuleMenuOpen(false, restoreMenuFocus);
  if (scrollToModule) {
    window.requestAnimationFrame(() => {
      const target = name === "terminal" ? $("terminal") : $(`panel-${name}`);
      target?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
        block: "start",
      });
    });
  }
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
  if (button) selectTab(button.dataset.tab, true);
});

$("module-menu-toggle").addEventListener("click", () => {
  setModuleMenuOpen($("module-menu-toggle").getAttribute("aria-expanded") !== "true");
});
$("module-menu-backdrop").addEventListener("click", () => setModuleMenuOpen(false, true));
document.addEventListener("keydown", (event) => {
  const menuOpen = $("module-menu-toggle").getAttribute("aria-expanded") === "true";
  if (event.key === "Escape" && menuOpen) {
    setModuleMenuOpen(false, true);
  } else if (event.key === "Tab" && menuOpen) {
    const focusable = [
      ...$("tabs").querySelectorAll("button[data-tab]"),
      $("module-menu-toggle"),
    ];
    const index = focusable.indexOf(document.activeElement);
    const next = event.shiftKey
      ? (index <= 0 ? focusable.length - 1 : index - 1)
      : (index < 0 || index === focusable.length - 1 ? 0 : index + 1);
    event.preventDefault();
    focusable[next].focus({ preventScroll: true });
  }
});
MOBILE_MODULE_MENU.addEventListener("change", () => setModuleMenuOpen(false));

$("refresh").addEventListener("click", refreshPlanOrDemo);
$("simbrief-create").addEventListener("click", openSimBriefPlanner);
$("support-open").addEventListener("click", openSupportPage);
$("support-open-toolbar").addEventListener("click", openSupportPage);
$("demo-toggle").addEventListener("change", toggleDemoMode);

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

$("ground-fit").addEventListener("click", () => GROUND.fit());
$("ground-plan").addEventListener("click", () => GROUND.fitPlan());
$("ground-clear").addEventListener("click", () => clearTaxiPlan());
$("ground-follow").addEventListener("click", () => GROUND.toggleFollow());
$("ground-secondary").addEventListener("click", () => GROUND.toggleSecondaryTaxiways());
$("ground-alarm").addEventListener("click", () => toggleTaxiAlarmSound());
$("ground-zoom-in").addEventListener("click", () => GROUND.zoomIn());
$("ground-zoom-out").addEventListener("click", () => GROUND.zoomOut());
$("settings-open").addEventListener("click", openSettings);
$("update-install").addEventListener("click", handleUpdateButton);
$("changelog-open").addEventListener("click", openChangelog);
$("changelog-close").addEventListener("click", () => $("changelog-dialog").close());
$("settings-close").addEventListener("click", () => $("settings-dialog").close());
$("settings-cancel").addEventListener("click", () => $("settings-dialog").close());
$("settings-form").addEventListener("submit", saveSettings);
$("settings-language").addEventListener("change", (event) => {
  window.I18N.setLanguage(event.target.value);
});
$("settings-theme").addEventListener("change", (event) => {
  window.THEME.setPreference(event.target.value);
});
// La langue ne vit que dans le navigateur : un client distant peut la changer
// sans toucher aux réglages du PC, qui lui restent fermés.
$("mobile-language").addEventListener("change", (event) => {
  window.I18N.setLanguage(event.target.value);
});
$("mobile-theme").addEventListener("change", (event) => {
  window.THEME.setPreference(event.target.value);
});
function syncThemeToggle(theme = document.documentElement.dataset.theme || "dark") {
  const button = $("theme-toggle");
  const target = theme === "light" ? "dark" : "light";
  const label = `${t("theme")} · ${t(`theme_${target}`)}`;
  button.dataset.targetTheme = target;
  button.title = label;
  button.setAttribute("aria-label", label);
  button.setAttribute("aria-pressed", String(theme === "dark"));
}
$("theme-toggle").addEventListener("click", () => {
  window.THEME.setPreference($("theme-toggle").dataset.targetTheme || "light");
});
window.addEventListener("navixav:themechange", (event) => {
  for (const id of ["settings-theme", "mobile-theme"]) {
    const select = $(id);
    if (select) select.value = event.detail.preference;
  }
  syncThemeToggle(event.detail.theme);
  // Les cartes lisent leurs couleurs dans les variables CSS au dessin.
  MAP.resize();
  GROUND.resize();
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
$("aircraft-refresh").addEventListener("click", loadAircraftSurvey);
$("aircraft-folder-browse").addEventListener("click", browseAircraftFolder);
$("settings-lan-copy").addEventListener("click", async () => {
  const value = $("settings-lan-url").value;
  if (!value) return;
  await navigator.clipboard.writeText(value);
  $("settings-message").textContent = t("lan_url_copied");
});
$("shutdown").addEventListener("click", shutdownApplication);
$("sim-status").addEventListener("click", pollSimulatorStatus);
$("global-flight-alert").addEventListener("click", openActiveAlerts);
initialiseStripScrolling();
window.I18N.apply();
syncThemeToggle();

window.addEventListener("navixav:languagechange", () => {
  renderProcedurePanel(currentProcedures, latestAircraft);
  if (currentPlan) renderPlan(currentPlan);
  else {
    updateHud(latestAircraft);
    updateGroundHud();
  }
  loadStatus().catch(() => {});
  pollSimulatorStatus();
  refreshUpdateButtonText();
  syncThemeToggle();
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
