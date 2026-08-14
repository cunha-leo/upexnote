#Requires -Version 5.1
<#
  rebuild-dev.ps1 — mata processos antigos do UpexNote, apaga o worker
  sidecar desatualizado (se existir, NAS DUAS copias) e recompila em modo
  --no-bundle.

  Correcao 2026-08-13 (i): a v1 deste script so apagava
  target\release\worker (a copia DE SAIDA). Isso nao chegava — o Tauri
  copia os "resources" do tauri.conf.json (worker -> worker) para
  target\release\ em TODO build, mesmo com --no-bundle, a partir da copia
  FONTE em src-tauri\worker. Essa fonte fica parada ali desde a ultima vez
  que alguem correu build_worker.ps1/make_portable.ps1 (empacotar para
  distribuicao) — se isso foi ha dias, o build de-bundle "ressuscita" o
  worker velho sem avisar, e comandos novos da CLI (ex.: notebook-note-open)
  falham com "invalid choice" mesmo depois de src/cli.py estar atualizado.

  Correcao 2026-08-13 (ii): apagar src-tauri\worker por INTEIRO parte o
  build — o Tauri valida em COMPILE-TIME que esse caminho existe (e' o
  "resources" declarado no tauri.conf.json), mesmo com --no-bundle:
  "resource path `worker` doesn't exist" e' erro fatal do build.rs. Por
  isso agora a pasta FONTE (src-tauri\worker) e' sempre mantida — so o seu
  CONTEUDO (o exe empacotado e tudo o resto) e' apagado. Uma pasta vazia
  satisfaz o Tauri em compile-time; sem o upexnote-worker.exe la dentro, o
  app em runtime (bundled_worker() em lib.rs) cai sempre no fallback de
  desenvolvimento. Ja a copia de SAIDA (target\release\worker) pode
  continuar a ser apagada por inteiro — nao e' validada em compile-time,
  so e' preenchida se a fonte tiver algo para copiar.

  Uso: clica com o botão direito neste ficheiro > "Executar com o PowerShell".
  Ou, num terminal PowerShell já aberto:
      cd C:\Users\cunha\Projects\upexflow\upexnote
      .\scripts\rebuild-dev.ps1
#>

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "== 1) A encerrar processos antigos do UpexNote ==" -ForegroundColor Cyan
# cmd /c em vez de chamar taskkill diretamente: quando o processo já nao
# existe, o taskkill escreve no stderr e o PowerShell converte isso num erro
# "terminating" mesmo com 2>$null — corrido dentro do cmd, essa mensagem
# fica so um texto normal (perdido no >nul), nunca vira erro do PowerShell.
cmd /c "taskkill /F /IM upexnote.exe /T >nul 2>&1"
cmd /c "taskkill /F /IM upexnote-worker.exe /T >nul 2>&1"
Start-Sleep -Seconds 1
$still = Get-Process | Where-Object { $_.Name -like "*upexnote*" }
if ($still) {
    Write-Host "AINDA ha processos do UpexNote a correr — fecha-os manualmente e volta a correr este script:" -ForegroundColor Red
    $still | Format-Table Name, Id -AutoSize
    exit 1
}
Write-Host "Nenhum processo do UpexNote a correr. OK." -ForegroundColor Green

Write-Host "`n== 2) A limpar o worker sidecar desatualizado ==" -ForegroundColor Cyan

# Copia de SAIDA (target\release\worker): pode ser apagada por inteiro —
# so e' recriada pelo build se houver algo na pasta fonte para copiar.
$workerOut = Join-Path $repoRoot "apps\desktop\src-tauri\target\release\worker"
if (Test-Path $workerOut) {
    try {
        Remove-Item -Recurse -Force $workerOut -ErrorAction Stop
        Write-Host "Pasta '$workerOut' apagada." -ForegroundColor Green
    } catch {
        Write-Host "FALHOU a apagar '$workerOut' — ainda ha ficheiros bloqueados por outro processo." -ForegroundColor Red
        Write-Host "Fecha todas as janelas do UpexNote, quaisquer terminais abertos dentro dessa pasta, e tenta de novo." -ForegroundColor Red
        Write-Host $_.Exception.Message
        exit 1
    }
} else {
    Write-Host "Pasta '$workerOut' ja nao existe. OK." -ForegroundColor Green
}

# Copia FONTE (src-tauri\worker): o Tauri exige que este CAMINHO exista em
# compile-time (e' o "resources" do tauri.conf.json) — por isso esvazia-se
# o CONTEUDO em vez de apagar a pasta toda.
$workerSrc = Join-Path $repoRoot "apps\desktop\src-tauri\worker"
try {
    if (Test-Path $workerSrc) {
        Get-ChildItem -Path $workerSrc -Force | Remove-Item -Recurse -Force -ErrorAction Stop
    } else {
        New-Item -ItemType Directory -Force $workerSrc | Out-Null
    }
    Write-Host "Pasta '$workerSrc' mantida, mas vazia (o Tauri exige que exista)." -ForegroundColor Green
} catch {
    Write-Host "FALHOU a esvaziar '$workerSrc' — ainda ha ficheiros bloqueados por outro processo." -ForegroundColor Red
    Write-Host "Fecha todas as janelas do UpexNote, quaisquer terminais abertos dentro dessa pasta, e tenta de novo." -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}
Write-Host "Sem worker empacotado: o app corre em modo desenvolvimento (python -m transcription.cli), sempre a codigo fresco. Se um dia precisares do zip portatil/instalador de novo, corre make_portable.ps1 primeiro." -ForegroundColor DarkGray

Write-Host "`n== 3) A recompilar (tauri build --no-bundle) ==" -ForegroundColor Cyan
Set-Location (Join-Path $repoRoot "apps\desktop")
& .\node_modules\.bin\tauri.cmd build --no-bundle
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nO build FALHOU (codigo $LASTEXITCODE) — ver o erro acima." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n== Build concluido. ==" -ForegroundColor Green
Write-Host "Executavel: $repoRoot\apps\desktop\src-tauri\target\release\upexnote.exe"
