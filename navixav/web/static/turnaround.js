"use strict";

/**
 * Module Escale : la rampe en direct, pilotée par GSX Pro.
 *
 * GSX publie l'état de ses services dans des LVars qui lui sont propres, pour
 * n'importe quel avion. Ce module en fait quatre choses :
 *
 *   1. une vue de dessus animée de l'avion au poste — cabine qui se remplit,
 *      soutes, réservoirs et véhicules qui arrivent et repartent ;
 *   2. une chronologie façon A-CDM : le rythme réel de chaque service donne
 *      son heure de fin, et la plus tardive l'heure de départ estimée (TOBT) ;
 *   3. un devis de masse et centrage à la fin de l'embarquement, comparé à
 *      l'OFP, avec la correction de dernière minute (LMC) à reporter ;
 *   4. un guidage d'accostage (VDGS) estimé d'après le poste MSFS.
 *
 * Ce qui est mesuré et ce qui est illustratif reste distinct à l'écran : le
 * nombre de passagers est réel, la place de chacun ne l'est pas — GSX ne la
 * publie pas.
 */
const TURNAROUND = (() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const SAMPLE_INTERVAL_MS = 5000;
  const SAMPLE_HISTORY_MS = 15 * 60 * 1000;
  const RATE_WINDOW_MS = 150 * 1000;
  const RATE_MIN_SPAN_MS = 20 * 1000;
  // Fermeture des portes et retrait du matériel après le dernier service.
  const DOORS_CLOSING_MS = 3 * 60 * 1000;
  // Durées forfaitaires des services dont GSX ne publie pas l'avancement.
  const STANDARD_DURATION_MS = { catering: 10 * 60 * 1000, water: 6 * 60 * 1000, lavatory: 6 * 60 * 1000 };
  // Au-delà, l'heure de l'OFP n'est manifestement pas celle du vol simulé.
  const SCHEDULE_RELEVANCE_MS = 3 * 60 * 60 * 1000;
  const LMC_ZFW_KG = 500;
  const VDGS_RANGE_M = 60;
  // Durées réelles des services sans avancement publié, apprises escale après
  // escale ; les forfaits ne servent qu'à la toute première.
  const DURATIONS_KEY = "navixav-turnaround-durations";
  const DURATION_HISTORY = 10;
  // Distance du nez au point de référence de chaque avion, mesurée au poste.
  // Relevé réel : MSFS gare l'avion nez au bord avant du cercle du poste, pas
  // sur son centre (Fenix A320 à LFBO U 21 : 21,4 m, centre 15,6 m derrière).
  const NOSE_OFFSET_KEY = "navixav-vdgs-nose-offset";
  const NOSE_OFFSET_RATIO = 0.57;

  function readStore(key) {
    try {
      return JSON.parse(localStorage.getItem(key) || "{}") || {};
    } catch (_error) {
      return {};
    }
  }
  function writeStore(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (_error) {
      // Préférence non retenue : la session garde sa valeur en mémoire.
    }
  }
  const median = (values) => {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted.length ? sorted[Math.floor(sorted.length / 2)] : null;
  };

  const tr = (key) => window.I18N.t(key);
  const fmt = (key, values) => window.I18N.format(key, values);
  const finite = (value) => {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const clamp01 = (value) => Math.max(0, Math.min(1, value));
  const locale = () => {
    const language = window.I18N.getLanguage();
    return { en: "en-GB", fr: "fr-FR", de: "de-DE", es: "es-ES", it: "it-IT", pt: "pt-PT", nl: "nl-NL", pl: "pl-PL" }[language] || "fr-FR";
  };
  const kg = (value) => (value === null ? "—" : `${Math.round(value).toLocaleString(locale())} kg`);
  const signedKg = (value) => `${value > 0 ? "+" : value < 0 ? "−" : "±"}${Math.abs(Math.round(value)).toLocaleString(locale())} kg`;
  const zulu = (ms) => {
    const date = new Date(ms);
    return `${String(date.getUTCHours()).padStart(2, "0")}:${String(date.getUTCMinutes()).padStart(2, "0")}Z`;
  };

  /* ------------------------------------------------------------ cellules */

  /*
   * Gabarits par famille. Dimensions réelles (longueur, envergure, en mètres),
   * cabine tout économique : le plan est une illustration du remplissage, pas
   * la configuration d'une compagnie. Un appareil inconnu reçoit un gabarit
   * générique dimensionné d'après les passagers prévus.
   */
  /*
   * `art` : silhouettes plane-watch par ordre de préférence. Le code OACI
   * exact passe toujours en premier ; à défaut, le type le plus proche par le
   * nombre et la place des moteurs. `diameter` : largeur du fuselage, en
   * mètres, pour poser la cabine dans la silhouette.
   */
  const FAMILIES = [
    { match: /A318|A319|A19N/, label: "A319", length: 33.8, span: 35.8, rows: 24, abreast: 6, widebody: false, diameter: 3.95, art: ["A319", "A19N", "A318", "A320"] },
    { match: /A320|A20N/, label: "A320", length: 37.6, span: 35.8, rows: 30, abreast: 6, widebody: false, diameter: 3.95, art: ["A320", "A20N"] },
    { match: /A321|A21N/, label: "A321", length: 44.5, span: 35.8, rows: 37, abreast: 6, widebody: false, diameter: 3.95, art: ["A321", "A21N"] },
    { match: /BCS1|BCS3|A220/, label: "A220", length: 38.7, span: 35.1, rows: 26, abreast: 5, widebody: false, diameter: 3.7, art: ["E290", "E190"] },
    { match: /B736|B737|B37M/, label: "B737", length: 33.6, span: 35.8, rows: 24, abreast: 6, widebody: false, diameter: 3.76, art: ["B737", "B738"] },
    { match: /B738|B38M|737-800|737 MAX 8/, label: "B738", length: 39.5, span: 35.9, rows: 31, abreast: 6, widebody: false, diameter: 3.76, art: ["B738", "B38M"] },
    { match: /B739|B39M|737-900/, label: "B739", length: 42.1, span: 35.9, rows: 33, abreast: 6, widebody: false, diameter: 3.76, art: ["B738", "B38M"] },
    { match: /B752|B753|757/, label: "B757", length: 47.3, span: 38.1, rows: 36, abreast: 6, widebody: false, diameter: 3.76, art: ["B752"] },
    { match: /E170|E175|E75L|E190|E195|E290|E295/, label: "E-Jet", length: 36.2, span: 28.7, rows: 25, abreast: 4, widebody: false, diameter: 3.0, art: ["E190", "E290"] },
    { match: /CRJ7|CRJ9|CRJX/, label: "CRJ", length: 32.5, span: 23.2, rows: 20, abreast: 4, widebody: false, diameter: 2.7, art: ["F100", "F70"] },
    { match: /AT72|AT76|AT75|ATR/, label: "ATR 72", length: 27.2, span: 27.1, rows: 18, abreast: 4, widebody: false, diameter: 2.8, art: ["AT75"] },
    { match: /DH8D|Q400/, label: "Q400", length: 32.8, span: 28.4, rows: 19, abreast: 4, widebody: false, diameter: 2.7, art: ["DH8D"] },
    { match: /A332|A333|A338|A339|A330/, label: "A330", length: 63.7, span: 60.3, rows: 36, abreast: 8, widebody: true, diameter: 5.64, art: ["A333", "A332", "A339", "A338"] },
    { match: /A359|A35K|A350/, label: "A350", length: 66.8, span: 64.8, rows: 36, abreast: 9, widebody: true, diameter: 5.96, art: ["A359", "A35K"] },
    { match: /A388|A380/, label: "A380", length: 72.7, span: 79.8, rows: 50, abreast: 10, widebody: true, diameter: 7.14, art: ["A388"] },
    { match: /B788|B789|B78X|787/, label: "B787", length: 62.8, span: 60.1, rows: 32, abreast: 9, widebody: true, diameter: 5.77, art: ["B789"] },
    { match: /B772|B773|B77W|B77L|777/, label: "B777", length: 73.9, span: 64.8, rows: 40, abreast: 10, widebody: true, diameter: 6.2, art: ["B77W", "B772"] },
    { match: /B744|B748|747/, label: "B747", length: 70.6, span: 64.4, rows: 42, abreast: 10, widebody: true, diameter: 6.5, art: ["A346", "A343"] },
    { match: /B763|B764|767/, label: "B767", length: 54.9, span: 47.6, rows: 34, abreast: 7, widebody: true, diameter: 5.03, art: ["A306", "A310"] },
  ];

  const AISLES = { 4: [2, 2], 5: [2, 3], 6: [3, 3], 7: [2, 3, 2], 8: [2, 4, 2], 9: [3, 3, 3], 10: [3, 4, 3] };

  function layoutFor(icao, title, plannedPax, realSeats = 0) {
    // Le type OACI fait foi ; le titre du simulateur ne départage qu'à défaut.
    const code = String(icao || "").toUpperCase();
    const family = (code && FAMILIES.find((entry) => entry.match.test(code)))
      || FAMILIES.find((entry) => entry.match.test(String(title || "").toUpperCase()));
    if (family) {
      // Quand l'avion publie ses sièges, la cabine en a exactement ce nombre.
      const rows = realSeats ? Math.ceil(realSeats / family.abreast) : family.rows;
      return { ...family, rows, generic: false };
    }
    const pax = Math.max(40, finite(plannedPax) || 150);
    const abreast = pax > 300 ? 9 : pax > 120 ? 6 : 4;
    const rows = Math.max(10, Math.min(50, Math.ceil(pax / abreast)));
    return {
      label: String(icao || "").toUpperCase() || "—",
      length: 12 + rows * 0.85,
      span: 12 + rows * 0.8,
      rows,
      abreast,
      widebody: abreast > 6,
      diameter: abreast > 6 ? 5.6 : abreast > 4 ? 3.95 : 2.8,
      art: abreast > 6 ? ["A333"] : abreast > 4 ? ["A320"] : ["AT75"],
      generic: true,
    };
  }

  /* ------------------------------------------------------------- état */

  let listeners = new Set();
  let planKey = null;
  let samples = [];
  let lastSampleAt = 0;
  let services = {};
  let previousDerived = {};
  let pushbackSeen = false;
  let pushbackDone = false;
  let loadsheet = null;
  let report = {};
  let latest = null;
  let lastGuidance = null;

  function reset(key) {
    planKey = key;
    samples = [];
    lastSampleAt = 0;
    services = {};
    previousDerived = {};
    pushbackSeen = false;
    pushbackDone = false;
    loadsheet = null;
    report = {};
  }

  function emit(event) {
    for (const listener of listeners) {
      try {
        listener(event);
      } catch (_error) {
        // Un abonné défaillant ne prive pas les autres de l'événement.
      }
    }
  }

  /** GSX ou MSFS repoussent-ils l'avion en ce moment ? */
  function pushbackActive(aircraft) {
    const gsx = aircraft?.ground_services;
    const ramp = aircraft?.ramp;
    // FSDT_GSX_PUSHBACK_STATUS n'en fait pas partie : relevé en direct, il
    // reste à 11 une fois le repoussage terminé, et ne dit donc rien de
    // l'instant présent. L'état « départ » de GSX, lui, revient à disponible.
    return Boolean(
      gsx?.departure === "active"
      || ramp?.pushback_attached === true
      || (ramp?.pushback_state !== null && ramp?.pushback_state !== undefined && ramp.pushback_state !== 3)
    );
  }

  function serviceTrack(key) {
    if (!services[key]) services[key] = { startedAt: null, endedAt: null, startValue: null };
    return services[key];
  }

  /** Avancement mesuré d'un service, de 0 à 1, ou null s'il n'est pas publié. */
  function progressOf(key, sample, ofp) {
    if (!sample) return null;
    if (key === "boarding") {
      return sample.planned ? clamp01(sample.boarded / sample.planned) : null;
    }
    if (key === "cargo") return sample.cargoBoarded === null ? null : clamp01(sample.cargoBoarded / 100);
    if (key === "deboarding") {
      return sample.planned ? clamp01(sample.deboarded / sample.planned) : null;
    }
    if (key === "refueling") {
      const track = services.refueling;
      const target = finite(ofp?.blockFuelKg);
      if (!track || track.startValue === null || target === null || sample.fuel === null) return null;
      const span = target - track.startValue;
      if (span <= 1) return 1;
      return clamp01((sample.fuel - track.startValue) / span);
    }
    return null;
  }

  /** Rythme récent d'un service, en fraction par milliseconde. */
  function rateOf(key, ofp, now) {
    const recent = samples.filter((sample) => now - sample.t <= RATE_WINDOW_MS);
    if (recent.length < 2) return null;
    const first = recent[0];
    const last = recent.at(-1);
    if (last.t - first.t < RATE_MIN_SPAN_MS) return null;
    const from = progressOf(key, first, ofp);
    const to = progressOf(key, last, ofp);
    if (from === null || to === null || to <= from) return null;
    return (to - from) / (last.t - first.t);
  }

  function derive(gsx) {
    const cargoActive = gsx && gsx.boarding === "active"
      && finite(gsx.cargo_boarded_pct) !== null && finite(gsx.cargo_boarded_pct) < 100;
    const cargoDone = gsx && finite(gsx.cargo_boarded_pct) !== null && finite(gsx.cargo_boarded_pct) >= 100;
    return {
      boarding: gsx?.boarding || null,
      cargo: cargoDone ? "completed" : cargoActive ? "active" : null,
      refueling: gsx?.refueling || null,
      catering: gsx?.catering || null,
      water: gsx?.water || null,
      lavatory: gsx?.lavatory || null,
      deboarding: gsx?.deboarding || null,
      departure: gsx?.departure || null,
    };
  }

  /** Intègre un relevé : échantillons, débuts et fins de service, événements. */
  function ingest(context) {
    const { aircraft, ofp } = context;
    const key = context.planKey || "none";
    if (key !== planKey) reset(key);
    const gsx = aircraft?.ground_services || null;
    const now = Date.now();
    const fuel = finite(aircraft?.configuration?.fuel_total_kg);
    const sample = gsx ? {
      t: now,
      planned: finite(gsx.passengers_planned),
      boarded: finite(gsx.passengers_boarded) || 0,
      deboarded: finite(gsx.passengers_deboarded) || 0,
      cargoBoarded: finite(gsx.cargo_boarded_pct),
      fuel,
    } : null;
    if (sample && now - lastSampleAt >= SAMPLE_INTERVAL_MS) {
      samples.push(sample);
      samples = samples.filter((entry) => now - entry.t <= SAMPLE_HISTORY_MS);
      lastSampleAt = now;
    }

    const derived = derive(gsx);
    for (const [service, state] of Object.entries(derived)) {
      const track = serviceTrack(service);
      const running = state === "active" || state === "requested";
      if (running && track.startedAt === null) {
        track.startedAt = now;
        track.endedAt = null;
        if (service === "refueling") track.startValue = fuel;
      }
      const wasRunning = ["active", "requested"].includes(previousDerived[service]);
      const finished = state === "completed" || (wasRunning && !running && state !== null);
      if (finished && track.startedAt !== null && track.endedAt === null) {
        track.endedAt = now;
        report[`${service}_s`] = Math.round((now - track.startedAt) / 1000);
        const duration = now - track.startedAt;
        if (STANDARD_DURATION_MS[service] && duration > 60000 && duration < 3600000) {
          const store = readStore(DURATIONS_KEY);
          store[service] = [...(store[service] || []), duration].slice(-DURATION_HISTORY);
          writeStore(DURATIONS_KEY, store);
        }
        if (service !== "departure") emit({ type: `${service}_completed`, aircraft });
      }
    }
    previousDerived = derived;

    if (pushbackActive(aircraft)) {
      if (!pushbackSeen) {
        pushbackSeen = true;
        report.pushback_started_at = new Date(now).toISOString();
        if (loadsheet) loadsheet.frozen = true;
        emit({ type: "pushback_started", aircraft });
      }
    } else if (pushbackSeen && !pushbackDone && aircraft) {
      pushbackDone = true;
      report.pushback_completed_at = new Date(now).toISOString();
      emit({ type: "pushback_completed", aircraft });
    }

    updateLoadsheet(context, derived, now);
    learnNoseOffset(context);
  }

  /** Mesure, au départ, où MSFS a garé cet avion par rapport à son poste. */
  function learnNoseOffset(context) {
    const { aircraft } = context;
    if (context.arrival || !aircraft?.on_ground || pushbackActive(aircraft)) return;
    if ((finite(aircraft.ground_speed_kt) || 0) > 0.5 || typeof GROUND === "undefined") return;
    const position = GROUND.localPosition(aircraft);
    if (!position) return;
    const heading = finite(aircraft.heading_true_deg) || 0;
    const layout = layoutFor(context.ofp?.type, aircraft.title, null);
    for (const parking of GROUND.parkings()) {
      const radius = finite(parking.radius_m);
      if (!radius) continue;
      const geometry = standGeometry(parking, position, heading);
      if (!geometry || geometry.angle > 3 || Math.abs(geometry.lateral) > 2) continue;
      if (Math.abs(geometry.along) > radius) continue;
      const offset = radius + geometry.along;
      // Une valeur hors de toute proportion trahit un avion garé à la main.
      if (offset < layout.length * 0.3 || offset > layout.length * 0.85) continue;
      const store = readStore(NOSE_OFFSET_KEY);
      const key = String(aircraft.title || layout.label);
      if (Math.abs((store[key] || 0) - offset) > 0.2) {
        store[key] = Math.round(offset * 10) / 10;
        writeStore(NOSE_OFFSET_KEY, store);
      }
      return;
    }
  }

  /** Position de l'avion dans le repère d'un poste : le long de l'axe, de côté. */
  function standGeometry(parking, position, heading) {
    const standHeading = finite(parking.heading) || 0;
    const angle = Math.abs((((heading - standHeading) % 360) + 540) % 360 - 180);
    const rad = (standHeading * Math.PI) / 180;
    const dx = parking.position.x - position.x;
    const dy = parking.position.y - position.y;
    return {
      angle,
      // Distance du centre du poste devant l'avion, et écart à droite de l'axe.
      along: dx * Math.sin(rad) + dy * Math.cos(rad),
      lateral: -(dx * Math.cos(rad) - dy * Math.sin(rad)),
    };
  }

  /* ------------------------------------------------------- A-CDM */

  const TIMELINE_SERVICES = ["boarding", "cargo", "refueling", "catering", "water", "lavatory", "deboarding"];

  function timeline(context, now = Date.now()) {
    const { ofp } = context;
    const rows = [];
    const lastSample = samples.at(-1) || null;
    for (const key of TIMELINE_SERVICES) {
      const track = services[key];
      if (!track || track.startedAt === null) continue;
      const progress = track.endedAt !== null ? 1 : progressOf(key, lastSample, ofp);
      let eta = track.endedAt;
      let estimate = "measured";
      if (eta === null) {
        const rate = rateOf(key, ofp, now);
        const learned = median(readStore(DURATIONS_KEY)[key] || []);
        if (rate && progress !== null) {
          eta = now + (1 - progress) / rate;
        } else if (learned) {
          eta = Math.max(now, track.startedAt + learned);
          estimate = "learned";
        } else if (STANDARD_DURATION_MS[key]) {
          eta = Math.max(now, track.startedAt + STANDARD_DURATION_MS[key]);
          estimate = "standard";
        } else {
          estimate = "unknown";
        }
      }
      rows.push({ key, start: track.startedAt, end: track.endedAt, eta, progress, estimate });
    }

    const departureRows = rows.filter((row) => row.key !== "deboarding");
    const open = departureRows.filter((row) => row.end === null);
    let tobt = null;
    let critical = null;
    if (open.length) {
      const known = open.filter((row) => row.eta !== null);
      if (known.length) {
        critical = known.reduce((latestRow, row) => (row.eta > latestRow.eta ? row : latestRow));
        tobt = critical.eta + DOORS_CLOSING_MS;
      }
    } else if (departureRows.length) {
      tobt = Math.max(...departureRows.map((row) => row.end)) + DOORS_CLOSING_MS;
    }

    const scheduled = Date.parse(ofp?.offBlock || "");
    let delayMin = null;
    if (tobt !== null && Number.isFinite(scheduled) && Math.abs(tobt - scheduled) <= SCHEDULE_RELEVANCE_MS) {
      delayMin = Math.round((tobt - scheduled) / 60000);
    }
    if (tobt !== null) {
      report.tobt = new Date(tobt).toISOString();
      if (delayMin !== null) report.tobt_vs_ofp_min = delayMin;
    }
    return {
      rows,
      tobt,
      critical,
      delayMin,
      scheduled: Number.isFinite(scheduled) ? scheduled : null,
      ready: tobt !== null && !open.length && departureRows.length > 0,
    };
  }

  /* ------------------------------------------------- masse et centrage */

  function updateLoadsheet(context, derived, now) {
    if (loadsheet?.frozen) return;
    const { aircraft, fms, ofp } = context;
    const gsx = aircraft?.ground_services;
    if (!gsx || derived.boarding !== "completed" || derived.refueling === "active") return;

    const fmsZfw = fms?.available ? finite(fms.weights?.zfw_kg) : null;
    const fmsFuel = fms?.available ? finite(fms.weights?.fuel_kg) : null;
    const msfsFuel = finite(aircraft.configuration?.fuel_total_kg);
    const msfsTotal = finite(aircraft.configuration?.total_weight_kg);
    const fuel = fmsFuel ?? msfsFuel;
    const zfw = fmsZfw ?? (msfsTotal !== null && msfsFuel !== null ? msfsTotal - msfsFuel : null);
    const taxi = finite(ofp?.taxiFuelKg) || 0;
    const tow = zfw !== null && fuel !== null ? zfw + fuel - taxi : null;
    const pax = finite(gsx.passengers_boarded);

    const lmc = [];
    const ofpPax = finite(ofp?.pax);
    if (pax !== null && ofpPax !== null && pax !== ofpPax) {
      lmc.push(fmt("ta_lmc_pax", { delta: `${pax - ofpPax > 0 ? "+" : "−"}${Math.abs(pax - ofpPax)}` }));
    }
    const ofpZfw = finite(ofp?.zfwKg);
    if (zfw !== null && ofpZfw !== null && Math.abs(zfw - ofpZfw) > LMC_ZFW_KG) {
      lmc.push(fmt("ta_lmc_zfw", { delta: signedKg(zfw - ofpZfw) }));
    }
    if (!loadsheet) emit({ type: "loadsheet_issued", aircraft });
    loadsheet = {
      editionAt: loadsheet?.editionAt || now,
      frozen: false,
      source: fmsZfw !== null ? "fms" : "msfs",
      pax,
      cargoPct: finite(gsx.cargo_boarded_pct),
      zfw,
      fuel,
      tow,
      cg: finite(aircraft.ramp?.cg_percent_mac) ?? finite(context.payload?.cg_percent_mac),
      // Centrages du devis final de l'avion lui-même, quand il en publie un.
      macZfw: finite(context.payload?.loadsheet?.mac_zfw),
      macTow: finite(context.payload?.loadsheet?.mac_tow),
      lmc,
    };
    report.loadsheet = {
      pax: loadsheet.pax,
      zfw_kg: zfw === null ? null : Math.round(zfw),
      fuel_kg: fuel === null ? null : Math.round(fuel),
      tow_kg: tow === null ? null : Math.round(tow),
      cg_percent_mac: loadsheet.cg === null ? null : Math.round(loadsheet.cg * 10) / 10,
      lmc: lmc.length,
    };
  }

  /* ------------------------------------------------------- VDGS */

  /**
   * Distance au point d'arrêt et écart d'axe, d'après le poste MSFS.
   *
   * Le point d'arrêt est le centre du poste, l'axe son cap : c'est là que MSFS
   * gare l'avion. Le résultat est une estimation, signalée comme telle.
   */
  function vdgs(context) {
    const { aircraft } = context;
    // À l'arrivée seulement : au départ, l'avion est déjà sur son poste.
    if (!context.arrival || !aircraft?.on_ground || typeof GROUND === "undefined") return null;
    if ((finite(aircraft.ground_speed_kt) || 0) > 15 || pushbackActive(aircraft)) return null;
    const position = GROUND.localPosition(aircraft);
    const parkings = GROUND.parkings();
    if (!position || !parkings.length) return null;
    const heading = finite(aircraft.heading_true_deg) || 0;
    const preferred = context.targetStand
      ? parkings.find((parking) => parking.label === context.targetStand)
      : null;
    const candidates = preferred ? [preferred] : parkings;
    // Le point d'arrêt place le nez au bord avant du poste : la distance du nez
    // au point de référence est celle mesurée au départ, à défaut estimée.
    const layout = layoutFor(context.ofp?.type, aircraft.title, null);
    const learned = finite(readStore(NOSE_OFFSET_KEY)[String(aircraft.title || layout.label)]);
    const noseOffset = learned ?? layout.length * NOSE_OFFSET_RATIO;
    let best = null;
    for (const parking of candidates) {
      const geometry = standGeometry(parking, position, heading);
      if (geometry.angle > 45) continue;
      const radius = finite(parking.radius_m) || 0;
      const remaining = geometry.along + radius - noseOffset;
      if (remaining < -4 || remaining > VDGS_RANGE_M || Math.abs(geometry.lateral) > 12) continue;
      if (!best || Math.abs(remaining) < Math.abs(best.along)) {
        best = { label: parking.label, along: remaining, lateral: geometry.lateral, learned: learned !== null };
      }
    }
    return best;
  }

  /* ------------------------------------------------------- rendu */

  const dom = {};
  let builtKey = "";

  function svg(tag, attributes = {}, parent = null) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    if (parent) parent.append(node);
    return node;
  }

  function html(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  /** Ordre de remplissage des sièges, selon les portes réellement servies. */
  function seatOrder(layout, twoDoors) {
    const seats = [];
    const middle = Math.floor(layout.rows / 2);
    const rowOrder = [];
    if (twoDoors) {
      // Deux escaliers : chaque moitié se remplit depuis le milieu vers sa porte.
      for (let offset = 0; offset < middle + 1; offset += 1) {
        if (middle - 1 - offset >= 0) rowOrder.push(middle - 1 - offset);
        if (middle + offset < layout.rows) rowOrder.push(middle + offset);
      }
    } else {
      // Porte avant seule : de l'arrière vers l'avant.
      for (let row = layout.rows - 1; row >= 0; row -= 1) rowOrder.push(row);
    }
    const columns = [...Array(layout.abreast).keys()];
    // Hublot, milieu, couloir : l'ordre naturel d'une rangée qui se remplit.
    const groups = AISLES[layout.abreast] || [layout.abreast];
    const distance = (column) => {
      let start = 0;
      for (const size of groups) {
        if (column < start + size) {
          const inGroup = column - start;
          return Math.min(inGroup, size - 1 - inGroup);
        }
        start += size;
      }
      return 0;
    };
    const ordered = columns.sort((a, b) => distance(a) - distance(b));
    for (const row of rowOrder) for (const column of ordered) seats.push(`${row}:${column}`);
    return seats;
  }

  /** Sous-ensemble stable des sièges occupés quand l'avion n'est pas plein. */
  function occupiedSubset(order, count) {
    if (count >= order.length) return order;
    const hash = (text) => {
      let value = 2166136261;
      for (const character of text) value = Math.imul(value ^ character.charCodeAt(0), 16777619);
      return value >>> 0;
    };
    const chosen = new Set(
      [...order].sort((a, b) => hash(a) - hash(b)).slice(0, Math.max(0, count))
    );
    return order.filter((seat) => chosen.has(seat));
  }

  /* ------------------------------------------------------- silhouettes */

  /** Silhouette plane-watch de l'avion : code exact, sinon le plus proche. */
  function silhouetteFor(icao, layout) {
    const data = typeof SILHOUETTES === "undefined" ? null : SILHOUETTES;
    if (!data) return null;
    const exact = String(icao || "").toUpperCase();
    const candidates = [exact, data.aliases?.[exact], ...(layout.art || []), "A320"];
    const code = candidates.find((candidate) => candidate && data.aircraft[candidate]);
    return code ? { code, ...data.aircraft[code] } : null;
  }

  /** Tracés d'une silhouette, transformations de calque comprises. */
  function silhouettePaths(art, parent, attributes = {}) {
    for (const entry of art.paths) {
      const group = entry.t ? svg("g", { transform: entry.t }, parent) : parent;
      svg("path", { d: entry.d, ...attributes }, group);
    }
  }

  const bboxCache = new Map();

  /**
   * Emprise réelle de la silhouette dans sa case de 70 px. Mesurée une fois,
   * dans un SVG hors écran mais affiché : un élément masqué renvoie une
   * emprise nulle, et le module est souvent construit onglet fermé.
   */
  function silhouetteBox(art) {
    if (bboxCache.has(art.code)) return bboxCache.get(art.code);
    const probe = svg("svg", { width: "10", height: "10", viewBox: art.viewBox });
    probe.style.cssText = "position:absolute;left:-9999px;top:0;visibility:hidden";
    const group = svg("g", {}, probe);
    silhouettePaths(art, group);
    document.body.append(probe);
    let box;
    try {
      const measured = group.getBBox();
      box = { x: measured.x, y: measured.y, width: measured.width, height: measured.height };
    } catch (_error) {
      box = null;
    }
    probe.remove();
    if (!box || !box.width || !box.height) {
      const [x, y, width, height] = String(art.viewBox).split(/\s+/).map(Number);
      box = { x, y, width, height };
    }
    bboxCache.set(art.code, box);
    return box;
  }

  /* ---------------------------------------------------------- véhicules */

  /*
   * Véhicules de piste, dessinés dans le style des silhouettes plane-watch :
   * aplat blanc, contour noir, vus de dessus, en mètres réels. Chacun est
   * tracé « bout utile » à l'origine — la marche haute de l'escalier, la
   * caisse du camion de commissariat — et s'étend vers les x positifs ; la
   * rotation le tourne vers l'avion.
   */
  const VEHICLE_SHAPES = {
    stairs(g) {
      rect(g, 0, -1.2, 1.6, 2.4);
      rect(g, 1.6, -1.1, 5, 2.2);
      for (let x = 2; x < 6.5; x += 0.45) line(g, x, -1.1, x, 1.1, "ta-detail");
      rect(g, 6.6, -1.25, 2.2, 2.5, 0.4);
      rect(g, 7.9, -1.05, 0.7, 2.1, 0.2, "ta-glass");
    },
    catering(g) {
      rect(g, 0.2, -1.3, 6.4, 2.6, 0.2);
      line(g, 0.9, -1.3, 0.9, 1.3, "ta-detail");
      rect(g, 6.8, -1.2, 2.2, 2.4, 0.5);
      rect(g, 8.1, -1.0, 0.7, 2.0, 0.2, "ta-glass");
    },
    fuel(g) {
      rect(g, 0, -1.25, 7.6, 2.5, 1.2);
      line(g, 2.5, -1.25, 2.5, 1.25, "ta-detail");
      line(g, 5.0, -1.25, 5.0, 1.25, "ta-detail");
      rect(g, 7.9, -1.2, 2.3, 2.4, 0.5);
      rect(g, 9.4, -1.0, 0.65, 2.0, 0.2, "ta-glass");
    },
    belt(g) {
      rect(g, 0, -0.6, 8, 1.2, 0.2);
      for (let x = 0.5; x < 8; x += 0.7) line(g, x, -0.6, x, 0.6, "ta-detail");
      rect(g, 4.6, 0.6, 2.2, 1.3, 0.3);
      rect(g, 5.9, 0.7, 0.7, 1.1, 0.15, "ta-glass");
    },
    carts(g) {
      for (let index = 0; index < 3; index += 1) {
        const x = index * 3.4;
        rect(g, x, -0.85, 2.8, 1.7, 0.2);
        line(g, x + 2.8, 0, x + 3.4, 0, "ta-detail");
      }
      // Le tracteur de tête est celui de plane-watch.
      const tug = SILHOUETTES?.vehicles?.baggage_tug;
      if (tug) {
        const [, , width] = String(tug.viewBox).split(/\s+/).map(Number);
        const scale = 3.2 / width;
        const holder = svg("g", { transform: `translate(${10.4 + 1.6} 0) rotate(90) scale(${scale}) translate(${-width / 2} ${-width / 2})` }, g);
        silhouettePaths(tug, holder, { class: "ta-shape" });
      }
    },
    gpu(g) {
      rect(g, 0.6, -0.8, 2.6, 1.6, 0.3);
      line(g, 0, 0, 0.6, 0, "ta-cable");
      line(g, 1.2, -0.8, 1.2, 0.8, "ta-detail");
    },
    service(g) {
      rect(g, 0.2, -1.1, 4.6, 2.2, 0.3);
      rect(g, 5.0, -1.05, 1.9, 2.1, 0.45);
      rect(g, 6.2, -0.9, 0.6, 1.8, 0.15, "ta-glass");
    },
    tug(g) {
      line(g, 0, 0, 2.2, 0, "ta-cable");
      rect(g, 2.2, -1.6, 5.6, 3.2, 0.8);
      rect(g, 5.6, -1.2, 1.4, 2.4, 0.3, "ta-glass");
    },
  };

  function rect(g, x, y, width, height, radius = 0, className = "ta-shape") {
    return svg("rect", { x, y, width, height, rx: radius, class: className }, g);
  }
  function line(g, x1, y1, x2, y2, className) {
    return svg("line", { x1, y1, x2, y2, class: className }, g);
  }

  /** Véhicule à l'échelle, posé en (x, y), tourné de `angle` degrés. */
  function vehicle(root, key, shape, x, y, angle, pxPerMetre, from) {
    const outer = svg("g", {
      class: `ta-vehicle ta-vehicle-${key}`,
      "data-show": "0",
      style: `--from-x:${from[0]}px;--from-y:${from[1]}px`,
    }, root);
    const inner = svg("g", { transform: `translate(${x} ${y}) rotate(${angle}) scale(${pxPerMetre})` }, outer);
    VEHICLE_SHAPES[shape](inner);
    dom.vehicles[key] = outer;
    return outer;
  }

  /* ------------------------------------------------------------ rampe */

  function buildRamp(layout, icao) {
    const width = 360;
    const height = 470;
    const root = svg("svg", {
      viewBox: `0 0 ${width} ${height}`,
      class: "ta-ramp-svg",
      role: "img",
      "aria-label": tr("ta_ramp"),
    });
    const cx = width / 2;
    const top = 62;
    const art = silhouetteFor(icao, layout);
    dom.vehicles = {};
    dom.seats = new Map();

    // Marquage au sol : axe du poste et barre d'arrêt.
    svg("line", { x1: cx, y1: 6, x2: cx, y2: height - 6, class: "ta-lead-line" }, root);
    svg("line", { x1: cx - 30, y1: top - 4, x2: cx + 30, y2: top - 4, class: "ta-stop-bar" }, root);
    if (!art) return root;

    // L'avion remplit la rampe, nez à la barre d'arrêt, proportions intactes.
    const box = silhouetteBox(art);
    const scale = Math.min(330 / box.height, 300 / box.width);
    const length = box.height * scale;
    const span = box.width * scale;
    const pxPerMetre = length / layout.length;
    const placement = `translate(${cx - (box.x + box.width / 2) * scale} ${top - box.y * scale}) scale(${scale})`;

    const defs = svg("defs", {}, root);
    // Un clipPath n'accepte que des formes : la transformation de chaque
    // tracé est donc portée par le tracé lui-même, pas par un groupe.
    const clip = svg("clipPath", { id: "ta-silhouette-clip" }, defs);
    for (const entry of art.paths) {
      svg("path", { d: entry.d, transform: `${placement} ${entry.t || ""}`.trim() }, clip);
    }

    const aircraft = svg("g", { class: "ta-aircraft", transform: placement }, root);
    silhouettePaths(art, aircraft, { class: "ta-silhouette" });

    const y = (fraction) => top + fraction * length;
    const fuselage = Math.max(layout.diameter * pxPerMetre, layout.abreast * 3.2 + 4);
    const left = cx - fuselage / 2;
    const right = cx + fuselage / 2;

    // Réservoirs d'aile : un aplat qui gagne du centre vers les saillants,
    // découpé par la silhouette elle-même.
    const tanks = svg("g", { "clip-path": "url(#ta-silhouette-clip)" }, root);
    const wingTop = y(0.34);
    const wingHeight = y(0.64) - wingTop;
    dom.fuelTanks = [
      svg("rect", { x: right, y: wingTop, width: 0, height: wingHeight, class: "ta-fuel-tank" }, tanks),
      svg("rect", { x: left, y: wingTop, width: 0, height: wingHeight, class: "ta-fuel-tank" }, tanks),
    ];
    dom.tankSpan = span / 2 - fuselage / 2;
    dom.tankLeft = left;

    // Cabine : un siège par place, découpée elle aussi par la silhouette.
    const seats = svg("g", { class: "ta-seats", "clip-path": "url(#ta-silhouette-clip)" }, root);
    const groups = AISLES[layout.abreast] || [layout.abreast];
    const aisle = Math.max(1.2, fuselage * 0.07);
    const cabinTop = y(0.13);
    const cabinBottom = y(0.84);
    const pitch = (cabinBottom - cabinTop) / layout.rows;
    const seatWidth = (fuselage - 2 - (groups.length - 1) * aisle) / layout.abreast;
    for (let row = 0; row < layout.rows; row += 1) {
      let x = left + 1;
      let column = 0;
      groups.forEach((size, groupIndex) => {
        for (let index = 0; index < size; index += 1) {
          const seat = svg("rect", {
            x: x + 0.3,
            y: cabinTop + row * pitch + pitch * 0.15,
            width: Math.max(0.8, seatWidth - 0.6),
            height: Math.max(0.8, pitch * 0.7),
            rx: Math.min(1, seatWidth / 4),
            class: "ta-seat",
          }, seats);
          dom.seats.set(`${row}:${column}`, seat);
          x += seatWidth;
          column += 1;
        }
        if (groupIndex < groups.length - 1) x += aisle;
      });
    }

    // Portes passagers à gauche (L1, arrière), portes cargo à droite.
    const doorFront = y(0.1);
    const doorRear = y(0.86);
    const holdFront = y(0.28);
    const holdRear = y(0.68);
    for (const doorY of [doorFront, doorRear]) {
      svg("rect", { x: left - 1.5, y: doorY - 3.5, width: 3, height: 7, rx: 1, class: "ta-door" }, root);
    }
    for (const holdY of [holdFront, holdRear]) {
      svg("rect", { x: right - 1.5, y: holdY - 4.5, width: 3, height: 9, rx: 1, class: "ta-door ta-door-cargo" }, root);
    }

    // Passerelle : rotonde côté aérogare, tunnel, cabine contre L1.
    const jetway = svg("g", { class: "ta-vehicle ta-jetway", "data-show": "0" }, root);
    const cab = 3.2 * pxPerMetre;
    svg("rect", { x: 0, y: doorFront - 30, width: 12, height: 60, class: "ta-terminal" }, jetway);
    svg("circle", { cx: 18, cy: doorFront - 14, r: 2.4 * pxPerMetre, class: "ta-shape" }, jetway);
    svg("rect", { x: 18, y: doorFront - 1.4 * pxPerMetre, width: left - 18 - cab, height: 2.8 * pxPerMetre, class: "ta-shape", transform: `rotate(12 18 ${doorFront})` }, jetway);
    svg("rect", { x: left - cab - 1, y: doorFront - cab / 2, width: cab, height: cab, rx: 2, class: "ta-shape" }, jetway);
    dom.vehicles.jetway = jetway;

    const m = pxPerMetre;
    vehicle(root, "stairs-front", "stairs", left - 0.5, doorFront, 180, m, [-90, 0]);
    vehicle(root, "stairs-rear", "stairs", left - 0.5, doorRear, 180, m, [-90, 0]);
    vehicle(root, "catering-front", "catering", right + 0.5, doorFront + 2, 0, m, [110, 0]);
    vehicle(root, "catering-rear", "catering", right + 0.5, doorRear - 2, 0, m, [110, 0]);
    vehicle(root, "belt-front", "belt", right + 0.5, holdFront, 0, m, [110, 0]);
    vehicle(root, "belt-rear", "belt", right + 0.5, holdRear, 0, m, [110, 0]);
    // Les trains de chariots attendent au pied des tapis, le long du
    // fuselage ; l'avitailleur se gare sous l'aile droite, plus au large.
    vehicle(root, "carts-front", "carts", right + 9 * m, holdFront, 90, m, [130, 0]);
    vehicle(root, "carts-rear", "carts", right + 9 * m, holdRear, 90, m, [130, 0]);
    const truckX = Math.min(width - 2.5 * m, cx + span * 0.4);
    vehicle(root, "fuel", "fuel", truckX, y(0.4), 90, m, [140, 60]);
    vehicle(root, "gpu", "gpu", cx - 1.5 * m, y(0.05), 180, m, [-90, -40]);
    vehicle(root, "water", "service", right + 0.5, y(0.78), 0, m, [110, 0]);
    vehicle(root, "lavatory", "service", right + 0.5, y(0.93), 0, m, [110, 0]);
    vehicle(root, "tug", "tug", cx, top - 1, -90, m, [0, -80]);

    // Flux animés : tuyau d'avitaillement, bagages, passagers.
    dom.hose = svg("path", {
      d: `M ${truckX} ${y(0.4)} Q ${truckX - 10} ${y(0.44)} ${cx + span * 0.24} ${y(0.47)}`,
      class: "ta-hose",
      "data-show": "0",
    }, root);
    dom.bagFlows = [holdFront, holdRear].map((holdY) => svg("line", {
      x1: right + 8 * m, y1: holdY, x2: right + 1, y2: holdY, class: "ta-bag-flow", "data-show": "0",
    }, root));
    dom.paxFlows = [
      svg("line", { x1: left - 9 * m, y1: doorFront, x2: left - 9 * m - 50, y2: doorFront + 36, class: "ta-pax-flow", "data-show": "0" }, root),
      svg("line", { x1: left - 9 * m, y1: doorRear, x2: left - 9 * m - 50, y2: doorRear - 36, class: "ta-pax-flow", "data-show": "0" }, root),
    ];

    // Crédit exigé par la licence CC BY-NC-SA des silhouettes.
    const credit = svg("text", { x: width - 6, y: height - 6, class: "ta-credit" }, root);
    credit.textContent = "Silhouette: plane-watch · CC BY-NC-SA 4.0";

    dom.rampLayout = layout;
    dom.rampArt = art.code;
    return root;
  }

  function build(panel, context) {
    panel.innerHTML = "";
    const gsxRunning = Boolean(context.aircraft?.ground_services);
    const layout = layoutFor(context.ofp?.type, context.aircraft?.title, context.aircraft?.ground_services?.passengers_planned || context.ofp?.pax, context.payload?.seats?.length || 0);

    const head = html("div", "ta-head");
    const title = html("div");
    title.append(html("div", "card-kicker", tr("ta_kicker")));
    title.append(html("h2", null, tr("ta_title")));
    head.append(title);
    dom.status = html("span", "ta-status-pill", "—");
    head.append(dom.status);
    panel.append(head);

    dom.waiting = html("p", "ta-waiting", tr("ta_waiting"));
    panel.append(dom.waiting);

    const grid = html("div", "ta-grid");
    dom.grid = grid;

    // Colonne gauche : la rampe.
    const rampCard = html("section", "ta-card ta-ramp-card");
    const rampHead = html("div", "ta-card-head");
    rampHead.append(html("h3", null, tr("ta_ramp")));
    rampHead.append(html("span", "ta-chip", layout.generic ? `${layout.label} · ${tr("ta_generic_layout")}` : layout.label));
    rampCard.append(rampHead);
    rampCard.append(buildRamp(layout, context.ofp?.type || context.aircraft?.title));
    const legend = html("div", "ta-ramp-figures");
    const figure = (label, id) => {
      const node = html("div", "ta-figure");
      node.append(html("span", "ta-figure-label", label));
      const value = html("strong", "ta-figure-value", "—");
      dom[id] = value;
      node.append(value);
      const bar = html("span", "ta-bar");
      const fill = html("span", "ta-bar-fill");
      bar.append(fill);
      dom[`${id}Bar`] = fill;
      node.append(bar);
      legend.append(node);
    };
    figure(tr("ta_pax"), "paxValue");
    dom.paxValueBar.classList.add("ta-bar-pax");
    figure(tr("ta_hold_fwd"), "holdFwdValue");
    figure(tr("ta_hold_aft"), "holdAftValue");
    figure(tr("ta_fuel"), "fuelValue");
    rampCard.append(legend);
    dom.payloadWarning = html("p", "ta-payload-warning", "");
    dom.payloadWarning.hidden = true;
    rampCard.append(dom.payloadWarning);
    dom.seatNote = html("p", "ta-note", tr("ta_seats_note"));
    rampCard.append(dom.seatNote);
    dom.cargoNote = html("p", "ta-note", tr("ta_cargo_estimated"));
    dom.cargoNote.hidden = true;
    rampCard.append(dom.cargoNote);
    grid.append(rampCard);

    // Colonne droite : prochaine étape, chronologie, devis, VDGS.
    const side = html("div", "ta-side");

    const next = html("section", "ta-card ta-next");
    next.append(html("div", "ta-card-kicker", tr("ta_next")));
    dom.nextText = html("p", "ta-next-text", "—");
    next.append(dom.nextText);
    dom.nextActions = html("div", "ta-next-actions");
    next.append(dom.nextActions);
    side.append(next);

    const acdm = html("section", "ta-card ta-acdm");
    const acdmHead = html("div", "ta-card-head");
    acdmHead.append(html("h3", null, tr("ta_timeline")));
    acdmHead.append(html("span", "ta-chip", "A-CDM"));
    acdm.append(acdmHead);
    const tobt = html("div", "ta-tobt");
    const tobtBlock = html("div");
    tobtBlock.append(html("span", "ta-figure-label", tr("ta_tobt")));
    dom.tobtValue = html("strong", "ta-tobt-value", "—");
    tobtBlock.append(dom.tobtValue);
    tobt.append(tobtBlock);
    const stdBlock = html("div");
    stdBlock.append(html("span", "ta-figure-label", tr("ta_std")));
    dom.stdValue = html("strong", "ta-std-value", "—");
    stdBlock.append(dom.stdValue);
    tobt.append(stdBlock);
    dom.delayValue = html("span", "ta-delay", "");
    tobt.append(dom.delayValue);
    acdm.append(tobt);
    dom.critical = html("p", "ta-critical", "");
    acdm.append(dom.critical);
    dom.gantt = html("div", "ta-gantt");
    acdm.append(dom.gantt);
    acdm.append(html("p", "ta-note", tr("ta_tobt_note")));
    side.append(acdm);

    const sheet = html("section", "ta-card ta-loadsheet");
    const sheetHead = html("div", "ta-card-head");
    sheetHead.append(html("h3", null, tr("ta_loadsheet")));
    sheet.append(sheetHead);
    dom.loadsheet = html("pre", "ta-loadsheet-text", tr("ta_loadsheet_pending"));
    sheet.append(dom.loadsheet);
    dom.lmc = html("p", "ta-lmc", "");
    sheet.append(dom.lmc);
    dom.loadsheetNote = html("p", "ta-note", "");
    sheet.append(dom.loadsheetNote);
    side.append(sheet);

    const dock = html("section", "ta-card ta-vdgs-card");
    const dockHead = html("div", "ta-card-head");
    dockHead.append(html("h3", null, tr("ta_vdgs")));
    dock.append(dockHead);
    dom.vdgs = buildVdgs();
    dock.append(dom.vdgs.root);
    dock.append(html("p", "ta-note", tr("ta_vdgs_note")));
    dom.vdgsCard = dock;
    side.append(dock);

    grid.append(side);
    panel.append(grid);
    dom.panel = panel;
    dom.gsxRunning = gsxRunning;
    builtKey = `${window.I18N.getLanguage()}|${layout.label}|${layout.rows}|${layout.abreast}`;
  }

  /** Panneau VDGS : fond noir, chiffres ambrés, comme au poste. */
  function buildVdgs() {
    const root = html("div", "ta-vdgs");
    root.setAttribute("aria-live", "polite");
    const type = html("div", "ta-vdgs-type", "—");
    const distance = html("div", "ta-vdgs-distance", "—");
    const bar = html("div", "ta-vdgs-bar");
    const fill = html("span", "ta-vdgs-bar-fill");
    bar.append(fill);
    const arrows = html("div", "ta-vdgs-arrows");
    const leftArrow = html("span", "ta-vdgs-arrow", "◀");
    const centre = html("span", "ta-vdgs-centre", "▲");
    const rightArrow = html("span", "ta-vdgs-arrow", "▶");
    arrows.append(leftArrow, centre, rightArrow);
    root.append(type, distance, bar, arrows);
    return { root, type, distance, fill, leftArrow, rightArrow, centre };
  }

  function renderVdgs(target, guidance, label) {
    if (!target) return;
    target.root.dataset.state = guidance ? "active" : "idle";
    if (!guidance) {
      target.type.textContent = label || "—";
      target.distance.textContent = "—";
      target.fill.style.width = "0%";
      target.leftArrow.dataset.on = "0";
      target.rightArrow.dataset.on = "0";
      return;
    }
    target.type.textContent = `${label || ""} · ${guidance.label}`.trim();
    let text;
    let state = "approach";
    if (guidance.along < -1) {
      text = "TOO FAR";
      state = "stop";
    } else if (guidance.along <= 0.5) {
      text = "STOP";
      state = "stop";
    } else {
      text = `${guidance.along < 10 ? guidance.along.toFixed(1) : Math.round(guidance.along)} m`;
    }
    target.root.dataset.state = state;
    target.distance.textContent = text;
    target.fill.style.width = `${Math.round(clamp01(1 - guidance.along / 20) * 100)}%`;
    // Écart d'axe : la flèche indique le côté vers lequel tourner.
    target.leftArrow.dataset.on = guidance.lateral > 0.6 ? "1" : "0";
    target.rightArrow.dataset.on = guidance.lateral < -0.6 ? "1" : "0";
  }

  /**
   * D'où vient l'occupation de la cabine, de la plus réelle à l'illustrative :
   * les sièges publiés par l'avion (EFB du Fenix), sinon la répartition par
   * zone des « payload stations » MSFS, sinon l'ordre d'embarquement seul.
   */
  function cabinSource(context) {
    const seats = context.payload?.seats;
    if (Array.isArray(seats) && seats.length) return { source: "aircraft", seats };
    const zones = (context.aircraft?.ramp?.payload_stations || [])
      .filter((station) => station.kind === "cabin" && station.rows && finite(station.weight_kg) > 0)
      .map((station) => ({ rows: station.rows, weight: finite(station.weight_kg) }));
    if (zones.length) return { source: "zones", zones };
    return { source: "illustrative" };
  }

  /** Masse réelle par soute, ou null quand rien ne la publie. */
  function holdSource(context) {
    const cargo = context.payload?.cargo;
    if (cargo?.forward) {
      const aftKg = (finite(cargo.aft?.amount_kg) || 0) + (finite(cargo.bulk?.amount_kg) || 0);
      const aftCapacity = (finite(cargo.aft?.capacity_kg) || 0) + (finite(cargo.bulk?.capacity_kg) || 0);
      return {
        forward: { kg: finite(cargo.forward.amount_kg) || 0, fill: (finite(cargo.forward.amount_kg) || 0) / cargo.forward.capacity_kg },
        aft: { kg: aftKg, fill: aftCapacity ? aftKg / aftCapacity : 0 },
      };
    }
    const stations = (context.aircraft?.ramp?.payload_stations || []).filter((station) => station.kind === "cargo");
    const forwardKg = stations.filter((s) => s.position === "forward").reduce((sum, s) => sum + (finite(s.weight_kg) || 0), 0);
    const aftKg = stations.filter((s) => s.position !== "forward").reduce((sum, s) => sum + (finite(s.weight_kg) || 0), 0);
    const total = forwardKg + aftKg;
    if (!total) return null;
    return { forward: { kg: forwardKg, fill: forwardKg / total }, aft: { kg: aftKg, fill: aftKg / total } };
  }

  function setVehicle(key, visible) {
    const node = dom.vehicles?.[key];
    if (node) node.dataset.show = visible ? "1" : "0";
  }

  function running(state) {
    return state === "active" || state === "requested";
  }

  function renderRamp(context, derived) {
    const { aircraft, ofp } = context;
    const gsx = aircraft?.ground_services || {};
    const layout = dom.rampLayout;
    if (!layout || !dom.seats) return;

    // Cabine.
    const planned = finite(gsx.passengers_planned) || finite(ofp?.pax) || 0;
    // Passerelle : une seule porte, l'avant. Escaliers : les deux portes.
    const twoDoors = gsx.jetway !== "active";
    let onboard;
    if (derived.deboarding === "active" || derived.deboarding === "completed") {
      onboard = Math.max(0, planned - (finite(gsx.passengers_deboarded) || 0));
    } else {
      onboard = Math.min(planned, finite(gsx.passengers_boarded) || 0);
    }
    let cabin = cabinSource(context);
    // Un avion qui n'a pas été synchronisé avec GSX déclare ses sièges vides
    // pendant que GSX embarque : la cabine suit alors GSX, et l'alerte plus
    // bas dit que l'avion lui-même n'est pas chargé.
    const aircraftSeats = cabin.source === "aircraft" ? cabin.seats.filter(Boolean).length : null;
    const gsxBoarded = finite(gsx.passengers_boarded) || 0;
    if (aircraftSeats !== null && aircraftSeats < onboard - 2) {
      cabin = cabinSource({ ...context, payload: null });
    }
    // Pendant l'embarquement ou le débarquement, le compteur GSX est la
    // chronologie visible : certains avions publient leur charge cabine finale
    // dès le début, ce qui colorait tous les sièges avant l'arrivée des pax.
    const followingGsxProgress = running(derived.boarding) || running(derived.deboarding);
    let filled;
    let reserved;
    if (cabin.source === "aircraft" && !followingGsxProgress) {
      // Sièges réellement occupés, publiés par l'avion lui-même.
      filled = new Set(
        cabin.seats.map((on, index) => (on ? `${Math.floor(index / layout.abreast)}:${index % layout.abreast}` : null))
          .filter(Boolean)
      );
      reserved = new Set();
    } else {
      const order = occupiedSubset(seatOrder(layout, twoDoors), Math.min(planned, dom.seats.size));
      reserved = new Set(order);
      const scaled = planned > dom.seats.size ? Math.round((onboard / planned) * dom.seats.size) : onboard;
      if (followingGsxProgress) {
        // Un siège devient vert uniquement quand le compteur GSX gagne un pax.
        // Au débarquement, la cabine se vide dans l'ordre inverse.
        filled = new Set(
          derived.deboarding === "active" ? order.slice(order.length - scaled) : order.slice(0, scaled)
        );
      } else if (cabin.source === "zones") {
        // Répartition réelle par zone lue dans MSFS ; la place dans la zone
        // reste celle de l'ordre d'embarquement.
        filled = new Set();
        const total = cabin.zones.reduce((sum, zone) => sum + zone.weight, 0);
        for (const zone of cabin.zones) {
          const count = Math.round(scaled * (zone.weight / total));
          order.filter((seat) => {
            const row = Number(seat.split(":")[0]) + 1;
            return row >= zone.rows[0] && row <= zone.rows[1];
          }).slice(0, count).forEach((seat) => filled.add(seat));
        }
      } else {
        filled = new Set(
          derived.deboarding === "active" ? order.slice(order.length - scaled) : order.slice(0, scaled)
        );
      }
    }
    for (const [id, node] of dom.seats) {
      node.dataset.state = filled.has(id) ? "occupied" : reserved.has(id) ? "reserved" : "empty";
    }
    dom.seatNote.textContent = tr({
      aircraft: "ta_seats_aircraft",
      zones: "ta_seats_zones",
    }[cabin.source] || "ta_seats_note");
    // L'avion compte moins de passagers que GSX n'en a embarqué : il n'a pas
    // été chargé, et ses masses le diront aussi.
    const mismatch = aircraftSeats !== null && gsxBoarded && Math.abs(gsxBoarded - aircraftSeats) > 2
      && derived.deboarding !== "active";
    dom.payloadWarning.hidden = !mismatch;
    if (mismatch) dom.payloadWarning.textContent = fmt("ta_payload_mismatch", { gsx: gsxBoarded, aircraft: aircraftSeats });

    // Véhicules. GSX laisse parfois la passerelle ou les escaliers « en
    // service » après le départ : dès que le repoussage commence, ou que
    // l'avion a quitté son poste, le matériel d'escale n'est plus là. Seul le
    // tracteur reste, le temps du repoussage. À l'arrivée, rien n'approche
    // avant que l'avion soit arrêté au poste.
    const pushing = pushbackActive(aircraft);
    const moving = (finite(aircraft?.ground_speed_kt) || 0) >= 1;
    const departed = !context.arrival && (pushing || pushbackDone || awayFromStand(aircraft));
    const services = Boolean(aircraft?.on_ground) && !departed && !(context.arrival && (moving || awayFromStand(aircraft)));
    const boardingRunning = services && running(derived.boarding);
    const deboardingRunning = services && running(derived.deboarding);
    const stairsOn = services && (gsx.stairs === "active" || gsx.stairs === "requested");
    const jetwayOn = services && (gsx.jetway === "active" || gsx.jetway === "requested");
    setVehicle("jetway", jetwayOn);
    setVehicle("stairs-front", stairsOn && !jetwayOn);
    setVehicle("stairs-rear", stairsOn);
    setVehicle("catering-front", services && running(derived.catering));
    setVehicle("catering-rear", services && running(derived.catering) && layout.rows > 20);
    const cargoMoving = services && (derived.cargo === "active" || deboardingRunning);
    setVehicle("belt-front", cargoMoving);
    setVehicle("belt-rear", cargoMoving);
    setVehicle("carts-front", cargoMoving);
    setVehicle("carts-rear", cargoMoving);
    const refuelRunning = services && running(derived.refueling);
    setVehicle("fuel", refuelRunning);
    setVehicle("gpu", services && (gsx.gpu === "active" || aircraft?.ramp?.external_power_on === true));
    setVehicle("water", services && running(derived.water));
    setVehicle("lavatory", services && running(derived.lavatory));
    setVehicle("tug", pushing || (!departed && gsx.departure === "requested"));
    dom.hose.dataset.show = refuelRunning && gsx.fuel_hose_connected === true ? "1" : "0";
    for (const flow of dom.bagFlows) {
      flow.dataset.show = cargoMoving ? "1" : "0";
      flow.dataset.direction = deboardingRunning ? "out" : "in";
    }
    dom.paxFlows[0].dataset.show = (boardingRunning || deboardingRunning) && (stairsOn || !jetwayOn) ? "1" : "0";
    dom.paxFlows[1].dataset.show = (boardingRunning || deboardingRunning) && stairsOn ? "1" : "0";
    for (const flow of dom.paxFlows) flow.dataset.direction = deboardingRunning ? "out" : "in";

    // Chiffres.
    dom.paxValue.textContent = planned ? `${onboard}/${planned} pax` : "—";
    dom.paxValueBar.style.width = `${planned ? Math.round((onboard / planned) * 100) : 0}%`;
    let holds = holdSource(context);
    // Même règle pour le fret : soutes vides dans l'avion alors que GSX a
    // chargé, on montre le chargement GSX.
    if (holds && holds.forward.kg + holds.aft.kg < 1 && (finite(gsx.cargo_boarded_pct) || 0) > 0) holds = null;
    if (holds) {
      // Masse réelle par soute : celle de l'avion, ou des zones MSFS.
      dom.holdFwdValue.textContent = kg(holds.forward.kg);
      dom.holdFwdValueBar.style.width = `${Math.round(clamp01(holds.forward.fill) * 100)}%`;
      dom.holdAftValue.textContent = kg(holds.aft.kg);
      dom.holdAftValueBar.style.width = `${Math.round(clamp01(holds.aft.fill) * 100)}%`;
      dom.cargoNote.hidden = true;
    } else {
      const cargo = derived.deboarding === "active"
        ? 100 - (finite(gsx.cargo_deboarded_pct) || 0)
        : finite(gsx.cargo_boarded_pct);
      // GSX ne publie qu'un pourcentage global : la soute avant d'abord, comme
      // on charge un appareil pour garder le centrage. Signalé comme estimé.
      const fwd = cargo === null ? null : Math.min(100, cargo * 2);
      const aft = cargo === null ? null : Math.max(0, cargo * 2 - 100);
      dom.holdFwdValue.textContent = fwd === null ? "—" : `${Math.round(fwd)} %*`;
      dom.holdFwdValueBar.style.width = `${fwd || 0}%`;
      dom.holdAftValue.textContent = aft === null ? "—" : `${Math.round(aft)} %*`;
      dom.holdAftValueBar.style.width = `${aft || 0}%`;
      dom.cargoNote.hidden = cargo === null;
    }

    const fuel = finite(aircraft?.configuration?.fuel_total_kg);
    const target = finite(ofp?.blockFuelKg);
    const ratio = fuel !== null && target ? clamp01(fuel / target) : fuel !== null ? 0.5 : 0;
    dom.fuelValue.textContent = fuel === null
      ? "—"
      : target ? `${kg(fuel)} / ${kg(target)}` : kg(fuel);
    dom.fuelValueBar.style.width = `${Math.round(ratio * 100)}%`;
    // Les réservoirs se remplissent de l'emplanture vers les saillants.
    if (dom.fuelTanks) {
      const reach = Math.max(0, dom.tankSpan * ratio);
      dom.fuelTanks[0].setAttribute("width", String(reach));
      dom.fuelTanks[1].setAttribute("x", String(dom.tankLeft - reach));
      dom.fuelTanks[1].setAttribute("width", String(reach));
    }
  }

  function renderTimeline(context) {
    const data = timeline(context);
    dom.tobtValue.textContent = data.tobt === null ? "—" : zulu(data.tobt);
    dom.stdValue.textContent = data.scheduled === null ? "—" : zulu(data.scheduled);
    dom.delayValue.textContent = "";
    dom.delayValue.dataset.state = "";
    if (data.delayMin !== null) {
      if (Math.abs(data.delayMin) <= 2) {
        dom.delayValue.textContent = tr("ta_on_time");
        dom.delayValue.dataset.state = "good";
      } else if (data.delayMin > 0) {
        dom.delayValue.textContent = fmt("ta_delay", { minutes: data.delayMin });
        dom.delayValue.dataset.state = data.delayMin > 10 ? "danger" : "warning";
      } else {
        dom.delayValue.textContent = fmt("ta_early", { minutes: Math.abs(data.delayMin) });
        dom.delayValue.dataset.state = "good";
      }
    } else if (data.scheduled !== null && data.tobt !== null) {
      dom.delayValue.textContent = tr("ta_schedule_unrelated");
    }
    dom.critical.textContent = data.ready
      ? tr("ta_ready")
      : data.critical ? fmt("ta_critical", { service: serviceLabel(data.critical.key) }) : "";
    dom.critical.dataset.state = data.ready ? "ready" : "";

    dom.gantt.innerHTML = "";
    if (!data.rows.length) {
      dom.gantt.append(html("p", "ta-note", tr("ta_timeline_empty")));
      return;
    }
    // Une barre de progression par service : pleine et verte une fois
    // terminé. L'avancement est celui mesuré (passagers, fret, carburant) ;
    // à défaut, le temps écoulé sur la durée prévue, sans jamais atteindre la
    // fin tant que GSX n'a pas déclaré le service fini.
    const now = Date.now();
    for (const row of data.rows) {
      const complete = row.end !== null;
      let progress = complete ? 1 : row.progress;
      if (!complete && progress === null && row.eta !== null && row.eta > row.start) {
        progress = Math.min(0.95, (now - row.start) / (row.eta - row.start));
      }
      progress = clamp01(progress ?? 0);
      const line = html("div", "ta-gantt-row");
      line.dataset.state = complete ? "done" : "running";
      if (data.critical?.key === row.key) line.dataset.critical = "1";
      line.append(html("span", "ta-gantt-label", serviceLabel(row.key)));
      const track = html("div", "ta-gantt-track");
      track.setAttribute("role", "progressbar");
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "100");
      track.setAttribute("aria-valuenow", String(Math.round(progress * 100)));
      const fill = html("span", "ta-gantt-done");
      fill.style.width = `${Math.round(progress * 100)}%`;
      track.append(fill);
      line.append(track);
      const marker = row.estimate === "standard" ? "*" : row.estimate === "learned" ? "~" : "";
      const label = complete
        ? `✓ ${zulu(row.end)}`
        : `${Math.round(progress * 100)} % · ${row.eta !== null ? `${zulu(row.eta)}${marker}` : "…"}`;
      line.append(html("span", "ta-gantt-eta", label));
      dom.gantt.append(line);
    }
  }

  function serviceLabel(key) {
    return tr({
      boarding: "gsx_boarding",
      deboarding: "gsx_deboarding",
      catering: "gsx_catering",
      refueling: "gsx_refueling",
      departure: "gsx_departure",
      water: "gsx_water",
      lavatory: "gsx_lavatory",
      cargo: "ta_service_cargo",
    }[key] || key);
  }

  function renderLoadsheet(context) {
    if (!loadsheet) {
      dom.loadsheet.textContent = tr("ta_loadsheet_pending");
      dom.loadsheet.dataset.state = "pending";
      dom.lmc.textContent = "";
      dom.loadsheetNote.textContent = "";
      return;
    }
    const { ofp } = context;
    const pad = (label, value, extra = "") => `${label.padEnd(7)}${String(value).padStart(11)}  ${extra}`.trimEnd();
    const delta = (value, planned) => (value === null || planned === null ? "" : `OFP ${kg(planned)} ${signedKg(value - planned)}`);
    const lines = [
      // Émis seulement embarquement, fret et avitaillement terminés : c'est
      // le devis final. Il se fige au début du repoussage.
      `LOADSHEET FINAL   ${zulu(loadsheet.editionAt)}`,
      `${ofp?.callsign || "----"}  ${ofp?.departure || "----"}-${ofp?.arrival || "----"}  ${ofp?.type || ""}  ${ofp?.registration || ""}`.trimEnd(),
      "─".repeat(38),
      pad("PAX", loadsheet.pax ?? "—", finite(ofp?.pax) === null ? "" : `OFP ${ofp.pax}`),
      pad("CARGO", loadsheet.cargoPct === null ? "—" : `${Math.round(loadsheet.cargoPct)} %`),
      pad("ZFW", kg(loadsheet.zfw), delta(loadsheet.zfw, finite(ofp?.zfwKg))),
      pad("FOB", kg(loadsheet.fuel), finite(ofp?.blockFuelKg) === null ? "" : `BLOCK ${kg(finite(ofp.blockFuelKg))}`),
      pad("TOW", kg(loadsheet.tow), delta(loadsheet.tow, finite(ofp?.towKg))),
      pad("CG", loadsheet.cg === null ? "—" : `${loadsheet.cg.toFixed(1)} %MAC`),
    ];
    if (loadsheet.macZfw !== null) {
      const planned = finite(ofp?.zfwcg);
      lines.push(pad("MACZFW", `${loadsheet.macZfw.toFixed(1)} %`, planned === null ? "" : `OFP ${planned.toFixed(1)} %`));
    }
    if (loadsheet.macTow !== null) lines.push(pad("MACTOW", `${loadsheet.macTow.toFixed(1)} %`));
    dom.loadsheet.textContent = lines.join("\n");
    dom.loadsheet.dataset.state = loadsheet.lmc.length ? "lmc" : "ok";
    dom.lmc.textContent = loadsheet.lmc.length
      ? fmt("ta_lmc", { detail: loadsheet.lmc.join(" · ") })
      : tr("ta_lmc_none");
    dom.lmc.dataset.state = loadsheet.lmc.length ? "warning" : "good";
    dom.loadsheetNote.textContent = `${tr(loadsheet.source === "fms" ? "ta_source_fms" : "ta_source_msfs")} · ${tr("ta_cg_note")}`;
  }

  function awayFromStand(aircraft) {
    if (typeof GROUND === "undefined" || !GROUND.nearestParking) return false;
    const nearest = GROUND.nearestParking(aircraft);
    return Boolean(nearest && nearest.distance_m > 60);
  }

  function renderNext(context, derived) {
    const { aircraft } = context;
    const gsx = aircraft?.ground_services;
    dom.nextActions.innerHTML = "";
    const action = (label, tab) => {
      const button = html("button", "icon-btn", label);
      button.type = "button";
      button.addEventListener("click", () => context.openTab?.(tab));
      dom.nextActions.append(button);
    };
    let text;
    if (!gsx) text = tr("ta_waiting");
    else if (running(derived.deboarding)) text = `${tr("gsx_deboarding")} · ${tr("gsx_state_active")}`;
    else if (derived.deboarding === "completed") text = tr("ta_next_arrival_done");
    // À l'arrivée, GSX garde les compteurs de l'embarquement du départ : ils ne
    // disent plus rien de l'étape suivante, qui est le débarquement.
    else if (context.arrival) text = tr("ta_next_request_deboarding");
    else if (pushbackActive(aircraft)) text = tr("ta_pushback_active");
    // Après un rechargement, le repoussage n'est plus en mémoire : un avion
    // éloigné de tout poste a de toute façon quitté le sien.
    else if (pushbackDone || awayFromStand(aircraft)) {
      text = tr("ta_next_taxi");
      action(tr("tab_ground"), "ground");
    } else if (derived.boarding === "completed" && !running(derived.refueling) && !running(derived.catering)) {
      text = tr("ta_next_before_start");
      action(tr("tab_procedures"), "procedures");
    } else if (running(derived.boarding)) text = `${tr("gsx_boarding")} · ${tr("gsx_state_active")}`;
    else if (running(derived.refueling)) text = `${tr("gsx_refueling")} · ${tr("gsx_state_active")}`;
    else text = tr("ta_next_request_boarding");
    dom.nextText.textContent = text;

    dom.status.textContent = !gsx
      ? tr("ta_gsx_off")
      : pushbackActive(aircraft) ? tr("ta_pushback_active") : "GSX Pro";
    dom.status.dataset.state = gsx ? "on" : "off";
  }

  /* ------------------------------------------------------- public */

  return {
    /** Appelé à chaque relevé, même module masqué : le suivi ne s'arrête pas. */
    update(context) {
      latest = context;
      ingest(context);
      const panel = document.getElementById("panel-turnaround");
      if (!panel) return;
      const gsx = context.aircraft?.ground_services || null;
      const layout = layoutFor(context.ofp?.type, context.aircraft?.title, gsx?.passengers_planned || context.ofp?.pax, context.payload?.seats?.length || 0);
      const key = `${window.I18N.getLanguage()}|${layout.label}|${layout.rows}|${layout.abreast}`;
      if (!dom.panel || builtKey !== key || dom.panel !== panel) build(panel, context);
      dom.waiting.hidden = Boolean(gsx);
      dom.grid.dataset.gsx = gsx ? "on" : "off";
      const derived = derive(gsx);
      renderRamp(context, derived);
      renderTimeline(context);
      renderLoadsheet(context);
      renderNext(context, derived);
      const guidance = vdgs(context);
      lastGuidance = guidance;
      renderVdgs(dom.vdgs, guidance, dom.rampLayout?.label);
      if (context.groundVdgs) renderGroundVdgs(context.groundVdgs, guidance, dom.rampLayout?.label);
      if (typeof GROUND !== "undefined") {
        GROUND.setRampOverlay(pushbackActive(context.aircraft) ? { pushback: true, label: "PUSH" } : null);
      }
    },
    /** Reconstruit le module, après un changement de langue par exemple. */
    rebuild() {
      builtKey = "";
      if (latest) this.update(latest);
    },
    pushbackActive,
    /** Arrêté sur le point d'arrêt du poste, d'après le VDGS. */
    docked() {
      return Boolean(lastGuidance && lastGuidance.along <= 0.5 && lastGuidance.along >= -1.5);
    },
    /** L'escale est-elle le sujet du moment ? Sert à recommander le module. */
    relevant(aircraft) {
      return Boolean(
        aircraft?.on_ground && aircraft.ground_services
        && (finite(aircraft.ground_speed_kt) || 0) < 1 && !pushbackDone
      );
    },
    /** Temps d'escale du vol, pour le carnet. */
    report() {
      return Object.keys(report).length ? { ...report } : null;
    },
    onEvent(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    // Exposés pour les tests.
    _layoutFor: layoutFor,
    _seatOrder: seatOrder,
    _occupiedSubset: occupiedSubset,
  };

  function renderGroundVdgs(container, guidance, label) {
    if (!container.vdgs) {
      container.innerHTML = "";
      container.vdgs = buildVdgs();
      container.append(container.vdgs.root);
    }
    container.hidden = !guidance;
    renderVdgs(container.vdgs, guidance, label);
  }
})();
