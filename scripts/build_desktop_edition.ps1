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
    $name=if($Edition -eq "internal"){"UpexNote Internal_0.45.0-internal_x64-setup.exe"}else{"UpexNote_0.45.0_x64-setup.exe"}
    $bundle=Join-Path $desktop "src-tauri\target\release\bundle\nsis"
    $installer=Join-Path $bundle $name
    if(-not(Test-Path -LiteralPath $installer)){throw "Expected installer missing: $name"}
    Copy-Item -LiteralPath $installer -Destination $release -Force
    Get-FileHash -LiteralPath (Join-Path $release $name) -Algorithm SHA256
    Write-Host "EDITION_BUILD_OK $Edition"
} finally {
    Remove-Item Env:VITE_UPEXNOTE_EDITION -ErrorAction SilentlyContinue
    Remove-Item Env:UPEXNOTE_EDITION -ErrorAction SilentlyContinue
    Set-Location $root
}
