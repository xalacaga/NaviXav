# NaviXav 1.8.0

Publicado el 2026-11-08.

## Novedades

- Avisos de voz: NaviXav anuncia las alarmas MASTER CAUTION y MASTER WARNING, el inicio de descenso a 50, 10 y 0 NM y las instrucciones de rodaje como los puntos de espera antes de pista; se activan en Ajustes o desde Seguimiento del vuelo.
- Seguimiento del combustible: Seguimiento del vuelo compara el combustible a bordo con el OFP de SimBrief en su posición sobre la ruta, estima el combustible en destino (EFOB) y avisa cuando baja de la reserva final más el combustible al alternativo.
- Registro de diagnóstico: cada pérdida y cada recuperación de la conexión con MSFS se registran ahora con su motivo, la duración de la lectura fallida y la de la interrupción, para facilitar el análisis de los problemas de conexión.
- Mapa y plano de rodaje: su avión se muestra ahora con la misma silueta de avión de línea en ambas vistas, orientada al rumbo, con motores, parabrisas y una sombra suave, en lugar de la flecha.
- Voz NaviXav: los avisos los dicen voces neuronales de alta calidad incluidas con la aplicación, en los ocho idiomas, totalmente sin conexión y sin nada que instalar; los términos aeronáuticos se mantienen en inglés y hay tres voces en inglés.
- SIGMET en el mapa: los SIGMET vigentes cerca de la ruta se dibujan como zonas de color con sus niveles, los que cruza la ruta se resaltan, la pestaña de meteorología los enumera con su texto completo y una alarma avisa cuando el avión va a entrar en uno a su nivel.
- Aproximación estabilizada: por debajo de la puerta (1000 ft IMC, 500 ft VMC), NaviXav comprueba tren, flaps, velocidad, régimen de descenso y las agujas ILS, anuncia «Estabilizado» cuando todo está en orden y, si no, activa una alarma de aproximación no estabilizada; una casilla del seguimiento de vuelo muestra los criterios en fallo.
- Panel de MSFS 1.2.3: el panel del simulador muestra las alarmas activas, coloreadas según su gravedad, y el estado de estabilización en final; actualízalo desde los ajustes de NaviXav.

## Correcciones

- Un avión que no publica su cantidad de combustible ya no muestra 0 kg ni dispara un falso MASTER WARNING de combustible por debajo de la reserva.
- Guardar los ajustes vuelve a ser inmediato: las miniaturas de la lista de aviones instalados ya no releen cada una miles de archivos de Community ni retienen el resto de la aplicación.
- Los avisos meteorológicos «en condiciones LIFR» y «meteorología no disponible» ya no aparecen en francés cuando se elige otro idioma de interfaz.

## Cambios

- Mettre en cache la lecture des aircraft.cfg de Community.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
