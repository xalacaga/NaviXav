# Recupere la declaration compilee du panneau NaviXav pour MSFS.
#
# Deux chemins mènent au `.spb`, et le script les couvre tous les deux :
#
#  1. `fspackagetool.exe` en ligne de commande. Ce n'est qu'un lanceur : il
#     s'attache à l'exécutable du simulateur, qui fait le travail. Sur une
#     installation Microsoft Store il sort parfois en code 0 sans rien écrire.
#  2. L'éditeur de projet du mode développeur, dans le simulateur, qui lui
#     produit toujours quelque chose et affiche ses erreurs.
#
# Le script tente le premier, puis cherche le fichier où que l'un ou l'autre
# l'ait déposé — y compris dans le dossier Communauté, quand le simulateur a
# recopié le paquet lui-même.
#
# Le `.spb` obtenu est versionné : personne n'a besoin du SDK pour installer le
# panneau, seulement pour le reconstruire, et seulement si sa déclaration
# change.

[CmdletBinding()]
param(
    [string]$Sdk = "C:\MSFS 2024 SDK",
    [string[]]$AlsoSearch = @(),
    [switch]$SkipCompile
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $root "msfs-panel\build"
$project = Join-Path $buildDir "navixav-toolbar.xml"
$tool = Join-Path $Sdk "Tools\bin\fspackagetool.exe"

if (-not (Test-Path $project)) { throw "Projet introuvable : $project" }

if (-not $SkipCompile) {
    if (-not (Test-Path $tool)) { throw "fspackagetool introuvable : $tool" }
    Push-Location $buildDir
    try {
        & $tool "navixav-toolbar.xml"
        if ($LASTEXITCODE -ne 0) { throw "fspackagetool a echoue (code $LASTEXITCODE)." }
    }
    finally {
        Pop-Location
    }
}

$places = @($buildDir) + $AlsoSearch
$built = $null
foreach ($place in $places) {
    if (-not (Test-Path $place)) { continue }
    $found = Get-ChildItem -Path $place -Recurse -Filter "navixav-toolbar.spb" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found) { $built = $found; break }
}

if (-not $built) {
    throw @"
Aucun .spb produit.

La ligne de commande du SDK ne fait rien sur certaines installations. Passe par
le simulateur :

  1. MSFS 2024, mode developpeur actif.
  2. Barre de menus > File > Open project...
     $project
  3. Dans l'editeur de projet, bouton Build All.
  4. Relance ce script :  .\scripts\build_msfs_panel.ps1 -SkipCompile
     (ajoute -AlsoSearch "<dossier>" si l'editeur a ecrit ailleurs)
"@
}

$target = Join-Path $root "navixav\msfs_panel\navixav-toolbar\InGamePanels"
New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item $built.FullName (Join-Path $target "navixav-toolbar.spb") -Force
Write-Output "Trouve : $($built.FullName)"
Write-Output "Copie  : $target"
