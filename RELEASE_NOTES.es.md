# NaviXav 1.4.10

Publicado el 2026-08-06.

## Novedades

- Los ajustes abren ahora el historial completo de versiones: todos los cambios importantes desde el inicio del seguimiento, versión por versión, con la fecha y una marca en la instalada. El historial se entrega con la aplicación y se lee sin conexión. Los textos de los cambios siguen en inglés; el marco y las secciones siguen el idioma seleccionado.
- El seguimiento de vuelo distingue ahora una simulación en pausa de una perdida: el indicador MSFS y la pastilla de seguimiento muestran «MSFS en pausa» en lugar de hacer creer que la conexión se ha cortado. Un simulador que no expone este estado sigue siendo seguido con normalidad.
- Un lápiz discreto aparece al pasar por la pista, la SID, la STAR, sus transiciones y la aproximación: abre la lista de los demás procedimientos publicados y permite cambiar la elección a posteriori, incluso cuando el motor está seguro. La lista ya no se limita a tres entradas, muestra todo lo volable desde la pista seleccionada, y «Volver a la elección automática» devuelve el mando al motor. El lápiz sigue encendido en una elección impuesta.

## Correcciones

- Un procedimiento ausente ya no ocupa el sitio de uno real. Cuando no hay ninguna STAR publicada para la pista, el motivo sustituye al guion en una sola línea más ajustada, y la línea de transición que solo repetía la ausencia desaparece. El mismo ajuste para una SID o una aproximación sin transición.
- Una SID o STAR que no está publicada para la pista seleccionada ya no se encadena: parte de otro umbral o lleva al IAF del lado opuesto del aeropuerto. NaviXav anuncia ahora una salida con guiado radar o una llegada directa, y el procedimiento descartado sigue ofreciéndose en la lista de opciones. En Brive-Souillac aterrizando por la pista 29, el plan indica BSC y luego ILS RWY 29 en lugar de una STAR no volable.
- Sin STAR, la aproximación y su transición se conectan ahora al último punto de la ruta en lugar de quedar sin enlace. Una transición publicada en ese mismo punto se reconoce y ya no se presenta como una elección incierta.
- Los puntos de aproximación que SimBrief deja en el registro de navegación sin marcarlos, como CF29 o RW11, ya no cuentan como puntos de ruta: dejan de dibujarse en la ruta y de servir para enlazar la llegada.
- Cuando una STAR sí sirve a la pista de aterrizaje pero termina en un punto que no inicia ninguna aproximación, NaviXav lo indica explícitamente en lugar de dejar que la ruptura se descubra en vuelo.
- El historial de versiones ya no se muestra permanentemente sobre la interfaz: solo se abre al pulsar su icono en los ajustes y se cierra por completo.
- La ventana de ajustes ya no tiene barra de desplazamiento horizontal: un campo invisible desbordaba todo el ancho del cuadro, fuera cual fuera el tamaño de la ventana.

## Cambios

- Correction bug et améliorations diverses.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
