# -*- mode: python ; coding: utf-8 -*-

import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)

# Ressource VERSIONINFO : un binaire Windows sans métadonnées d'éditeur est
# traité comme suspect par les moteurs heuristiques (Wacatac.B!ml et voisins).
version_source = (project_root / "navixav" / "__init__.py").read_text(encoding="utf-8")
version_match = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', version_source)
if not version_match:
    raise SystemExit("Version NaviXav introuvable dans navixav/__init__.py.")
version_tuple = tuple(int(part) for part in version_match.groups()) + (0,)
version_text = ".".join(str(part) for part in version_tuple)

version_resource = project_root / "build" / "version_info.txt"
version_resource.parent.mkdir(parents=True, exist_ok=True)
version_resource.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040C04B0',
        [StringStruct('CompanyName', 'Xalacaga'),
         StringStruct('FileDescription', 'NaviXav - assistant de vol IFR pour MSFS'),
         StringStruct('FileVersion', '{version_text}'),
         StringStruct('InternalName', 'NaviXav'),
         StringStruct('LegalCopyright', 'Xalacaga'),
         StringStruct('OriginalFilename', 'NaviXav.exe'),
         StringStruct('ProductName', 'NaviXav'),
         StringStruct('ProductVersion', '{version_text}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1036, 1200])])
  ]
)
""",
    encoding="utf-8",
)
webview_datas, webview_binaries, webview_hidden = collect_all("webview")
sdk_simconnect = Path(r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll")
if not sdk_simconnect.is_file():
    raise SystemExit(
        "SimConnect.dll moderne introuvable. Installe le SDK MSFS avant de "
        "construire la distribution."
    )

# NaviXav utilise son propre client ctypes et la DLL officielle du SDK MSFS.
# Le paquet Python SimConnect n'est volontairement pas distribué : il est AGPL.
app_binaries = [(str(sdk_simconnect), "SimConnect")]
app_binaries += webview_binaries

datas = [
    (str(project_root / "navixav" / "web" / "static"), "navixav/web/static"),
    # Le journal des versions est lu par les Paramètres : sans lui, la fenêtre
    # s'ouvrirait vide dans l'application installée.
    (str(project_root / "CHANGELOG.md"), "."),
    (str(project_root / "assets" / "navixav.ico"), "assets"),
    (str(project_root / "tests" / "data" / "ofp_lcph_eham.json"), "tests/data"),
    (str(project_root / "data" / "airport_preferences.json"), "data"),
]
datas += webview_datas

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
hiddenimports += webview_hidden

a = Analysis(
    ["navixav/desktop.py"],
    pathex=[str(project_root)],
    binaries=app_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Outil personnel d'administration : ne jamais l'inclure dans NaviXav.
    excludes=["pytest", "navixav.release_dashboard"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NaviXav",
    icon=str(project_root / "assets" / "navixav.ico"),
    version=str(version_resource),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX reste désactivé : la compression d'exécutable est le principal
    # déclencheur des détections heuristiques génériques sur les binaires
    # PyInstaller non signés.
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NaviXav",
)
