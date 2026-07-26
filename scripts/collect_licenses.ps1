[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$PythonPath,
    [Parameter(Mandatory)][string]$Destination
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ThirdPartyDir = Join-Path $Destination "third-party"

New-Item -ItemType Directory -Path $ThirdPartyDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination $Destination -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "NOTICE") -Destination $Destination -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "THIRD_PARTY_NOTICES") -Destination $Destination -Force

$Distributions = @(
    "annotated_doc", "annotated_types", "anyio", "bottle", "certifi", "cffi",
    "charset_normalizer", "click", "clr_loader", "colorama", "fastapi", "h11",
    "idna", "markdown_it_py", "mdurl", "proxy_tools", "pycparser", "pydantic",
    "pydantic_core", "pygments", "pypdf", "python_dotenv", "pythonnet",
    "pywebview", "requests", "rich", "starlette", "typing_extensions",
    "typing_inspection", "urllib3", "uvicorn"
)

$SitePackages = & $PythonPath -c "import sysconfig; print(sysconfig.get_paths()['purelib'])"
if ($LASTEXITCODE -ne 0 -or -not $SitePackages) {
    throw "Répertoire site-packages introuvable."
}

foreach ($Name in $Distributions) {
    $InfoDir = Get-ChildItem -LiteralPath $SitePackages -Directory -Filter "$Name-*.dist-info" |
        Select-Object -First 1
    if (-not $InfoDir) {
        throw "Métadonnées de licence introuvables pour $Name."
    }
    $LicenseFiles = Get-ChildItem -LiteralPath $InfoDir.FullName -Recurse -File |
        Where-Object { $_.Name -match '^(LICENSE|LICENCE|COPYING|NOTICE)(\.|$)' }
    if (-not $LicenseFiles) {
        $ProjectLicense = Join-Path $ProjectRoot "third_party_licenses\$Name"
        if (-not (Test-Path -LiteralPath $ProjectLicense)) {
            throw "Texte de licence introuvable pour $Name."
        }
        $LicenseFiles = @(Get-Item -LiteralPath $ProjectLicense)
    }
    $PackageDir = Join-Path $ThirdPartyDir $Name
    New-Item -ItemType Directory -Path $PackageDir -Force | Out-Null
    foreach ($LicenseFile in $LicenseFiles) {
        Copy-Item -LiteralPath $LicenseFile.FullName -Destination $PackageDir -Force
    }
}

$PythonLicense = & $PythonPath -c "import pathlib,sys; print(pathlib.Path(sys.base_prefix)/'LICENSE.txt')"
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PythonLicense)) {
    throw "Licence de l'environnement Python introuvable."
}
Copy-Item -LiteralPath $PythonLicense -Destination (Join-Path $ThirdPartyDir "PYTHON_LICENSE.txt") -Force

$PyInstallerInfo = Get-ChildItem -LiteralPath $SitePackages -Directory -Filter "pyinstaller-*.dist-info" |
    Select-Object -First 1
if (-not $PyInstallerInfo) {
    throw "Métadonnées PyInstaller introuvables."
}
$PyInstallerLicense = Get-ChildItem -LiteralPath $PyInstallerInfo.FullName -Recurse -File |
    Where-Object { $_.Name -match '^(COPYING|LICENSE)' } |
    Select-Object -First 1
if (-not $PyInstallerLicense) {
    throw "Licence PyInstaller introuvable."
}
Copy-Item -LiteralPath $PyInstallerLicense.FullName `
    -Destination (Join-Path $ThirdPartyDir "PYINSTALLER_COPYING.txt") `
    -Force

Write-Host "Licences copiées dans $Destination" -ForegroundColor Green
