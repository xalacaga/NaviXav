[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    [int]$KeepReleases = 0, # Nombre d'anciennes versions à conserver en plus de la nouvelle (0 = conserve uniquement la dernière)
    [switch]$SkipToolInstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Force l'encodage UTF-8 global pour préserver tous les accents français
$env:LC_ALL = "fr_FR.UTF-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$OutputEncoding           = [System.Text.Encoding]::UTF8

# 1. Déblocage de la politique d'exécution pour la session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Clear-OldReleases([string]$ReleaseDir, [string]$CurrentVersion, [int]$KeepCount) {
    if (-not (Test-Path -LiteralPath $ReleaseDir)) { return }

    Write-Step "Nettoyage des anciennes versions (conservation de v$CurrentVersion)..."

    # Récupération des fichiers de publication
    $AllFiles = Get-ChildItem -LiteralPath $ReleaseDir -File | 
        Where-Object { $_.Extension -in ".exe", ".zip", ".sha256" }

    # Extraction des numéros de version
    $Versions = $AllFiles | ForEach-Object {
        if ($_.Name -match '(\d+\.\d+\.\d+)') { $Matches[1] }
    } | Select-Object -Unique

    # Exclusion explicite de la version actuelle qu'on vient de générer
    $OldVersions = $Versions | Where-Object { $_ -ne $CurrentVersion }

    if (-not $OldVersions -or $OldVersions.Count -eq 0) {
        Write-Host "Aucune ancienne version à nettoyer." -ForegroundColor Gray
        return
    }

    # Sélection des anciennes versions à conserver/supprimer
    $OldVersionsToKeep = $OldVersions | Sort-Object {
        ($AllFiles | Where-Object { $_.Name -like "*$_*" } | Measure-Object -Property LastWriteTime -Maximum).Maximum
    } -Descending | Select-Object -First $KeepCount

    $VersionsToRemove = $OldVersions | Where-Object { $_ -notin $OldVersionsToKeep }

    foreach ($Ver in $VersionsToRemove) {
        $FilesToDelete = $AllFiles | Where-Object { $_.Name -like "*$Ver*" }
        foreach ($File in $FilesToDelete) {
            Remove-Item -LiteralPath $File.FullName -Force
            Write-Host "Supprimé (ancienne version) : $($File.Name)" -ForegroundColor Yellow
        }
    }

    Write-Host "Nettoyage terminé. La version v$CurrentVersion est conservée." -ForegroundColor Green
}

# 2. Contrôle Git et gestion du français dans le terminal
Write-Step "Vérification de l'état Git..."
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
        Write-Host "Fichiers non enregistrés détectés :" -ForegroundColor Yellow
        & git status -s
        $Choice = Read-Host "`nVoulez-vous enregistrer automatiquement tous ces changements ? (O/n)"
        if ($Choice -eq "" -or $Choice -match "^[OyY]") {
            # Un message générique se retrouverait tel quel dans les notes de
            # version : la description des nouveautés est donc obligatoire.
            $Msg = ""
            while (-not $Msg) {
                $Msg = (Read-Host "Message de commit (ex. « feat: suivi du temps restant en vol »)").Trim()
                if (-not $Msg) {
                    Write-Host "Décrivez la nouveauté : ce texte alimente les notes de version." -ForegroundColor Yellow
                }
            }
            & git add .
            & git commit -m "$Msg"
        } else {
            throw "Publication annulée. Enregistrez vos modifications avant de relancer."
        }
    }
}

# 3. Synchronisation avec le dépôt distant
Write-Step "Vérification de la branche principale..."
& git fetch origin main --quiet 2>$null
$Behind = & git rev-list --count HEAD..origin/main
if ($LASTEXITCODE -eq 0 -and [int]$Behind -gt 0) {
    throw "Votre branche locale a $Behind commit(s) de retard par rapport à origin/main. Exécutez 'git pull' d'abord."
}

# 4. Exécution du processus de publication
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

# 5. Nettoyage sécurisé des anciennes releases
$InitSource = Get-Content -LiteralPath (Join-Path $ProjectRoot "navixav\__init__.py") -Raw -Encoding UTF8
if ($InitSource -match '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"') {
    $CurrentVersion = $Matches.version
    $ReleaseDirectory = Join-Path $ProjectRoot "release"
    Clear-OldReleases -ReleaseDir $ReleaseDirectory -CurrentVersion $CurrentVersion -KeepCount $KeepReleases
}

Write-Host "`nPublication terminée avec succès !" -ForegroundColor Green