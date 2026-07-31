"use strict";

/**
 * Plan de terrain et route sur canvas.
 *
 * Le repère monde est celui des tuiles : Web Mercator, en mètres (EPSG:3857),
 * x vers l'est et y vers le nord. Le rendu n'applique donc qu'une échelle et un
 * centrage, avec l'axe y inversé à l'écran pour garder le nord en haut.
 *
 * Le plan de terrain, lui, arrive projeté en mètres locaux tangents à
 * l'aérodrome : il est reconverti une fois à la réception. Sans cela, l'échelle
 * de Mercator variant en 1/cos(latitude), le fond de carte et la route
 * dériveraient l'un par rapport à l'autre dès qu'on s'éloigne du terrain — près
 * de 14 NM au bout d'une route de 385 NM.
 */

const MAP = (() => {
  const canvas = document.getElementById("chart-canvas");
  const context = canvas.getContext("2d");

  const view = { scale: 0.2, centerX: 0, centerY: 0, follow: true };
  let chart = null;
  let aircraft = null;
  let trail = [];
  let route = [];
  let routeSegments = [];
  let dragging = null;
  let taxiPlan = null;
  let selectedParking = null;
  let parkingListener = null;
  let basemapVisible = true;
  let basemapKey = "osm";
  let trailColor = "#22d3ee";
  const tileCache = new Map();
  // Le fond est assemblé opaque à part, puis déposé en une seule fois. Appliquer
  // sa transparence tuile par tuile ferait ressortir chaque raccord.
  const basemapLayer = document.createElement("canvas");
  const basemapContext = basemapLayer.getContext("2d");
  const TILE_SIZE = 256;
  // Rayon des tuiles Web Mercator, identique à celui de la projection locale
  // du serveur : les deux repères se recouvrent donc exactement.
  const EARTH_RADIUS_M = 6378137;
  const MERCATOR_WORLD_M = 2 * Math.PI * EARTH_RADIUS_M;
  const MERCATOR_LIMIT_DEG = 85.051129;
  const MAX_TILE_CACHE = 320;
  const MAX_TILE_RADIUS = 8;
  let fitPending = false;
  // Les tuiles CARTO sont réparties sur quatre sous-domaines pour paralléliser
  // les téléchargements, comme le recommande leur documentation.
  const cartoSubdomain = (x, y) => "abcd"[(Math.abs(x) + Math.abs(y)) % 4];
  const BASEMAPS = {
    osm: {
      url: (zoom, x, y) => `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`,
      maxZoom: 19,
      alpha: 0.78,
      attribution: "© OpenStreetMap contributors",
      attributionUrl: "https://www.openstreetmap.org/copyright",
    },
    opentopo: {
      url: (zoom, x, y) => `https://a.tile.opentopomap.org/${zoom}/${x}/${y}.png`,
      maxZoom: 17,
      alpha: 0.78,
      attribution: "© OpenStreetMap contributors · SRTM · OpenTopoMap",
      attributionUrl: "https://opentopomap.org/about",
    },
    carto_light: {
      url: (zoom, x, y) =>
        `https://${cartoSubdomain(x, y)}.basemaps.cartocdn.com/light_all/${zoom}/${x}/${y}.png`,
      maxZoom: 19,
      // Fond très clair et peu contrasté : il supporte une opacité plus forte
      // sans masquer les pistes ni la route.
      alpha: 0.9,
      attribution: "© OpenStreetMap contributors © CARTO",
      attributionUrl: "https://carto.com/attributions",
    },
    carto_dark: {
      url: (zoom, x, y) =>
        `https://${cartoSubdomain(x, y)}.basemaps.cartocdn.com/dark_all/${zoom}/${x}/${y}.png`,
      maxZoom: 19,
      alpha: 0.92,
      attribution: "© OpenStreetMap contributors © CARTO",
      attributionUrl: "https://carto.com/attributions",
    },
  };

  /* ------------------------------------------------------------ géométrie */

  function css(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  /** Latitude/longitude vers le repère monde, en mètres Web Mercator. */
  function project(latitude, longitude) {
    const clamped = Math.max(
      -MERCATOR_LIMIT_DEG,
      Math.min(MERCATOR_LIMIT_DEG, Number(latitude))
    );
    const phi = (clamped * Math.PI) / 180;
    return {
      x: (EARTH_RADIUS_M * Number(longitude) * Math.PI) / 180,
      y: EARTH_RADIUS_M * Math.log(Math.tan(Math.PI / 4 + phi / 2)),
    };
  }

  /**
   * Mètres au sol représentés par un mètre Mercator à cette ordonnée, soit
   * cos(latitude). L'identité cos φ = sech(y / R) évite la trigonométrie
   * inverse.
   */
  function groundRatio(worldY) {
    return 1 / Math.cosh(worldY / EARTH_RADIUS_M);
  }

  /** Pixels écran par mètre au sol, au centre de la vue. */
  function pixelsPerGroundMetre() {
    return view.scale / groundRatio(view.centerY);
  }

  /** Inverse de la projection locale du plan de terrain. */
  function localToLatLon(origin, point) {
    return [
      origin.lat + ((point.y / EARTH_RADIUS_M) * 180) / Math.PI,
      origin.lon
        + ((point.x / (EARTH_RADIUS_M * Math.cos((origin.lat * Math.PI) / 180))) * 180)
          / Math.PI,
    ];
  }

  /**
   * Repasse le plan de terrain dans le repère monde. Seules les géométries
   * réellement dessinées et l'emprise sont converties ; le reste du plan est
   * transmis tel quel.
   */
  function prepareChart(data) {
    if (!data?.origin) return data;
    const toWorld = (point) => {
      const [latitude, longitude] = localToLatLon(data.origin, point);
      return { ...point, ...project(latitude, longitude) };
    };
    const runways = (data.runways || []).map((runway) => ({
      ...runway,
      start: toWorld(runway.start),
      end: toWorld(runway.end),
      ends: (runway.ends || []).map((end) => ({
        ...end,
        threshold: toWorld(end.threshold),
      })),
    }));
    const taxiways = (data.taxiways || []).map((taxiway) => ({
      ...taxiway,
      start: toWorld(taxiway.start),
      end: toWorld(taxiway.end),
    }));
    const parkings = (data.parkings || []).map((parking) => ({
      ...parking,
      position: toWorld(parking.position),
    }));

    // L'emprise du serveur couvre aussi les taxiways et les postes : on
    // convertit ses quatre coins plutôt que de la recalculer sur les pistes.
    const source = data.bounds;
    const corners = source
      ? [
        { x: source.min_x, y: source.min_y },
        { x: source.max_x, y: source.min_y },
        { x: source.min_x, y: source.max_y },
        { x: source.max_x, y: source.max_y },
      ].map(toWorld)
      : runways.flatMap((runway) => [runway.start, runway.end]);
    if (!corners.length) return { ...data, runways, taxiways, parkings };
    const xs = corners.map((point) => point.x);
    const ys = corners.map((point) => point.y);
    return {
      ...data,
      runways,
      taxiways,
      parkings,
      bounds: {
        min_x: Math.min(...xs),
        max_x: Math.max(...xs),
        min_y: Math.min(...ys),
        max_y: Math.max(...ys),
      },
    };
  }

  function toScreen(x, y) {
    return [
      canvas.clientWidth / 2 + (x - view.centerX) * view.scale,
      canvas.clientHeight / 2 - (y - view.centerY) * view.scale,
    ];
  }

  function toWorld(px, py) {
    return [
      (px - canvas.clientWidth / 2) / view.scale + view.centerX,
      -(py - canvas.clientHeight / 2) / view.scale + view.centerY,
    ];
  }

  function fit() {
    if (!chart) return;
    if (canvas.clientWidth <= 0 || canvas.clientHeight <= 0) {
      fitPending = true;
      return;
    }
    const b = chart.bounds;
    const width = Math.max(1, b.max_x - b.min_x);
    const height = Math.max(1, b.max_y - b.min_y);
    view.centerX = (b.min_x + b.max_x) / 2;
    view.centerY = (b.min_y + b.max_y) / 2;
    view.scale = Math.min(
      canvas.clientWidth / width,
      canvas.clientHeight / height
    ) * 0.92;
    fitPending = false;
    view.follow = false;
    syncFollowButton();
    draw();
  }

  /* --------------------------------------------------------------- rendu */

  function resize() {
    if (canvas.clientWidth <= 0 || canvas.clientHeight <= 0) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (chart && (fitPending || !Number.isFinite(view.scale) || view.scale <= 0)) {
      fit();
      return;
    }
    draw();
  }

  function draw() {
    context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    if (!chart) return;

    if (basemapVisible) drawBasemap();
    // Les voies passent sous les pistes : à leur croisement, c'est la piste
    // qui est continue au sol.
    drawTaxiways();
    drawRunways();
    drawParkings();
    drawTaxiRoute();
    drawTaxiwayLabels();
    drawRoute();
    drawTrail();
    drawAircraft();
    drawScaleBar();
    drawNorth();
  }

  /** Niveau de tuiles dont un pixel vaut à peu près un pixel écran. */
  function basemapZoom() {
    return Math.max(3, Math.min(BASEMAPS[basemapKey].maxZoom,
      Math.round(Math.log2((MERCATOR_WORLD_M * view.scale) / TILE_SIZE))
    ));
  }

  function getTile(zoom, x, y) {
    const key = `${basemapKey}/${zoom}/${x}/${y}`;
    let tile = tileCache.get(key);
    if (tile) return tile;

    const image = new Image();
    image.crossOrigin = "anonymous";
    tile = { image, loaded: false, failed: false };
    tileCache.set(key, tile);
    image.onload = () => {
      tile.loaded = true;
      draw();
    };
    image.onerror = () => {
      tile.failed = true;
    };
    image.src = BASEMAPS[basemapKey].url(zoom, x, y);

    if (tileCache.size > MAX_TILE_CACHE) {
      const oldest = tileCache.keys().next().value;
      tileCache.delete(oldest);
    }
    return tile;
  }

  function drawBasemap() {
    if (!Number.isFinite(view.scale) || view.scale <= 0) return;
    // Onglet masqué : un calque de taille nulle ferait échouer la composition.
    if (canvas.clientWidth <= 0 || canvas.clientHeight <= 0) return;
    const zoom = basemapZoom();
    const tileCount = 2 ** zoom;
    // Le repère monde étant celui des tuiles, l'indice se lit directement.
    const tileWorldM = MERCATOR_WORLD_M / tileCount;
    const screenPixelsPerTile = tileWorldM * view.scale;
    if (!Number.isFinite(screenPixelsPerTile) || screenPixelsPerTile <= 0) return;
    const halfWorld = MERCATOR_WORLD_M / 2;
    const centreTileX = (view.centerX + halfWorld) / tileWorldM;
    const centreTileY = (halfWorld - view.centerY) / tileWorldM;
    const radiusX = Math.min(
      MAX_TILE_RADIUS,
      Math.ceil(canvas.clientWidth / screenPixelsPerTile / 2) + 1
    );
    const radiusY = Math.min(
      MAX_TILE_RADIUS,
      Math.ceil(canvas.clientHeight / screenPixelsPerTile / 2) + 1
    );
    const firstX = Math.floor(centreTileX) - radiusX;
    const lastX = Math.floor(centreTileX) + radiusX;
    const firstY = Math.max(0, Math.floor(centreTileY) - radiusY);
    const lastY = Math.min(tileCount - 1, Math.floor(centreTileY) + radiusY);

    const ratio = window.devicePixelRatio || 1;
    const layerWidth = Math.round(canvas.clientWidth * ratio);
    const layerHeight = Math.round(canvas.clientHeight * ratio);
    if (basemapLayer.width !== layerWidth || basemapLayer.height !== layerHeight) {
      basemapLayer.width = layerWidth;
      basemapLayer.height = layerHeight;
    }
    // Redimensionner un canvas réinitialise sa transformation : on la repose.
    basemapContext.setTransform(ratio, 0, 0, ratio, 0, 0);
    basemapContext.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);

    for (let tileY = firstY; tileY <= lastY; tileY += 1) {
      for (let tileX = firstX; tileX <= lastX; tileX += 1) {
        const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
        const tile = getTile(zoom, wrappedX, tileY);
        if (!tile.loaded || tile.failed) continue;
        const screenX =
          canvas.clientWidth / 2 + (tileX - centreTileX) * screenPixelsPerTile;
        const screenY =
          canvas.clientHeight / 2 + (tileY - centreTileY) * screenPixelsPerTile;
        // Chaque tuile s'arrête exactement là où commence la suivante : ni
        // chevauchement, ni couture due aux pixels fractionnaires.
        const left = Math.floor(screenX);
        const top = Math.floor(screenY);
        basemapContext.drawImage(
          tile.image,
          left,
          top,
          Math.max(1, Math.floor(screenX + screenPixelsPerTile) - left),
          Math.max(1, Math.floor(screenY + screenPixelsPerTile) - top)
        );
      }
    }

    context.save();
    context.globalAlpha = BASEMAPS[basemapKey].alpha ?? 0.78;
    context.drawImage(basemapLayer, 0, 0, canvas.clientWidth, canvas.clientHeight);
    context.restore();
  }

  /* ------------------------------------------------------------- le sol */

  /** Couleur d'un segment selon ce qu'il est, pas selon son apparence. */
  function taxiwayColour(kind) {
    if (kind === "vehicle") return css("--taxiway-service");
    if (kind === "closed") return css("--taxiway-closed");
    return css("--taxiway");
  }

  /** Le segment est-il au moins partiellement à l'écran ? */
  function onScreen(x1, y1, x2, y2, margin = 40) {
    return !(
      (x1 < -margin && x2 < -margin)
      || (y1 < -margin && y2 < -margin)
      || (x1 > canvas.clientWidth + margin && x2 > canvas.clientWidth + margin)
      || (y1 > canvas.clientHeight + margin && y2 > canvas.clientHeight + margin)
    );
  }

  function drawTaxiways() {
    const taxiways = chart.taxiways || [];
    if (!taxiways.length) return;
    const pixelsPerMetre = pixelsPerGroundMetre();

    context.save();
    context.lineCap = "round";
    for (const taxiway of taxiways) {
      // Une portion de piste est déjà dessinée par la piste elle-même : la
      // repasser en voie de circulation la ferait paraître plus étroite.
      if (taxiway.kind === "runway") continue;
      const [x1, y1] = toScreen(taxiway.start.x, taxiway.start.y);
      const [x2, y2] = toScreen(taxiway.end.x, taxiway.end.y);
      if (!onScreen(x1, y1, x2, y2)) continue;

      context.strokeStyle = taxiwayColour(taxiway.kind);
      context.lineWidth = Math.max(1, (taxiway.width_m || 15) * pixelsPerMetre);
      context.setLineDash(taxiway.kind === "closed" ? [6, 5] : []);
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();
    }
    context.setLineDash([]);
    context.restore();
  }

  /**
   * Nom des voies, une seule fois par case d'écran.
   *
   * Une étiquette par segment en produirait des milliers sur un grand terrain,
   * toutes superposées. Le regroupement par case garde le nom là où l'œil le
   * cherche — le long de la voie — sans le répéter.
   */
  function drawTaxiwayLabels() {
    const pixelsPerMetre = pixelsPerGroundMetre();
    if (pixelsPerMetre < 0.12) return;
    const taxiways = chart.taxiways || [];
    if (!taxiways.length) return;

    const CELL = 130;
    const placed = new Set();
    context.save();
    context.font = "700 11px 'Inter', system-ui, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";

    for (const taxiway of taxiways) {
      if (!taxiway.name || taxiway.kind === "runway") continue;
      const [x1, y1] = toScreen(taxiway.start.x, taxiway.start.y);
      const [x2, y2] = toScreen(taxiway.end.x, taxiway.end.y);
      if (!onScreen(x1, y1, x2, y2, 0)) continue;
      const x = (x1 + x2) / 2;
      const y = (y1 + y2) / 2;
      if (x < 0 || y < 0 || x > canvas.clientWidth || y > canvas.clientHeight) {
        continue;
      }
      const cell = `${taxiway.name}/${Math.round(x / CELL)}/${Math.round(y / CELL)}`;
      if (placed.has(cell)) continue;
      placed.add(cell);

      const width = context.measureText(taxiway.name).width + 8;
      context.fillStyle = css("--label-bg");
      context.globalAlpha = 0.85;
      roundRect(x - width / 2, y - 8, width, 16, 4);
      context.fill();
      context.globalAlpha = 1;
      context.fillStyle = css("--label-text");
      context.fillText(taxiway.name, x, y + 1);
    }
    context.restore();
  }

  function drawParkings() {
    const parkings = chart.parkings || [];
    if (!parkings.length) return;
    const pixelsPerMetre = pixelsPerGroundMetre();
    if (pixelsPerMetre < 0.05) return;
    const showLabels = pixelsPerMetre > 0.35;

    context.save();
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = "600 10px 'Inter', system-ui, sans-serif";

    for (const parking of parkings) {
      const [x, y] = toScreen(parking.position.x, parking.position.y);
      if (x < -30 || y < -30 || x > canvas.clientWidth + 30 || y > canvas.clientHeight + 30) {
        continue;
      }
      const active = parking.label === selectedParking;
      const radius = Math.max(3, (parking.radius_m || 15) * pixelsPerMetre);

      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.fillStyle = active ? css("--parking-active") : css("--parking");
      context.globalAlpha = active ? 0.55 : 0.32;
      context.fill();
      context.globalAlpha = 1;
      context.strokeStyle = active ? css("--parking-active") : css("--parking");
      context.lineWidth = active ? 2 : 1;
      context.stroke();

      if (showLabels || active) {
        context.fillStyle = css("--label-text");
        context.fillText(parking.label, x, y + radius + 8);
      }
    }
    context.restore();
  }

  /* --------------------------------------------------------- roulage */

  /** Tracé du roulage en une seule ligne, avec ses distances cumulées. */
  function taxiPolyline() {
    if (!taxiPlan?.legs?.length) return { points: [], total: 0 };
    const points = [];
    for (const leg of taxiPlan.legs) {
      for (const point of leg.points || []) {
        const last = points[points.length - 1];
        if (last && last.x === point.x && last.y === point.y) continue;
        points.push(point);
      }
    }
    let total = 0;
    for (let index = 1; index < points.length; index += 1) {
      total += Math.hypot(
        points[index].x - points[index - 1].x,
        points[index].y - points[index - 1].y
      );
    }
    return { points, total };
  }

  /**
   * Distance déjà parcourue, par projection de l'avion sur le tracé.
   *
   * La projection se fait sur le segment le plus proche et non sur le point le
   * plus proche : sur un aller-retour, deux portions du tracé se frôlent, et un
   * simple plus-proche-point ferait sauter la progression de l'une à l'autre.
   */
  function taxiProgress(points) {
    if (!aircraft || points.length < 2) return 0;
    let travelled = 0;
    let best = { distance: Infinity, along: 0 };
    for (let index = 1; index < points.length; index += 1) {
      const from = points[index - 1];
      const to = points[index];
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const length = Math.hypot(dx, dy);
      if (length > 0) {
        const ratio = Math.max(0, Math.min(1,
          ((aircraft.x - from.x) * dx + (aircraft.y - from.y) * dy) / (length * length)
        ));
        const closestX = from.x + dx * ratio;
        const closestY = from.y + dy * ratio;
        const distance = Math.hypot(aircraft.x - closestX, aircraft.y - closestY);
        if (distance < best.distance) {
          best = { distance, along: travelled + length * ratio };
        }
      }
      travelled += length;
    }
    return best.along;
  }

  /** Dessine le tracé, vert derrière l'avion et bleu devant. */
  function drawTaxiRoute() {
    const { points } = taxiPolyline();
    if (points.length < 2) return;
    const done = taxiProgress(points);

    context.save();
    context.lineWidth = 5;
    context.lineJoin = "round";
    context.lineCap = "round";

    let travelled = 0;
    for (let index = 1; index < points.length; index += 1) {
      const from = points[index - 1];
      const to = points[index];
      const length = Math.hypot(to.x - from.x, to.y - from.y);
      const segments = [];
      if (travelled + length <= done) {
        segments.push([from, to, true]);
      } else if (travelled >= done) {
        segments.push([from, to, false]);
      } else {
        // L'avion est au milieu de ce segment : on le coupe à sa hauteur pour
        // que la bascule de couleur suive l'appareil et non le nœud suivant.
        const ratio = (done - travelled) / length;
        const split = {
          x: from.x + (to.x - from.x) * ratio,
          y: from.y + (to.y - from.y) * ratio,
        };
        segments.push([from, split, true], [split, to, false]);
      }
      for (const [a, b, walked] of segments) {
        const [x1, y1] = toScreen(a.x, a.y);
        const [x2, y2] = toScreen(b.x, b.y);
        if (!onScreen(x1, y1, x2, y2)) continue;
        context.strokeStyle = css(walked ? "--taxi-done" : "--taxi-ahead");
        context.globalAlpha = walked ? 0.7 : 0.95;
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();
      }
      travelled += length;
    }
    context.restore();
    drawHoldShortMarks();
  }

  /** Barre d'arrêt en travers du tracé, là où il faut attendre. */
  function drawHoldShortMarks() {
    if (!taxiPlan?.legs?.length) return;
    context.save();
    context.strokeStyle = css("--hold-short");
    context.lineWidth = 3;
    context.lineCap = "butt";

    for (const leg of taxiPlan.legs) {
      if (!leg.hold_short) continue;
      const points = leg.points || [];
      if (points.length < 2) continue;
      const last = points[points.length - 1];
      const previous = points[points.length - 2];
      const [x, y] = toScreen(last.x, last.y);
      if (x < 0 || y < 0 || x > canvas.clientWidth || y > canvas.clientHeight) {
        continue;
      }
      const [px, py] = toScreen(previous.x, previous.y);
      const length = Math.hypot(x - px, y - py) || 1;
      // Perpendiculaire au tracé, longueur fixe pour rester lisible dézoomé.
      const nx = (-(y - py) / length) * 11;
      const ny = ((x - px) / length) * 11;
      context.beginPath();
      context.moveTo(x - nx, y - ny);
      context.lineTo(x + nx, y + ny);
      context.stroke();
    }
    context.restore();
  }

  function drawRunways() {
    const highlight = (chart.highlight_runway || "").toUpperCase();
    const pixelsPerMetre = pixelsPerGroundMetre();

    for (const runway of chart.runways) {
      const isHighlighted = runway.ends.some(
        (end) => end.name.toUpperCase() === highlight
      );
      const [x1, y1] = toScreen(runway.start.x, runway.start.y);
      const [x2, y2] = toScreen(runway.end.x, runway.end.y);
      const width = Math.max(2.5, runway.width_m * pixelsPerMetre);

      context.strokeStyle = isHighlighted ? css("--rwy-active") : css("--rwy");
      context.lineWidth = width;
      context.lineCap = "butt";
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();

      if (isHighlighted) {
        context.save();
        context.strokeStyle = css("--rwy-active");
        context.globalAlpha = 0.28;
        context.lineWidth = width + 14;
        context.stroke();
        context.restore();
      }

      // Axe de piste en tirets, seulement quand il reste lisible.
      if (width > 6) {
        context.save();
        context.strokeStyle = css("--rwy-centreline");
        context.lineWidth = Math.max(1, width * 0.06);
        context.setLineDash([width * 0.9, width * 0.9]);
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();
        context.restore();
      }

      for (const end of runway.ends) {
        drawRunwayLabel(end, isHighlighted && end.name.toUpperCase() === highlight);
      }
    }
  }

  function drawRunwayLabel(end, active) {
    const [x, y] = toScreen(end.threshold.x, end.threshold.y);
    if (x < -60 || y < -60 || x > canvas.clientWidth + 60 || y > canvas.clientHeight + 60) {
      return;
    }
    context.save();
    context.translate(x, y);
    context.font = "600 13px 'Inter', system-ui, sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";

    const text = end.name;
    const padding = 6;
    const width = context.measureText(text).width + padding * 2;
    context.fillStyle = active ? css("--rwy-active") : css("--label-bg");
    context.strokeStyle = css("--label-border");
    context.lineWidth = 1;
    roundRect(-width / 2, -11, width, 22, 5);
    context.fill();
    context.stroke();

    context.fillStyle = active ? css("--label-on-active") : css("--label-text");
    context.fillText(text, 0, 1);
    context.restore();
  }

  function drawTrail() {
    if (trail.filter(Boolean).length < 2) return;
    context.save();
    context.strokeStyle = trailColor;
    context.globalAlpha = 0.9;
    context.lineWidth = 3;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.beginPath();
    let drawing = false;
    trail.forEach((point) => {
      if (!point) {
        drawing = false;
        return;
      }
      const [wx, wy] = point;
      const [x, y] = toScreen(wx, wy);
      if (!drawing) context.moveTo(x, y);
      else context.lineTo(x, y);
      drawing = true;
    });
    context.stroke();
    context.restore();
  }

  function drawRoute() {
    if (!routeSegments.length && route.length < 2) return;
    context.save();
    const segments = routeSegments.length
      ? routeSegments
      : [{ stage: "enroute", points: route }];
    const colours = {
      sid: "--route-sid",
      enroute: "--route-enroute",
      star: "--route-star",
      approach: "--route-approach",
    };
    for (const segment of segments) {
      if (segment.points.length < 2) continue;
      context.strokeStyle = css(colours[segment.stage] || "--accent");
      context.lineWidth = segment.stage === "approach" ? 4 : 3;
      context.lineJoin = "round";
      context.setLineDash(segment.stage === "enroute" ? [10, 5] : []);
      context.beginPath();
      segment.points.forEach((point, index) => {
        const [x, y] = toScreen(point.x, point.y);
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();
      context.setLineDash([]);

      for (const point of segment.points) {
        const [x, y] = toScreen(point.x, point.y);
        if (x < -60 || y < -40 || x > canvas.clientWidth + 60 || y > canvas.clientHeight + 40) {
          continue;
        }
        context.fillStyle = css(colours[segment.stage] || "--accent");
        context.beginPath();
        context.arc(x, y, segment.stage === "approach" ? 5 : 4, 0, Math.PI * 2);
        context.fill();
        context.font = "650 11px 'Inter', system-ui, sans-serif";
        context.textAlign = "center";
        context.fillStyle = css("--label-text");
        context.fillText(point.ident, x, y - 10);
      }
    }
    context.restore();
  }

  function drawAircraft() {
    if (!aircraft) return;
    const [x, y] = toScreen(aircraft.x, aircraft.y);
    const heading = ((aircraft.heading ?? 0) * Math.PI) / 180;

    context.save();
    context.translate(x, y);

    // Halo, pour rester repérable même dézoomé.
    context.fillStyle = css("--accent");
    context.globalAlpha = 0.18;
    context.beginPath();
    context.arc(0, 0, 22, 0, Math.PI * 2);
    context.fill();
    context.globalAlpha = 1;

    context.rotate(heading);
    context.fillStyle = css("--accent");
    context.strokeStyle = css("--aircraft-outline");
    context.lineWidth = 1.5;
    context.beginPath();
    context.moveTo(0, -13);
    context.lineTo(11, 9);
    context.lineTo(0, 4);
    context.lineTo(-11, 9);
    context.closePath();
    context.fill();
    context.stroke();
    context.restore();
  }

  function drawScaleBar() {
    // L'échelle annonce des mètres au sol : Mercator les dilate en 1/cos(φ).
    const pixelsPerMetre = pixelsPerGroundMetre();
    const candidates = [
      10, 25, 50, 100, 250, 500, 1000, 2000, 5000,
      10000, 25000, 50000, 100000, 250000, 500000,
    ];
    const target = 120;
    const metres =
      candidates.find((m) => m * pixelsPerMetre >= target) ||
      candidates[candidates.length - 1];
    const pixels = metres * pixelsPerMetre;
    const x = 18;
    const y = canvas.clientHeight - 22;

    context.save();
    context.strokeStyle = css("--text-dim");
    context.fillStyle = css("--text-dim");
    context.lineWidth = 1.5;
    context.beginPath();
    context.moveTo(x, y - 5);
    context.lineTo(x, y);
    context.lineTo(x + pixels, y);
    context.lineTo(x + pixels, y - 5);
    context.stroke();
    context.font = "500 11px 'Inter', system-ui, sans-serif";
    context.textAlign = "left";
    context.textBaseline = "bottom";
    const label = metres >= 1000 ? `${metres / 1000} km` : `${metres} m`;
    context.fillText(label, x, y - 8);
    context.restore();
  }

  function drawNorth() {
    const x = canvas.clientWidth - 30;
    const y = 30;
    context.save();
    context.translate(x, y);
    context.fillStyle = css("--text-dim");
    context.beginPath();
    context.moveTo(0, -12);
    context.lineTo(5, 6);
    context.lineTo(0, 2);
    context.lineTo(-5, 6);
    context.closePath();
    context.fill();
    context.font = "600 10px 'Inter', system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("N", 0, 20);
    context.restore();
  }

  function roundRect(x, y, width, height, radius) {
    context.beginPath();
    context.moveTo(x + radius, y);
    context.arcTo(x + width, y, x + width, y + height, radius);
    context.arcTo(x + width, y + height, x, y + height, radius);
    context.arcTo(x, y + height, x, y, radius);
    context.arcTo(x, y, x + width, y, radius);
    context.closePath();
  }

  /* ----------------------------------------------------------- interaction */

  function zoomAt(px, py, factor) {
    const [worldX, worldY] = toWorld(px, py);
    view.scale = Math.min(6, Math.max(0.000001, view.scale * factor));
    const [newX, newY] = toWorld(px, py);
    view.centerX += worldX - newX;
    view.centerY += worldY - newY;
    draw();
  }

  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    zoomAt(
      event.clientX - rect.left,
      event.clientY - rect.top,
      event.deltaY < 0 ? 1.15 : 1 / 1.15
    );
  }, { passive: false });

  canvas.addEventListener("pointerdown", (event) => {
    dragging = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY };
    canvas.setPointerCapture(event.pointerId);
    canvas.style.cursor = "grabbing";
  });

  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    view.centerX -= (event.clientX - dragging.x) / view.scale;
    view.centerY += (event.clientY - dragging.y) / view.scale;
    dragging = { x: event.clientX, y: event.clientY };
    if (view.follow) {
      view.follow = false;
      syncFollowButton();
    }
    draw();
  });

  /**
   * Poste sous le pointeur, ou null.
   *
   * La tolérance ne descend jamais sous 10 px : dézoomé, un poste ne fait que
   * quelques pixels et deviendrait impossible à viser.
   */
  function parkingAt(px, py) {
    if (!chart?.parkings?.length) return null;
    const pixelsPerMetre = pixelsPerGroundMetre();
    let closest = null;
    let closestDistance = Infinity;
    for (const parking of chart.parkings) {
      const [x, y] = toScreen(parking.position.x, parking.position.y);
      const distance = Math.hypot(px - x, py - y);
      const reach = Math.max(10, (parking.radius_m || 15) * pixelsPerMetre);
      if (distance <= reach && distance < closestDistance) {
        closest = parking;
        closestDistance = distance;
      }
    }
    return closest;
  }

  const endDrag = (event) => {
    // Un clic est un appui qui n'a pas bougé : au-delà, c'était un glissement
    // de la carte, et sélectionner un poste au relâchement surprendrait.
    if (dragging && event) {
      const moved = Math.hypot(
        event.clientX - dragging.startX,
        event.clientY - dragging.startY
      );
      if (moved <= 4 && parkingListener) {
        const rect = canvas.getBoundingClientRect();
        const parking = parkingAt(event.clientX - rect.left, event.clientY - rect.top);
        if (parking) parkingListener(parking.label, parking);
      }
    }
    dragging = null;
    canvas.style.cursor = "grab";
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);

  function syncFollowButton() {
    const button = document.getElementById("map-follow");
    if (button) button.classList.toggle("active", view.follow);
  }

  function syncBasemapAttribution() {
    const attribution = document.getElementById("map-attribution");
    if (!attribution) return;
    const source = BASEMAPS[basemapKey];
    attribution.textContent = source.attribution;
    attribution.href = source.attributionUrl;
  }

  /** Aligne le sélecteur de la barre carte sur le fond réellement affiché. */
  function syncBasemapSelect() {
    const select = document.getElementById("map-basemap-style");
    if (!select) return;
    if (select.value !== basemapKey) select.value = basemapKey;
    select.disabled = !basemapVisible;
  }

  /** Applique un fond connu ; renvoie la clé retenue (repli sur OSM). */
  function applyBasemap(key) {
    const nextBasemap = BASEMAPS[key] ? key : "osm";
    if (nextBasemap !== basemapKey) {
      basemapKey = nextBasemap;
      tileCache.clear();
    }
    syncBasemapAttribution();
    syncBasemapSelect();
    return basemapKey;
  }

  /* --------------------------------------------------------------- public */

  return {
    project,
    setChart(data) {
      chart = prepareChart(data);
      aircraft = null;
      routeSegments = [];
      // Le plan de roulage appartient au terrain affiché : le garder d'un
      // aérodrome à l'autre tracerait une route sur le mauvais sol.
      taxiPlan = null;
      selectedParking = null;
      fitPending = true;
      fit();
    },
    setAircraft(position) {
      aircraft = position;
      if (position) {
        if (view.follow) {
          view.centerX = position.x;
          view.centerY = position.y;
        }
      }
      draw();
    },
    setTrail(points) {
      trail = Array.isArray(points)
        ? points.map((point) => (
          Number.isFinite(point?.x) && Number.isFinite(point?.y)
            ? [point.x, point.y]
            : null
        ))
        : [];
      draw();
    },
    configure(options = {}) {
      const nextColor = /^#[0-9a-f]{6}$/i.test(options.trailColor || "")
        ? options.trailColor
        : "#22d3ee";
      applyBasemap(options.basemap);
      trailColor = nextColor;
      draw();
    },
    setRoute(points) {
      route = points || [];
      routeSegments = [];
      draw();
    },
    setRouteSegments(segments) {
      routeSegments = (segments || []).filter((segment) => segment.points?.length);
      route = routeSegments.flatMap((segment) => segment.points);
      draw();
    },
    fitRoute() {
      const visiblePoints = [
        ...route,
        ...trail.filter(Boolean).map(([x, y]) => ({ x, y })),
      ];
      if (visiblePoints.length < 2) return;
      const xs = visiblePoints.map((point) => point.x);
      const ys = visiblePoints.map((point) => point.y);
      const width = Math.max(1000, Math.max(...xs) - Math.min(...xs));
      const height = Math.max(1000, Math.max(...ys) - Math.min(...ys));
      view.centerX = (Math.min(...xs) + Math.max(...xs)) / 2;
      view.centerY = (Math.min(...ys) + Math.max(...ys)) / 2;
      view.scale = Math.min(
        canvas.clientWidth / width,
        canvas.clientHeight / height
      ) * 0.86;
      view.follow = false;
      syncFollowButton();
      draw();
    },
    clearAircraft() {
      aircraft = null;
      draw();
    },
    /**
     * Itinéraire de roulage à afficher.
     *
     * Il arrive en mètres locaux, comme le plan de terrain : il est reconverti
     * ici dans le repère monde, avec la même projection, faute de quoi il
     * dériverait du sol qu'il est censé suivre.
     */
    setTaxiPlan(plan) {
      if (!plan?.legs?.length || !chart?.origin) {
        taxiPlan = null;
        selectedParking = null;
        draw();
        return;
      }
      const toWorld = (point) => {
        const [latitude, longitude] = localToLatLon(chart.origin, point);
        return project(latitude, longitude);
      };
      taxiPlan = {
        ...plan,
        legs: plan.legs.map((leg) => ({
          ...leg,
          points: (leg.points || []).map(toWorld),
        })),
      };
      selectedParking = plan.parking?.label ?? null;
      draw();
    },
    clearTaxiPlan() {
      taxiPlan = null;
      selectedParking = null;
      draw();
    },
    /** Appelé avec le libellé du poste cliqué sur la carte. */
    onParkingSelect(callback) {
      parkingListener = typeof callback === "function" ? callback : null;
    },
    get taxiPlan() { return taxiPlan; },
    fit,
    zoomIn: () => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1.35),
    zoomOut: () => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1 / 1.35),
    toggleFollow() {
      view.follow = !view.follow;
      syncFollowButton();
      if (view.follow && aircraft) {
        view.centerX = aircraft.x;
        view.centerY = aircraft.y;
      }
      draw();
    },
    toggleBasemap() {
      basemapVisible = !basemapVisible;
      const button = document.getElementById("map-basemap");
      if (button) {
        button.classList.toggle("active", basemapVisible);
        button.setAttribute("aria-pressed", String(basemapVisible));
      }
      syncBasemapSelect();
      draw();
    },
    /** Change le fond depuis la barre carte ; renvoie la clé appliquée. */
    setBasemap(key) {
      const applied = applyBasemap(key);
      draw();
      return applied;
    },
    get basemap() { return basemapKey; },
    get following() { return view.follow; },
    resize,
    hasChart: () => chart !== null,
  };
})();

window.addEventListener("resize", () => MAP.resize());
