[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    [switch]$SkipToolInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
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

if (git status --porcelain) {
    throw "Le dépôt doit être propre. Committe d'abord les modifications de l'application."
}

$Gh = Find-GitHubCli
if (-not $Gh -and -not $SkipToolInstall) {
    $Winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
    if ($Winget) {
        & $Winget.Source install --id GitHub.cli --exact --silent --accept-package-agreements --accept-source-agreements
        $Gh = Find-GitHubCli
    }
}
if (-not $Gh) {
    throw "GitHub CLI est absent. Installe-le ou relance sans -SkipToolInstall."
}
& $Gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "Connecte GitHub CLI avec : gh auth login"
}

$VersionOutput = & (Join-Path $PSScriptRoot "prepare_release.ps1") -Bump $Bump
$Version = [string]($VersionOutput | Select-Object -Last 1)
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version générée invalide : $Version"
}

& (Join-Path $PSScriptRoot "build_windows.ps1")
if ($LASTEXITCODE -ne 0) { throw "La construction de la Release a échoué." }

git add navixav/__init__.py pyproject.toml CHANGELOG.md RELEASE_NOTES.md
git commit -m "chore(release): v$Version"
git tag -a "v$Version" -m "NaviXav $Version"
git push origin main
git push origin "v$Version"

$Installer = "release\NaviXav-Setup-$Version.exe"
$Portable = "release\NaviXav-$Version-windows-x64-portable.zip"
& $Gh release create "v$Version" `
    $Installer "$Installer.sha256" $Portable "$Portable.sha256" `
    --repo "xalacaga/NaviXav" `
    --title "NaviXav $Version" `
    --notes-file "RELEASE_NOTES.md" `
    --latest
if ($LASTEXITCODE -ne 0) { throw "La création de la Release GitHub a échoué." }

Write-Host "Release v$Version publiée sur GitHub." -ForegroundColor Green
