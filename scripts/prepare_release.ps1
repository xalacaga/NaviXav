[CmdletBinding()]
param(
    [ValidateSet("auto", "major", "minor", "patch")]
    [string]$Bump = "auto",
    # Publication d'une version sans changement visible par l'utilisateur : les
    # notes reprennent alors les sujets de commit, faute de mieux.
    [switch]$AllowGenericNotes
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

# Les textes de publication (Flightsim.to, Buy Me a Coffee, notice de
# l'installateur) annoncent un numéro de version et un nom de fichier
# d'installation. Laissés à la main, ils dérivent silencieusement et la page
# publique finit par décrire une version que plus personne ne télécharge.
function Update-PublishingVersions([string]$Current, [string]$Next) {
    $Root = Join-Path $ProjectRoot "publishing"
    if (-not (Test-Path -LiteralPath $Root)) { return }

    # Le journal de la fiche Flightsim.to est reconstruit plus bas depuis
    # CHANGELOG.md : il porte l'historique complet, donc le numéro de chaque
    # version déjà publiée. L'aligner transformerait le titre de la version
    # précédente en celui de la version préparée, et le garde-fou y verrait
    # autant de publications oubliées qu'il existe de versions.
    $Generated = @("flightsim-to-changelog.txt")

    # Une annonce « what's new » porte le numéro de la version qu'elle
    # annonce : c'est un texte daté, pas une fiche à tenir à jour. L'aligner
    # daterait de la version préparée l'annonce d'une version déjà publiée.
    $Historical = '^flightsim-to-whats-new-\d+\.\d+\.\d+\.txt$'

    $Files = @(
        Get-ChildItem -LiteralPath $Root -Recurse -File -Include "*.md", "*.txt" |
            Where-Object {
                $Generated -notcontains $_.Name -and $_.Name -notmatch $Historical
            }
    )

    # Une version précédée de « v » décrit une borne historique immuable
    # (par exemple la dernière Release encore disponible sous une ancienne
    # licence), pas la Release en cours de préparation.
    $Pattern = "(?<!v)" + [regex]::Escape($Current)
    $Touched = @()
    foreach ($File in $Files) {
        $Content = [System.IO.File]::ReadAllText($File.FullName)
        $Updated = [regex]::Replace($Content, $Pattern, $Next)
        if ($Updated -ne $Content) {
            [System.IO.File]::WriteAllText(
                $File.FullName,
                $Updated,
                [System.Text.UTF8Encoding]::new($false)
            )
            $Touched += $File.Name
        }
    }

    # Garde-fou : toute version résiduelle signale une publication oubliée.
    $Stale = @()
    foreach ($File in $Files) {
        $Content = [System.IO.File]::ReadAllText($File.FullName)
        foreach ($Match in [regex]::Matches($Content, '\d+\.\d+\.\d+')) {
            if ($Match.Value -eq $Next) { continue }

            # Une adresse IPv4 contient elle aussi un triplet qui ressemble à
            # une version (127.0.0 dans 127.0.0.1). Le quatrième octet la rend
            # sans ambiguïté et ne doit jamais être réécrit ni signalé.
            $AfterMatch = $Match.Index + $Match.Length
            $SuffixLength = [Math]::Min(5, $Content.Length - $AfterMatch)
            $Suffix = $Content.Substring($AfterMatch, $SuffixLength)
            if ($Suffix -match '^\.\d{1,3}(?!\d)') {
                continue
            }

            # « v1.4.12 » peut être une Release historique citée à dessein.
            if ($Match.Index -gt 0 -and $Content[$Match.Index - 1] -eq 'v') {
                continue
            }

            # PolyForm Noncommercial 1.0.0 est le nom officiel de la licence,
            # pas une version de NaviXav. Le préfixe accepte les retours à la
            # ligne utilisés dans les textes de publication.
            $PrefixStart = [Math]::Max(0, $Match.Index - 80)
            $Prefix = $Content.Substring($PrefixStart, $Match.Index - $PrefixStart)
            if ($Prefix -match 'PolyForm\s+Noncommercial(?:\s+License)?\s*$') {
                continue
            }

            $Stale += "$($File.Name) : $($Match.Value)"
        }
    }
    if ($Stale.Count -gt 0) {
        throw @"
Publications non alignées sur la version $Next :
$($Stale | Sort-Object -Unique | ForEach-Object { "  - $_" } | Out-String)
Corrige ces fichiers dans publishing\ puis relance la préparation.
"@
    }

    if ($Touched.Count -gt 0) {
        Write-Host "Publications alignées : $($Touched -join ', ')" -ForegroundColor Green
    }
}

# Espace insécable exigée par la typographie française devant les ponctuations
# doubles et à l'intérieur des guillemets.
$NoBreakSpace = [char]0x00A0

# Langues de l'interface, dans l'ordre où elles apparaissent dans i18n.js.
# Une note de version est un texte que l'utilisateur lit : elle suit donc la
# même règle que le reste de l'interface et existe dans toutes les langues que
# NaviXav parle. « en » reste la langue de la release GitHub et le repli.
$Locales = @("en", "fr", "de", "es", "it", "pt", "nl", "pl")

$SectionTitles = @{
    en = @{ Added = "Added";      Fixed = "Fixed";       Changed = "Changed" }
    fr = @{ Added = "Nouveautés"; Fixed = "Corrections"; Changed = "Modifications" }
    de = @{ Added = "Neu";        Fixed = "Behoben";     Changed = "Geändert" }
    es = @{ Added = "Novedades";  Fixed = "Correcciones";Changed = "Cambios" }
    it = @{ Added = "Novità";     Fixed = "Correzioni";  Changed = "Modifiche" }
    pt = @{ Added = "Novidades";  Fixed = "Correções";   Changed = "Alterações" }
    nl = @{ Added = "Nieuw";      Fixed = "Opgelost";    Changed = "Gewijzigd" }
    pl = @{ Added = "Nowości";    Fixed = "Poprawki";    Changed = "Zmiany" }
}

$ReleasedOn = @{
    en = "Released on {0}."
    fr = "Publié le {0}."
    de = "Veröffentlicht am {0}."
    es = "Publicado el {0}."
    it = "Pubblicato il {0}."
    pt = "Publicado em {0}."
    nl = "Uitgebracht op {0}."
    pl = "Opublikowano {0}."
}

$InstallerFooter = @{
    en = "The installer is verified against its SHA-256 checksum before any automatic update."
    fr = "L'installateur est vérifié par sa somme de contrôle SHA-256 avant toute mise à jour automatique."
    de = "Das Installationsprogramm wird vor jeder automatischen Aktualisierung anhand seiner SHA-256-Prüfsumme verifiziert."
    es = "El instalador se verifica con su suma de comprobación SHA-256 antes de cualquier actualización automática."
    it = "Il programma di installazione è verificato tramite il suo checksum SHA-256 prima di ogni aggiornamento automatico."
    pt = "O instalador é verificado através da sua soma de verificação SHA-256 antes de qualquer atualização automática."
    nl = "Het installatieprogramma wordt vóór elke automatische update geverifieerd aan de hand van zijn SHA-256-controlesom."
    pl = "Instalator jest weryfikowany za pomocą sumy kontrolnej SHA-256 przed każdą automatyczną aktualizacją."
}

# Journal pour la fiche Flightsim.to.
#
# Le site n'accepte ni Markdown ni HTML : ses puces sont des lignes indentées,
# et ses titres se reconnaissent à leur émoji. Le fichier reprend donc tout
# l'historique de CHANGELOG.md dans cette présentation, prêt à être collé d'un
# bloc — recopier une seule version obligerait à fusionner à la main, et c'est
# là que les journaux divergent.
#
# Les émojis sont assemblés depuis leur point de code : Windows PowerShell 5.1
# lit le script en Windows-1252 si le BOM venait à disparaître, et des paires
# de substitution écrites en clair y deviendraient illisibles.
$FsEmoji = @{
    Log      = [char]::ConvertFromUtf32(0x1F4D1)
    Lock     = [char]::ConvertFromUtf32(0x1F512)
    Release  = [char]::ConvertFromUtf32(0x1F680)
    Added    = [char]::ConvertFromUtf32(0x2728)
    Changed  = [char]::ConvertFromUtf32(0x1F504)
    Fixed    = [char]::ConvertFromUtf32(0x1F6E0) + [char]0xFE0F
}

# La vérification du programme d'installation vaut pour toutes les versions
# depuis la 1.4.11 : elle est annoncée une fois en tête plutôt que répétée sous
# chaque version, où elle noierait les nouveautés.
$FsSecurityNote = "Security Note: Starting from version 1.4.11, the installer is systematically verified against its SHA-256 checksum before any automatic update."

# Indentation qui fait une puce sur Flightsim.to.
$FsBullet = "    "

function ConvertTo-FlightsimToChangelog([string]$Markdown) {
    $Lines = [System.Collections.Generic.List[string]]::new()
    $Lines.Add("$($FsEmoji.Log) Changelog | NaviXav")
    $Lines.Add("")
    $Lines.Add("$FsBullet$($FsEmoji.Lock) $FsSecurityNote")

    # La version en cours est mise de côté avant d'être écrite : une version
    # dont il ne reste rien après filtrage ne doit pas laisser un titre seul.
    $Block = [System.Collections.Generic.List[string]]::new()
    $Bullets = 0
    $Skipping = $false

    foreach ($Line in ($Markdown -split "`r?`n")) {
        $Text = $Line.TrimEnd()

        if ($Text -match '^##\s+\[(?<version>[^\]]+)\]\s*-\s*(?<date>.+)$') {
            if ($Bullets -gt 0) {
                $Lines.Add("")
                $Lines.AddRange($Block)
            }
            $Block.Clear()
            $Bullets = 0
            $Skipping = $false
            $Block.Add(
                "$($FsEmoji.Release) [$($Matches.version)] - $($Matches.date.Trim())"
            )
            continue
        }

        # Les versions 1.4.8 et 1.4.9 titrent leurs rubriques au niveau 2, avant
        # que le format ne se fixe. Les deux niveaux sont donc acceptés : s'en
        # tenir au niveau 3 rattacherait leurs puces à la version précédente.
        if ($Text -match '^#{2,3}\s+(?<title>[A-Za-z].*)$') {
            $Title = $Matches.title.Trim()
            # « Changed » ne recueille que les sujets de commit, faute de texte
            # rédigé : du vocabulaire de dépôt, parfois en français et parfois
            # tronqué. Cela a sa place dans l'historique du dépôt, pas sur une
            # fiche publique lue en anglais.
            if ($Title -eq "Changed") {
                $Skipping = $true
                continue
            }
            $Skipping = $false
            $Icon = switch ($Title) {
                "Added" { $FsEmoji.Added }
                "Fixed" { $FsEmoji.Fixed }
                default { $FsEmoji.Changed }
            }
            # Une rubrique se détache de ce qui précède, sauf quand elle suit
            # immédiatement le numéro de version : là, les deux lignes forment
            # le titre du bloc.
            $Previous = if ($Block.Count -gt 0) { $Block[$Block.Count - 1] } else { "" }
            if ($Previous -and -not $Previous.StartsWith($FsEmoji.Release)) {
                $Block.Add("")
            }
            $Block.Add("$Icon $Title")
            continue
        }

        if (-not $Skipping -and $Text -match '^-\s+(?<item>.+)$') {
            $Block.Add("")
            $Block.Add("$FsBullet$($Matches.item.Trim())")
            $Bullets += 1
            continue
        }
        # Le reste — titre du fichier, lignes vides, et la phrase sur la somme
        # de contrôle répétée sous chaque version — n'a pas sa place ici : la
        # note de sécurité est déjà donnée une fois en tête.
    }

    if ($Bullets -gt 0) {
        $Lines.Add("")
        $Lines.AddRange($Block)
    }
    $Lines.Add("")
    return ($Lines -join "`n")
}

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

# Typographie neutre, pour toutes les langues sauf le français : majuscule
# initiale et point final, sans toucher à la ponctuation. Les espaces
# insécables de Format-FrenchSentence sont une règle française ; les appliquer
# à l'anglais ou au néerlandais y introduirait des espaces parasites.
function Format-PlainSentence([string]$Text) {
    $Value = ([string]$Text).Trim()
    if (-not $Value) { return "" }
    $Value = [regex]::Replace(
        $Value,
        '^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)(\([^)]+\))?!?:\s*',
        ''
    )
    if (-not $Value) { return "" }
    $Value = $Value.Substring(0, 1).ToUpperInvariant() + $Value.Substring(1)
    if ($Value -notmatch '[.!?»”]$') { $Value += "." }
    return $Value
}

function Format-Sentence([string]$Text, [string]$Locale) {
    if ($Locale -eq "fr") { return Format-FrenchSentence $Text }
    return Format-PlainSentence $Text
}

function Add-Category(
    [System.Collections.Generic.List[string]]$Lines,
    [string]$Title,
    [object[]]$Items,
    [string]$Locale
) {
    $Sentences = @($Items | ForEach-Object { Format-Sentence $_ $Locale } | Where-Object { $_ })
    if ($Sentences.Count -eq 0) { return }
    $Lines.Add("## $Title")
    $Lines.Add("")
    foreach ($Sentence in $Sentences) {
        $Lines.Add("- $Sentence")
    }
    $Lines.Add("")
}

# Texte d'une entrée dans une langue donnée, avec repli sur l'anglais.
function Get-EntryText($Entry, [string]$Locale) {
    if ($null -eq $Entry) { return "" }
    if ($Entry.ContainsKey($Locale)) { return $Entry[$Locale] }
    return $Entry["en"]
}

function Select-EntryTexts([object[]]$Entries, [string]$Locale) {
    return @(
        $Entries |
            Where-Object { $null -ne $_ } |
            ForEach-Object { Get-EntryText $_ $Locale }
    )
}

# Nouveautés et corrections rédigées à la main pour cette version.
#
# Les sujets de commit décrivent le dépôt, pas le produit : ils donnent des
# notes de version illisibles pour l'utilisateur. RELEASE_HIGHLIGHTS.json prend
# donc le pas sur eux, section par section, dès qu'il contient au moins une
# entrée. Le fichier est réinitialisé après la publication.
#
# Chaque entrée porte son texte dans les langues de l'interface. Le format est
# structuré plutôt que rédigé en Markdown : huit traductions par changement ne
# tiennent pas dans une liste à puces sans qu'on finisse par mélanger les
# changements entre eux.
function Read-HighlightEntries($Entries) {
    $Result = [System.Collections.Generic.List[hashtable]]::new()
    foreach ($Entry in @($Entries)) {
        if ($null -eq $Entry) { continue }
        $Texts = @{}
        foreach ($Locale in $Locales) {
            $Value = ([string]$Entry.$Locale).Trim()
            if ($Value) { $Texts[$Locale] = $Value }
        }
        if ($Texts.Count -eq 0) { continue }
        foreach ($Required in @("en", "fr")) {
            if (-not $Texts.ContainsKey($Required)) {
                throw @"
RELEASE_HIGHLIGHTS.json : une entrée n'a pas de texte « $Required ».

Chaque entrée doit au moins porter « fr » et « en ». Les autres langues
retombent sur « en » lorsqu'elles manquent.

Entrée fautive : $(($Texts.Values | Select-Object -First 1))
"@
            }
        }
        $Result.Add($Texts)
    }
    return $Result.ToArray()
}

function Get-Highlights([string]$Path) {
    $Empty = [pscustomobject]@{ Features = @(); Fixes = @() }
    if (-not (Test-Path -LiteralPath $Path)) { return $Empty }
    $Content = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if (-not $Content.Trim()) { return $Empty }
    try {
        $Data = $Content | ConvertFrom-Json
    } catch {
        throw "RELEASE_HIGHLIGHTS.json est illisible : $($_.Exception.Message)"
    }
    return [pscustomobject]@{
        Features = @(Read-HighlightEntries $Data.added)
        Fixes = @(Read-HighlightEntries $Data.fixed)
    }
}

# Notes de version d'une langue, prêtes à être écrites sur disque.
function New-ReleaseNotes(
    [string]$Locale,
    [string]$Version,
    [string]$Date,
    [object[]]$AddedEntries,
    [object[]]$FixedEntries,
    [object[]]$ChangedItems
) {
    $Titles = $SectionTitles[$Locale]
    $Lines = [System.Collections.Generic.List[string]]::new()
    $Lines.Add("# NaviXav $Version")
    $Lines.Add("")
    $Lines.Add(($ReleasedOn[$Locale] -f $Date))
    $Lines.Add("")
    Add-Category $Lines $Titles.Added (Select-EntryTexts $AddedEntries $Locale) $Locale
    Add-Category $Lines $Titles.Fixed (Select-EntryTexts $FixedEntries $Locale) $Locale
    # Les sujets de commit n'existent que dans la langue où ils ont été écrits :
    # seul leur titre de section est traduit. C'est un repli, pas une note.
    Add-Category $Lines $Titles.Changed $ChangedItems $Locale
    if ($Lines[$Lines.Count - 1] -ne "") { $Lines.Add("") }
    $Lines.Add($InstallerFooter[$Locale])
    $Lines.Add("")
    return $Lines
}

$HighlightsTemplate = @"
{
  "_comment": [
    "Highlights for the next release. Update this file for EVERY code change,",
    "not only immediately before a release.",
    "",
    "One entry per change, written from the user's point of view, in the eight",
    "interface languages. The rule is the same as for i18n.js: a text the user",
    "reads exists in every language NaviXav speaks.",
    "",
    "'fr' and 'en' are required; a missing language falls back to 'en'.",
    "Aviation identifiers and METAR/MCDU notation stay unchanged in every",
    "language.",
    "",
    "prepare_release.ps1 turns these entries into RELEASE_NOTES.md and its",
    "localised siblings, and prepends a version section to CHANGELOG.md, the",
    "history the application reads, then resets this file."
  ],
  "added": [],
  "fixed": []
}
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
$HighlightsPath = Join-Path $ProjectRoot "RELEASE_HIGHLIGHTS.json"
$Highlights = Get-Highlights $HighlightsPath

# Contrôle avant toute modification : rien n'est publié avec des notes qui ne
# décrivent pas la version. Échouer ici coûte deux secondes, pas une
# construction complète.
if (
    $Highlights.Features.Count -eq 0 -and
    $Highlights.Fixes.Count -eq 0 -and
    -not $AllowGenericNotes
) {
    throw @"
RELEASE_HIGHLIGHTS.json does not describe this release.

Add one entry per change to "added" or "fixed", written from the user's point
of view, with at least its "fr" and "en" texts, then run the command again.

To publish without a visible change, run again with -AllowGenericNotes.
"@
}

Set-VersionInFile "navixav\__init__.py" '__version__\s*=\s*"\d+\.\d+\.\d+"' "__version__ = `"$Next`""
Set-VersionInFile "pyproject.toml" '(?m)^version\s*=\s*"\d+\.\d+\.\d+"' "version = `"$Next`""
Update-PublishingVersions $Current $Next

$Features = @($Commits | Where-Object { $_ -match '^feat(\([^)]+\))?!?:' })
$Fixes = @($Commits | Where-Object { $_ -match '^fix(\([^)]+\))?:' })
$Other = @(
    $Commits | Where-Object {
        $_ -notmatch '^feat(\([^)]+\))?!?:' -and
        $_ -notmatch '^fix(\([^)]+\))?:' -and
        $_ -notmatch '^chore\(release\):'
    }
)
# Les textes rédigés à la main l'emportent, section par section : ils parlent
# du produit, là où le sujet de commit ne décrit que le dépôt. Un sujet de
# commit repris faute de mieux n'existe que dans sa langue d'origine : il est
# rangé sous « en », d'où toutes les autres langues le reprendront.
$FeatureItems = @(
    if ($Highlights.Features.Count -gt 0) {
        $Highlights.Features
    } else {
        $Features | ForEach-Object { @{ en = $_ } }
    }
)
$FixItems = @(
    if ($Highlights.Fixes.Count -gt 0) {
        $Highlights.Fixes
    } else {
        $Fixes | ForEach-Object { @{ en = $_ } }
    }
)

# Une note par langue de l'interface. « RELEASE_NOTES.md » reste l'anglais :
# c'est le corps de la release GitHub, lu par tout le monde.
$NotesByLocale = @{}
foreach ($Locale in $Locales) {
    $NotesByLocale[$Locale] = New-ReleaseNotes `
        -Locale $Locale `
        -Version $Next `
        -Date $Date `
        -AddedEntries $FeatureItems `
        -FixedEntries $FixItems `
        -ChangedItems $Other
}
$Notes = $NotesByLocale["en"]

foreach ($Locale in $Locales) {
    $Text = ($NotesByLocale[$Locale] -join "`n")
    $Targets = @("RELEASE_NOTES.$Locale.md")
    if ($Locale -eq "en") { $Targets += "RELEASE_NOTES.md" }
    foreach ($Target in $Targets) {
        [System.IO.File]::WriteAllText(
            (Join-Path $ProjectRoot $Target),
            $Text,
            [System.Text.UTF8Encoding]::new($false)
        )
    }
}

# Le journal reste en anglais : c'est un historique de dépôt, que les Paramètres
# se contentent de relire.
# Dans le journal, la version porte le titre de section : ses rubriques passent
# donc un niveau plus bas, sinon « Added » a le même rang que « [1.4.9] ».
$ChangelogBody = @(
    $Notes | Select-Object -Skip 4 | ForEach-Object {
        if ($_ -like "## *") { "#" + $_ } else { $_ }
    }
) -join "`n"
$ChangelogEntry = "## [$Next] - $Date`n`n" + $ChangelogBody
if (Test-Path -LiteralPath "CHANGELOG.md") {
    $Existing = Get-Content -LiteralPath "CHANGELOG.md" -Raw -Encoding UTF8
    $Header = "# Changelog`n`n"
    $Body = if ($Existing.StartsWith($Header)) { $Existing.Substring($Header.Length) } else { $Existing }
    [System.IO.File]::WriteAllText(
        (Join-Path $ProjectRoot "CHANGELOG.md"),
        ($Header + $ChangelogEntry + "`n" + $Body),
        [System.Text.UTF8Encoding]::new($false)
    )
} else {
    [System.IO.File]::WriteAllText(
        (Join-Path $ProjectRoot "CHANGELOG.md"),
        ("# Changelog`n`n" + $ChangelogEntry),
        [System.Text.UTF8Encoding]::new($false)
    )
}

# Journal de la fiche Flightsim.to, reconstruit depuis le journal qui vient
# d'être écrit : il porte donc toujours l'historique complet et à jour, sans
# rien à fusionner à la main avant de le coller.
$FlightsimToPath = Join-Path $ProjectRoot "publishing\flightsim-to-changelog.txt"
[System.IO.File]::WriteAllText(
    $FlightsimToPath,
    (ConvertTo-FlightsimToChangelog (
        Get-Content -LiteralPath (Join-Path $ProjectRoot "CHANGELOG.md") -Raw -Encoding UTF8
    )),
    [System.Text.UTF8Encoding]::new($false)
)

# Le fichier repart vide : les nouveautés d'une version ne doivent jamais
# réapparaître dans la suivante.
[System.IO.File]::WriteAllText(
    $HighlightsPath,
    ($HighlightsTemplate + "`n"),
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Version prepared: $Current -> $Next ($EffectiveBump)" -ForegroundColor Green
Write-Host "Notes: $ProjectRoot\RELEASE_NOTES.md ($($Locales -join ', '))"
Write-Host "Flightsim.to: $FlightsimToPath"
Write-Output $Next
