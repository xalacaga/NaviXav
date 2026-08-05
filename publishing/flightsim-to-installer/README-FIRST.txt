NaviXav 1.4.7 - Recommended Windows Installer
================================================

NaviXav is an external IFR flight assistance application for Microsoft Flight
Simulator 2024.

INSTALLATION

1. Run NaviXav-Setup-1.4.7.exe.
2. Follow the installation wizard.
3. Start NaviXav from the Windows Start menu or the optional desktop shortcut.
4. Open Settings and enter your SimBrief Pilot ID or username.
5. Start Microsoft Flight Simulator, load a flight and wait for the connection
   indicator to turn green.

On phones and tablets narrower than 760 px, the MSFS connection indicator is a
compact coloured dot without a text label, so it remains visible on narrow
screens.

On wide desktop windows, module switching uses a compact floating rail at the
upper left. A concise Flight plan entry replaces the collapsible Departure, Route and
Arrival section, behaves like every other module and is selected by default.
Every choice scrolls to
its content, the main area fills the remaining width, and an opened official
PDF expands across the chart grid. Compact desktop windows retain the
horizontal selector. A visible global flight alert moves the rail below the
enlarged header instead of covering its first entry, and mobile navigation
retains its accessible side drawer.

IMPORTANT

- Do not install NaviXav in the MSFS Community folder.
- Windows 10 or Windows 11 64-bit is required.
- A generated SimBrief OFP is required for SimBrief plan retrieval.
- When its detailed navlog contains coordinates, NaviXav reuses them to speed
  up the first plan preparation and requests only missing positions from MSFS.
- Ground charts keep named taxiways visible even when MSFS classifies them as
  generic paths; unnamed secondary links remain available through the
  Secondary control.
- Aircraft configuration and Flight events cross-check official flap, spoiler
  and parking-brake SimVars so third-party aircraft cannot freeze the display
  on FULL or silently hide control changes. Fenix A319/A320/A321 cockpit
  controls are read directly, including with engines and hydraulics off.
- Internet access is required for SimBrief, maps, weather, official charts and
  updates.
- NaviXav is for flight simulation only. Verify all important information
  against current official publications and ATC instructions.

ANTIVIRUS

NaviXav is a Python application packaged into a standalone Windows executable.
Unsigned executables built this way are sometimes flagged by generic
machine-learning heuristics without any malicious code being present. This
build ships uncompressed and carries full publisher information, which removes
the usual cause. The application is unsigned, so Windows SmartScreen may warn
on first run. Verify the published SHA-256 checksum if in doubt, and please
report any detection with the version number.

HOW NAVIXAV IS DEVELOPED

NaviXav is a one-person project written with heavy use of AI coding assistants.
Every feature is specified, reviewed and flight-tested by the author, an
automated suite of more than four hundred tests must pass before any build is
produced, and the complete source is published under the Apache License 2.0 so
that anyone can read exactly what runs on their machine.

PRIVACY

NaviXav has no advertising telemetry and does not identify or profile users.
Settings, navigation data and completed-flight summaries remain on the
computer.

SUPPORT AND SOURCE

https://github.com/xalacaga/NaviXav

LICENSE

NaviXav is licensed under the Apache License 2.0.
Copyright 2026 Xavier BEGUE (xalacaga).
