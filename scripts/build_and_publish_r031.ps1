param([ValidateSet('personal','internal','both')][string]$Edition='both')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$env:PATH=(Join-Path $root 'services\worker\.venv\Scripts')+';'+$env:PATH
$editions=if($Edition -eq 'both'){@('personal','internal')}else{@($Edition)}
foreach($e in $editions){
    & (Join-Path $PSScriptRoot 'build_desktop_edition.ps1') -Edition $e
    if($LASTEXITCODE -ne 0){throw "Build failure: $e"}
    & (Join-Path $PSScriptRoot 'verify_desktop_edition.ps1') -Edition $e
    if($LASTEXITCODE -ne 0){throw "Validation failure: $e"}
    & (Join-Path $PSScriptRoot 'publish_desktop_shortcuts.ps1') -Edition $e
    if($LASTEXITCODE -ne 0){throw "Shortcut failure: $e"}
}
Write-Host 'R03.1_BUILD_VALIDATED_SHORTCUTS_READY'
