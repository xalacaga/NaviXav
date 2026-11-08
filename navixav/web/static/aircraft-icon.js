"use strict";

/**
 * Silhouette de l'avion suivi, commune à la carte et au plan de roulage.
 *
 * Une seule définition : le pilote reconnaît son appareil au même dessin
 * d'une vue à l'autre. Nez vers le haut, centrée sur la position ; le tracé
 * fait 34 unités d'envergure, ramenées à l'écran par DEFAULT_SCALE.
 */
const AIRCRAFT_ICON = (() => {
  // Environ 20 pixels d'envergure : assez pour reconnaître un avion de ligne,
  // sans masquer la route ni les points qu'il survole.
  const DEFAULT_SCALE = 0.6;
  const HALO_RADIUS_PX = 15;
  let paths = null;

  // Construite à la première utilisation : Path2D n'existe que dans un vrai
  // navigateur, et le module doit rester chargeable sans lui.
  function shape() {
    if (!paths) {
      paths = {
        body: new Path2D(
          "M0,-17 C1.5,-17 2.3,-15 2.3,-12.4 L2.3,-3.4 L15.6,4.3 L15.6,6.8 "
          + "L2.3,3.1 L1.8,11 L6.7,14.6 L6.7,16.4 L0.9,15.2 L0,16.9 "
          + "L-0.9,15.2 L-6.7,16.4 L-6.7,14.6 L-1.8,11 L-2.3,3.1 L-15.6,6.8 "
          + "L-15.6,4.3 L-2.3,-3.4 L-2.3,-12.4 C-2.3,-15 -1.5,-17 0,-17 Z"
        ),
        engines: new Path2D(
          "M5.3,-2.6 h2.5 v3.4 a1.25,1.25 0 0 1 -2.5,0 Z "
          + "M-7.8,-2.6 h2.5 v3.4 a1.25,1.25 0 0 1 -2.5,0 Z"
        ),
        windscreen: new Path2D(
          "M-1.3,-13.6 Q0,-14.6 1.3,-13.6 L1.1,-12.6 Q0,-13.3 -1.1,-12.6 Z"
        ),
      };
    }
    return paths;
  }

  /**
   * Dessine l'avion en (x, y), cap en degrés vrais.
   * `halo` ajoute le disque qui le garde repérable une fois la vue éloignée.
   */
  function draw(context, x, y, headingDeg, { fill, outline, halo = false, scale = DEFAULT_SCALE }) {
    const icon = shape();
    context.save();
    context.translate(x, y);

    if (halo) {
      context.fillStyle = fill;
      context.globalAlpha = 0.18;
      context.beginPath();
      context.arc(0, 0, HALO_RADIUS_PX, 0, Math.PI * 2);
      context.fill();
      context.globalAlpha = 1;
    }

    context.rotate(((headingDeg ?? 0) * Math.PI) / 180);
    context.scale(scale, scale);

    // Ombre portée légère : l'avion se détache du fond, clair ou sombre,
    // sans cartouche.
    context.save();
    context.shadowColor = "rgba(0, 0, 0, 0.35)";
    context.shadowBlur = 4;
    context.shadowOffsetY = 1;
    context.fillStyle = fill;
    context.fill(icon.body);
    context.restore();

    context.strokeStyle = outline;
    // Épaisseur en pixels d'écran, quelle que soit l'échelle du dessin.
    context.lineWidth = 1.2 / scale;
    context.lineJoin = "round";
    context.stroke(icon.body);

    // Réacteurs et pare-brise dans la couleur du contour : ce sont eux qui
    // font lire un avion de ligne plutôt qu'une flèche.
    context.fillStyle = outline;
    context.globalAlpha = 0.85;
    context.fill(icon.engines);
    context.fill(icon.windscreen);
    context.restore();
  }

  return { draw };
})();
