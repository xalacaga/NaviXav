<#
.SYNOPSIS
Teste, avant la Release, le téléchargement de la voix naturelle par un
utilisateur qui a déjà NaviXav.

.DESCRIPTION
1. Construit l'archive NaviXav-<version>-voice-engine.zip et son .sha256
   exactement comme scripts\build_windows.ps1, à partir de voice_engine\
   (construit par scripts\fetch_voice_engine.py s'il manque).
2. Met le moteur de côté (voice_engine.off) : NaviXav se comporte comme chez
   un utilisateur qui ne l'a pas.
3. Lance NaviXav en mode test : le bouton « Télécharger la voix naturelle »
   lit cette archive locale au lieu de la Release GitHub, avec la même
   vérification SHA-256, la même progression et la même installation.

Relancer avec -Restore remet le moteur en place après l'essai.
#>
param(
    [switch]$Restore
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Engine = Join-Path $ProjectRoot "voice_engine"
$Parked = Join-Path $ProjectRoot "voice_engine.off"

if ($Restore) {
    if (Test-Path -LiteralPath $Parked) {
        if (Test-Path -LiteralPath $Engine) {
            # Le moteur réinstallé par l'essai est identique : l'original n'a
            # plus de raison d'être gardé de côté.
            Remove-Item -LiteralPath $Parked -Recurse -Force
        } else {
            Rename-Item -LiteralPath $Parked -NewName "voice_engine"
        }
    }
    Write-Host "Moteur vocal remis en place." -ForegroundColor Green
    exit 0
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VersionSource = Get-Content (Join-Path $ProjectRoot "navixav\__init__.py") -Raw -Encoding UTF8
$Version = [regex]::Match($VersionSource, '__version__\s*=\s*"([^"]+)"').Groups[1].Value
if (-not $Version) { throw "Version NaviXav introuvable." }

if (-not (Test-Path -LiteralPath $Engine) -and (Test-Path -LiteralPath $Parked)) {
    Rename-Item -LiteralPath $Parked -NewName "voice_engine"
}
if (-not (Test-Path -LiteralPath (Join-Path $Engine "VERSION.json"))) {
    Write-Host "Construction du moteur vocal…" -ForegroundColor Cyan
    & $VenvPython (Join-Path $PSScriptRoot "fetch_voice_engine.py")
    if ($LASTEXITCODE -ne 0) { throw "Le moteur vocal n'a pas pu être construit." }
}

$TestDir = Join-Path $ProjectRoot "build\voice-engine-test"
New-Item -ItemType Directory -Path $TestDir -Force | Out-Null
$Archive = Join-Path $TestDir "NaviXav-$Version-voice-engine.zip"
Write-Host "Archive de test : $Archive" -ForegroundColor Cyan
if (Test-Path -LiteralPath $Archive) { Remove-Item -LiteralPath $Archive -Force }
Compress-Archive -Path $Engine -DestinationPath $Archive -CompressionLevel Optimal
$Hash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
Set-Content -LiteralPath ($Archive + ".sha256") -Value "$Hash  $(Split-Path -Leaf $Archive)" -Encoding ascii

if (Test-Path -LiteralPath $Parked) { Remove-Item -LiteralPath $Parked -Recurse -Force }
Rename-Item -LiteralPath $Engine -NewName "voice_engine.off"
Write-Host "Moteur mis de côté : NaviXav se lance comme chez un utilisateur sans voix naturelle." -ForegroundColor Cyan
Write-Host "Paramètres > Vol & météo > Radio et interphone hors ligne > Télécharger la voix naturelle." -ForegroundColor Cyan
Write-Host "Après l'essai : scripts\test_voice_engine.ps1 -Restore" -ForegroundColor Yellow

$env:NAVIXAV_VOICE_ENGINE_ARCHIVE = $Archive
& (Join-Path $ProjectRoot "NaviXav.bat")
