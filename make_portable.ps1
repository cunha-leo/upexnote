# Gera o pacote portatil do UpexNote: dist\UpexNote-portable.zip
#
# Conteudo do zip:
#   UpexNote\
#   ├─ upexnote.exe    app desktop (Tauri)
#   └─ worker\         motor Python autonomo (PyInstaller onedir),
#                      com db_config.json incluido (SEM passwords)
#
# Em qualquer Windows 10/11: descompactar, abrir upexnote.exe, colar as
# chaves em Definicoes (uma vez, ficam no Credential Manager DESSA maquina)
# e esta a funcionar. Transcripts vao para Documentos\UpexNote\storage.
#
# NOTA de privacidade: o db_config.json leva o endereco da VPS (sem
# password) — este zip e para maquinas do proprio; para distribuir a
# terceiros, apagar transcription\db_config.json antes de correr isto.
#
# Uso:  powershell -ExecutionPolicy Bypass -File make_portable.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1. Worker autonomo (PyInstaller onedir + config, copiado p/ target/release/worker)
powershell -ExecutionPolicy Bypass -File services\worker\build_worker.ps1
if ($LASTEXITCODE -ne 0) { throw "build do worker falhou (exit $LASTEXITCODE)" }

# 2. App desktop (release)
Set-Location apps\desktop
npm run tauri build -- --no-bundle
if ($LASTEXITCODE -ne 0) { throw "tauri build falhou (exit $LASTEXITCODE)" }
Set-Location $PSScriptRoot

# 3. Montar e zipar
$rel = "apps\desktop\src-tauri\target\release"
$stage = Join-Path $env:TEMP "upexnote-portable-stage"
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force (Join-Path $stage "UpexNote") | Out-Null
Copy-Item (Join-Path $rel "upexnote.exe") (Join-Path $stage "UpexNote\")
Copy-Item -Recurse (Join-Path $rel "worker") (Join-Path $stage "UpexNote\worker")

New-Item -ItemType Directory -Force "dist" | Out-Null
$zip = "dist\UpexNote-portable.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $stage "UpexNote") -DestinationPath $zip
Remove-Item -Recurse -Force $stage

$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "OK: $((Resolve-Path $zip).Path) ($size MB)"
