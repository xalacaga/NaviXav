"use strict";

const $ = (id) => document.getElementById(id);

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
let liveTimer = null;
let simulatorTimer = null;
const siaRequests = new Map();

const EARTH_RADIUS_M = 6378137;
const LIVE_INTERVAL_MS = 1000;
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
  button.textContent = collapsed ? "Développer" : "Réduire";
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
    $("empty-hint").textContent =
      "Aucun compte SimBrief configuré. Ouvre Paramètres, ou active le mode Démo.";
  }
  if (status.demo_available) $("demo-toggle").disabled = false;
}

async function pollSimulatorStatus() {
  const indicator = $("sim-status");
  try {
    const status = await fetch("/api/simulator", { cache: "no-store" }).then((r) => r.json());
    indicator.classList.toggle("online", Boolean(status.connected));
    indicator.classList.toggle("offline", !status.connected);
    $("sim-status-text").textContent = status.connected ? "MSFS connecté" : "MSFS hors ligne";
    indicator.title = status.connected
      ? `Connexion directe active · ${status.source || "SimConnect"}`
      : (status.reason || "Microsoft Flight Simulator ne répond pas");
  } catch (_error) {
    indicator.classList.remove("online");
    indicator.classList.add("offline");
    $("sim-status-text").textContent = "Serveur arrêté";
  }
}

async function shutdownApplication() {
  const button = $("shutdown");
  button.disabled = true;
  button.textContent = "Arrêt…";
  try {
    const response = await fetch("/api/shutdown", { method: "POST" });
    if (!response.ok) throw new Error("Le serveur n’a pas accepté l’arrêt");
    clearInterval(simulatorTimer);
    document.body.innerHTML =
      '<main class="empty"><h2>NaviXav est arrêté</h2><p>Le processus et le port 8765 ont été libérés. Tu peux fermer cette fenêtre.</p></main>';
  } catch (error) {
    button.disabled = false;
    button.textContent = "Quitter";
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
    $("settings-dialog").showModal();
  } catch (error) {
    showBanner("error", "Impossible d’ouvrir les paramètres", [String(error)]);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const message = $("settings-message");
  message.textContent = "Enregistrement…";
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
    message.textContent = "Paramètres enregistrés.";
    await loadStatus();
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
  button.querySelector("span").textContent = "Calcul…";
  hideBanner();

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
    button.querySelector("span").textContent = "Compléter le plan";
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
  show($("empty"), false);
  for (const id of ["strip", "terminal", "tabs"]) show($(id), true);

  renderStrip(plan);
  renderTerminal(plan);
  renderConstraints(plan);
  renderDispatch(plan);
  renderAircraft(plan);
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

  const chip = (label, value, kind) => {
    const node = el("span", `chip ${kind}`);
    if (label) node.append(el("small", null, label));
    node.append(document.createTextNode(value));
    return node;
  };

  const dep = plan.departure;
  const arr = plan.arrival;

  if (dep) {
    strip.append(chip(null, dep.icao, "apt"));
    if (dep.runway?.value) strip.append(chip("rwy", dep.runway.value, "proc"));
    if (dep.sid.value) strip.append(chip("sid", dep.sid.value, "proc"));
    if (dep.sid_transition.value) strip.append(chip("trans", dep.sid_transition.value, "wpt"));
  }
  for (const fix of plan.enroute.waypoints || []) {
    strip.append(chip(null, fix, "wpt"));
  }
  if (arr) {
    if (arr.star_transition.value) strip.append(chip("trans", arr.star_transition.value, "wpt"));
    if (arr.star.value) strip.append(chip("star", arr.star.value, "proc"));
    if (arr.approach_transition.value) strip.append(chip("via", arr.approach_transition.value, "wpt"));
    if (arr.approach.value) strip.append(chip("appr", arr.approach.value, "proc"));
    if (arr.runway?.value) strip.append(chip("rwy", arr.runway.value, "proc"));
    strip.append(chip(null, arr.icao, "apt"));
  }
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

  const right = el("div", "card-wind", windLabel(block.wind));
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
  const request = fetch(`/api/sia/approach?${params}`).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Carte SIA indisponible.");
    return payload;
  });
  siaRequests.set(key, request);
  return request;
}

function siaApproachCard(plan) {
  const wrapper = el("section", "sia-card");
  const head = el("div", "sia-card-head");
  const title = el("div");
  title.append(el("div", "card-kicker", "Source officielle"));
  title.append(el("h2", null, "Carte d’approche SIA"));
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
    status.textContent = `AIRAC ${data.chart.effective_date}`;
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
    frame.title = `Carte SIA ${data.chart.title}`;
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
    });
  }
  if (plan.arrival) {
    entries.push({
      icao: plan.arrival.icao,
      runway: plan.arrival.runway?.value || null,
      role: "arrivée",
    });
  }

  for (const entry of entries) {
    const button = el("button", "airport-btn");
    button.textContent = entry.icao;
    button.append(el("small", null, entry.runway ? `${entry.role} · ${entry.runway}` : entry.role));
    button.addEventListener("click", () => loadChart(entry.icao, entry.runway));
    bar.append(button);
  }

  if (entries.length) loadChart(entries[0].icao, entries[0].runway);
}

async function loadChart(icao, runway) {
  for (const button of document.querySelectorAll(".airport-btn")) {
    button.classList.toggle("active", button.textContent.startsWith(icao));
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
    MAP.setChart(currentChart);
    const route = (currentPlan?.enroute?.route_path || []).map((point) => {
      const projected = projectToChart(point.lat, point.lon);
      return { ...projected, ident: point.ident, via: point.via };
    });
    MAP.setRoute(route);
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
      return;
    }
    const aircraft = data.aircraft;
    const point = projectToChart(aircraft.latitude, aircraft.longitude);
    setLiveState(true, `${aircraft.source} · en direct`);
    MAP.setAircraft({ x: point.x, y: point.y, heading: aircraft.heading_true_deg });
    updateHud(aircraft);
  } catch (error) {
    setLiveState(false, "Erreur de liaison");
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
  for (const key of ["map", "constraints", "dispatch", "aircraft", "mcdu", "raw"]) {
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
$("map-route").addEventListener("click", () => MAP.fitRoute());
$("settings-open").addEventListener("click", openSettings);
$("settings-close").addEventListener("click", () => $("settings-dialog").close());
$("settings-cancel").addEventListener("click", () => $("settings-dialog").close());
$("settings-form").addEventListener("submit", saveSettings);
$("shutdown").addEventListener("click", shutdownApplication);
$("sim-status").addEventListener("click", pollSimulatorStatus);
$("terminal-toggle").addEventListener("click", toggleTerminal);

setTerminalCollapsed(localStorage.getItem(TERMINAL_COLLAPSED_KEY) === "true");

pollSimulatorStatus();
simulatorTimer = setInterval(pollSimulatorStatus, 2500);

loadStatus();
