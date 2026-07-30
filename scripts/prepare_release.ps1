[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto"
)

$ErrorActionPreference = "Stop"
$env:LC_ALL = "C.UTF-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Get-CurrentVersion {
    $Source = Get-Content -LiteralPath "navixav\__init__.py" -Raw -Encoding UTF8
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
    $Content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
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

# Espace insécable exigée par la typographie française devant les ponctuations
# doubles et à l'intérieur des guillemets.
$NoBreakSpace = [char]0x00A0

# Phrase de note de version : majuscule initiale, point final et espaces
# insécables. L'espace n'est ajoutée devant « : » que si l'auteur en a déjà
# mis une, sinon les URL et les heures seraient déformées.
function Format-FrenchSentence([string]$Text) {
    $Value = ([string]$Text).Trim()
    if (-not $Value) { return "" }
    # Le préfixe « feat(scope): » du commit ne concerne que le dépôt. La liste
    # des types est explicite : « Attention : » ne doit pas être amputé.
    $Value = [regex]::Replace(
        $Value,
        '^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)(\([^)]+\))?!?:\s*',
        ''
    )
    if (-not $Value) { return "" }
    $Value = $Value.Substring(0, 1).ToUpperInvariant() + $Value.Substring(1)
    $Value = [regex]::Replace($Value, '(?<=\S)[ \t]+([:;!?])', "$NoBreakSpace`$1")
    $Value = [regex]::Replace($Value, '(?<=\p{L})([;!?])', "$NoBreakSpace`$1")
    # « : » collé à un mot et suivi d'une espace. Les URL (« https:// ») et les
    # heures (« 12:05 ») restent intactes : elles ne remplissent pas ces deux
    # conditions à la fois.
    $Value = [regex]::Replace($Value, '(?<=\p{L}):(?=\s|$)', "$NoBreakSpace" + ":")
    $Value = [regex]::Replace($Value, '«[ \t]*', "«$NoBreakSpace")
    $Value = [regex]::Replace($Value, '[ \t]*»', "$NoBreakSpace»")
    if ($Value -notmatch '[.!?»]$') { $Value += "." }
    return $Value
}

function Add-Category(
    [System.Collections.Generic.List[string]]$Lines,
    [string]$Title,
    [object[]]$Items
) {
    $Sentences = @($Items | ForEach-Object { Format-FrenchSentence $_ } | Where-Object { $_ })
    if ($Sentences.Count -eq 0) { return }
    $Lines.Add("## $Title")
    $Lines.Add("")
    foreach ($Sentence in $Sentences) {
        $Lines.Add("- $Sentence")
    }
    $Lines.Add("")
}

# Nouveautés et corrections rédigées à la main pour cette version.
#
# Les sujets de commit décrivent le dépôt, pas le produit : ils donnent des
# notes de version illisibles pour l'utilisateur. RELEASE_HIGHLIGHTS.md prend
# donc le pas sur eux, section par section, dès qu'il contient au moins une
# puce. Le fichier est réinitialisé après la publication.
#
# Les puces vont aux nouveautés jusqu'au titre « ## Corrections », qui bascule
# les suivantes vers la section des correctifs.
function Get-Highlights([string]$Path) {
    $Empty = [pscustomobject]@{ Features = @(); Fixes = @() }
    if (-not (Test-Path -LiteralPath $Path)) { return $Empty }
    $Content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $Features = [System.Collections.Generic.List[string]]::new()
    $Fixes = [System.Collections.Generic.List[string]]::new()
    $Items = $Features
    $Current = ""
    $InComment = $false
    foreach ($Line in ($Content -split "`r?`n")) {
        # Les exemples du gabarit vivent dans un commentaire HTML : ils ne
        # doivent jamais se retrouver dans les notes de version.
        if ($InComment) {
            if ($Line -match '-->') { $InComment = $false }
            continue
        }
        if ($Line -match '<!--') {
            if ($Line -notmatch '-->') { $InComment = $true }
            continue
        }
        if ($Line -match '^\s*[-*]\s+(?<text>.+?)\s*$') {
            if ($Current) { $Items.Add($Current) }
            $Current = $Matches.text
        } elseif ($Current -and $Line -match '^\s+\S') {
            # Puce sur plusieurs lignes : la continuation est indentée.
            $Current = "$Current " + $Line.Trim()
        } elseif (-not $Line.Trim()) {
            if ($Current) { $Items.Add($Current) }
            $Current = ""
        }
    }
    if ($Current) { $Items.Add($Current) }
    return $Items.ToArray()
}

$HighlightsTemplate = @"
# Nouveautés de la prochaine version

Décrivez ici, en français et du point de vue de l'utilisateur, ce que la
prochaine version apporte. Une puce par nouveauté. Ce fichier remplace les
sujets de commit dans la section « Nouvelles fonctionnalités » des notes de
version, puis il est réinitialisé par ``scripts\prepare_release.ps1``.

<!-- Exemple, à supprimer :
- Le suivi du vol affiche le temps restant avant l'arrivée.
-->
"@

$Current = Get-CurrentVersion
$LastTag = git tag --list "v*" --sort=-version:refname | Select-Object -First 1
$Commits = Get-ReleaseCommits $LastTag
if ($Commits.Count -eq 0) {
    throw "Aucun nouveau commit depuis $LastTag."
}
$EffectiveBump = if ($Bump -eq "auto") { Get-AutomaticBump $Commits } else { $Bump }
$Next = Get-NextVersion $Current $EffectiveBump
$Date = Get-Date -Format "yyyy-MM-dd"
$FrenchDate = (Get-Date).ToString(
    "d MMMM yyyy",
    [System.Globalization.CultureInfo]::GetCultureInfo("fr-FR")
)
$HighlightsPath = Join-Path $ProjectRoot "RELEASE_HIGHLIGHTS.md"
$Highlights = Get-Highlights $HighlightsPath

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
$Notes.Add("Publication du $FrenchDate.")
$Notes.Add("")
# Les nouveautés rédigées à la main l'emportent : elles parlent du produit,
# là où le sujet de commit ne décrit que le dépôt.
if ($Highlights.Count -gt 0) {
    Add-Category $Notes "Nouvelles fonctionnalités" $Highlights
} else {
    Write-Warning "RELEASE_HIGHLIGHTS.md est vide : les notes reprennent les sujets de commit."
    Add-Category $Notes "Nouvelles fonctionnalités" $Features
}
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
    $Existing = Get-Content -LiteralPath "CHANGELOG.md" -Raw -Encoding UTF8
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

# Le fichier repart vide : les nouveautés d'une version ne doivent jamais
# réapparaître dans la suivante.
[System.IO.File]::WriteAllText(
    $HighlightsPath,
    ($HighlightsTemplate + "`n"),
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Version préparée : $Current -> $Next ($EffectiveBump)" -ForegroundColor Green
Write-Host "Notes : $ProjectRoot\RELEASE_NOTES.md"
Write-Output $Next
