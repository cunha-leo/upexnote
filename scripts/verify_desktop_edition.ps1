param([Parameter(Mandatory=$true)][ValidateSet("personal","internal")][string]$Edition)
$ErrorActionPreference="Stop"
$root=Split-Path $PSScriptRoot -Parent
$release=Join-Path $root "releases\editions\$Edition"
$target=Join-Path $root "apps\desktop\src-tauri\target\release"
$worker=Join-Path $target "worker\upexnote-worker.exe"
if (-not(Test-Path -LiteralPath $worker)){throw "Worker missing"}
$exe=Join-Path $target "upexnote.exe"
if (-not(Test-Path -LiteralPath $exe)){throw "Application binary missing"}
$expectedName=if($Edition -eq "personal"){"UpexNote_0.45.0_x64-setup.exe"}else{"UpexNote Internal_0.45.0-internal_x64-setup.exe"}
$installer=Join-Path $release $expectedName
if (-not(Test-Path -LiteralPath $installer)){throw "Installer missing"}
if((Get-Item $exe).LastWriteTime -lt (Get-Item $worker).LastWriteTime.AddSeconds(-5)){throw "Application executable predates current worker"}
# Frozen worker privilege checks use Python byte-safe subprocess I/O.
# The previous PowerShell stdin path fed malformed JSON to frozen Python.
$python=Join-Path $root 'services\worker\.venv\Scripts\python.exe'
$check=Join-Path $root 'scripts\verify_worker_input.py'
if(-not(Test-Path $python)){throw 'Python test runtime missing'}
& $python $check $worker $Edition
if($LASTEXITCODE -ne 0){throw ('Worker edition safety check failed for '+$Edition)}
# If the build Python runtime loads an adjacent SSL trust companion, the
# frozen worker must carry it too. This avoids TLS failures on user machines.
$sslCompanion = & $python -c "import ssl,pathlib;print(pathlib.Path(ssl.__file__).with_name('codex-rejected-cas.pem'))"
if ($LASTEXITCODE -ne 0){throw "Could not inspect SSL runtime"}
if ((Test-Path -LiteralPath $sslCompanion) -and
    -not (Test-Path -LiteralPath (Join-Path (Split-Path $worker) '_internal\codex-rejected-cas.pem'))) {
    throw "Missing SSL trust companion in packaged worker"
}
$portable=Join-Path $release "portable"
if(Test-Path -LiteralPath $portable){
    $backup=Join-Path $root ('releases\R03.1\portable-backups\'+$Edition+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path (Split-Path $backup) | Out-Null
    Move-Item -LiteralPath $portable -Destination $backup
    Write-Host "Previous portable preserved: $backup"
}
New-Item -ItemType Directory -Path $portable | Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $portable "upexnote.exe")
Copy-Item -LiteralPath (Join-Path $target "worker") -Destination $portable -Recurse
Get-FileHash -LiteralPath $installer,(Join-Path $portable "upexnote.exe") -Algorithm SHA256 | Format-List
Write-Host "EDITION_VERIFIED $Edition"
