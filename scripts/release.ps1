[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    [switch]$SkipToolInstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$env:LC_ALL = "C.UTF-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# 1. Autoriser temporairement l'exécution de scripts dans la session active
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Vérification de l'état Git..."

# 2. Gestion des modifications non commitées
$Status = & git status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw "Impossible de lire l'état du dépôt Git."
}

if ($Status) {
    if ($Force) {
        Write-Host "Modifications détectées. Inscription automatique (staged)..." -ForegroundColor Yellow
        & git add .
        & git commit -m "feat: pré-release (auto-commit)"
    } else {
        Write-Host "Fichiers non commités détectés :" -ForegroundColor Yellow
        & git status -s
        $Choice = Read-Host "`nVoulez-vous commiter automatiquement tous ces changements ? (O/n)"
        if ($Choice -eq "" -or $Choice -match "^[OyY]") {
            $Msg = Read-Host "Message de commit [feat: mises à jour de l'application]"
            if (-not $Msg) { $Msg = "feat: mises à jour de l'application" }
            & git add .
            & git commit -m "$Msg"
        } else {
            throw "Publication annulée. Committez vos modifications avant de relancer."
        }
    }
}

# 3. Synchronisation avec le dépôt distant (optionnel mais recommandé)
Write-Step "Mise à jour avec origin/main..."
& git fetch origin main --quiet 2>$null
$Behind = & git rev-list --count HEAD..origin/main
if ($LASTEXITCODE -eq 0 -and [int]$Behind -gt 0) {
    throw "Votre branche locale a $Behind commit(s) de retard par rapport à origin/main. Faites un 'git pull' d'abord."
}

# 4. Lancement du processus complet de publication
Write-Step "Lancement de la publication..."
$PublishScript = Join-Path $PSScriptRoot "publish_release.ps1"
if (-not (Test-Path -LiteralPath $PublishScript)) {
    throw "Script introuvable : $PublishScript"
}

$PublishParams = @{
    Bump = $Bump
}
if ($SkipToolInstall) { $PublishParams.Add("SkipToolInstall", $true) }

& $PublishScript @PublishParams

Write-Host "`n Processus terminé avec succès !" -ForegroundColor Green