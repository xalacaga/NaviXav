[CmdletBinding()]
param(
    [switch]$SkipInstaller,
    [switch]$SkipToolInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VersionSource = Get-Content -LiteralPath (Join-Path $ProjectRoot "navixav\__init__.py") -Raw
if ($VersionSource -notmatch '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"') {
    throw "Version NaviXav introuvable dans navixav\__init__.py."
}
$Version = $Matches.version
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ReleaseDir = Join-Path $ProjectRoot "release"
$ModernSimConnect = "C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll"
$WebViewBootstrapper = Join-Path $ProjectRoot "installer\assets\MicrosoftEdgeWebView2Setup.exe"
$WebViewBootstrapperUrl = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
$AppIcon = Join-Path $ProjectRoot "assets\navixav.ico"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Find-Iscc {
    $command = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    return $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}

function Test-PythonImports([string]$Imports) {
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $VenvPython -c "import $Imports" 2>$null
    $Succeeded = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $PreviousPreference
    return $Succeeded
}

function New-PortableArchive([string]$Source, [string]$Destination) {
    for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
        try {
            if (Test-Path -LiteralPath $Destination) {
                Remove-Item -LiteralPath $Destination -Force
            }
            Compress-Archive -Path $Source -DestinationPath $Destination -CompressionLevel Optimal
            return
        }
        catch {
            if ($Attempt -eq 5) { throw }
            Write-Warning "Fichier de construction encore verrouillé ; nouvelle tentative $($Attempt + 1)/5."
            Start-Sleep -Seconds 2
        }
    }
}

Set-Location $ProjectRoot
Write-Step "Contrôle de l'environnement de construction"
if (-not [Environment]::Is64BitOperatingSystem) {
    throw "La construction NaviXav nécessite Windows 64 bits."
}
if (-not (Test-Path -LiteralPath $ModernSimConnect)) {
    throw "Le SDK MSFS et sa DLL SimConnect moderne sont requis pour construire la distribution."
}

Write-Step "Génération de l'icône NaviXav"
& (Join-Path $PSScriptRoot "generate_icon.ps1") -OutputPath $AppIcon

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if (-not $launcher) {
        if ($SkipToolInstall) {
            throw "Python 3.11+ est absent. Relance sans -SkipToolInstall pour l'installer."
        }
        $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
        if (-not $winget) { throw "Python et winget sont absents : installe Python 3.12." }
        Write-Step "Installation automatique de Python 3.12"
        & $winget.Source install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
        $launcher = Get-Command "py.exe" -ErrorAction SilentlyContinue
        if (-not $launcher) { throw "Python a été installé ; rouvre PowerShell puis relance ce script." }
    }
    Write-Step "Création de l'environnement Python isolé"
    & $launcher.Source -3 -m venv (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -c "import sys; assert sys.version_info >= (3, 11), sys.version"

Write-Step "Contrôle des bibliothèques du projet"
if (-not (Test-PythonImports "fastapi, requests, uvicorn, pydantic, pypdf")) {
    & $VenvPython -m pip install --disable-pip-version-check -e $ProjectRoot
}
if (-not (Test-PythonImports "webview")) {
    & $VenvPython -m pip install --disable-pip-version-check -e $ProjectRoot
}

if (-not (Test-PythonImports "PyInstaller")) {
    if ($SkipToolInstall) {
        throw "PyInstaller est absent. Relance sans -SkipToolInstall pour l'installer."
    }
    Write-Step "Installation automatique de PyInstaller"
    & $VenvPython -m pip install --disable-pip-version-check "pyinstaller>=6.10,<7"
}

Write-Step "Contrôle du composant Microsoft WebView2"
if (-not (Test-Path -LiteralPath $WebViewBootstrapper)) {
    New-Item -ItemType Directory -Path (Split-Path $WebViewBootstrapper) -Force | Out-Null
    Invoke-WebRequest -Uri $WebViewBootstrapperUrl -OutFile $WebViewBootstrapper
}
$WebViewSignature = Get-AuthenticodeSignature -LiteralPath $WebViewBootstrapper
if (
    $WebViewSignature.Status -ne "Valid" -or
    $WebViewSignature.SignerCertificate.Subject -notlike "*Microsoft Corporation*"
) {
    throw "Le programme d'installation WebView2 n'a pas une signature Microsoft valide."
}

Write-Step "Tests automatisés"
$TestTemp = Join-Path $env:TEMP "NaviXav-tests-$PID"
& $VenvPython -m pytest -m "not live_msfs" --basetemp $TestTemp -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { throw "Les tests ont échoué ; distribution annulée." }

Write-Step "Construction de l'application autonome"
& $VenvPython -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "NaviXav.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller n'a pas produit l'application." }

New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
$DistDir = Join-Path $ProjectRoot "dist\NaviXav"
Get-ChildItem -LiteralPath $ProjectRoot -Filter "README*.md" -File |
    Copy-Item -Destination $DistDir -Force
& (Join-Path $PSScriptRoot "collect_licenses.ps1") `
    -PythonPath $VenvPython `
    -Destination (Join-Path $DistDir "licenses")
if ($LASTEXITCODE -ne 0) { throw "La collecte des licences a échoué." }
$PortableArchive = Join-Path $ReleaseDir "NaviXav-$Version-windows-x64-portable.zip"
New-PortableArchive (Join-Path $DistDir "*") $PortableArchive

if (-not $SkipInstaller) {
    $Iscc = Find-Iscc
    if (-not $Iscc -and -not $SkipToolInstall) {
        $winget = Get-Command "winget.exe" -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Step "Installation automatique d'Inno Setup"
            & $winget.Source install --id JRSoftware.InnoSetup --exact --silent --accept-package-agreements --accept-source-agreements
            $Iscc = Find-Iscc
        }
    }
    if (-not $Iscc) {
        throw "Inno Setup 6 est absent. Utilise -SkipInstaller ou autorise son installation."
    }
    Write-Step "Construction de l'installateur Windows"
    & $Iscc "/DMyAppVersion=$Version" (Join-Path $ProjectRoot "installer\NaviXav.iss")
    if ($LASTEXITCODE -ne 0) { throw "La compilation de l'installateur a échoué." }
}

Write-Step "Sommes de contrôle SHA-256"
Get-ChildItem -LiteralPath $ReleaseDir -File |
    Where-Object Extension -In ".exe", ".zip" |
    ForEach-Object {
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        Set-Content -LiteralPath ($_.FullName + ".sha256") -Value "$hash  $($_.Name)" -Encoding ascii
        Write-Host "$($_.Name)  $hash"
    }

Write-Host "`nDistribution terminée : $ReleaseDir" -ForegroundColor Green
