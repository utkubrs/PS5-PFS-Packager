# Private, local-only build; do not commit or upload Obris.zip.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/build_private_orbis.ps1 -Archive C:\\path\\Obris.zip
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Archive)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$tools = Join-Path $project 'tools'
$privateTools = Join-Path $tools 'Obris'
if (Test-Path -LiteralPath $privateTools) {
    throw "Private tools directory already exists: $privateTools. No files were overwritten."
}
if (!(Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11 x64 launcher missing. Install Python 3.11.'
}
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required to check out the pinned open-source GP4 helper.'
}
if (!(Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw '.NET SDK 10 is required to compile the open-source GP4 helper.'
}
$versions = (& dotnet --list-sdks) -join ' '
if ($versions -notmatch '10\.0\.') {
    throw '.NET SDK 10 not found.'
}
$work = Join-Path $env:TEMP ('ps5_pfs_private_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    $expanded = Join-Path $work 'extracted'
    Expand-Archive -LiteralPath $archivePath -DestinationPath $expanded -Force
    $source = Join-Path $expanded 'Obris'
    $need = @(
        'orbis-pub-cmd.exe', 'orbis-pub-prx.dll', 'orbis-pub-gen.exe',
        'orbis-pub-chk.exe', 'orbis-pub-sfo.exe', 'orbis-pub-trp.exe',
        'gengp4_app.exe', 'gengp4_patch.exe',
        'ext/sc.exe', 'ext/di.exe', 'ext/libatrac9.dll', 'ext/trp_compare_default.css'
    )
    foreach ($rel in $need) {
        if (!(Test-Path -LiteralPath (Join-Path $source $rel))) {
            throw "Archive is missing: Obris/$rel"
        }
    }
    New-Item -ItemType Directory -Force -Path $privateTools | Out-Null
    foreach ($rel in $need) {
        $dst = Join-Path $privateTools $rel
        $parent = Split-Path -Parent $dst
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Copy-Item -LiteralPath (Join-Path $source $rel) -Destination $dst
    }
    Write-Host '[OK] Private Orbis Publisher Tools staged for embedding.' -ForegroundColor Green
    New-Item -ItemType Directory -Force -Path $tools | Out-Null
    if (!(Test-Path (Join-Path $tools 'pkgextract.exe'))) {
        $archive = Join-Path $work 'extractor.zip'
        $url = 'https://github.com/paulomanrique/ps4-pkg-extractor/releases/download/v0.0.1/pkgextract-x86_64-pc-windows-msvc.zip'
        Invoke-WebRequest -Uri $url -OutFile $archive
        $expected = '0c736ee02779fb5cf4403a91da23f94fdaa72debf995be0c400ac9c36acee63a'
        $actual = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "PS4 extractor checksum mismatch: $actual" }
        $extractDir = Join-Path $work 'extractor'
        Expand-Archive -LiteralPath $archive -DestinationPath $extractDir
        $candidate = Get-ChildItem $extractDir -Recurse -File -Filter pkgextract.exe | Select-Object -First 1
        if (!$candidate) { throw 'PS4 extractor missing inside downloaded ZIP' }
        Copy-Item -LiteralPath $candidate.FullName -Destination (Join-Path $tools 'pkgextract.exe')
    }
    if (!(Test-Path (Join-Path $tools 'OrbisPkgTool.exe'))) {
        $sourceRepo = Join-Path $work 'orbis-src'
        & git clone --quiet https://github.com/pearlxcore/OrbisPkgTool.git $sourceRepo
        if ($LASTEXITCODE -ne 0) { throw 'Open-source helper git clone failed' }
        $sha = '5cd42a515dc29a453c7abcb93318493bdb5b5e1f'
        & git -C $sourceRepo checkout --quiet $sha
        if ($LASTEXITCODE -ne 0) { throw 'Failed to checkout pinned GP4 helper' }
        $publish = Join-Path $work 'orbis-out'
        & dotnet publish (Join-Path $sourceRepo 'OrbisPkgTool/OrbisPkgTool.csproj') -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:PublishTrimmed=false -p:IncludeNativeLibrariesForSelfExtract=true -o $publish
        if ($LASTEXITCODE -ne 0) { throw 'Open-source GP4 helper failed to compile' }
        Copy-Item (Join-Path $publish 'OrbisPkgTool.exe') (Join-Path $tools 'OrbisPkgTool.exe')
        Copy-Item (Join-Path $sourceRepo 'LICENSE') (Join-Path $tools 'OrbisPkgTool.LICENSE.txt')
    }
    Push-Location $project
    try {
        & cmd.exe /c 'call scripts\build_windows.bat <nul'
        if ($LASTEXITCODE -ne 0) { throw 'Private standalone EXE build failed' }
    } finally { Pop-Location }
    $exe = Join-Path $project 'dist/ps5_pfs_packager.dist/PS5-PFS-Packager.exe'
    if (!(Test-Path $exe)) { throw 'Missing resulting PS5-PFS-Packager.exe' }
    # Nuitka builds the GUI with a requireAdministrator manifest.
    # Start-Process without -Verb RunAs fails with ERROR_ELEVATION_REQUIRED
    # (740); -Verb RunAs needs no parent admin session, but does show UAC.
    Write-Host 'Checking embedded Orbis tools (approve the Windows UAC prompt)...' -ForegroundColor Cyan
    try {
        $proc = Start-Process -FilePath $exe -ArgumentList '--check-orbis-bundle' -Verb RunAs -Wait -PassThru
    }
    catch {
        throw "Embedded Orbis verification could not start with administrator rights: $($_.Exception.Message)"
    }
    if ($proc.ExitCode -ne 0) {
        throw "Private EXE embedded Orbis verification failed (exit code: $($proc.ExitCode))."
    }
    Write-Host '[OK] Embedded Orbis Publisher Tools verified in standalone EXE.' -ForegroundColor Green
    Write-Host "SINGLE EXE READY: $exe" -ForegroundColor Green
    Write-Host ('SHA256: ' + (Get-FileHash $exe -Algorithm SHA256).Hash)
    Write-Host 'This executable includes your private Orbis tools. Do not publish without redistribution rights.' -ForegroundColor Yellow
} finally {
    if (Test-Path $work) { Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue }
}
