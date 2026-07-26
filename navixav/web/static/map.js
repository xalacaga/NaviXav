"use strict";

/**
 * Plan de terrain sur canvas.
 *
 * Le plan arrive déjà projeté en mètres locaux (x est, y nord). Le rendu ne
 * fait donc qu'appliquer une échelle et un centrage, avec l'axe y inversé pour
 * garder le nord en haut.
 */

const MAP = (() => {
  const canvas = document.getElementById("chart-canvas");
  const context = canvas.getContext("2d");

  const view = { scale: 0.2, centerX: 0, centerY: 0, follow: true };
  let chart = null;
  let aircraft = null;
  let trail = [];
  let route = [];
  let dragging = null;
  let basemapVisible = true;
  let groundDetailsVisible = false;
  const tileCache = new Map();
  const TILE_SIZE = 256;
  const MAX_TILE_CACHE = 320;

  /* ------------------------------------------------------------ géométrie */

  function css(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
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
    const b = chart.bounds;
    const width = Math.max(1, b.max_x - b.min_x);
    const height = Math.max(1, b.max_y - b.min_y);
    view.centerX = (b.min_x + b.max_x) / 2;
    view.centerY = (b.min_y + b.max_y) / 2;
    view.scale = Math.min(
      canvas.clientWidth / width,
      canvas.clientHeight / height
    ) * 0.92;
    view.follow = false;
    syncFollowButton();
    draw();
  }

  /* --------------------------------------------------------------- rendu */

  function resize() {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = canvas.clientWidth * ratio;
    canvas.height = canvas.clientHeight * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }

  function draw() {
    context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    if (!chart) return;

    if (basemapVisible) drawBasemap();
    if (groundDetailsVisible) drawTaxiways();
    drawRunways();
    if (groundDetailsVisible && view.scale > 0.42) drawParkings();
    drawRoute();
    drawTrail();
    drawAircraft();
    drawScaleBar();
    drawNorth();
  }

  function webMercatorPixel(latitude, longitude, zoom) {
    const size = TILE_SIZE * (2 ** zoom);
    const lat = Math.max(-85.05112878, Math.min(85.05112878, latitude));
    const sin = Math.sin((lat * Math.PI) / 180);
    return {
      x: ((longitude + 180) / 360) * size,
      y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size,
    };
  }

  function basemapZoom() {
    const latitude = chart.origin.lat * Math.PI / 180;
    const circumference = 2 * Math.PI * 6371000 * Math.cos(latitude);
    return Math.max(3, Math.min(19,
      Math.round(Math.log2((view.scale * circumference) / TILE_SIZE))
    ));
  }

  function getTile(zoom, x, y) {
    const key = `${zoom}/${x}/${y}`;
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
    image.src = `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`;

    if (tileCache.size > MAX_TILE_CACHE) {
      const oldest = tileCache.keys().next().value;
      tileCache.delete(oldest);
    }
    return tile;
  }

  function drawBasemap() {
    const zoom = basemapZoom();
    const tileCount = 2 ** zoom;
    const origin = webMercatorPixel(chart.origin.lat, chart.origin.lon, zoom);
    const metresPerPixel =
      (2 * Math.PI * 6371000 * Math.cos(chart.origin.lat * Math.PI / 180)) /
      (TILE_SIZE * tileCount);
    const screenPixelsPerTile = (TILE_SIZE * metresPerPixel) * view.scale;
    const centreGlobalX = origin.x + view.centerX / metresPerPixel;
    const centreGlobalY = origin.y - view.centerY / metresPerPixel;
    const centreTileX = centreGlobalX / TILE_SIZE;
    const centreTileY = centreGlobalY / TILE_SIZE;
    const radiusX = Math.ceil(canvas.clientWidth / screenPixelsPerTile / 2) + 1;
    const radiusY = Math.ceil(canvas.clientHeight / screenPixelsPerTile / 2) + 1;
    const firstX = Math.floor(centreTileX) - radiusX;
    const lastX = Math.floor(centreTileX) + radiusX;
    const firstY = Math.max(0, Math.floor(centreTileY) - radiusY);
    const lastY = Math.min(tileCount - 1, Math.floor(centreTileY) + radiusY);

    context.save();
    context.globalAlpha = 0.78;
    for (let tileY = firstY; tileY <= lastY; tileY += 1) {
      for (let tileX = firstX; tileX <= lastX; tileX += 1) {
        const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
        const tile = getTile(zoom, wrappedX, tileY);
        if (!tile.loaded || tile.failed) continue;
        const screenX =
          canvas.clientWidth / 2 + (tileX - centreTileX) * screenPixelsPerTile;
        const screenY =
          canvas.clientHeight / 2 + (tileY - centreTileY) * screenPixelsPerTile;
        // Le léger chevauchement évite les coutures dues aux pixels fractionnaires.
        context.drawImage(
          tile.image,
          Math.floor(screenX),
          Math.floor(screenY),
          Math.ceil(screenPixelsPerTile) + 1,
          Math.ceil(screenPixelsPerTile) + 1
        );
      }
    }
    context.restore();
  }

  function drawTaxiways() {
    const overview = view.scale < 0.28;
    const opacity = basemapVisible
      ? (overview ? 0.28 : 0.48)
      : (overview ? 0.5 : 0.72);

    context.save();
    context.strokeStyle = css("--taxi");
    context.globalAlpha = opacity;
    context.lineCap = "round";
    for (const segment of chart.taxiways) {
      const [x1, y1] = toScreen(segment.start.x, segment.start.y);
      const [x2, y2] = toScreen(segment.end.x, segment.end.y);
      if (
        Math.max(x1, x2) < -20 || Math.min(x1, x2) > canvas.clientWidth + 20 ||
        Math.max(y1, y2) < -20 || Math.min(y1, y2) > canvas.clientHeight + 20
      ) {
        continue;
      }
      // À l'échelle de l'aéroport, une voie est une ligne de repère et non
      // une large surface opaque. Son emprise ne réapparaît qu'en zoom proche.
      context.lineWidth = overview
        ? 0.85
        : Math.min(4.5, Math.max(1.1, segment.width_m * view.scale * 0.28));
      context.beginPath();
      context.moveTo(x1, y1);
      context.lineTo(x2, y2);
      context.stroke();
    }
    context.restore();
  }

  function drawRunways() {
    const highlight = (chart.highlight_runway || "").toUpperCase();

    for (const runway of chart.runways) {
      const isHighlighted = runway.ends.some(
        (end) => end.name.toUpperCase() === highlight
      );
      const [x1, y1] = toScreen(runway.start.x, runway.start.y);
      const [x2, y2] = toScreen(runway.end.x, runway.end.y);
      const width = Math.max(2.5, runway.width_m * view.scale);

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

  function drawParkings() {
    const showLabels = view.scale > 0.9;
    context.save();
    context.globalAlpha = basemapVisible ? 0.68 : 0.85;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = "500 10px 'Inter', system-ui, sans-serif";

    for (const parking of chart.parkings) {
      const [x, y] = toScreen(parking.position.x, parking.position.y);
      if (x < -40 || y < -40 || x > canvas.clientWidth + 40 || y > canvas.clientHeight + 40) {
        continue;
      }
      const radius = Math.min(5, Math.max(1.8, parking.radius_m * view.scale * 0.35));
      context.fillStyle = css("--parking");
      context.beginPath();
      context.arc(x, y, radius, 0, Math.PI * 2);
      context.fill();

      if (showLabels && radius > 4) {
        context.fillStyle = css("--parking-label");
        context.fillText(parking.label, x, y + radius + 8);
      }
    }
    context.restore();
  }

  function drawTrail() {
    if (trail.length < 2) return;
    context.save();
    context.strokeStyle = css("--accent");
    context.globalAlpha = 0.45;
    context.lineWidth = 2;
    context.lineCap = "round";
    context.lineJoin = "round";
    context.beginPath();
    trail.forEach(([wx, wy], index) => {
      const [x, y] = toScreen(wx, wy);
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
    context.restore();
  }

  function drawRoute() {
    if (route.length < 2) return;
    context.save();
    context.strokeStyle = css("--accent");
    context.lineWidth = 3;
    context.lineJoin = "round";
    context.setLineDash([10, 5]);
    context.beginPath();
    route.forEach((point, index) => {
      const [x, y] = toScreen(point.x, point.y);
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
    context.setLineDash([]);

    for (const point of route) {
      const [x, y] = toScreen(point.x, point.y);
      if (x < -60 || y < -40 || x > canvas.clientWidth + 60 || y > canvas.clientHeight + 40) {
        continue;
      }
      context.fillStyle = css("--accent");
      context.beginPath();
      context.arc(x, y, 5, 0, Math.PI * 2);
      context.fill();
      context.font = "650 11px 'Inter', system-ui, sans-serif";
      context.textAlign = "center";
      context.fillStyle = css("--label-text");
      context.fillText(point.ident, x, y - 10);
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
    const candidates = [10, 25, 50, 100, 250, 500, 1000, 2000, 5000];
    const target = 120;
    const metres =
      candidates.find((m) => m * view.scale >= target) ||
      candidates[candidates.length - 1];
    const pixels = metres * view.scale;
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
    dragging = { x: event.clientX, y: event.clientY };
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

  const endDrag = () => {
    dragging = null;
    canvas.style.cursor = "grab";
  };
  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);

  function syncFollowButton() {
    const button = document.getElementById("map-follow");
    if (button) button.classList.toggle("active", view.follow);
  }

  function syncGroundButton() {
    const button = document.getElementById("map-ground");
    if (button) {
      button.classList.toggle("active", groundDetailsVisible);
      button.setAttribute("aria-pressed", String(groundDetailsVisible));
    }
    for (const item of document.querySelectorAll("[data-ground-detail]")) {
      item.classList.toggle("hidden", !groundDetailsVisible);
    }
  }

  /* --------------------------------------------------------------- public */

  return {
    setChart(data) {
      chart = data;
      trail = [];
      aircraft = null;
      fit();
    },
    setAircraft(position) {
      aircraft = position;
      if (position) {
        const last = trail[trail.length - 1];
        if (!last || Math.hypot(last[0] - position.x, last[1] - position.y) > 4) {
          trail.push([position.x, position.y]);
          if (trail.length > 600) trail.shift();
        }
        if (view.follow) {
          view.centerX = position.x;
          view.centerY = position.y;
        }
      }
      draw();
    },
    setRoute(points) {
      route = points || [];
      draw();
    },
    fitRoute() {
      if (route.length < 2) return;
      const xs = route.map((point) => point.x);
      const ys = route.map((point) => point.y);
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
      trail = [];
      draw();
    },
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
      draw();
    },
    toggleGroundDetails() {
      groundDetailsVisible = !groundDetailsVisible;
      syncGroundButton();
      draw();
    },
    get following() { return view.follow; },
    resize,
    hasChart: () => chart !== null,
  };
})();

window.addEventListener("resize", () => MAP.resize());
