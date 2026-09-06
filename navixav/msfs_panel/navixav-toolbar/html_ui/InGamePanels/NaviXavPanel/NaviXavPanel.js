/**
 * Panneau NaviXav de la barre d'outils MSFS.
 *
 * Il ne calcule rien : il interroge le service local de NaviXav et rend ce
 * qu'il reçoit. Tout ce qu'il commande existe déjà dans l'application, et
 * l'application reste seule maîtresse de l'injection.
 *
 * Le nom d'élément est propre à NaviXav : deux paquets qui appelleraient
 * `customElements.define` avec le même nom s'excluraient dans la barre.
 */

// NaviXav prend 8765 et glisse jusqu'à 8775 si le port est occupé — la plage
// de `desktop.py`. Le panneau essaie la même suite, dans le même ordre, et
// retient le premier qui répond. `127.0.0.1` plutôt que `localhost` : le
// service n'écoute jamais en IPv6, et `localhost` peut se résoudre en `::1`.
const NAVIXAV_FIRST_PORT = 8765;
const NAVIXAV_LAST_PORT = 8775;
const NAVIXAV_PORTS = [];
for (let port = NAVIXAV_FIRST_PORT; port <= NAVIXAV_LAST_PORT; port += 1) {
  NAVIXAV_PORTS.push(port);
}
const NAVIXAV_REFRESH_MS = 3000;
const NAVIXAV_CONNECTION_NOTICES = {
  "fr": "Connexion à NaviXav indisponible. Nouvelle tentative automatique…",
  "en": "NaviXav connection unavailable. Retrying automatically…",
  "de": "Verbindung zu NaviXav nicht verfügbar. Automatischer Wiederholungsversuch…",
  "es": "Conexión con NaviXav no disponible. Reintentando automáticamente…",
  "it": "Connessione a NaviXav non disponibile. Nuovo tentativo automatico…",
  "pt": "Ligação ao NaviXav indisponível. Nova tentativa automática…",
  "nl": "Verbinding met NaviXav niet beschikbaar. Automatisch opnieuw proberen…",
  "pl": "Połączenie z NaviXav niedostępne. Ponawianie automatyczne…"
};

function navixavRequest(url) {
  return new Promise((resolve, reject) => {
    // Coherent panels support XHR; abort the actual request on timeout.
    const request = new XMLHttpRequest();
    request.open("GET", url, true);
    request.timeout = 3000;
    request.onload = () => {
      if (request.status < 200 || request.status >= 300) {
        reject(new Error("HTTP " + request.status));
        return;
      }
      try { resolve(JSON.parse(request.responseText)); }
      catch (error) { reject(error); }
    };
    request.onerror = () => reject(new Error("NaviXav connection unavailable"));
    request.ontimeout = () => reject(new Error("NaviXav timeout"));
    request.send();
  });
}

// Les quatre sources, dans l'ordre des boutons. Le nom lisible est celui que
// l'application emploie ; « static » n'est pas un réseau et le dit.
const NAVIXAV_SOURCES = [
  { id: "vatsim", button: "sourceVatsim", label: "VATSIM" },
  { id: "ivao", button: "sourceIvao", label: "IVAO" },
  { id: "opensky", button: "sourceOpensky", label: "OpenSky · real traffic" },
  { id: "static", button: "sourceStatic", label: "Static · MSFS stands" },
];

class IngamePanelNaviXav extends UIElement {
  constructor() {
    super(...arguments);
    this.base = "";
    this.timer = null;
    this.state = null;
    this.refreshPending = false;
    this.generation = 0;
    this.closed = false;
    this.searchPending = false;
    this.listenersBound = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this.closed = false;
    this.generation += 1;
    this.refreshPending = false;
    this.searchPending = false;
    if (!this.listenersBound) {
      this.listenersBound = true;
      document.getElementById("trafficToggle").addEventListener("click", () => {
        const next = this.state && this.state.traffic_enabled ? "off" : "on";
        this.command("/api/panel/traffic/" + next);
      });
      NAVIXAV_SOURCES.forEach((source) => {
        const button = document.getElementById(source.button);
        if (!button) return;
        button.addEventListener("click", () => {
          this.command("/api/panel/source/" + source.id);
        });
      });
      document.getElementById("openWindow").addEventListener("click", () => {
        this.command("/api/panel/show");
      });
    }

    this.showOffline();
    this.findService(0);
    this.startPolling();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.closed = true;
    this.generation += 1;
    this.stopPolling();
  }

