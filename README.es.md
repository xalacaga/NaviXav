# NaviXav

**Sitio web oficial:** [navixav.fr](https://navixav.fr/en)

**Documentación:** [Français](README.fr.md) · [English](README.md) ·
[Deutsch](README.de.md) · Español · [Italiano](README.it.md) ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav es una aplicación local de asistencia al vuelo IFR para Microsoft
Flight Simulator. Recupera el último plan de vuelo de SimBrief, completa la
información terminal con los datos del simulador y lo presenta todo en una
interfaz pensada para la preparación del vuelo y la introducción en el MCDU.

La aplicación dispone de su propia ventana de Windows. Su interfaz se muestra
mediante Microsoft WebView2 y solo se comunica con un servicio local vinculado a
`127.0.0.1`. Solo se abre un navegador externo cuando el usuario pulsa **Crear
un plan SimBrief** para abrir el editor oficial. Los ajustes, la base de
navegación y las cachés permanecen en el ordenador.

La ventana es totalmente redimensionable. La interfaz reorganiza sus paneles,
controles, pestañas y la altura del mapa según el espacio disponible, hasta un
tamaño mínimo de 720 × 560 píxeles.

> NaviXav está destinado únicamente a la simulación de vuelo. La información
> mostrada debe contrastarse con las publicaciones oficiales y las
> instrucciones ATC aplicables.

## Funcionalidades

### Plan de vuelo SimBrief

- recuperación automática del último OFP al iniciar;
- compatibilidad con el Pilot ID o el nombre de usuario de SimBrief;
- visualización de la ruta completa, del origen al destino;
- resalte del siguiente punto de ruta según la posición real del avión, con
  atenuación de los puntos ya sobrevolados;
- masas, combustible, tiempo de vuelo, alternativo y datos de despacho;
- información de la aeronave, matrícula y equipamiento declarado.

### Meteorología del vuelo

- METAR y TAF esenciales para salida, llegada y alternativo;
- viento y temperatura de crucero procedentes del OFP de SimBrief;
- en modo **METAR en directo**, actualización automática cada cinco minutos
  desde aviationweather.gov y botón de actualización inmediata;
- representación gráfica del tiempo, viento, visibilidad y techo sin cambiar
  automáticamente la pista ni los procedimientos del plan.

### Preparación IFR

NaviXav completa y presenta:

- la pista de salida y la pista de llegada;
- la SID y su transición;
- la STAR y su transición;
- la aproximación y su VIA;
- la frecuencia y el identificador ILS;
- las restricciones de altitud y velocidad;
- la altitud de transición y el nivel de transición;
- la altitud de interceptación de la aproximación;
- la altitud de aproximación frustrada;
- la justificación y el nivel de confianza de cada elección.

Los bloques **Salida · Ruta · Llegada** pueden plegarse para liberar espacio en
la interfaz.

### Seguimiento del vuelo

La pestaña **Seguimiento del vuelo** utiliza la posición MSFS en tiempo real
para mostrar:

- la fase de vuelo detectada automáticamente;
- la velocidad respecto al suelo (GS) y la velocidad indicada (IAS)
  proporcionadas por MSFS;
- el siguiente punto y su distancia;
- la desviación lateral respecto al segmento activo;
- la distancia restante;
- la siguiente restricción de altitud o velocidad;
- el régimen vertical necesario para alcanzar esa restricción;
- el Top of Descent y un régimen de descenso indicativo con pendiente de 3°;
- la desviación respecto al perfil vertical previsto.

Tras el aterrizaje, el diario local guarda un resumen conciso y una cronología
limitada de eventos: fases del vuelo, pista de despegue y aterrizaje con el
viento observado, y cambios estables del tren, flaps, spoilers, freno de
estacionamiento, luces y modos del piloto automático. Los eventos se almacenan
como datos y se reproducen en el idioma seleccionado en ese momento. Todos los
resúmenes pueden purgarse desde la interfaz y no se envían datos de vuelo a
servicios externos.

Para flaps, spoilers y freno de estacionamiento, NaviXav compara las SimVars
oficiales de palanca, posición efectiva, superficie e indicador de cabina. La
configuración del avión y los eventos de vuelo siguen actualizándose aunque un
avión de terceros deje congelado uno de los valores estándar de MSFS.
Un adaptador específico para los Fenix A319/A320/A321 lee directamente los tres
mandos de cabina, de modo que los cambios de flaps, aerofrenos y freno de
estacionamiento se notifican incluso con motores y sistemas hidráulicos apagados.

### Ficha MCDU

La pestaña **Ficha MCDU** adapta sus páginas al tipo de avión: MCDU de Airbus,
CDU de Boeing o FMS genérico para otros aparatos. No ofrece valores de
rendimiento de despegue que no puedan automatizarse:

- `FROM/TO`, número de vuelo y alternativo;
- Cost Index y nivel de crucero;
- ZFW, combustible de bloque, rodaje, trayecto y reservas;
- pista, SID, transición y altitud de transición;
- ruta `VIA/TO`;
- STAR, transición, aproximación y VIA;
- QNH, temperatura, viento, frecuencia ILS y rumbo final;
- mínimos RADIO o BARO y RVR.

### Conexión directa con MSFS

NaviXav utiliza SimConnect para:

- detectar la presencia del simulador;
- mostrar un indicador verde o rojo en la barra superior;
- seguir la posición del avión en tiempo real;
- leer la altitud, la altura sobre el suelo, el rumbo, la velocidad respecto al
  suelo y la velocidad vertical;
- obtener aeropuertos, pistas, procedimientos, puntos de notificación y
  radioayudas;
- construir progresivamente una base local en `data/navixav.sqlite`.

El simulador debe estar iniciado con un vuelo cargado para obtener nuevos
datos. La información ya almacenada en caché permanece disponible sin conexión.

Cuando el registro de navegación detallado de SimBrief incluye coordenadas
validadas, NaviXav las usa de inmediato para dibujar la ruta y solo consulta
MSFS Facilities para las posiciones que faltan. Los enlaces de procedimientos
publicados también evitan consultas de posición innecesarias. Así se acelera la
primera carga del plan sin perder las comprobaciones del corredor ni la caché
local de MSFS como alternativa.

### Mapa

El mapa incluye:

- un fondo OpenStreetMap;
- la ruta SimBrief dibujada con sus puntos;
- colores distintos para la SID, el tramo en ruta, la STAR y la aproximación;
- las pistas y la pista seleccionada;
- la posición y el rumbo del avión;
- una traza del desplazamiento;
- un modo de seguimiento automático;
- el zoom, el desplazamiento y el ajuste al aeródromo o a la ruta.

### Rodaje en tierra

La pestaña **Rodaje** ofrece un plano de aeródromo independiente del mapa de
vuelo y construido únicamente con las instalaciones nativas de MSFS:

- el lienzo ocupa toda la zona disponible, incluso en ventanas compactas;
- un fondo aeronáutico oscuro con cuadrícula métrica y flecha norte aporta
  escala y orientación sin el ruido de un mapa de carreteras;
- pistas, calles principales, puestos y avión tienen prioridad visual;
- las calles de rodaje con nombre permanecen visibles aunque MSFS las
  clasifique como segmentos genéricos `path`; solo los enlaces secundarios sin
  nombre y los accesos a puestos se ocultan por defecto, y el botón
  **Secundarias** los muestra bajo demanda;
- en salida, si el avión está en tierra a menos de 180 m de un puesto, NaviXav
  propone automáticamente la ruta hasta la pista seleccionada;
- al pulsar otro puesto se sustituye inmediatamente la propuesta; en llegada,
  el puesto de destino sigue siendo una elección manual;
- se muestran la parte recorrida y pendiente, los nombres útiles, puntos de
  espera, próxima maniobra y distancia restante;
- tras una desviación, la ruta se recalcula desde la posición real del avión.

Los caminos de estacionamiento de SimConnect solo vinculan los puestos con la
red y nunca pueden convertirse en atajos artificiales a través de las pistas.

### Cartas AIS nacionales oficiales

NaviXav consulta directamente las publicaciones de las autoridades nacionales,
sin pasar por EUROCONTROL/EAD:

- Francia: SIA eAIP (`LF`);
- España y Canarias: AIP de ENAIRE (`LE`, `GC`, `GE`);
- Países Bajos: LVNL eAIP (`EH`);
- Suecia: LFV eAIP (`ES`);
- Bélgica y Luxemburgo: skeyes eAIP (`EB`, `EL`);
- Austria: Austro Control eAIP (`LO`);
- Reino Unido: NATS eAIP (`EG`);
- Estados Unidos y territorios cubiertos: FAA d-TPP.

Para estos aeródromos, NaviXav puede:

- presentar en la pestaña **Cartas oficiales** todos los PDF de la salida y de
  la llegada, clasificados por tipo;
- abrir cada documento dentro de la interfaz o por separado;
- seleccionar por omisión la SID, la STAR o la aproximación correspondiente al
  vuelo actual;
- localizar automáticamente la carta de aproximación correspondiente a la pista
  y al tipo de aproximación elegidos;
- descargar bajo demanda únicamente los PDF consultados;
- conservar la publicación en la caché AIRAC local;
- mostrar la carta oficial en la ficha MCDU;
- extraer los mínimos ILS CAT I del SIA cuando se reconoce el formato;
- proponer la DA, la DH y la RVR antes de su validación.

Los valores extraídos nunca se aplican de forma silenciosa: deben validarse en
la interfaz. El botón **Capa oficial** solo se ofrece para un documento con
georreferenciación validada. Sigue la elección de carta: el PDF de la salida
solo puede superponerse sobre la salida, y el de la llegada sobre la llegada.
Esta regla es idéntica para todas las fuentes.

Un país solo se añade a la lista automática tras validar un acceso directo y
estable a sus PDF oficiales. Por tanto, una fuente ausente nunca se sustituye
en silencio por un agregador de terceros.

## Requisitos

- Windows 10 o Windows 11 de 64 bits;
- Microsoft WebView2 Runtime, instalado automáticamente por el instalador;
- Microsoft Flight Simulator para los datos y el seguimiento en tiempo real;
- una cuenta SimBrief con un OFP generado;
- una conexión a Internet para SimBrief, el fondo cartográfico y las
  publicaciones AIS nacionales o de la FAA.

El instalador incluye Python, las bibliotecas, pywebview, el conector
SimConnect autónomo de NaviXav y el bootstrapper de Microsoft WebView2 firmado.
Ninguna de estas herramientas debe instalarse por separado. MSFS no es
obligatorio para probar el modo Demo o consultar los datos ya guardados.

NaviXav nunca instala ni reinstala SimConnect en Windows. La aplicación
incorpora una copia privada de la DLL moderna en su propia carpeta. Si el
equipo ya dispone de SimConnect, su instalación, su versión y sus ajustes no se
sustituyen ni se modifican. Esta DLL privada dialoga con el servicio SimConnect
de MSFS: solo el simulador debe estar instalado e iniciado para recibir los
datos en directo.

### Idiomas de la interfaz

El idioma se elige en **Ajustes**, se aplica de inmediato y queda memorizado en
el ordenador. NaviXav ofrece las interfaces en francés, inglés, alemán,
español, italiano, portugués, neerlandés y polaco. Las abreviaturas
aeronáuticas, los identificadores de procedimientos, los METAR y los valores
MCDU se mantienen deliberadamente en su notación internacional.

## Instalación rápida en Windows

1. Descargar el archivo `NaviXav-Setup-<versión>.exe` de la última
   [Release de GitHub](https://github.com/xalacaga/NaviXav/releases/latest).
2. Ejecutar el instalador.
3. Revisar la página de comprobación de requisitos.
4. Mantener o cambiar la carpeta propuesta y hacer clic en **Instalar**.
5. Iniciar NaviXav desde el menú Inicio o el acceso directo opcional del
   escritorio.

El instalador comprueba Microsoft WebView2 y lo instala automáticamente si
falta. La instalación se realiza para el usuario actual y normalmente no
requiere derechos de administrador.

También está disponible un archivo portable: extraer
`NaviXav-<versión>-windows-x64-portable.zip` y ejecutar `NaviXav.exe`. En un
equipo sin WebView2, utilizar primero el instalador completo.

### Desde el código fuente

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

En el primer inicio, el script:

1. busca Python;
2. crea el entorno virtual `.venv`;
3. instala NaviXav y sus dependencias;
4. inicia el servicio local privado;
5. abre la interfaz en la ventana de NaviXav.

Los inicios siguientes reutilizan el entorno ya instalado.

### Construir una distribución

Desde PowerShell, en la carpeta del proyecto:

```powershell
.\scripts\build_windows.ps1
```

El script:

1. comprueba Windows de 64 bits, Python y el SDK de SimConnect;
2. instala las herramientas de construcción que falten;
3. descarga el bootstrapper oficial de WebView2 y verifica su firma de
   Microsoft;
4. ejecuta las pruebas excluyendo la integración MSFS en directo;
5. genera el instalador, el archivo portable y sus sumas SHA-256 en `release\`.

El SDK de SimConnect mencionado en el paso 1 solo concierne al equipo que
construye NaviXav. No se instala en los equipos de los usuarios.

### Archivos de distribución

Tras una construcción correcta:

| Archivo | Uso |
|---|---|
| `release\NaviXav-Setup-<versión>.exe` | instalador de Windows recomendado |
| `release\NaviXav-<versión>-windows-x64-portable.zip` | versión portable |
| `release\*.sha256` | huellas de control de los archivos distribuidos |

La carpeta `release\` está deliberadamente excluida de Git. Los ejecutables son
artefactos de construcción que deben publicarse en una Release de GitHub, no
fuentes que deban versionarse.

## Instalación manual

Desde PowerShell, en la carpeta del proyecto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m navixav.desktop
```

Este comando abre la ventana de NaviXav. Para un diagnóstico del servicio local
sin ventana:

```powershell
.\.venv\Scripts\python.exe -m navixav.desktop --no-open
```

El servicio queda entonces accesible únicamente en `http://127.0.0.1:8765`.

## Configuración

La configuración habitual se realiza desde el botón **Ajustes** de la interfaz.

### Cuenta SimBrief

Rellenar uno de los dos campos:

- **Pilot ID de SimBrief**: identificador numérico que aparece en los ajustes
  de la cuenta SimBrief;
- **Nombre de usuario de SimBrief**: alias de la cuenta.

Se recomienda el Pilot ID. Tras guardar, NaviXav recupera de inmediato el
último OFP disponible. En cada nuevo inicio, ese último plan se carga
automáticamente.

### Ajustes disponibles

La interfaz permite configurar además:

- la fuente METAR;
- el orden de preferencia de las aproximaciones;
- la componente máxima de viento en cola;
- la componente máxima de viento cruzado;
- la longitud mínima de pista;
- la apariencia de la interfaz: automática, clara u oscura;
- la carpeta Community de MSFS utilizada para inventariar los procedimientos por aeronave;
- la capacidad RNP de la aeronave.

En la versión instalada, los valores se conservan en
`%LOCALAPPDATA%\NaviXav\user_settings.json`.

### Procedimientos por aeronave

El módulo **Procedimientos** asocia la aeronave cargada en MSFS con la base local
de NaviXav. Presenta los procedimientos normales por fase de vuelo, su progreso
y los elementos confirmados automáticamente por SimConnect. La nota de la fuente
sigue el idioma elegido. La cobertura se consulta en la sección contraída
**Procedimientos por aeronave** de los ajustes.

## Primer uso

1. Generar un plan de vuelo en SimBrief.
2. Iniciar Microsoft Flight Simulator y cargar un vuelo.
3. Iniciar NaviXav desde el menú Inicio, o con `NaviXav.bat` en modo
   desarrollo.
4. Abrir **Ajustes** y guardar el Pilot ID de SimBrief.
5. Esperar la carga automática del último OFP.
6. Comprobar el indicador **MSFS conectado** arriba a la derecha.
7. Revisar las elecciones de pista, SID, STAR y aproximación.
8. Consultar las restricciones y la carta oficial.
9. Validar los mínimos antes de copiarlos en el MCDU.

El botón **Completar el plan** permite recuperar de nuevo el último OFP tras
generar o modificar un vuelo en SimBrief.

## Uso del mapa

- **Fondo del mapa**: muestra u oculta OpenStreetMap.
- **Rodaje**: abre el plano de suelo dedicado; **Secundarias** muestra u oculta
  los accesos y calles de menor prioridad.
- **Capa oficial**: aparece únicamente para la carta georreferenciada del
  aeródromo mostrado y ajusta su opacidad.
- **Ruta completa**: encuadra toda la ruta del vuelo.
- **Seguir**: mantiene el avión centrado.
- **Ajustar**: encuadra el aeropuerto seleccionado.
- **+ / −**: modifica el nivel de zoom.
- **Rueda**: amplía bajo el puntero.
- **Arrastrar**: desplaza el mapa.

Los botones de aeropuerto permiten pasar rápidamente del aeródromo de salida al
de llegada.

## Ventana y visualización adaptable

### Acceso desde teléfono y tableta en la red local

Activa **Acceso para teléfono y tableta** en **Ajustes**, guarda y reinicia
NaviXav. Abre la dirección protegida mostrada en el PC desde un dispositivo
conectado al mismo Wi-Fi. La interfaz móvil ofrece seguimiento en tiempo real,
mapa, restricciones, datos del MCDU, del avión y cartas oficiales. Los ajustes,
el cierre y las actualizaciones quedan reservados al PC. Si Windows lo solicita,
autoriza NaviXav solo en redes privadas.

En pantallas remotas de menos de 760 px, el estado de conexión con MSFS se
reduce a su punto de color para que `MSFS connected` no desborde la barra de
herramientas. La etiqueta traducida sigue disponible para las tecnologías de
asistencia. La barra móvil también ofrece su propio selector de idioma sin
exponer los ajustes reservados al PC.

NaviXav adapta automáticamente su interfaz al redimensionar:

- por encima de 1100 px, la navegación entre módulos pasa a una barra flotante
  compacta en la parte superior izquierda, con un indicador activo claro; la entrada breve
  **Plan de vuelo** abre Salida, Ruta y Llegada como un módulo exclusivo normal,
  sin control para contraer, está seleccionada por defecto y cada opción lleva directamente a su contenido.
  El área principal usa todo el ancho restante y un PDF oficial abierto ocupa
  toda la cuadrícula. Las ventanas más estrechas conservan el selector
  horizontal y los móviles su panel lateral accesible. Cuando una alerta global
  añade una segunda fila al encabezado, la barra de escritorio baja
  automáticamente y vuelve a subir al desaparecer la alerta;
- por encima de 1100 px, las tarjetas Salida, Ruta y Llegada pueden mostrarse
  una junto a otra;
- por debajo de 1100 px, estas tarjetas pasan a una sola columna;
- por debajo de 980 px, la barra de herramientas y los controles del mapa
  ocupan todo el ancho disponible;
- por debajo de 760 px, las pestañas se vuelven desplazables, los botones se
  redistribuyen y las tablas siguen consultándose en horizontal;
- por debajo de 520 px, las estadísticas y los paneles complejos pasan a
  columna.

El mapa detecta cada cambio de tamaño de la ventana y recalcula su lienzo de
inmediato. El tamaño mínimo de la ventana nativa es de 720 × 560 píxeles.

## Modo Demo

El conmutador **Demo** carga un vuelo de ejemplo y simula un desplazamiento en
tierra. Permite descubrir la interfaz sin cuenta SimBrief ni simulador.

El modo Demo siempre está desactivado al inicio para que NaviXav dé prioridad
al último plan de SimBrief.

## Cierre de la aplicación

Utilizar el botón **Salir** de la barra superior. NaviXav detiene el servidor
correctamente, cierra la ventana y la conexión SimConnect, y libera el puerto
`8765`. Cerrar directamente la ventana produce el mismo resultado.

En modo de diagnóstico `--no-open`, la combinación `Ctrl+C` en la consola
también realiza un cierre normal.

## Opciones de inicio

El lanzador de Windows acepta las siguientes opciones:

```powershell
.\NaviXav.bat --port 9000
.\NaviXav.bat --no-open
```

- `--port` cambia el puerto local;
- `--no-open` inicia únicamente el servicio local, para diagnóstico.

La dirección de escucha permanece deliberadamente fijada en `127.0.0.1`.

## Comandos complementarios

NaviXav también puede utilizarse desde PowerShell:

```powershell
# Mostrar el último plan de SimBrief
.\.venv\Scripts\navixav.exe plan

# Generar una ficha MCDU en texto
.\.venv\Scripts\navixav.exe plan --mcdu

# Producir una salida JSON
.\.venv\Scripts\navixav.exe plan --json

# Importar aeropuertos desde MSFS
.\.venv\Scripts\navixav.exe import LFBO LFPO

# Examinar la base local
.\.venv\Scripts\navixav.exe navdata

# Mostrar la información de un aeropuerto
.\.venv\Scripts\navixav.exe airport LFBO --runway 32R
```

## Datos locales

NaviXav utiliza las siguientes ubicaciones:

| Ubicación | Contenido |
|---|---|
| `%LOCALAPPDATA%\NaviXav\user_settings.json` | configuración de la versión instalada |
| `%LOCALAPPDATA%\NaviXav\navixav.sqlite` | base de navegación construida desde MSFS |
| `%LOCALAPPDATA%\NaviXav\cache\` | cartas AIS nacionales y de la FAA en caché |
| `%LOCALAPPDATA%\NaviXav\webview\` | almacenamiento local de la ventana WebView2 |
| `%LOCALAPPDATA%\NaviXav\logs\navixav.log` | registro de la versión instalada |
| `data\` y `.venv\` | datos y entorno del modo desarrollo |

Estos datos locales, los secretos y las cachés no están destinados a
versionarse.

El registro anota los inicios y cierres, los errores, las llamadas API lentas,
los tiempos de recuperación de SimBrief, los tiempos de completado MSFS y los
llenados de caché. No anota ni el Pilot ID, ni el nombre de usuario, ni la ruta
completa. Su tamaño está limitado a 2 MB, conservando cinco versiones
anteriores (`navixav.log.1` a `navixav.log.5`).

En el primer acceso a un aeródromo o a un procedimiento, la interfaz advierte
de que la caché MSFS se está llenando y de que la operación puede durar varias
decenas de segundos. Los accesos siguientes reutilizan los datos locales.

## Versionado con Git

El repositorio fuente está previsto para alojarse en:
`https://github.com/xalacaga/NaviXav.git`.

El archivo `.gitignore` excluye en particular:

- `.env`, los ajustes de usuario y las bases locales;
- `.claude/`, `CLAUDE.md`, `.codex/`, `AGENTS.md` y `CODEX.md`;
- los datos de Graphify y `graphify-out/`;
- los entornos Python, las cachés de pruebas y las salidas de construcción;
- `dist\`, `build\` y `release\`.

Las memorias de Claude/Codex pueden mantenerse localmente sin publicarse en el
repositorio Git.

### Actualizaciones automáticas

Al iniciarse, NaviXav consulta únicamente la última Release pública del
repositorio `xalacaga/NaviXav`. Si su versión es superior a la instalada,
aparece un botón **Actualización** en la barra superior. La instalación solo
comienza tras la confirmación del usuario.

El instalador se descarga en `%LOCALAPPDATA%\NaviXav\updates\` y después se
compara su huella SHA-256 con la publicada por GitHub. Si la huella falta o
difiere, el archivo se elimina y nunca se ejecuta. Una avería de GitHub o de
Internet no bloquea ni el inicio ni las funciones de vuelo.

El repositorio es público en lectura. Un usuario puede consultar el código y
descargar las Releases sin cuenta de GitHub, pero solo los colaboradores
autorizados pueden escribir en el repositorio.

### Versión y notas de Release

La versión sigue el formato semántico `MAYOR.MENOR.CORRECCIÓN`. Los mensajes de
commit convencionales determinan automáticamente el siguiente nivel:

- `feat:` produce normalmente una versión menor;
- `fix:` produce una versión de corrección;
- `BREAKING CHANGE` o `!:` produce una versión mayor;
- los demás cambios producen una versión de corrección.

Preparar localmente la versión y sus notas:

```powershell
.\scripts\prepare_release.ps1 -Bump auto
```

Publicar el instalador, el archivo portable, sus huellas y las notas en una
Release de GitHub:

```powershell
.\scripts\publish_release.ps1 -Bump auto
```

El segundo script exige un repositorio limpio y GitHub CLI autenticado. Ejecuta
las pruebas, construye los entregables, crea el commit y la etiqueta de
versión, envía `main` y la etiqueta, y luego crea la Release de GitHub.
`CHANGELOG.md` conserva el historial y `RELEASE_NOTES.md` contiene las notas de
la versión actual.

## Resolución de problemas

### El puerto 8765 ya está en uso

Probablemente sigue abierta una instancia de NaviXav. Cerrar su ventana o hacer
clic en **Salir** en la interfaz. El ejecutable detecta una instancia
existente; si otra aplicación ocupa el 8765, elige automáticamente un puerto
libre entre 8766 y 8775.

Para identificar el proceso:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

También es posible iniciar la aplicación en otro puerto:

```powershell
.\NaviXav.bat --port 9000
```

### La ventana de NaviXav no se abre

- volver a ejecutar el instalador completo para que compruebe WebView2;
- comprobar que Windows y Microsoft Edge WebView2 Runtime están actualizados;
- consultar `%LOCALAPPDATA%\NaviXav\logs\navixav.log`;
- comprobar que un antivirus no bloquea `NaviXav.exe` ni los procesos
  `msedgewebview2.exe`.

El archivo portable no puede instalar WebView2 por sí mismo. En un equipo que
no posea este componente, utilizar `NaviXav-Setup-<versión>.exe`.

### El indicador MSFS permanece rojo

- comprobar que el simulador está iniciado;
- cargar completamente un vuelo;
- esperar unos segundos y hacer clic en el indicador;
- volver a ejecutar el instalador si la copia privada de `SimConnect.dll`
  entregada con NaviXav ha sido eliminada o puesta en cuarentena por un
  antivirus.

### No se carga ningún plan de SimBrief

- comprobar el Pilot ID o el nombre de usuario en **Ajustes**;
- generar un OFP en SimBrief antes de reintentar la recuperación;
- comprobar la conexión a Internet.

### Una carta oficial no está disponible

- comprobar que el prefijo OACI está cubierto por SIA, ENAIRE, LVNL, LFV,
  skeyes, Austro Control, NATS o FAA;
- comprobar la conexión a Internet;
- confirmar que se han determinado la pista y la aproximación;
- utilizar la introducción manual de los mínimos si la extracción no está
  disponible.

## Limitaciones actuales

- el procedimiento realmente autorizado puede diferir del plan según el ATIS,
  la meteorología y las instrucciones ATC;
- los mínimos dependen de la categoría del avión, de su equipamiento y de las
  condiciones operativas;
- la extracción automática de los mínimos se limita a los formatos SIA
  reconocidos;
- un PDF sin georreferenciación validada sigue siendo consultable, pero no
  puede utilizarse como capa;
- los nuevos datos MSFS requieren que el simulador esté accesible.

Confirmar siempre la información importante antes de introducirla en el
simulador.

## Arquitectura y confidencialidad

- `navixav/desktop.py` gestiona la ventana nativa y el ciclo de vida del
  proceso;
- `navixav/web/app.py` proporciona la API FastAPI vinculada únicamente a
  `127.0.0.1`;
- `navixav/web/static/` contiene la interfaz adaptable HTML/CSS/JavaScript;
- `navixav/planner/` completa el plan IFR;
- `navixav/navdata/` construye y consulta la base procedente de MSFS;
- `navixav/live/` asegura el seguimiento SimConnect;
- `navixav/sia.py`, `navixav/faa.py` y `navixav/national_aip.py` gestionan las
  publicaciones oficiales.

El servicio local nunca escucha en la red exterior. El Pilot ID de SimBrief,
las preferencias, los resúmenes de vuelo y los PDF en caché permanecen en el
equipo. Solo salen del ordenador las peticiones necesarias para SimBrief,
OpenStreetMap, la meteorología y las publicaciones AIS oficiales.

## Licencia

NaviXav es software libre distribuido bajo la licencia
[Apache 2.0](LICENSE).

Copyright 2026 Xavier BEGUE (xalacaga)

Puedes usar, modificar, redistribuir e integrar NaviXav libremente, incluso en
un proyecto comercial. A cambio, la licencia obliga a **acreditar al autor**:

- conservar la mención de copyright y una copia de la licencia en toda
  redistribución;
- conservar el archivo [NOTICE](NOTICE) y su contenido de atribución;
- **indicar de forma visible todo archivo que hayas modificado**, conforme a la
  sección 4(b) de la licencia.

La licencia concede además una licencia de patentes y excluye toda garantía.
Los datos de navegación, las cartas oficiales y el fondo cartográfico no están
cubiertos por esta licencia: siguen sujetos a las condiciones de sus
respectivos proveedores, detalladas en el archivo NOTICE.

## Pruebas

El perfil reproducible utilizado para construir la distribución es:

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not live_msfs"
```

Las pruebas marcadas `live_msfs` consultan un simulador realmente iniciado y
por tanto no forman parte del control automático del instalador.
