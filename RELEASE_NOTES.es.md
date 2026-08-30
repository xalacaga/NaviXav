# NaviXav 1.6.0

Publicado el 2026-08-30.

## Novedades

- Controles más claros: Seguimiento de vuelo ofrece ahora un interruptor visible para desactivar o reactivar todas las alarmas de NaviXav, incluidos los mensajes MASTER WARNING y MASTER CAUTION, sin detener el seguimiento; tras una actualización, el historial de versiones se abre automáticamente en el primer reinicio y después sigue disponible bajo demanda.
- Cambio inmediato de la fuente de tráfico desde las barras de Mapa y Rodaje: los selectores VATSIM, IVAO y OpenSky permanecen sincronizados, reinician correctamente la consulta y guardan la elección localmente.
- Tráfico real OpenSky: NaviXav puede mostrar vectores de estado ADS-B públicos en un radio de 100 NM alrededor de la aeronave, con atribución de la fuente y caché respetuosa con la API; esta vista real permanece estrictamente separada de la inyección en MSFS.
- Los ajustes se reorganizan en categorías plegables adaptadas a ventanas compactas, con ruta FSLTL manual, acceso al instalador oficial de FlyByWire cuando faltan modelos e IVAO como segunda fuente pública y gratuita de tráfico de red junto a VATSIM.
- Compatibilidad exclusiva con MSFS 2024: NaviXav utiliza ahora la API SimConnect AI EX1 nativa de MSFS 2024 y rechaza una DLL antigua de MSFS 2020 al iniciar o compilar, en lugar de continuar con una conexión o funciones inadecuadas.
- Inyección de tráfico VATSIM en MSFS: NaviXav detecta automáticamente FSLTL Base Models en Community, indexa sus archivos aircraft.cfg y reglas VMR sin modificarlos, elige el modelo exacto o genérico más seguro y crea, actualiza y elimina únicamente sus propios objetos SimConnect dentro de una zona limitada alrededor del jugador. La opción está desactivada de forma predeterminada y la interfaz muestra la versión de FSLTL detectada.
- Tráfico circundante: un botón «Tráfico VATSIM» en la barra del mapa y «Tráfico del simulador» en la del rodaje muestra las demás aeronaves. En el mapa cada aeronave de la red es una silueta orientada al rumbo con su indicativo debajo, y un clic abre su ficha: tipo, frecuencia, piloto, aeródromos de salida y llegada nombrados según la base de MSFS, velocidad respecto al suelo y altitud. El plano de rodaje muestra el tráfico del simulador, el único exacto al metro. Apagado por defecto, no se realiza ninguna llamada mientras lo esté.
- Perfil vertical: el TOD utiliza ahora prioritariamente el punto de prestaciones del último OFP de SimBrief tras validar sus coordenadas con la ruta activa; se siguen aplicando los límites máximos de la STAR y la aproximación, y el cálculo geométrico de 3° toma el relevo automáticamente si el punto falta o ya no coincide con la ruta.
- Posiciones VATSIM en línea: activado en los ajustes, NaviXav marca con un punto las frecuencias del aeródromo cuyo puesto está atendido y muestra al pasar el ratón el indicativo del controlador y su frecuencia — la de la red no siempre es la que publica el simulador. El ajuste está desactivado por defecto y no se realiza ninguna llamada mientras lo esté.
- Frecuencias del aeródromo: la frecuencia de salida completa ahora la fila, y una función con varias frecuencias lo indica con un «+n» en lugar de dar a entender que solo hay una; el detalle de cada puesto, plataformas incluidas, se lee al pasar el ratón.
- Seguimiento del vuelo: un segundo indicador anuncia la frecuencia prevista en la fase actual y se marca cuando la radio ya está sintonizada. Permanece en silencio cuando el aeródromo publica varias frecuencias para la misma función, al no saberse cuál atiende la pista en servicio.
- Seguimiento del vuelo: un indicador de radio muestra la frecuencia sintonizada en COM1 y nombra el puesto correspondiente del aeródromo, incluido el rodaje por pista — para comprobar de un vistazo que se ha marcado la frecuencia indicada.
- Diagnóstico: el comando «navixav airport» enumera las frecuencias del aeródromo junto al número con el que el simulador designa cada función, y señala una función que no sabe traducir en lugar de ocultarla.
- Frecuencias del aeródromo: las tarjetas Salida y Llegada del plan de vuelo muestran ahora la cadena de radio publicada por MSFS, en el orden en que se utiliza — ATIS, DEL, GND, TWR en la salida, ATIS, APP, TWR, GND en la llegada. Si un aeródromo publica varias frecuencias para un mismo rol, las demás se ven al pasar el ratón.
- Preparación del TOD: a 50 NM, el sistema de alertas pide preparar el descenso y resalta la tarjeta TOD; a 10 NM se activa una alerta TOD inminente independiente que permanece activa hasta iniciar el descenso.
- Configuración del avión: la interfaz guiada adopta un sinóptico de cabina más claro con tarjetas equilibradas, un icono por sistema, un indicador de estado y verdaderos testigos para las luces; la interfaz clásica conserva el diseño anterior.
- Nueva interfaz guiada por el vuelo: una franja permanente destaca la fase, pista o procedimiento, la próxima acción y el módulo recomendado; las cartas de salida, llegada y aproximación se preparan en un panel y Rodaje gana espacio. El ajuste Organización de la interfaz permite recuperar al instante la interfaz clásica sin reiniciar.
- Plan de rodaje: la salida de un puesto de morro al terminal empieza por un retroceso, trazado en violeta y con trazo discontinuo corto en el plano y anunciado en la banda con su distancia y el rumbo una vez alineado; una rampa, un rodaje retomado o una llegada no muestran ninguno.
- Preparación del plan: la banda que anuncia el llenado de la caché de MSFS muestra ahora un avión que cruza el marco, con su estela, mientras dura la lectura. La espera podía llegar a varias decenas de segundos sin que nada se moviera en pantalla.
- Ficha MCDU: NaviXav recupera ahora el ZFWCG de SimBrief y muestra el centro de gravedad sin combustible junto con el número de pasajeros en la página de pesos; el ZFWCG también aparece en Dispatch.
- Elegir una fuente de tráfico basta ahora para inyectarla en MSFS: la inyección está activa por defecto y la casilla de los ajustes solo sirve para desactivarla.
- Un indicador «solo mapa» aparece en la barra del mapa cuando el tráfico se muestra sin inyectarse, y su descripción emergente da el motivo: inyección desactivada, FSLTL ausente o fuente real.
- El tráfico real ADS-B entra por fin en MSFS: el tipo de cada aeronave se resuelve desde dos registros públicos complementarios, lo que permite al fin elegirle un modelo FSLTL. Una aeronave desconocida en la primera lectura aparece en la siguiente, una vez resuelta su dirección.
- Elegir una fuente de tráfico basta ahora para inyectarla en el simulador. La casilla «Inyectar tráfico de red en MSFS» desaparece de los ajustes: el botón de la capa es el único interruptor, y lo que muestra es lo que vuela.

