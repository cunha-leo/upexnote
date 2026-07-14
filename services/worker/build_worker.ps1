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

# Inclui a config da base de dados (host/porta/base/user — SEM password)
# no pacote, para o zip portatil funcionar sem copiar nada para o AppData.
# Se o ficheiro nao existir (ex.: build para distribuir a terceiros), segue
# sem ele — a app funciona na mesma, so nao grava historico na VPS.
$cfg = Join-Path $PSScriptRoot "transcription\db_config.json"
if (Test-Path $cfg) {
    Copy-Item $cfg ".\dist\upexnote-worker\db_config.json" -Force
    Write-Host "db_config.json incluido no pacote."
} else {
    Write-Host "db_config.json ausente — pacote sem ligacao a VPS (so ficheiro local)."
}

# Sanity check: o exe responde ao comando mais barato (sem tocar em APIs).
& ".\dist\upexnote-worker\upexnote-worker.exe" engines | Out-Null
if ($LASTEXITCODE -ne 0) { throw "O worker empacotado nao respondeu a 'engines' (exit $LASTEXITCODE)" }

# Copia para junto do exe da app (a app procura worker\upexnote-worker.exe
# ao lado do proprio executavel; se nao existir, usa o python do sistema).
$dest = Join-Path $PSScriptRoot "..\..\apps\desktop\src-tauri\target\release\worker"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse ".\dist\upexnote-worker" $dest
Write-Host "OK: worker empacotado em $((Resolve-Path $dest).Path)"
