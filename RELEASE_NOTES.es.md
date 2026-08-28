# NaviXav 1.5.0

Publicado el 2026-08-28.

## Novedades

- Al hacer clic en la foto de una aeronave, ahora se abre una vista ampliada dentro de NaviXav; se cierra con su botón, un clic fuera o la tecla Escape.
- La ficha y el inventario Aircraft muestran ahora una foto real con licencia libre junto al nombre de cada familia de aeronaves compatible; los aviones adicionales instalados en Community utilizan automáticamente su miniatura local cuando está disponible.
- Cuando una carta ChartFox no se puede integrar, NaviXav ofrece ahora el catálogo nacional oficial en la misma ficha cuando el aeropuerto está cubierto.
- El seguimiento del vuelo estima ahora el Top of Climb a partir del nivel de crucero, la velocidad vertical y la velocidad respecto al suelo; los puntos calculados TOC y TOD aparecen como puntos distintos en el mapa.
- ChartFox ahora se puede vincular desde Ajustes con una cuenta VATSIM; sus cartas bajo demanda se ofrecen como fuente opcional para los aeropuertos de salida y llegada.
- El menú Charts indica ahora que se necesita una cuenta de ChartFox/VATSIM para acceder a las cartas AIRAC de ChartFox y ofrece un enlace directo a Ajustes.

## Correcciones

- Las fotos de las aeronaves ya no quedan ocultas detrás de la ficha del tipo OACI en la tarjeta y el inventario Aircraft.
- Al abrir el PDF de un aeropuerto en Charts, el otro aeropuerto ya no queda debajo del documento: Salida y Llegada permanecen lado a lado en pantallas anchas, y la ficha no abierta aparece primero en ventanas compactas.
- La indicación «solo simulación» de ChartFox en Ajustes ahora sigue el idioma de la interfaz.
- Las cartas ChartFox cuya fuente prohíbe la integración ya no muestran una zona en blanco: NaviXav explica la restricción y permite abrirlas directamente en ChartFox.
- Los puntos calculados TOC y TOD usan ahora colores propios magenta y rojo, distintos de todos los puntos de la ruta.
- Se han retirado los fondos de mapa CartoDB Positron y Dark Matter: su servicio gratuito ahora marca cada tesela con la mención «API key required». La elección es entre OpenStreetMap Standard y OpenTopoMap, y un ajuste que ha dejado de ser válido vuelve automáticamente a OpenStreetMap.
- El briefing meteorológico ya no aparece parcialmente en francés cuando la interfaz está en otro idioma: los puntos de atención y los fenómenos METAR siguen ahora el idioma seleccionado.
- Las tormentas sin precipitación observada ahora se señalan: los grupos TS, VCTS y VCSH eran ignorados al decodificar el METAR. Además, el «PO» de «TEMPO» ya no se lee como remolinos de polvo.
- Las SID aparecen por fin en el mapa: su trazado, sus puntos y sus restricciones publicadas faltaban en cuanto un mismo procedimiento servía a dos cabeceras, lo que ocurre en casi todos los grandes aeropuertos. La salida quedaba reducida a una línea recta hasta el primer punto en ruta. Las STAR recuperan además su tramo final, propio de la pista de aterrizaje. La base de navegación se vuelve a importar automáticamente del simulador en el siguiente arranque.

## Cambios

- Reformuler l'annonce ChartFox de la 1.5.0.
- Ajout fonctionnalite et correction bugs.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
