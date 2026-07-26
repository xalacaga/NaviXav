# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH)
simconnect_datas, simconnect_binaries, simconnect_hidden = collect_all("SimConnect")
webview_datas, webview_binaries, webview_hidden = collect_all("webview")
sdk_simconnect = Path(r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll")
if not sdk_simconnect.is_file():
    raise SystemExit(
        "SimConnect.dll moderne introuvable. Installe le SDK MSFS avant de "
        "construire la distribution."
    )

# Le paquet Python fournit une DLL ancienne suffisante pour quelques SimVars,
# mais dépourvue de l'API Facilities nécessaire à NaviXav. La distribution
# embarque donc la DLL du SDK MSFS installée sur la machine de construction.
simconnect_binaries = [
    entry
    for entry in simconnect_binaries
    if Path(entry[0]).name.lower() != "simconnect.dll"
]
simconnect_binaries.append((str(sdk_simconnect), "SimConnect"))
simconnect_binaries += webview_binaries

datas = [
    (str(project_root / "navixav" / "web" / "static"), "navixav/web/static"),
    (str(project_root / "assets" / "navixav.ico"), "assets"),
    (str(project_root / "tests" / "data" / "ofp_lfst_lfbo.json"), "tests/data"),
    (str(project_root / "data" / "airport_preferences.json"), "data"),
]
datas += simconnect_datas
datas += webview_datas

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
hiddenimports += simconnect_hidden
hiddenimports += webview_hidden

a = Analysis(
    ["navixav/desktop.py"],
    pathex=[str(project_root)],
    binaries=simconnect_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
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
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name="NaviXav",
)
