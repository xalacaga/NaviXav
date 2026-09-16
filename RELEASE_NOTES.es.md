# NaviXav 1.7.3

Publicado el 2026-09-16.

## Novedades

- Planes de vuelo de MSFS: NaviXav lee ahora el plan preparado en el planificador de MSFS, para los pilotos que no usan SimBrief. Un ajuste «Origen del plan de vuelo» elige entre SimBrief y un plan de MSFS (.PLN); el vuelo cargado en MSFS se lee automáticamente y un botón «Abrir un archivo .PLN» permite elegir otro. Aeropuertos, ruta, aerovías, SID, STAR y pistas previstas se usan como un OFP de SimBrief; la meteorología se toma en directo. El primer inicio ofrece esta elección y ya no exige una cuenta SimBrief.
- Diagnóstico: el comando «navixav probe-fms» registra lo que el avión cargado expone de su FMS — el plan de vuelo del simulador por SimConnect y, en el Fenix A320, el plan del FMGC publicado por la pasarela local del EFB — en un informe aparte, de solo lectura.
- Fenix A320: NaviXav lee el plan de vuelo activo del FMGC a través de la pasarela local del EFB Fenix, solo lectura. En el mapa, la ruta del FMS se dibuja en amarillo solo donde se aparta de la ruta NaviXav (DIRECT TO, nueva STAR), con su entrada en la leyenda, y el plan alternativo se muestra a petición; el T/C y el T/D del FMGC sustituyen a las estimaciones (fuente «FMGC del avión»); en vuelo la fase del FMGC sustituye a la deducida de la telemetría. El seguimiento del vuelo gana el punto activo del FMGC, la ETA y las masas FMS, más dos alertas: límite de velocidad 250 kt y punto de deceleración. La ficha MCDU se abre con una verificación línea a línea de lo que contiene el FMGC (FROM/TO, alternativo, número de vuelo, nivel, pistas, SID, ruta, STAR, aproximación, ZFW, velocidades de despegue) y termina con un espejo de los MCDU 1 y 2. El libro de vuelo conserva el número de vuelo y la ETA del FMGC.
- FlyByWire y PMDG: el espejo del MCDU funciona también en el A32NX/A380X (pantallas leídas por SimBridge, fase FMGC por la variable del avión) y en los PMDG 737/777 (pantallas del CDU difundidas por el SDK una vez activado EnableCDUBroadcast). Solo lectura, con el origen mostrado en el espejo; el comando «navixav probe-fms» indica qué canal responde.

## Correcciones

- Mapa: la marca TOC ya no sigue al avión. Se fija donde el ascenso termina realmente, incluso si ATC ha asignado un nivel distinto del planificado, y solo se recalcula si el ascenso se reanuda (step climb). Reiniciado en vuelo, NaviXav ya no coloca el TOC bajo el avión: toma el del perfil SimBrief o no lo muestra. Con un plan de MSFS, el vuelo se reconoce por su contenido y no por la fecha del archivo, que MSFS reescribe en cada carga: el registro de vuelo y el TOC recuperado sobreviven a un reinicio.
- Alertas: se elimina la alerta «Apertura peligrosa detectada», tomada de la señal de seguridad de MSFS. Se activaba con puertas o trampillas que el piloto abre a propósito en tierra.

## Cambios

- News.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