## Correcciones

- Las aeronaves OpenSky estacionadas siguen siendo inyectables cuando su transpondedor omite altitud barométrica, velocidad o rumbo: NaviXav usa primero la altitud geométrica y después completa únicamente los datos de tierra ausentes.
- Tráfico real OpenSky en MSFS: las aeronaves sin tipo ADS-B usan inmediatamente un modelo FSLTL genérico seguro en vez de permanecer invisibles y adoptan su modelo exacto en cuanto responde el registro ICAO24; la inyección actualiza ahora su posición cada segundo.
- Tráfico IVAO y OpenSky más fluido en MSFS: NaviXav extrapola la posición cada segundo entre lecturas de red y conserva brevemente una aeronave omitida por la fuente, evitando que desaparezca y reaparezca; se ha retirado de la interfaz la cuenta atrás fija de 15 segundos, inexacta para estas fuentes.
- Tráfico de red en puertas y calles de rodaje: cuando VATSIM no publica el estado en tierra, NaviXav lo deduce ahora de una velocidad igual o inferior a 50 kt; las aeronaves estacionadas y en rodaje se inyectan en vez de descartarse.
- Inventario de aeronaves: Actualizar detecta ahora los complementos pilotables con isAirTraffic mal configurado, como el Rafale M, y cada aeronave muestra su propia miniatura local en vez de reutilizar la imagen del avión cargado.
- Plan de rodaje de llegada: la posición real del avión y el rumbo de pista descartan ahora las salidas ya rebasadas; tras aterrizar en la 24R, NaviXav ya no propone volver en sentido contrario hacia una salida situada detrás del avión.
- Mapa: la parte en ruta del plan de vuelo conserva el color violeta, pero ahora utiliza una línea continua más legible con niveles de zoom bajos.
- Página Aircraft: las cadenas largas de equipo OACI ahora se ajustan dentro de su tarjeta en vez de desbordarse sobre el perfil vecino.
- Identidad SimConnect: las variables de texto como TITLE y ATC MODEL se declaran ahora con la unidad nula esperada por el SDK de MSFS, en lugar de la cadena literal NULL que producía silenciosamente un valor vacío.
- Página Aircraft: la identidad principal sigue ahora en directo el avión realmente cargado en MSFS y recurre automáticamente a ATC MODEL cuando un add-on deja TITLE vacío; el avión previsto en SimBrief permanece claramente separado para los pesos y prestaciones del OFP.
- Luces exteriores: NaviXav compara ahora las siete SimVars individuales con la máscara oficial LIGHT STATES de MSFS; los aviones complejos que solo publican el estado global vuelven a mostrar sus indicadores y activar correctamente las alertas, con retorno automático a la lectura anterior si la máscara no está disponible.
- Seguimiento del vuelo: el nuevo sinóptico de Configuración del avión queda ahora estrictamente aislado en su propio bloque y ya no agranda ni desordena las tarjetas de seguimiento en tiempo real.
- Se ha eliminado el modo Demo: NaviXav utiliza ahora exclusivamente el último plan de SimBrief y los datos de vuelo reales proporcionados por MSFS mediante SimConnect.
- Interfaz guiada: la franja horizontal de ruta permanece ahora solo en el menú Plan de vuelo y ya no se superpone a la franja superior en los demás módulos; la interfaz clásica conserva su visualización habitual.
- Navegación entre módulos: la franja superior guiada mide ahora la altura real de la barra de herramientas y permanece totalmente visible en vez de quedar recortada al cambiar de menú.
- Módulo Procedimientos: una fase compuesta solo de avisos, como el aterrizaje, ya no aparece completada antes del vuelo; su indicador permanece vacío y sus puntos llevan la marca de información en lugar de una confirmación verde.
- Módulo Procedimientos: una fase que el vuelo aún no ha alcanzado ya no muestra confirmaciones; en el estacionamiento, el freno puesto y las luces apagadas ya no validan los puntos de después del aterrizaje ni de la parada.
- Plan de rodaje: la entrada de salida se elige ahora entre todas las uniones de pista accesibles para aeronaves según su proximidad al umbral solicitado. En CYYZ, una salida del puesto 139 hacia la pista 23 utiliza ahora AK, A, H y Q en vez de cruzar la pista 15L para llegar a la intersección H3. Cada cruce de pista confirmado se divide en un punto de espera explícito y la ruta se rechaza si falta esa instrucción.
- Tráfico de red inyectado en MSFS: las aeronaves que el simulador descartaba en pleno vuelo ahora se detectan y se recrean en el ciclo siguiente, en lugar de desaparecer definitivamente mientras NaviXav creía seguirlas.
- El registro anota ahora cada cambio de un ciclo de inyección — aeronaves seguidas, recreadas, retiradas y descartadas — lo que hace visible una inyección que se había quedado muda.
- La etiqueta de la opción de inyección ya no menciona solo VATSIM: nombra el tráfico de red, sea cual sea la fuente elegida.
- La fuente real se llama ahora «Tráfico real · OpenSky» en las tres listas de selección, en lugar del solo nombre del proveedor, y esa etiqueta sigue por fin el idioma de la interfaz.
- Una aeronave situada en el lugar exacto de la tuya ya no se muestra ni se inyecta: casi siempre es tu propia aeronave, representada por la red a la que estás conectado. El estacionamiento vecino sigue visible y un sobrevuelo no se confunde con una superposición.
- Una aeronave que no publica indicativo recibe uno genérico y estable, en lugar de su dirección hexadecimal o de un campo vacío que el simulador mostraría como matrícula ausente.
- La inyección de tráfico tiene ahora su propio ciclo de vida: su estado puede consultarse en lugar de quedar encerrado en el servicio web, de modo que una inyección detenida ya no puede hacerse pasar por una sana.

## Cambios

- Integration trafic.

El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática.
