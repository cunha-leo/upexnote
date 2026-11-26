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

param([ValidateSet("personal", "internal")][string]$Edition = "personal")
$ErrorActionPreference = "Stop"
$env:UPEXNOTE_EDITION = $Edition
Set-Location $PSScriptRoot

$editionFile = Join-Path $PSScriptRoot "transcription\_build_edition.py"
$originalEdition = [IO.File]::ReadAllBytes($editionFile)
try {
    $flag = if ($Edition -eq "internal") { "True" } else { "False" }
    [IO.File]::WriteAllText($editionFile, "INTERNAL = $flag`n", [Text.Encoding]::ASCII)
    $extra = @()
    # The current Python runtime can carry a patched ssl.py that loads an
    # extra CA distrust list. Bundle the adjacent file rather than disabling
    # TLS verification; the frozen SSLContext needs the same resource.
    $tlsCompanion = python -c "import ssl,pathlib;print(pathlib.Path(ssl.__file__).with_name('codex-rejected-cas.pem'))"
    if ($LASTEXITCODE -ne 0) { throw "Cannot resolve Python SSL runtime" }
    if (Test-Path -LiteralPath $tlsCompanion) {
        $extra += @("--add-data", "$tlsCompanion;.")
        Write-Host "SSL companion bundled for patched Python runtime."
    }
    if ($Edition -eq "personal") { $extra += @("--exclude-module", "transcription.data_studio") }
    python -m PyInstaller --noconfirm --clean --onedir --console `
        --name upexnote-worker `
        --hidden-import keyring.backends.Windows `
        @extra worker_entry.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed: $LASTEXITCODE" }
} finally {
    [IO.File]::WriteAllBytes($editionFile, $originalEdition)
}

# Inclui a config da base de dados (host/porta/base/user — SEM password)
# no pacote, para o zip portatil funcionar sem copiar nada para o AppData.
# Se o ficheiro nao existir (ex.: build para distribuir a terceiros), segue
# sem ele — a app funciona na mesma, so nao grava historico na VPS.
$cfg = Join-Path $PSScriptRoot "transcription\db_config.json"
if ($Edition -eq "internal" -and (Test-Path $cfg)) {
    Copy-Item $cfg ".\dist\upexnote-worker\db_config.json" -Force
    Write-Host "db_config.json incluido no pacote."
} else {
    Write-Host "No database configuration bundled for this edition."
}

# Inclui o registo OAuth da aplicacao (client IDs Google/GitHub) no pacote:
# a app instala e o login social funciona em QUALQUER maquina, sem passos
# manuais — padrao de apps desktop de mercado (client IDs nao sao segredos;
# a seguranca do fluxo e o PKCE/Device Flow).
$oauthCfg = Join-Path $PSScriptRoot "transcription\oauth_config.json"
if (Test-Path $oauthCfg) {
    Copy-Item $oauthCfg ".\dist\upexnote-worker\oauth_config.json" -Force
    Write-Host "oauth_config.json incluido no pacote (login social pronto a usar)."
} else {
    Write-Host "oauth_config.json ausente — botoes de login social ficarao inativos."
}

# URL publica da API central (nao e segredo). Empacotada para a aplicacao ser
# autocontida, com AppData como override opcional no runtime.
$apiCfg = Join-Path $PSScriptRoot "transcription\api_config.json"
if (Test-Path $apiCfg) {
    Copy-Item $apiCfg ".\dist\upexnote-worker\api_config.json" -Force
    Write-Host "api_config.json incluido no pacote (recuperacao de senha pronta a usar)."
} else {
    throw "api_config.json ausente — o build nao pode oferecer recuperacao segura de senha."
}

# Sanity check: o exe responde ao comando mais barato (sem tocar em APIs).
& ".\dist\upexnote-worker\upexnote-worker.exe" engines | Out-Null
if ($LASTEXITCODE -ne 0) { throw "O worker empacotado nao respondeu a 'engines' (exit $LASTEXITCODE)" }

# Distribuir yt-dlp standalone com o worker para que importar legendas
# funcione mesmo em computadores sem yt-dlp no PATH.
# FFmpeg continua pré-requisito externo para a opção de extrair áudio.
$ytDlp = Get-Command yt-dlp.exe -ErrorAction SilentlyContinue
if (-not $ytDlp) { throw "yt-dlp.exe nao encontrado: nao gerar release sem suporte a URL." }
Copy-Item -LiteralPath $ytDlp.Source -Destination ".\dist\upexnote-worker\yt-dlp.exe" -Force
& ".\dist\upexnote-worker\yt-dlp.exe" --version
if ($LASTEXITCODE -ne 0) { throw "yt-dlp empacotado falhou no teste de versao." }
Write-Host "yt-dlp empacotado e verificado."

# Copia para dois destinos:
# 1. target\release\worker — junto do exe "solto" (atalho/zip portatil);
# 2. src-tauri\worker — fonte dos "resources" do bundler Tauri, que os
#    poe ao lado do exe INSTALADO (mesma deteccao em runtime nos 2 casos).
$dests = @(
    (Join-Path $PSScriptRoot "..\..\apps\desktop\src-tauri\target\release\worker"),
    (Join-Path $PSScriptRoot "..\..\apps\desktop\src-tauri\worker")
)
foreach ($dest in $dests) {
    if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
    Copy-Item -Recurse ".\dist\upexnote-worker" $dest
    Write-Host "OK: worker copiado para $((Resolve-Path $dest).Path)"
}
