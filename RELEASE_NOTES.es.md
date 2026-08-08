# NaviXav 1.4.16

Publicado el 2026-08-08.

## Correcciones

- Los aerofrenos de los Fenix A319/A320/A321 ahora muestran ARMED correctamente aunque el nombre del avión en SimBrief sea genérico.
- El Top of Descent es ahora un punto fijo de la ruta, calculado a partir del nivel de crucero: disminuye hasta cero y después se indica como superado. Antes podía quedarse congelado durante un descenso a 3° o incluso aumentar cuando el descenso se iniciaba demasiado pronto.
- La desviación respecto al perfil de descenso se sigue indicando durante un nivel intermedio por debajo del nivel de crucero. Antes desaparecía en cuanto la velocidad vertical volvía a cero, justo cuando el avión estaba muy por debajo del perfil.
- El Top of Descent tiene ahora en cuenta los techos de altitud publicados de la STAR y de la aproximación, y lee la altitud en la atmósfera estándar como un nivel de vuelo.
- La velocidad vertical necesaria para la siguiente restricción se compara ahora con la altitud indicada, la única comparable con una restricción publicada.

## Cambios

- Correction bug TOD.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