  /** Cherche le port de NaviXav, un essai à la fois, sans en manquer aucun. */
  findService(index, generation) {
    if (this.closed) return;
    if (index === 0) {
      if (this.searchPending) return;
      this.searchPending = true;
      generation = this.generation;
    }
    if (generation !== this.generation) return;
    if (index >= NAVIXAV_PORTS.length) {
      this.searchPending = false;
      this.showOffline();
      return;
    }
    const base = "http://127.0.0.1:" + NAVIXAV_PORTS[index];
    navixavRequest(base + "/api/panel/state")
      .then((state) => {
        if (this.closed || generation !== this.generation) return;
        if (!state || state.running !== true) throw new Error("Not a NaviXav service");
        this.searchPending = false;
        this.base = base;
        this.renderState(state);
      })
      .catch(() => this.findService(index + 1, generation));
  }

  command(path) {
    if (!this.base) {
      this.findService(0);
      return;
    }
    const generation = ++this.generation;
    this.refreshPending = false;
    navixavRequest(this.base + path)
      .then((payload) => {
        if (this.closed || generation !== this.generation) return;
        // `/api/panel/show` ne rend pas d'état : on garde le dernier connu.
        if (payload && payload.running) this.renderState(payload);
      })
      .catch((error) => {
        if (this.closed || generation !== this.generation) return;
        console.log("NaviXav: " + error.message);
        this.showOffline();
      });
  }

  refresh() {
    if (this.closed) return;
    if (!this.base) { this.findService(0); return; }
    if (this.refreshPending) return;
    this.refreshPending = true;
    const generation = this.generation;
    navixavRequest(this.base + "/api/panel/state")
      .then((state) => {
        if (!state || state.running !== true) throw new Error("Not a NaviXav service");
        if (!this.closed && generation === this.generation) this.renderState(state);
      })
      .catch(() => {
        if (!this.closed && generation === this.generation) this.showOffline();
      })
      .then(() => { if (generation === this.generation) this.refreshPending = false; });
  }

  startPolling() {
    this.stopPolling();
    this.timer = setInterval(() => this.refresh(), NAVIXAV_REFRESH_MS);
  }

