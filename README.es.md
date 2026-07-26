# NaviXav

**Documentación:** [Français](README.md) · [English](README.en.md) ·
[Deutsch](README.de.md) · Español · [Italiano](README.it.md) ·
[Português](README.pt.md) · [Nederlands](README.nl.md) ·
[Polski](README.pl.md)

NaviXav es un asistente IFR local para Microsoft Flight Simulator. Recupera
automáticamente el último OFP de SimBrief, completa la información terminal con
datos del simulador y presenta los valores necesarios para preparar el vuelo y
configurar el MCDU.

La aplicación utiliza una ventana Windows propia y adaptable basada en
Microsoft WebView2. No abre un navegador externo. Su servicio privado solo
escucha en `127.0.0.1`; los ajustes, datos de navegación, cartas y cachés
permanecen en el ordenador.

> NaviXav está destinado exclusivamente a la simulación. Verifica siempre los
> datos con las publicaciones oficiales vigentes y las instrucciones ATC.

## Funciones

- recuperación automática del último plan de vuelo SimBrief;
- Pilot ID o nombre de usuario SimBrief configurables en la interfaz;
- ruta completa y posición del avión sobre la ruta;
- selección explicada de pista, SID, STAR, transiciones y aproximación;
- restricciones de altitud/velocidad, altitud y nivel de transición, ILS,
  altitud de interceptación y aproximación frustrada;
- información de avión, despacho, combustible, pesos y datos para el MCDU;
- QNH debajo de los valores del viento;
- seguimiento MSFS en tiempo real y registro local reproducible;
- ruta dibujada sobre un fondo OpenStreetMap;
- acceso directo a PDF oficiales de salida y llegada;
- superposición de carta únicamente con georreferenciación validada;
- datos de navegación directamente desde MSFS, sin Little Navmap, Navigraph ni
  EUROCONTROL.

## Requisitos e instalación

- Windows 10 u 11 de 64 bits;
- Microsoft Flight Simulator para datos en directo y navegación;
- cuenta SimBrief con un OFP ya generado;
- Internet para SimBrief, mapa y publicaciones AIS/FAA.

Ejecuta `NaviXav-Setup-0.1.0.exe`, revisa los requisitos y pulsa **Instalar**.
Python y las bibliotecas están incluidos. WebView2 solo se instala si falta.
También puedes extraer el archivo portátil y ejecutar `NaviXav.exe`.

### SimConnect autónomo

NaviXav nunca instala, registra, reinstala ni sustituye SimConnect en Windows.
Incluye una `SimConnect.dll` moderna y privada dentro de su propia carpeta.
Cualquier instalación existente permanece intacta. MSFS debe estar ejecutándose
porque el conector privado se comunica con el servicio SimConnect del simulador.

## Primera configuración

En **Ajustes**, selecciona el idioma, introduce el Pilot ID o usuario SimBrief
y configura la fuente METAR y las preferencias de aproximación, pista y avión.
El idioma se aplica de inmediato y queda guardado localmente. Están disponibles
francés, inglés, alemán, español, italiano, portugués, neerlandés y polaco.

Al iniciarse, NaviXav busca siempre el último OFP disponible. La generación del
plan se sigue realizando en el sitio web de SimBrief.

## Cartas oficiales

La pestaña **Cartas oficiales** propone documentos de salida y llegada de
fuentes compatibles como SIA, ENAIRE, LVNL y FAA d-TPP. Los PDF se visualizan
dentro de NaviXav. El botón de superposición no aparece si el alineamiento
geográfico no ha sido validado.

## Código fuente y distribución

```powershell
git clone https://github.com/xalacaga/NaviXav.git
cd NaviXav
.\NaviXav.bat
```

Para construir:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

El instalador, archivo portátil y sumas SHA-256 se generan en `release\`. El
SDK SimConnect de MSFS solo es necesario en el equipo de compilación.

## Solución de problemas y privacidad

- Sin plan: comprueba la identificación SimBrief, el OFP e Internet.
- Indicador MSFS rojo: inicia MSFS, carga completamente un vuelo y espera.
- Sin ventana: usa el instalador completo para reparar WebView2.
- Puerto 8765 ocupado: cierra la instancia anterior de NaviXav.

NaviXav no envía telemetría. Los ajustes, cachés e historial permanecen en el
equipo; solo se contactan SimBrief, OpenStreetMap y las fuentes oficiales
solicitadas.

El registro rotativo de diagnóstico se encuentra en
`%LOCALAPPDATA%\NaviXav\logs\navixav.log`. Incluye errores y tiempos, pero no el
identificador SimBrief ni la ruta completa.
