[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Destination = Join-Path $ProjectRoot "navixav\web\static\aircraft"
$CreditsPath = Join-Path $ProjectRoot "AIRCRAFT_PHOTO_CREDITS.md"
$UserAgent = "NaviXav/0.1 aircraft-photo-curation (local application)"

# Curated Wikimedia Commons photographs. The file title is deliberately pinned:
# running this script again refreshes the same work, not an arbitrary search result.
$Photos = [ordered]@{
    "airbus-a319" = "United_Airbus_A319_(13942617705).jpg"
    "airbus-a320" = "Airbus_A320-214,_Airbus_Industrie_JP7617615.jpg"
    "airbus-a321" = "Airbus_A321-200_(37119973880).jpg"
    "airbus-a330" = "Delta_Air_Lines_Airbus_A330-300_N830NW_departing_Boston_July_2026_1.jpg"
    "airbus-a340" = "Frankfurt_Airport_Lufthansa_Airbus_A340-313_D-AIGY_(DSC02566).jpg"
    "airbus-a350" = "EGLF_-_Airbus_A350-941_-_F-WZNW.jpg"
    "airbus-a380" = "A6-EDY_A380_Emirates_31_jan_2013_jfk_(8442269364)_(cropped).jpg"
    "piper-aerostar" = "TedSmith600AerostarC-FEHK.JPG"
    "boeing-b737" = "Delta_Boeing_737-800_N371DA_departing_Boston_June_2025.jpg"
    "boeing-b777" = "Cathay_Pacific_Boeing_777-200;_B-HNL@HKG.jpg"
    "beech-king-air" = "Beechcraft_King_Air_350_N614CW_FDK_MD1.jpg"
    "beech-sierra" = "Beechcraft_C24R_Sierra_(N62BV,_cn_MC-649)_(4-13-2024).jpg"
    "beech-bonanza" = "Beech_Bonanza_Takeoff_(5517383917).jpg"
    "beech-baron" = "Beechcraft_Baron_58.jpg"
    "beech-duke" = "Duke2.jpg"
    "britten-norman-bn2" = "BN-2_Islander_Crosswind_landing_F369-10A-V.jpg"
    "cessna-c172" = "2001_N793SP_Cessna_172S_Skyhawk_at_Doylestown_Airport,_Pennsylvania.jpg"
    "cessna-cj4" = "Reliant_Air_Cessna_Citation_Danbury_Municipal_Airport_KDXR.jpg"
    "cessna-c414" = "PH-MZL_Cessna_414_Chancellor_(EHMZ_1990-08-20).jpg"
    "diamond-da42" = "OH-DAC_Tour_de_Sky_Oulu_20140810_02.JPG"
    "diamond-da62" = "Diamond_Sky,_ES-KEN,_Diamond_DA-62_(36833726330).jpg"
    "fokker-f28" = "STOCKHOLM_ARLANDA_MARCH_2001_AIR_BOTNIA_FOKKER_F28_FELLOWSHIP_SE-DGP_(8878528980).jpg"
    "focke-wulf-fw190" = "Fw_190A-3_JG_2_in_Britain_1942.jpg"
    "bombardier-learjet35" = "Learjet_35_(8738280921).jpg"
    "north-american-p51" = "P-51-361.jpg"
    "piper-pa24" = "Pa24-N5760P-071126-01-16.jpg"
    "pilatus-pc12" = "Pilatus_PC-12_N610GH_FDK_MD1.jpg"
    "pilatus-pc6" = "Pilatus_PC-6_SkydiveLillo_JD18032008_(cropped).jpg"
    "bae-avro-rj" = "Avro_RJ85.jpg"
    "cirrus-sf50" = "Cirrus_Vision_SF50_N124MW_cn_0009_(28664083278).jpg"
    "daher-tbm930" = "Daher_TBM_930,_EBACE_2018,_Le_Grand-Saconnex_(BL7C0504).jpg"
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$titles = $Photos.Values | ForEach-Object { "File:$_" }
$encoded = [uri]::EscapeDataString(($titles -join "|"))
$api = "https://commons.wikimedia.org/w/api.php?action=query&format=json&formatversion=2&prop=imageinfo&iiprop=url%7Cextmetadata%7Cmime%7Csize&iiurlwidth=640&titles=$encoded"
$pages = (Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = $UserAgent }).query.pages
$byTitle = @{}
foreach ($page in $pages) { $byTitle[$page.title.Replace(" ", "_")] = $page }

$credits = @(
    "# Aircraft photo credits",
    "",
    "The photographs below are bundled with NaviXav. Each image remains under",
    "the licence stated on its Wikimedia Commons description page.",
    ""
)

foreach ($entry in $Photos.GetEnumerator()) {
    $title = "File:$($entry.Value)"
    $page = $byTitle[$title.Replace(" ", "_")]
    if (-not $page -or -not $page.imageinfo) { throw "Commons image not found: $title" }
    $info = $page.imageinfo[0]
    if ($info.mime -notin @("image/jpeg", "image/png")) {
        throw "Unsupported image format for ${title}: $($info.mime)"
    }
    $metadata = $info.extmetadata
    $license = $metadata.LicenseShortName.value
    $artist = [regex]::Replace($metadata.Artist.value, "<[^>]+>", " ")
    $artist = [System.Net.WebUtility]::HtmlDecode($artist)
    $artist = [regex]::Replace($artist, "\s+", " ").Trim()
    if (-not $license -or -not $artist) { throw "Incomplete attribution for $title" }
    if ($license -notmatch "^(CC0|CC BY(?:-SA)?|Public domain)") {
        throw "Unexpected licence for ${title}: $license"
    }

    $extension = if ($info.mime -eq "image/png") { ".png" } else { ".jpg" }
    $output = Join-Path $Destination ($entry.Key + $extension)
    if (-not (Test-Path -LiteralPath $output)) {
        $fileName = [uri]::EscapeDataString([string]$entry.Value)
        $downloadUrl = "https://commons.wikimedia.org/wiki/Special:Redirect/file/${fileName}?width=640"
        $downloaded = $false
        foreach ($attempt in 1..3) {
            try {
                Invoke-WebRequest -Uri $downloadUrl -OutFile $output -Headers @{ "User-Agent" = $UserAgent }
                $downloaded = $true
                break
            }
            catch {
                if ($attempt -eq 3) { throw }
                Start-Sleep -Seconds (3 * $attempt)
            }
        }
        if (-not $downloaded) { throw "Download failed for $title" }
        Start-Sleep -Milliseconds 1500
    }
    $credits += "- **$($entry.Key)** - $artist, $license. [$($entry.Value)]($($info.descriptionurl))"
}

$credits += @(
    "",
    "The images are resized Wikimedia thumbnails; no other modification is applied."
)
$credits -join "`n" | Set-Content -LiteralPath $CreditsPath -Encoding utf8
Write-Host "Downloaded $($Photos.Count) aircraft photographs to $Destination"
Write-Host "Wrote attribution details to $CreditsPath"
