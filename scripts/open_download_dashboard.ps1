[CmdletBinding()]
param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Environnement Python absent. Lance d'abord NaviXav.bat."
}

$Arguments = @("-m", "navixav.release_dashboard")
if ($NoOpen) { $Arguments += "--no-open" }

Write-Host "Administration locale uniquement : aucun tableau de bord n'est publié." -ForegroundColor Cyan
& $Python @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "La génération du tableau de bord a échoué."
}
