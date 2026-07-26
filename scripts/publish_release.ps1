[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    [switch]$SkipToolInstall
)

$ErrorActionPreference = "Stop"
$env:LC_ALL = "C.UTF-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReleaseFiles = @(
    "navixav/__init__.py",
    "pyproject.toml",
    "CHANGELOG.md",
    "RELEASE_NOTES.md"
)
Set-Location $ProjectRoot

function Find-GitHubCli {
    $Command = Get-Command "gh.exe" -ErrorAction SilentlyContinue
    if ($Command) { return $Command.Source }

    $Candidates = @(
        (Join-Path $env:ProgramFiles "GitHub CLI\gh.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\GitHub CLI\gh.exe")
    )
    return $Candidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$FailureMessage
    )
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (code $LASTEXITCODE)."
    }
}

function Get-AppVersion {
    $Source = Get-Content -LiteralPath "navixav\__init__.py" -Raw -Encoding UTF8
    if ($Source -notmatch '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"') {
        throw "Version NaviXav introuvable."
    }
    return $Matches.version
}

function Assert-CleanRepository {
    $Status = & git status --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw "Impossible de lire l'état du dépôt Git."
    }
    if ($Status) {
        throw "Le dépôt doit être propre. Committe d'abord les modifications de l'application."
    }
}

function Ensure-GitHubAuthentication([string]$GhPath) {
    & $GhPath auth status --hostname github.com
    if ($LASTEXITCODE -eq 0) { return }

    Write-Host "La session GitHub est absente ou expirée. Reconnexion..." -ForegroundColor Yellow
    & $GhPath auth login --hostname github.com --git-protocol https --web
    if ($LASTEXITCODE -ne 0) {
        throw "Connexion GitHub annulée ou échouée."
    }
    & $GhPath auth status --hostname github.com
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI n'est toujours pas authentifié."
    }
}

Assert-CleanRepository

$Gh = Find-GitHubCli
if (-not $Gh -and -not $SkipToolInstall) {
    $Winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if (-not $Winget) {
        throw "GitHub CLI est absent et winget n'est pas disponible pour l'installer."
    }
    Invoke-Checked $Winget.Source @(
        "install", "--id", "GitHub.cli", "--exact", "--silent",
        "--accept-package-agreements", "--accept-source-agreements"
    ) "L'installation de GitHub CLI a échoué"
    $Gh = Find-GitHubCli
}
if (-not $Gh) {
    throw "GitHub CLI est absent. Installe-le ou retire -SkipToolInstall."
}
Ensure-GitHubAuthentication $Gh

# Une exécution interrompue après le commit de Release reprend la même version.
$HeadSubject = & git log -1 --pretty=format:"%s"
if ($LASTEXITCODE -ne 0) {
    throw "Impossible de lire le dernier commit Git."
}
$Resume = $HeadSubject -match '^chore\(release\): v(?<version>\d+\.\d+\.\d+)$'
$ReleaseCommitted = $Resume

if ($Resume) {
    $Version = $Matches.version
    if ((Get-AppVersion) -ne $Version) {
        throw "Le commit de Release v$Version ne correspond pas à la version de l'application."
    }
    Write-Host "Reprise de la publication v$Version." -ForegroundColor Yellow
} else {
    try {
        $VersionOutput = & (Join-Path $PSScriptRoot "prepare_release.ps1") -Bump $Bump
        if ($LASTEXITCODE -ne 0) {
            throw "La préparation de la Release a échoué."
        }
        $Version = [string]($VersionOutput | Select-Object -Last 1)
        if ($Version -notmatch '^\d+\.\d+\.\d+$') {
            throw "Version générée invalide : $Version"
        }

        & (Join-Path $PSScriptRoot "build_windows.ps1")
        if ($LASTEXITCODE -ne 0) {
            throw "La construction de la Release a échoué."
        }

        Invoke-Checked "git" (@("add") + $ReleaseFiles) "Impossible de préparer les fichiers de Release"
        Invoke-Checked "git" @("commit", "-m", "chore(release): v$Version") "Impossible de créer le commit de Release"
        $ReleaseCommitted = $true
    } catch {
        if (-not $ReleaseCommitted) {
            Write-Host "Restauration des fichiers de version après l'échec." -ForegroundColor Yellow
            & git restore --staged --worktree -- @ReleaseFiles
        }
        throw
    }
}

$Tag = "v$Version"
$HeadCommit = & git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "Impossible de lire le commit courant." }
$null = & git show-ref --verify --quiet "refs/tags/$Tag"
if ($LASTEXITCODE -eq 0) {
    $ExistingTagCommit = & git rev-list -n 1 $Tag
    if ($LASTEXITCODE -ne 0) { throw "Impossible de lire le tag $Tag." }
    if ($ExistingTagCommit -ne $HeadCommit) {
        throw "Le tag $Tag existe déjà sur un autre commit."
    }
} else {
    Invoke-Checked "git" @("tag", "-a", $Tag, "-m", "NaviXav $Version") "Impossible de créer le tag $Tag"
}

$Installer = "release\NaviXav-Setup-$Version.exe"
$Portable = "release\NaviXav-$Version-windows-x64-portable.zip"
$Assets = @($Installer, "$Installer.sha256", $Portable, "$Portable.sha256")
if ($Assets | Where-Object { -not (Test-Path -LiteralPath $_) }) {
    Write-Host "Les paquets sont absents : reconstruction de v$Version." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "build_windows.ps1")
    if ($LASTEXITCODE -ne 0) { throw "La reconstruction de la Release a échoué." }
}
foreach ($Asset in $Assets) {
    if (-not (Test-Path -LiteralPath $Asset)) {
        throw "Fichier de Release manquant : $Asset"
    }
}

Invoke-Checked "git" @("push", "origin", "main") "L'envoi de la branche main a échoué"
Invoke-Checked "git" @("push", "origin", $Tag) "L'envoi du tag $Tag a échoué"

$ReleaseTags = @(
    & $Gh release list `
        --repo "xalacaga/NaviXav" `
        --limit 100 `
        --json "tagName" `
        --jq ".[].tagName"
)
if ($LASTEXITCODE -ne 0) {
    throw "Impossible de consulter les Releases GitHub."
}
$ReleaseExists = $ReleaseTags -contains $Tag
if ($ReleaseExists) {
    Write-Host "La Release $Tag existe : mise à jour de ses fichiers." -ForegroundColor Yellow
    Invoke-Checked $Gh (@("release", "upload", $Tag) + $Assets + @(
        "--repo", "xalacaga/NaviXav", "--clobber"
    )) "La mise à jour des fichiers GitHub a échoué"
    Invoke-Checked $Gh @(
        "release", "edit", $Tag,
        "--repo", "xalacaga/NaviXav",
        "--title", "NaviXav $Version",
        "--notes-file", "RELEASE_NOTES.md",
        "--latest"
    ) "La mise à jour de la Release GitHub a échoué"
} else {
    Invoke-Checked $Gh (@("release", "create", $Tag) + $Assets + @(
        "--repo", "xalacaga/NaviXav",
        "--title", "NaviXav $Version",
        "--notes-file", "RELEASE_NOTES.md",
        "--latest"
    )) "La création de la Release GitHub a échoué"
}

Write-Host "Release $Tag publiée sur GitHub." -ForegroundColor Green
