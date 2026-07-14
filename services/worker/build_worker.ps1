# Empacota o worker Python como pasta autonoma (PyInstaller onedir) e
# copia-a para junto do executavel da app desktop.
#
# Onedir (e nao onefile): a app lanca o worker muitas vezes em chamadas
# curtas (listar motores, verificar chaves, ...). O onefile descomprime-se
# para o temp A CADA chamada — lento e mais falsos positivos de antivirus.
# O onedir arranca instantaneamente.
#
# Uso:  powershell -ExecutionPolicy Bypass -File build_worker.ps1
# Resultado: dist\upexnote-worker\  ->  copiado para
#            ..\..\apps\desktop\src-tauri\target\release\worker\

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# `python -m PyInstaller` (e nao `pyinstaller`): o Python da MS Store nao
# poe a pasta Scripts no PATH, mas o modulo esta sempre acessivel.
python -m PyInstaller --noconfirm --clean --onedir --console `
    --name upexnote-worker `
    --hidden-import keyring.backends.Windows `
    worker_entry.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou (exit $LASTEXITCODE)" }

# Sanity check: o exe responde ao comando mais barato (sem tocar em APIs).
& ".\dist\upexnote-worker\upexnote-worker.exe" engines | Out-Null
if ($LASTEXITCODE -ne 0) { throw "O worker empacotado nao respondeu a 'engines' (exit $LASTEXITCODE)" }

# Copia para junto do exe da app (a app procura worker\upexnote-worker.exe
# ao lado do proprio executavel; se nao existir, usa o python do sistema).
$dest = Join-Path $PSScriptRoot "..\..\apps\desktop\src-tauri\target\release\worker"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse ".\dist\upexnote-worker" $dest
Write-Host "OK: worker empacotado em $((Resolve-Path $dest).Path)"
