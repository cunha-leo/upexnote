param([ValidateSet("personal","internal")][string]$Edition="personal")
$ErrorActionPreference="Stop"
$root=Split-Path $PSScriptRoot -Parent
$desktop=Join-Path $root "apps\desktop"
$env:VITE_UPEXNOTE_EDITION=$Edition
$env:UPEXNOTE_EDITION=$Edition
$worker=Join-Path $root "services\worker\build_worker.ps1"
$release=Join-Path $root "releases\editions\$Edition"
New-Item -ItemType Directory -Path $release -Force | Out-Null
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $worker -Edition $Edition
    if($LASTEXITCODE -ne 0){throw "Worker build failed"}
    Set-Location $desktop
    $argsList=@("run","tauri","build","--","--config","src-tauri/tauri.$Edition.conf.json")
    if($Edition -eq "internal"){$argsList+=@("--features","internal")}
    & npm.cmd @argsList
    if($LASTEXITCODE -ne 0){throw "Tauri build failed"}
    . (Join-Path $PSScriptRoot 'resolve_release_installer.ps1')
    $installerInfo=Get-UpexNoteInstaller -Root $root -Edition $Edition -Location bundle
    Copy-Item -LiteralPath $installerInfo.FullName -Destination $release -Force
    Get-FileHash -LiteralPath (Join-Path $release $installerInfo.Name) -Algorithm SHA256
    Write-Host "EDITION_BUILD_OK $Edition"
} finally {
    Remove-Item Env:VITE_UPEXNOTE_EDITION -ErrorAction SilentlyContinue
    Remove-Item Env:UPEXNOTE_EDITION -ErrorAction SilentlyContinue
    Set-Location $root
}
