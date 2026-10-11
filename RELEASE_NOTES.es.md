# NaviXav 1.7.4

Publicado el 2026-10-11.

## Novedades

- El tráfico de VATSIM, IVAO y OpenSky anticipa los virajes: un avión que viraba en la última lectura sigue virando, cada vez con menos intensidad, en el mapa y en el simulador, en lugar de seguir recto hasta la siguiente lectura.
- Análisis del aterrizaje: en la toma, NaviXav muestra la velocidad vertical registrada por MSFS, el cabeceo y el alabeo, la distancia tras el umbral y la desviación del eje de la pista realmente utilizada, el viento de cara y cruzado, los rebotes y la estabilidad de la aproximación final, con una puntuación sobre 100. El análisis se vincula al vuelo en el diario de a bordo y se puede copiar o guardar una imagen lista para compartir.
- El diario de a bordo se guarda ahora en la carpeta de datos de NaviXav en lugar de en la ventana: sobrevive a una reinstalación o a un restablecimiento de WebView2, y una tableta conectada por la red local muestra el mismo diario, en solo lectura. Los vuelos ya registrados se recuperan automáticamente en el primer inicio.
- Estadísticas del diario de a bordo: número de vuelos, horas de vuelo y distancia totales, toma y puntuación medias, mejor aterrizaje, aviones más volados y aeródromos más frecuentados. El diario completo se puede exportar en CSV para una hoja de cálculo.

## Correcciones

- El tráfico de OpenSky sigue ahora avanzando con fluidez en el mapa y en el simulador entre dos lecturas, en lugar de quedarse inmóvil y luego saltar varias millas náuticas.
- OpenSky se consulta mucho más a menudo al inicio de un vuelo, aproximadamente cada 30 segundos: la cuota pública se reparte a lo largo de un vuelo en lugar de un día entero.
- La primera carga de un aeródromo ya no tarda casi un minuto: NaviXav busca ahora el ILS y los puntos en la región del aeródromo en lugar de recorrer las de todos los aeródromos ya conocidos, y recupera las frecuencias ILS que daba por error como inexistentes, como la de la pista 23R de EGCC.

## Cambios

- Correction bug et ajout logbook.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