  stopPolling() {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  showOffline() {
    const notice = document.getElementById("navixavConnectionNotice");
    const language = typeof navigator !== "undefined" ? String(navigator.language || "fr").slice(0, 2).toLowerCase() : "fr";
    if (notice) notice.textContent = NAVIXAV_CONNECTION_NOTICES[language] || NAVIXAV_CONNECTION_NOTICES.en;
    this.base = "";
    this.state = null;
    navixavControls.setAttribute("class", "panelHidden");
    navixavOffline.setAttribute("class", "");
  }

  renderState(state) {
    // An interface error is not a connection failure; keep polling the service.
    try { this.showControls(state); }
    catch (error) { console.log("NaviXav panel display: " + error.message); }
  }

  showControls(state) {
    if (this.closed) return;
    this.state = state;
    navixavOffline.setAttribute("class", "panelHidden");
    navixavControls.setAttribute("class", "");

    const source = String(state.traffic_source || "").toLowerCase();
    const known = NAVIXAV_SOURCES.find((entry) => entry.id === source);

    navixavVersion.textContent = "NaviXav " + (state.version || "");
    navixavModels.textContent = state.models_detected
      ? state.models_version + " · " + state.models_count + " configurations"
      : "No model set";
    navixavTraffic.textContent = state.traffic_enabled ? "On" : "Off";
    navixavSource.textContent = known ? known.label : source.toUpperCase();

    // Le bouton allumé est celui qui commande, les autres restent lisibles
    // sans prétendre l'être : un seul jeu de modèles, une seule source.
    NAVIXAV_SOURCES.forEach((entry) => {
      const button = document.getElementById(entry.button);
      if (!button) return;
      button.setAttribute(
        "class",
        entry.id === source
          ? "triggerButton sourceButton sourceActive"
          : "triggerButton sourceButton"
      );
    });

    this.showInjection(state);
    this.showFlight(state);
    this.showHint(state, source);
  }

  /**
   * L'état d'injection est ce que le panneau apporte de plus utile en vol :
   * le calque peut être allumé sans qu'un seul appareil entre dans MSFS.
   */
  showInjection(state) {
    const injection = state.injection || {};
    const labels = (state.flight && state.flight.labels) || {};
    const confirmed = Math.max(0, Number(injection.confirmed) || 0);
    let text = "Off";
    let dot = "navixavDot";
    if (state.conflict && state.conflict.length) {
      text = state.conflict.join(", ") + " is injecting — NaviXav stays out";
      dot = "navixavDot navixavDotWarn";
    } else if (!state.traffic_enabled) {
      text = "Traffic off";
    } else if (["loading", "active", "empty", "error", "stale"].includes(injection.state)) {
      const fallback = { loading: "Chargement du trafic", active: "Trafic actif",
        empty: "Aucun avion injectable", error: "Erreur de trafic", stale: "État du trafic ancien" };
      text = injection.state === "error" && injection.error_code === "opensky_daily_quota"
        ? String(labels.traffic_state_opensky_quota || "Quota quotidien OpenSky épuisé")
        : String(labels["traffic_state_" + injection.state] || fallback[injection.state])
          .replace("{count}", String(confirmed));
      dot = injection.state === "active" && confirmed > 0
        ? "navixavDot navixavDotLive" : "navixavDot navixavDotWarn";
    } else if (!state.models_detected) {
      text = "Map only — no models available";
      dot = "navixavDot navixavDotWarn";
    } else {
      text = "Map only — injection did not start";
      dot = "navixavDot navixavDotWarn";
    }
    navixavInjection.textContent = text;
    navixavDot.setAttribute("class", dot);
    const detail = document.getElementById("navixavInjectionDetail");
    const template = labels.traffic_state_detail || "{count} confirmés · {selected} sélectionnés · {skipped} écartés";
    const quota = injection.state === "error" && injection.error_code === "opensky_daily_quota";
    detail.textContent = quota
      ? String(labels.traffic_state_opensky_quota_detail || "NaviXav attend automatiquement la reprise indiquée par OpenSky.")
      : (state.traffic_enabled ? template
        .replace("{count}", String(confirmed))
        .replace("{selected}", String(injection.selected || 0))
        .replace("{skipped}", String(injection.skipped || 0)) : "");
    detail.title = labels.panel_confirmed || "Objets confirmés par MSFS ; la visibilité à l’écran n’est pas garantie.";
  }

  showFlight(state) {
    const flight = state.flight || {};
    const labels = flight.labels || {};
    document.getElementById("navixavFlightTitle").textContent = labels.panel_my_flight || "Mon vol";
    document.getElementById("navixavFlightRoute").textContent = flight.route || "—";
    document.getElementById("navixavFlightNotice").textContent = flight.fresh && flight.connected
      ? "" : (labels.panel_flight_unavailable || "Données de vol indisponibles ou anciennes.");
    const container = document.getElementById("navixavFlightValues");
    container.textContent = "";
    const values = flight.fresh && flight.connected ? (flight.values || {}) : {};
    const rows = [
      [labels.flight_next_fix || "Prochain point", "flight-next-fix", "flight-next-distance"],
      [labels.panel_remaining || "Temps restant", "flight-progress-remaining"],
      [labels.flight_next_constraint || "Prochaine contrainte", "flight-next-constraint", "flight-constraint-distance"],
      ["TOD", "flight-tod"],
    ];
    rows.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "navixavRow";
      const label = document.createElement("span");
      label.textContent = entry[0];
      const value = document.createElement("span");
      value.className = "navixavValue";
      value.textContent = entry.slice(1).map((key) => values[key] || "—").join(" · ");
      row.appendChild(label); row.appendChild(value); container.appendChild(row);
    });
  }

  /**
   * Une seule ligne d'explication, et seulement quand elle apprend quelque
   * chose : un panneau qui commente en permanence ne se lit plus.
   */
  showHint(state, source) {
    let text = "";
    if (!state.models_detected) {
      text = "Install FSLTL or AIG, then choose it in NaviXav settings.";
    } else if (source === "static") {
      text = "Parked aircraft on the simulator's own stands. No network, and nobody taxis.";
    }
    navixavHint.textContent = text;
    navixavHint.setAttribute("class", text ? "navixavHint" : "navixavHint panelHidden");
  }

  initialize() {}

  updateImage() {}
}

window.customElements.define("ingamepanel-navixav", IngamePanelNaviXav);
checkAutoload();
