[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Get-CurrentVersion {
    $Source = Get-Content -LiteralPath "navixav\__init__.py" -Raw
    if ($Source -notmatch '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"') {
        throw "Version NaviXav introuvable."
    }
    return [version]$Matches.version
}

function Get-ReleaseCommits([string]$LastTag) {
    if ($LastTag) {
        return @(git log "$LastTag..HEAD" --pretty=format:"%s")
    }
    return @(git log --pretty=format:"%s")
}

function Get-AutomaticBump([string[]]$Commits) {
    if ($Commits | Where-Object { $_ -match 'BREAKING CHANGE|^[a-z]+(\([^)]+\))?!:' }) {
        return "major"
    }
    if ($Commits | Where-Object { $_ -match '^feat(\([^)]+\))?:' }) {
        return "minor"
    }
    return "patch"
}

function Get-NextVersion([version]$Current, [string]$Kind) {
    switch ($Kind) {
        "major" { return "$($Current.Major + 1).0.0" }
        "minor" { return "$($Current.Major).$($Current.Minor + 1).0" }
        default { return "$($Current.Major).$($Current.Minor).$($Current.Build + 1)" }
    }
}

function Set-VersionInFile(
    [string]$Path,
    [string]$Pattern,
    [string]$Replacement
) {
    $Content = Get-Content -LiteralPath $Path -Raw
    $Updated = [regex]::Replace($Content, $Pattern, $Replacement, 1)
    if ($Updated -eq $Content) {
        throw "Version non modifiée dans $Path."
    }
    [System.IO.File]::WriteAllText(
        (Resolve-Path -LiteralPath $Path).Path,
        $Updated,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Add-Category(
    [System.Collections.Generic.List[string]]$Lines,
    [string]$Title,
    [object[]]$Items
) {
    if ($Items.Count -eq 0) { return }
    $Lines.Add("## $Title")
    $Lines.Add("")
    foreach ($Item in $Items) {
        $Text = [regex]::Replace([string]$Item, '^[a-z]+(\([^)]+\))?!?:\s*', '')
        $Lines.Add("- $Text")
    }
    $Lines.Add("")
}

$Current = Get-CurrentVersion
$LastTag = git tag --list "v*" --sort=-version:refname | Select-Object -First 1
$Commits = Get-ReleaseCommits $LastTag
if ($Commits.Count -eq 0) {
    throw "Aucun nouveau commit depuis $LastTag."
}
$EffectiveBump = if ($Bump -eq "auto") { Get-AutomaticBump $Commits } else { $Bump }
$Next = Get-NextVersion $Current $EffectiveBump
$Date = Get-Date -Format "yyyy-MM-dd"

Set-VersionInFile "navixav\__init__.py" '__version__\s*=\s*"\d+\.\d+\.\d+"' "__version__ = `"$Next`""
Set-VersionInFile "pyproject.toml" '(?m)^version\s*=\s*"\d+\.\d+\.\d+"' "version = `"$Next`""

$Features = @($Commits | Where-Object { $_ -match '^feat(\([^)]+\))?!?:' })
$Fixes = @($Commits | Where-Object { $_ -match '^fix(\([^)]+\))?:' })
$Other = @(
    $Commits | Where-Object {
        $_ -notmatch '^feat(\([^)]+\))?!?:' -and
        $_ -notmatch '^fix(\([^)]+\))?:' -and
        $_ -notmatch '^chore\(release\):'
    }
)
$Notes = [System.Collections.Generic.List[string]]::new()
$Notes.Add("# NaviXav $Next")
$Notes.Add("")
$Notes.Add("Publication du $Date.")
$Notes.Add("")
Add-Category $Notes "Nouvelles fonctionnalités" $Features
Add-Category $Notes "Corrections de bugs" $Fixes
Add-Category $Notes "Autres changements" $Other
if ($Notes[$Notes.Count - 1] -ne "") { $Notes.Add("") }
$Notes.Add("L’installateur est contrôlé par une empreinte SHA-256 avant toute mise à jour automatique.")
$Notes.Add("")
$ReleaseText = $Notes -join "`n"
[System.IO.File]::WriteAllText(
    (Join-Path $ProjectRoot "RELEASE_NOTES.md"),
    $ReleaseText,
    [System.Text.UTF8Encoding]::new($false)
)

$ChangelogEntry = "## [$Next] - $Date`n`n" + (($Notes | Select-Object -Skip 4) -join "`n")
if (Test-Path -LiteralPath "CHANGELOG.md") {
    $Existing = Get-Content -LiteralPath "CHANGELOG.md" -Raw
    $Header = "# Journal des modifications`n`n"
    $Body = if ($Existing.StartsWith($Header)) { $Existing.Substring($Header.Length) } else { $Existing }
    [System.IO.File]::WriteAllText(
        (Join-Path $ProjectRoot "CHANGELOG.md"),
        ($Header + $ChangelogEntry + "`n" + $Body),
        [System.Text.UTF8Encoding]::new($false)
    )
} else {
    [System.IO.File]::WriteAllText(
        (Join-Path $ProjectRoot "CHANGELOG.md"),
        ("# Journal des modifications`n`n" + $ChangelogEntry),
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Host "Version préparée : $Current -> $Next ($EffectiveBump)" -ForegroundColor Green
Write-Host "Notes : $ProjectRoot\RELEASE_NOTES.md"
Write-Output $Next
