"use strict";

/**
 * Plan de roulage : l'aérodrome seul, et le chemin à suivre.
 *
 * Ce module est volontairement séparé de la carte. Celle-ci sert à suivre un
 * vol : elle porte un fond OpenStreetMap, la route SID/STAR et la trace. Au
 * sol, tout cela nuit — le fond de carte noie les voies sous les rues de la
 * ville, et la route de vol traverse le terrain de part en part sans rien
 * apprendre au pilote qui cherche sa piste.
 *
 * Le repère est celui du plan de terrain tel que le service l'envoie : des
 * mètres locaux tangents à l'aérodrome, x vers l'est et y vers le nord. Aucune
 * reprojection n'est nécessaire, il n'y a pas de tuiles avec lesquelles
 * s'aligner, et à l'échelle d'un terrain cette approximation est exacte à
 * quelques centimètres.
 *
 * Les noms de voies ne sont affichés que pour l'itinéraire calculé. Les
 * afficher tous couvrait le terrain de pastilles — plus de mille à Toulouse —
 * et masquait précisément ce qu'on venait y chercher.
 */

const GROUND = (() => {
  const canvas = document.getElementById("ground-canvas");
  const context = canvas ? canvas.getContext("2d") : null;

  const EARTH_RADIUS_M = 6378137;

  const view = { scale: 0.35, centerX: 0, centerY: 0, follow: true };
  let chart = null;
  let plan = null;
  let aircraft = null;
  let travelled = 0;
  let dragging = null;
  let fitPending = false;
  let parkingListener = null;
  let showSecondaryTaxiways = false;

  /* ------------------------------------------------------------ géométrie */

  function css(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
  }

  /**
   * Latitude/longitude vers les mètres locaux du plan.
   *
   * C'est l'inverse exact de la projection du service : les deux doivent se
   * correspondre au centimètre, sinon l'avion flotterait à côté des voies.
   */
  function toLocal(latitude, longitude) {
    if (!chart?.origin) return null;
    const originLat = (chart.origin.lat * Math.PI) / 180;
    return {
      x: (((longitude - chart.origin.lon) * Math.PI) / 180)
        * EARTH_RADIUS_M * Math.cos(originLat),
      y: (((latitude - chart.origin.lat) * Math.PI) / 180) * EARTH_RADIUS_M,
    };
  }

  /** Distance d'un point au segment [a, b], en mètres locaux. */
  function distanceToSegment(x, y, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const squared = dx * dx + dy * dy;
    if (squared <= 0) return Math.hypot(x - a.x, y - a.y);
    const ratio = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / squared));
    return Math.hypot(x - (a.x + dx * ratio), y - (a.y + dy * ratio));
  }

  function toScreen(x, y) {
    return [
      canvas.clientWidth / 2 + (x - view.centerX) * view.scale,
      canvas.clientHeight / 2 - (y - view.centerY) * view.scale,
    ];
  }

  function toLocalFromScreen(px, py) {
    return [
      (px - canvas.clientWidth / 2) / view.scale + view.centerX,
      -(py - canvas.clientHeight / 2) / view.scale + view.centerY,
    ];
  }

  /** Le segment touche-t-il l'écran ? Un grand terrain a 3 000 voies. */
  function onScreen(x1, y1, x2, y2, margin = 60) {
    return !(
      (x1 < -margin && x2 < -margin)
      || (y1 < -margin && y2 < -margin)
      || (x1 > canvas.clientWidth + margin && x2 > canvas.clientWidth + margin)
      || (y1 > canvas.clientHeight + margin && y2 > canvas.clientHeight + margin)
    );
  }

  function fit() {
    if (!chart || !canvas) return;
    if (canvas.clientWidth <= 0 || canvas.clientHeight <= 0) {
      fitPending = true;
      return;
    }
    const bounds = chart.bounds;
    const width = Math.max(1, bounds.max_x - bounds.min_x);
    const height = Math.max(1, bounds.max_y - bounds.min_y);
    view.centerX = (bounds.min_x + bounds.max_x) / 2;
    view.centerY = (bounds.min_y + bounds.max_y) / 2;
    view.scale = Math.min(
      canvas.clientWidth / width,
      canvas.clientHeight / height
    ) * 0.92;
    view.follow = false;
    fitPending = false;
    syncButtons();
    draw();
  }

  /** Cadre sur l'itinéraire plutôt que sur tout le terrain. */
  function fitPlan() {
    const points = planPolyline();
    if (points.length < 2 || !canvas.clientWidth) return fit();
    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    const width = Math.max(300, Math.max(...xs) - Math.min(...xs));
    const height = Math.max(300, Math.max(...ys) - Math.min(...ys));
    view.centerX = (Math.min(...xs) + Math.max(...xs)) / 2;
    view.centerY = (Math.min(...ys) + Math.max(...ys)) / 2;
    view.scale = Math.min(
      canvas.clientWidth / width,
      canvas.clientHeight / height
    ) * 0.82;
    view.follow = false;
    syncButtons();
    draw();
  }

  /* ---------------------------------------------------------------- rendu */

  function resize() {
    if (!canvas || canvas.clientWidth <= 0 || canvas.clientHeight <= 0) return;
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
    if (!context) return;
    context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    context.fillStyle = css("--ground-bg");
    context.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    if (!chart) return;

    drawGroundGrid();
    drawTaxiways();
    drawRunways();
    drawParkings();
    drawRoute();
    drawRouteLabels();
    drawAircraft();
    drawScaleBar();
    drawNorthArrow();
  }

  /**
   * Fond de roulage métrique, calé sur le repère réel de l'aérodrome.
   *
   * Il donne une notion immédiate des distances et de l'orientation sans
   * ajouter les rues, bâtiments et libellés d'un fond routier.
   */
  function drawGroundGrid() {
    const steps = [25, 50, 100, 200, 500, 1000, 2000, 5000];
    const step = steps.find((value) => value * view.scale >= 64) || 10000;
    const [minX, maxY] = toLocalFromScreen(0, 0);
    const [maxX, minY] = toLocalFromScreen(canvas.clientWidth, canvas.clientHeight);

    context.save();
    context.lineWidth = 1;
    for (let x = Math.ceil(minX / step) * step; x <= maxX; x += step) {
      const [screenX] = toScreen(x, 0);
      const major = Math.round(x / step) % 5 === 0;
      context.strokeStyle = css(major ? "--ground-grid-major" : "--ground-grid");
      context.beginPath();
      context.moveTo(Math.round(screenX) + 0.5, 0);
      context.lineTo(Math.round(screenX) + 0.5, canvas.clientHeight);
      context.stroke();
    }
    for (let y = Math.ceil(minY / step) * step; y <= maxY; y += step) {
      const [, screenY] = toScreen(0, y);
      const major = Math.round(y / step) % 5 === 0;
      context.strokeStyle = css(major ? "--ground-grid-major" : "--ground-grid");
      context.beginPath();
      context.moveTo(0, Math.round(screenY) + 0.5);
      context.lineTo(canvas.clientWidth, Math.round(screenY) + 0.5);
      context.stroke();
    }
    context.restore();
  }

  function drawNorthArrow() {
    const x = canvas.clientWidth - 25;
    const y = 27;
    context.save();
    context.strokeStyle = css("--ground-label");
    context.fillStyle = css("--ground-label");
    context.globalAlpha = 0.7;
    context.lineWidth = 1.5;
    context.beginPath();
    context.moveTo(x, y + 13);
    context.lineTo(x, y - 7);
    context.lineTo(x - 4, y - 1);
    context.moveTo(x, y - 7);
    context.lineTo(x + 4, y - 1);
    context.stroke();
    context.font = "700 10px 'Inter', system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText("N", x, y - 12);
    context.restore();
  }

  function drawTaxiways() {
    const taxiways = chart.taxiways || [];
    if (!taxiways.length) return;

    context.save();
    context.lineCap = "round";
    context.lineJoin = "round";
    for (const taxiway of taxiways) {
      // La piste est dessinée à part, en bande pleine : repasser ses segments
      // en voie de circulation la ferait paraître plus étroite qu'elle n'est.
      if (taxiway.kind === "runway") continue;
      // Les routes de service ne concernent pas l'avion ; les tracer avec les
      // voies doublait la densité du plan pour rien.
      if (taxiway.kind === "vehicle") continue;
      // MSFS uses `path` both for anonymous secondary links and for real,
      // published taxiways at some airports (LCPH exposes A, B, K, etc. this
      // way). A name therefore takes precedence over the generic kind: named
      // taxiways remain visible, while stand lead-ins and anonymous paths stay
      // behind the Secondary control.
      const secondary = taxiway.kind === "parking" || (
        taxiway.kind === "path" && !String(taxiway.name || "").trim()
      );
      if (secondary && !showSecondaryTaxiways) continue;
      const [x1, y1] = toScreen(taxiway.start.x, taxiway.start.y);
      const [x2, y2] = toScreen(taxiway.end.x, taxiway.end.y);
      if (!onScreen(x1, y1, x2, y2)) continue;

      const closed = taxiway.kind === "closed";
      context.strokeStyle = css(closed ? "--ground-closed" : "--ground-taxiway");
      context.globalAlpha = closed ? 0.72 : (plan ? 0.34 : 0.68);
      context.lineWidth = Math.max(
        1.1,
        Math.min(4.5, (taxiway.width_m || 15) * view.scale * 0.48)
      );
      context.setLineDash(closed ? [7, 6] : []);
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();
    }
    context.globalAlpha = 1;
    context.setLineDash([]);
    context.restore();
  }

  function drawRunways() {
    const highlight = (chart.highlight_runway || "").toUpperCase();
    context.save();
    context.lineCap = "butt";

    for (const runway of chart.runways || []) {
      const [x1, y1] = toScreen(runway.start.x, runway.start.y);
      const [x2, y2] = toScreen(runway.end.x, runway.end.y);
      const width = Math.max(3, runway.width_m * view.scale);
      const active = (runway.ends || []).some(
        (end) => end.name.toUpperCase() === highlight
      );

      context.strokeStyle = css(active ? "--ground-runway-active" : "--ground-runway");
      context.lineWidth = width;
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();

      if (width > 7) {
        context.save();
        context.strokeStyle = css("--ground-centreline");
        context.globalAlpha = 0.55;
        context.lineWidth = Math.max(1, width * 0.045);
        context.setLineDash([width * 1.1, width * 1.1]);
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();
        context.restore();
      }

      for (const end of runway.ends || []) {
        drawRunwayNumber(end, runway, end.name.toUpperCase() === highlight);
      }
    }
    context.restore();
  }

  /** Numéro peint sur le seuil, orienté comme la piste. */
  function drawRunwayNumber(end, runway, active) {
    const width = Math.max(3, runway.width_m * view.scale);
    if (width < 9) return;
    const [x, y] = toScreen(end.threshold.x, end.threshold.y);
    if (x < -40 || y < -40 || x > canvas.clientWidth + 40 || y > canvas.clientHeight + 40) {
      return;
    }
    // Le texte se lit dans le sens du décollage, et jamais à l'envers.
    let heading = ((end.heading ?? 0) + 360) % 360;
    let rotation = (heading * Math.PI) / 180;
    if (heading > 180) rotation -= Math.PI;

    context.save();
    context.translate(x, y);
    context.rotate(rotation);
    context.font = `700 ${Math.max(10, Math.min(22, width * 0.55))}px 'Inter', system-ui, sans-serif`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillStyle = css(active ? "--ground-runway-text-active" : "--ground-runway-text");
    // Décalé vers l'intérieur de la piste : sur le seuil même, il déborderait.
    context.fillText(end.name, 0, heading > 180 ? -width * 1.1 : width * 1.1);
    context.restore();
  }

  function drawParkings() {
    const parkings = chart.parkings || [];
    if (!parkings.length || view.scale < 0.08) return;
    const selected = plan?.parking?.label ?? null;
    const showLabels = view.scale > 0.62;

    context.save();
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = "600 10px 'Inter', system-ui, sans-serif";

    for (const parking of parkings) {
      const [x, y] = toScreen(parking.position.x, parking.position.y);
      if (x < -30 || y < -30 || x > canvas.clientWidth + 30 || y > canvas.clientHeight + 30) {
        continue;
      }
      const active = parking.label === selected;
      const radius = active
        ? Math.max(4, Math.min(9, (parking.radius_m || 15) * view.scale))
        : Math.max(1.8, Math.min(4.5, (parking.radius_m || 15) * view.scale * 0.55));

      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.fillStyle = css(active ? "--ground-parking-active" : "--ground-parking");
      context.globalAlpha = active ? 1 : (plan ? 0.28 : 0.58);
      context.fill();
      context.globalAlpha = 1;

      // Le nom du poste retenu reste lisible à toute échelle : c'est le point
      // de départ ou d'arrivée du roulage.
      if (showLabels || active) {
        context.fillStyle = css(active ? "--ground-parking-active" : "--ground-label");
        context.font = active
          ? "700 11px 'Inter', system-ui, sans-serif"
          : "600 10px 'Inter', system-ui, sans-serif";
        // Le libellé du service est français : seul l'affichage est traduit,
        // la sélection continue de se faire sur l'étiquette d'origine.
        context.fillText(window.I18N.groundLabel(parking.label), x, y + radius + 9);
      }
    }
    context.restore();
  }

  /* -------------------------------------------------------------- roulage */

  /** Itinéraire en une seule ligne, sans point répété. */
  function planPolyline() {
    if (!plan?.legs?.length) return [];
    const points = [];
    for (const leg of plan.legs) {
      for (const point of leg.points || []) {
        const last = points[points.length - 1];
        if (last && last.x === point.x && last.y === point.y) continue;
        points.push(point);
      }
    }
    return points;
  }

  /**
   * Trace l'itinéraire, atténué derrière l'avion et vif devant.
   *
   * La coupure se fait à la position exacte de l'appareil, au milieu d'un
   * segment s'il le faut : bascule au nœud suivant, la couleur avancerait par
   * à-coups sans rapport avec le déplacement réel.
   */
  function drawRoute() {
    const points = planPolyline();
    if (points.length < 2) return;

    context.save();
    context.lineWidth = Math.max(3, Math.min(9, 14 * view.scale));
    context.lineJoin = "round";
    context.lineCap = "round";

    let walked = 0;
    for (let index = 1; index < points.length; index += 1) {
      const from = points[index - 1];
      const to = points[index];
      const length = Math.hypot(to.x - from.x, to.y - from.y);
      const pieces = [];
      if (walked + length <= travelled) {
        pieces.push([from, to, true]);
      } else if (walked >= travelled) {
        pieces.push([from, to, false]);
      } else {
        const ratio = (travelled - walked) / length;
        const split = {
          x: from.x + (to.x - from.x) * ratio,
          y: from.y + (to.y - from.y) * ratio,
        };
        pieces.push([from, split, true], [split, to, false]);
      }
      for (const [a, b, done] of pieces) {
        const [x1, y1] = toScreen(a.x, a.y);
        const [x2, y2] = toScreen(b.x, b.y);
        if (!onScreen(x1, y1, x2, y2)) continue;
        context.strokeStyle = css("--ground-bg");
        context.globalAlpha = 0.9;
        context.lineWidth = Math.max(5, Math.min(12, 18 * view.scale));
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();

        context.strokeStyle = css(done ? "--taxi-done" : "--taxi-ahead");
        context.globalAlpha = done ? 0.5 : 1;
        context.lineWidth = Math.max(3, Math.min(8, 12 * view.scale));
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();
      }
      walked += length;
    }
    context.restore();
    drawHoldBars();
  }

  /** Barre d'arrêt en travers du tracé, là où il faut attendre. */
  function drawHoldBars() {
    if (!plan?.legs?.length) return;
    context.save();
    context.lineCap = "butt";

    for (const leg of plan.legs) {
      if (!leg.hold_short) continue;
      const points = leg.points || [];
      if (points.length < 2) continue;
      const last = points[points.length - 1];
      const previous = points[points.length - 2];
      const [x, y] = toScreen(last.x, last.y);
      if (x < 0 || y < 0 || x > canvas.clientWidth || y > canvas.clientHeight) continue;
      const [px, py] = toScreen(previous.x, previous.y);
      const length = Math.hypot(x - px, y - py) || 1;
      const half = Math.max(9, 26 * view.scale);
      const nx = (-(y - py) / length) * half;
      const ny = ((x - px) / length) * half;

      context.strokeStyle = css("--ground-hold");
      context.lineWidth = 3;
      context.beginPath();
      context.moveTo(x - nx, y - ny);
      context.lineTo(x + nx, y + ny);
      context.stroke();
    }
    context.restore();
  }

  /**
   * Nom des voies de l'itinéraire, une fois chacune.
   *
   * C'est toute la différence avec la carte : seules les voies à emprunter
   * portent leur nom. Les milliers d'autres restent muettes, et le chemin se
   * lit d'un coup d'œil.
   */
  function drawRouteLabels() {
    if (!plan?.legs?.length) return;
    context.save();
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = "700 12px 'Inter', system-ui, sans-serif";

    const placed = new Set();
    const occupied = [];
    for (const leg of plan.legs) {
      if (!leg.name || leg.kind === "stand" || leg.kind === "join") continue;
      if (placed.has(leg.name)) continue;
      const points = leg.points || [];
      if (points.length < 2) continue;
      const middle = points[Math.floor(points.length / 2)];
      const [x, y] = toScreen(middle.x, middle.y);
      if (x < 12 || y < 12 || x > canvas.clientWidth - 12 || y > canvas.clientHeight - 12) {
        continue;
      }
      const width = context.measureText(leg.name).width + 12;
      const box = {
        left: x - width / 2 - 4, right: x + width / 2 + 4,
        top: y - 14, bottom: y + 14,
      };
      if (occupied.some((other) => !(
        box.right < other.left || box.left > other.right
        || box.bottom < other.top || box.top > other.bottom
      ))) continue;
      occupied.push(box);
      placed.add(leg.name);

      context.fillStyle = css("--ground-label-bg");
      roundRect(x - width / 2, y - 10, width, 20, 5);
      context.fill();
      context.strokeStyle = css("--taxi-ahead");
      context.lineWidth = 1;
      context.stroke();
      context.fillStyle = css("--ground-label");
      context.fillText(leg.name, x, y + 1);
    }
    context.restore();
  }

  function drawAircraft() {
    if (!aircraft) return;
    const position = toLocal(aircraft.latitude, aircraft.longitude);
    if (!position) return;
    const [x, y] = toScreen(position.x, position.y);
    const heading = ((aircraft.heading_true_deg ?? 0) * Math.PI) / 180;

    context.save();
    context.translate(x, y);
    context.rotate(heading);
    context.fillStyle = css("--ground-aircraft");
    context.strokeStyle = css("--ground-bg");
    context.lineWidth = 1.5;

    // Silhouette simple : fuselage, ailes et empennage.
    context.beginPath();
    context.moveTo(0, -13);
    context.lineTo(2.6, -4);
    context.lineTo(14, 3);
    context.lineTo(14, 6);
    context.lineTo(2.6, 3.5);
    context.lineTo(2.2, 10);
    context.lineTo(6, 13);
    context.lineTo(6, 15);
    context.lineTo(0, 13.5);
    context.lineTo(-6, 15);
    context.lineTo(-6, 13);
    context.lineTo(-2.2, 10);
    context.lineTo(-2.6, 3.5);
    context.lineTo(-14, 6);
    context.lineTo(-14, 3);
    context.lineTo(-2.6, -4);
    context.closePath();
    context.fill();
    context.stroke();
    context.restore();
  }

  function drawScaleBar() {
    const targetPixels = 110;
    const metres = [50, 100, 200, 500, 1000, 2000].find(
      (value) => value * view.scale >= targetPixels
    ) || 5000;
    const pixels = metres * view.scale;
    const left = 16;
    const bottom = canvas.clientHeight - 18;

    context.save();
    context.strokeStyle = css("--ground-label");
    context.fillStyle = css("--ground-label");
    context.globalAlpha = 0.75;
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(left, bottom - 5);
    context.lineTo(left, bottom);
    context.lineTo(left + pixels, bottom);
    context.lineTo(left + pixels, bottom - 5);
    context.stroke();
    context.font = "600 10px 'Inter', system-ui, sans-serif";
    context.textAlign = "center";
    context.fillText(`${metres} m`, left + pixels / 2, bottom - 10);
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

  /* ---------------------------------------------------------- interaction */

  function zoomAt(px, py, factor) {
    const [x, y] = toLocalFromScreen(px, py);
    view.scale = Math.min(12, Math.max(0.02, view.scale * factor));
    const [nx, ny] = toLocalFromScreen(px, py);
    view.centerX += x - nx;
    view.centerY += y - ny;
    draw();
  }

  /** Poste sous le pointeur, ou null. */
  function parkingAt(px, py) {
    if (!chart?.parkings?.length) return null;
    let closest = null;
    let closestDistance = Infinity;
    for (const parking of chart.parkings) {
      const [x, y] = toScreen(parking.position.x, parking.position.y);
      const distance = Math.hypot(px - x, py - y);
      // Dézoomé, un poste ne fait que quelques pixels : sans ce minimum il
      // deviendrait impossible à viser.
      const reach = Math.max(11, (parking.radius_m || 15) * view.scale);
      if (distance <= reach && distance < closestDistance) {
        closest = parking;
        closestDistance = distance;
      }
    }
    return closest;
  }

  function syncButtons() {
    const followButton = document.getElementById("ground-follow");
    if (followButton) followButton.classList.toggle("active", view.follow);
    const secondaryButton = document.getElementById("ground-secondary");
    if (secondaryButton) {
      secondaryButton.classList.toggle("active", showSecondaryTaxiways);
      secondaryButton.setAttribute("aria-pressed", String(showSecondaryTaxiways));
    }
  }

  if (canvas) {
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
      dragging = {
        x: event.clientX, y: event.clientY,
        startX: event.clientX, startY: event.clientY,
      };
      canvas.setPointerCapture(event.pointerId);
      canvas.style.cursor = "grabbing";
    });

    canvas.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      view.centerX -= (event.clientX - dragging.x) / view.scale;
      view.centerY += (event.clientY - dragging.y) / view.scale;
      dragging = { ...dragging, x: event.clientX, y: event.clientY };
      if (view.follow) {
        view.follow = false;
        syncButtons();
      }
      draw();
    });

    const endDrag = (event) => {
      // Un clic est un appui qui n'a pas bougé : au-delà c'était un
      // déplacement du plan, et choisir un poste au relâchement surprendrait.
      if (dragging && event) {
        const moved = Math.hypot(
          event.clientX - dragging.startX,
          event.clientY - dragging.startY
        );
        if (moved <= 4 && parkingListener) {
          const rect = canvas.getBoundingClientRect();
          const parking = parkingAt(
            event.clientX - rect.left, event.clientY - rect.top
          );
          if (parking) parkingListener(parking.label, parking);
        }
      }
      dragging = null;
      canvas.style.cursor = "grab";
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);
  }

  /* --------------------------------------------------------------- public */

  return {
    /** Plan de terrain brut du service, en mètres locaux. */
    setChart(data) {
      chart = data;
      plan = null;
      aircraft = null;
      travelled = 0;
      fitPending = true;
      fit();
    },
    /** Itinéraire de roulage à suivre, ou null pour l'effacer. */
    setPlan(data) {
      plan = data?.legs?.length ? data : null;
      travelled = 0;
      draw();
    },
    /**
     * Distance déjà parcourue sur l'itinéraire, mesurée par le service.
     *
     * Elle vient du guidage plutôt que d'un calcul local : les deux doivent
     * désigner le même point, sous peine d'annoncer une manœuvre que le tracé
     * situe ailleurs.
     */
    setProgress(metres) {
      travelled = Number.isFinite(metres) ? metres : 0;
      draw();
    },
    setAircraft(state) {
      aircraft = state?.latitude != null ? state : null;
      if (aircraft && view.follow) {
        const position = toLocal(aircraft.latitude, aircraft.longitude);
        if (position) {
          view.centerX = position.x;
          view.centerY = position.y;
        }
      }
      draw();
    },
    clearAircraft() {
      aircraft = null;
      draw();
    },
    /**
     * L'avion est-il sur une piste plutôt que sur une voie de circulation ?
     *
     * C'est la seule question qui compte pour une limite de roulage : la
     * déduire de la vitesse ferait taire l'alarme précisément quand elle est
     * la plus justifiée, un roulage à 50 kt étant alors pris pour un décollage.
     * La bande est élargie de quelques mètres, un avion aligné n'ayant aucune
     * raison d'avoir son point de référence exactement sur l'axe.
     */
    onRunway(state = aircraft) {
      const position = state?.latitude != null
        ? toLocal(state.latitude, state.longitude)
        : null;
      if (!position || !chart?.runways?.length) return false;
      return chart.runways.some((runway) => distanceToSegment(
        position.x, position.y, runway.start, runway.end
      ) <= (runway.width_m || 45) / 2 + 10);
    },
    onParkingSelect(callback) {
      parkingListener = typeof callback === "function" ? callback : null;
    },
    nearestParking(state) {
      const position = state?.latitude != null
        ? toLocal(state.latitude, state.longitude)
        : null;
      if (!position || !chart?.parkings?.length) return null;
      let nearest = null;
      for (const parking of chart.parkings) {
        const distance = Math.hypot(
          parking.position.x - position.x,
          parking.position.y - position.y
        );
        if (!nearest || distance < nearest.distance_m) {
          nearest = { label: parking.label, distance_m: distance };
        }
      }
      return nearest;
    },
    toggleSecondaryTaxiways() {
      showSecondaryTaxiways = !showSecondaryTaxiways;
      syncButtons();
      draw();
    },
    toggleFollow() {
      view.follow = !view.follow;
      syncButtons();
      if (view.follow && aircraft) {
        const position = toLocal(aircraft.latitude, aircraft.longitude);
        if (position) {
          view.centerX = position.x;
          view.centerY = position.y;
          // Au sol, on lit le détail : suivre sans zoomer laisserait le plan
          // à l'échelle du terrain entier.
          view.scale = Math.max(view.scale, 1.1);
        }
      }
      draw();
    },
    fit,
    fitPlan,
    zoomIn: () => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1.35),
    zoomOut: () => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1 / 1.35),
    resize,
    hasChart: () => chart !== null,
    get following() { return view.follow; },
  };
})();

window.addEventListener("resize", () => GROUND.resize());
