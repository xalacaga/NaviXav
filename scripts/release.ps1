[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    [int]$KeepReleases = 1, # Nombre de releases récents à conserver dans release/
    [switch]$SkipToolInstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$env:LC_ALL = "C.UTF-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

# 1. Autoriser l'exécution de scripts pour la session en cours
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Clear-OldReleases([string]$ReleaseDir, [int]$KeepCount) {
    if (-not (Test-Path -LiteralPath $ReleaseDir)) { return }

    Write-Step "Nettoyage du dossier release/..."

    # Récupérer tous les fichiers .exe, .zip et .sha256 triés par date de modification (les plus récents en premier)
    $AllFiles = Get-ChildItem -LiteralPath $ReleaseDir -File | 
        Where-Object { $_.Extension -in ".exe", ".zip", ".sha256" }

    # Identifier les versions uniques à partir des noms de fichiers (ex: NaviXav-0.6.0-windows-x64-portable.zip)
    # Extrait la version (ex: 0.6.0)
    $Versions = $AllFiles | ForEach-Object {
        if ($_.Name -match '(\d+\.\d+\.\d+)') { $Matches[1] }
    } | Select-Object -Unique

    if ($Versions.Count -le $KeepCount) {
        Write-Host "Aucune ancienne release à supprimer (total versions : $($Versions.Count), limite : $KeepCount)." -ForegroundColor Gray
        return
    }

    # Conserver les $KeepCount versions les plus récentes en fonction de la date des fichiers associés
    $VersionsToKeep = $Versions | Sort-Object {
        ($AllFiles | Where-Object { $_.Name -like "*$_*" } | Measure-Object -Property LastWriteTime -Maximum).Maximum
    } -Descending | Select-Object -First $KeepCount

    $VersionsToRemove = $Versions | Where-Object { $_ -notin $VersionsToKeep }

    foreach ($Ver in $VersionsToRemove) {
        $FilesToDelete = $AllFiles | Where-Object { $_.Name -like "*$Ver*" }
        foreach ($File in $FilesToDelete) {
            Remove-Item -LiteralPath $File.FullName -Force
            Write-Host "Supprimé : $($File.Name)" -ForegroundColor Yellow
        }
    }

    Write-Host "Nettoyage terminé. Seule(s) la/les $KeepCount dernière(s) version(s) ont été conservée(s)." -ForegroundColor Green
}

# 2. Vérification de l'état Git
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

# 3. Synchronisation avec le dépôt distant
Write-Step "Mise à jour avec origin/main..."
& git fetch origin main --quiet 2>$null
$Behind = & git rev-list --count HEAD..origin/main
if ($LASTEXITCODE -eq 0 -and [int]$Behind -gt 0) {
    throw "Votre branche locale a $Behind commit(s) de retard par rapport à origin/main. Faites un 'git pull' d'abord."
}

# 4. Lancement du processus de publication
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

# 5. Nettoyage final des anciens fichiers de release locaux
$ReleaseDirectory = Join-Path $ProjectRoot "release"
Clear-OldReleases -ReleaseDir $ReleaseDirectory -KeepCount $KeepKeepReleases

Write-Host "`nProcessus terminé avec succès !" -ForegroundColor Green