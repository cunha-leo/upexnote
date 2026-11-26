# Backwards-compatible entry point for earlier R03.1 recovery instructions.
param(
    [ValidateSet('personal','internal','both')]
    [string]$Edition='both'
)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'build_and_publish.ps1') -Edition $Edition
if(-not $? -or $LASTEXITCODE -ne 0){throw 'Desktop build and publishing failed'}
