// Ponte entre a interface (React) e o worker de transcrição (CLI Python).
// A interface chama estes comandos via `invoke`; o `transcribe` transmite os
// eventos NDJSON do worker em tempo real para a janela via eventos Tauri.
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::{AppHandle, Emitter};

/// Lança o Python SEM janela de consola. Sendo esta uma app gráfica, cada
/// chamada ao worker faria piscar um terminal preto (e roubava o foco à
/// janela, causando ecrãs em branco ao interagir). CREATE_NO_WINDOW evita isso.
fn with_no_window(cmd: &mut Command) -> &mut Command {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    cmd
}

/// Caminho absoluto para `services/worker` (onde vive o pacote `transcription`).
/// Em desenvolvimento, deriva-se da localização do crate (layout fixo do repo).
fn worker_dir() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR")); // .../apps/desktop/src-tauri
    p.pop(); // .../apps/desktop
    p.pop(); // .../apps
    p.pop(); // .../ (raiz do repo)
    p.push("services");
    p.push("worker");
    p
}

/// Worker empacotado (PyInstaller onedir), se existir: `worker\upexnote-worker.exe`
/// ao lado do executável da app. É este que torna a app portável para máquinas
/// sem o repositório nem Python instalado.
fn bundled_worker() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let p = exe.parent()?.join("worker").join("upexnote-worker.exe");
    p.exists().then_some(p)
}

/// Constrói o comando do worker com os argumentos da CLI. Preferência:
/// 1) worker empacotado (sidecar) ao lado do exe — máquinas de utilizadores;
/// 2) fallback de desenvolvimento — `python -m transcription.cli` no repo.
/// PYTHONUNBUFFERED garante que os eventos NDJSON chegam linha a linha
/// (equivalente ao antigo `-u`, mas funciona também no exe congelado).
fn worker_command(cli_args: &[&str]) -> Command {
    let mut cmd = match bundled_worker() {
        Some(exe) => {
            let dir = exe.parent().expect("exe tem pasta").to_path_buf();
            let mut c = Command::new(exe);
            c.current_dir(dir);
            c
        }
        None => {
            let mut c = Command::new("python");
            c.arg("-m").arg("transcription.cli").current_dir(worker_dir());
            c
        }
    };
    cmd.args(cli_args).env("PYTHONUNBUFFERED", "1");
    cmd
}

fn run_cli(args: &[&str]) -> Result<String, String> {
    let mut cmd = worker_command(args);
    with_no_window(&mut cmd);
    let out = cmd
        .output()
        .map_err(|e| format!("Falha ao iniciar o worker Python: {e}"))?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(if err.trim().is_empty() {
            String::from_utf8_lossy(&out.stdout).to_string()
        } else {
            err.to_string()
        });
    }
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}

/// Versão assíncrona: corre `run_cli` numa thread de bloqueio, para não
/// congelar a UI enquanto o worker abre o túnel SSH + consulta a base
/// (pode demorar 2-5s). Comandos síncronos de Tauri correm na thread
/// principal e bloqueariam a janela toda durante esse tempo.
async fn run_cli_async(args: Vec<String>) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        run_cli(&refs)
    })
    .await
    .map_err(|e| format!("erro na thread do worker: {e}"))?
}

async fn run_cli_stdin_async(args: Vec<String>, payload: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let refs: Vec<&str> = args.iter().map(|s| s.as_str()).collect();
        let mut cmd = worker_command(&refs);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child.stdin.as_mut().ok_or("sem stdin")?
            .write_all(payload.as_bytes()).map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

fn admin_proof_json(email: Option<String>, token: Option<String>, text: Option<String>) -> String {
    serde_json::json!({
        "admin_email": email.unwrap_or_default(),
        "admin_token": token.unwrap_or_default(),
        "text": text.unwrap_or_default(),
    }).to_string()
}

/// Lista os motores (JSON de uma linha, tal como a CLI devolve).
/// `async`: comandos síncronos correm na THREAD PRINCIPAL e congelavam a
/// janela inteira no arranque até o worker responder (lição da v0.5.1,
/// que só tinha sido aplicada à Biblioteca — visto de novo em 2026-07-19).
#[tauri::command]
async fn list_engines() -> Result<String, String> {
    run_cli_async(vec!["engines".into()]).await
}

/// Diz se uma chave está configurada (JSON), sem revelar o valor.
#[tauri::command]
async fn check_key(name: String) -> Result<String, String> {
    run_cli_async(vec!["check-key".into(), "--name".into(), name]).await
}

/// Remove o sufixo de formato ("Arial (TrueType)" → "Arial") e os estilos no
/// fim do nome ("Segoe UI Semibold Italic" → "Segoe UI"), para o seletor de
/// tipografia listar FAMÍLIAS e não cada variante instalada.
#[cfg(windows)]
fn clean_font_family(raw: &str) -> Option<String> {
    let mut s = raw.split(" (").next().unwrap_or(raw).trim().to_string();
    const STYLES: [&str; 16] = [
        "Bold", "Italic", "Oblique", "Regular", "Light", "Semilight", "SemiLight",
        "Medium", "SemiBold", "Semibold", "ExtraBold", "Black", "Thin", "ExtraLight",
        "Condensed", "SemiCondensed",
    ];
    loop {
        let mut trimmed = false;
        for st in STYLES {
            if let Some(p) = s.strip_suffix(st) {
                s = p.trim_end().to_string();
                trimmed = true;
            }
        }
        if !trimmed {
            break;
        }
    }
    (!s.is_empty()).then_some(s)
}

/// Famílias de fontes instaladas no Windows (HKLM = para todos os utilizadores,
/// HKCU = instaladas só para este utilizador), únicas e ordenadas. Alimenta o
/// grupo "Instaladas nesta máquina" do seletor de tipografia.
#[tauri::command]
fn list_system_fonts() -> Result<Vec<String>, String> {
    #[cfg(windows)]
    {
        use std::collections::BTreeSet;
        use winreg::enums::{HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE};
        use winreg::RegKey;
        const FONTS_KEY: &str = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts";
        let mut families: BTreeSet<String> = BTreeSet::new();
        for root in [HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER] {
            if let Ok(key) = RegKey::predef(root).open_subkey(FONTS_KEY) {
                for value in key.enum_values().flatten() {
                    if let Some(f) = clean_font_family(&value.0) {
                        families.insert(f);
                    }
                }
            }
        }
        Ok(families.into_iter().collect())
    }
    #[cfg(not(windows))]
    {
        Ok(Vec::new())
    }
}

/// Estado de todas as chaves numa só chamada (o ecrã de Definições usa isto).
#[tauri::command]
async fn list_credentials() -> Result<String, String> {
    run_cli_async(vec!["list-keys".into()]).await
}

/// Guarda uma chave/credencial recebida da interface. O valor é escrito no
/// stdin do worker (nunca em argumentos/linha de comando, que seriam visíveis
/// na lista de processos) e acaba no Windows Credential Manager.
#[tauri::command]
fn save_credential(name: String, value: String) -> Result<String, String> {
    use std::io::Write;
    let mut cmd = worker_command(&["set-key", "--name", &name, "--stdin"]);
    cmd.stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    with_no_window(&mut cmd);
    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Falha ao iniciar o worker Python: {e}"))?;
    if let Some(stdin) = child.stdin.as_mut() {
        stdin.write_all(value.as_bytes()).map_err(|e| e.to_string())?;
        stdin.write_all(b"\n").map_err(|e| e.to_string())?;
    }
    let out = child.wait_with_output().map_err(|e| e.to_string())?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(if err.trim().is_empty() {
            String::from_utf8_lossy(&out.stdout).to_string()
        } else {
            err.to_string()
        });
    }
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}

/// Remove uma chave/credencial do Windows Credential Manager.
#[tauri::command]
fn clear_credential(name: String) -> Result<String, String> {
    run_cli(&["clear-key", "--name", &name])
}

/// Histórico + agregados da Biblioteca (JSON). `search` filtra por nome.
/// `async` para correr fora da thread principal (não congela a UI).
#[tauri::command]
async fn library(
    search: Option<String>, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["library".into(), "--json-stdin".into()];
    if let Some(s) = search {
        if !s.trim().is_empty() {
            args.push("--search".into());
            args.push(s);
        }
    }
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// Acrescenta `--user <id>` (conta da sessão — isolamento por utilizador).
fn push_user(args: &mut Vec<String>, user: Option<i64>) {
    if let Some(u) = user {
        args.push("--user".into());
        args.push(u.to_string());
    }
}

/// Uma transcrição completa (com texto) para a vista de detalhe.
#[tauri::command]
async fn library_item(
    id: i64, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["library-item".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// Operações de conta (item 13-C): payload JSON via STDIN (nunca argv, que é
/// visível na lista de processos). `op` é validado contra a whitelist.
#[tauri::command]
async fn account(op: String, payload: String, mode: Option<String>) -> Result<String, String> {
    const OPS: [&str; 4] = ["register", "login", "oauth-login", "update"];
    if !OPS.contains(&op.as_str()) {
        return Err(format!("operação desconhecida: {op}"));
    }
    if let Some(m) = mode.as_deref() {
        if m != "local" && m != "vps" {
            return Err(format!("modo desconhecido: {m}"));
        }
    }
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let cmd_name = format!("account-{op}");
        let mut cli: Vec<&str> = vec![&cmd_name];
        if let Some(m) = mode.as_deref() {
            cli.push("--mode");
            cli.push(m);
        }
        let mut cmd = worker_command(&cli);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child
            .stdin
            .as_mut()
            .ok_or("sem stdin")?
            .write_all(payload.as_bytes())
            .map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Password reset through the central HTTPS API. All sensitive fields remain
/// in the JSON stdin pipe and never enter the process command line.
#[tauri::command]
async fn api_reset(op: String, payload: String) -> Result<String, String> {
    const OPS: [&str; 3] = ["request", "verify", "complete"];
    if !OPS.contains(&op.as_str()) {
        return Err(format!("operação desconhecida: {op}"));
    }
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let cmd_name = format!("api-reset-{op}");
        let mut cmd = worker_command(&[&cmd_name]);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child
            .stdin
            .as_mut()
            .ok_or("sem stdin")?
            .write_all(payload.as_bytes())
            .map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Administrative e-mail/TOTP factor through the central HTTPS API. Secrets,
/// one-time codes and session tokens stay in the stdin JSON pipe.
#[tauri::command]
async fn api_admin_factor(op: String, payload: String) -> Result<String, String> {
    const OPS: [&str; 6] = ["challenge", "verify", "validate", "revoke", "totp-enroll", "totp-confirm"];
    if !OPS.contains(&op.as_str()) {
        return Err(format!("operação desconhecida: {op}"));
    }
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let cmd_name = format!("api-admin-{op}");
        let mut cmd = worker_command(&[&cmd_name]);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child
            .stdin
            .as_mut()
            .ok_or("sem stdin")?
            .write_all(payload.as_bytes())
            .map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Operações da aba de Administração: payload JSON por stdin (contém o ator,
/// que o worker REVALIDA na base — o cliente não consegue afirmar-se admin).
#[tauri::command]
async fn admin(op: String, payload: String, mode: Option<String>) -> Result<String, String> {
    const OPS: [&str; 7] = ["overview", "users", "create-user", "update-user", "delete-user", "events", "audit"];
    if !OPS.contains(&op.as_str()) {
        return Err(format!("operação desconhecida: {op}"));
    }
    if let Some(m) = mode.as_deref() {
        if m != "local" && m != "vps" {
            return Err(format!("modo desconhecido: {m}"));
        }
    }
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let cmd_name = format!("admin-{op}");
        let mut cli: Vec<&str> = vec![&cmd_name];
        if let Some(m) = mode.as_deref() {
            cli.push("--mode");
            cli.push(m);
        }
        let mut cmd = worker_command(&cli);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child
            .stdin
            .as_mut()
            .ok_or("sem stdin")?
            .write_all(payload.as_bytes())
            .map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn account_suggest(user_id: String, mode: Option<String>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["account-suggest".into(), "--user-id".into(), user_id];
    if let Some(m) = mode {
        if m == "local" || m == "vps" {
            args.push("--mode".into());
            args.push(m);
        }
    }
    run_cli_async(args).await
}

/// Gate do administrador: valida uma credencial DIGITADA (via stdin, nunca
/// argv) com uma ligação real à base — prova de conhecimento, não de posse.
#[tauri::command]
async fn db_check_secret(secret: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        use std::io::Write;
        let mut cmd = worker_command(&["db-check", "--mode", "vps", "--stdin-password"]);
        cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        with_no_window(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| e.to_string())?;
        child
            .stdin
            .as_mut()
            .ok_or("sem stdin")?
            .write_all(secret.as_bytes())
            .map_err(|e| e.to_string())?;
        drop(child.stdin.take());
        let out = child.wait_with_output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if stdout.is_empty() {
            return Err(String::from_utf8_lossy(&out.stderr).to_string());
        }
        Ok(stdout)
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Login social (item 13-C): corre `oauth --provider X` e emite cada linha
/// NDJSON como `oauth://event` — o device flow do GitHub mostra um código que
/// o utilizador precisa de ver DURANTE o fluxo. Fecha com `oauth://done`.
#[tauri::command]
fn oauth_start(app: AppHandle, provider: String) -> Result<(), String> {
    if provider != "google" && provider != "github" {
        return Err("provider inválido".into());
    }
    let mut cmd = worker_command(&["oauth", "--provider", &provider]);
    cmd.stdout(Stdio::piped()).stderr(Stdio::null());
    with_no_window(&mut cmd);
    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    std::thread::spawn(move || {
        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                if !line.trim().is_empty() {
                    let _ = app.emit("oauth://event", line);
                }
            }
        }
        let _ = child.wait();
        // The event bus is asynchronous: give the UI time to process the
        // OAuth payload before emitting the terminal completion event.
        std::thread::sleep(std::time::Duration::from_millis(250));
        // Traz a janela da app para a frente — a pessoa autenticou no browser
        // e o retorno deve "aterrar" no UpexNote sem cliques (2026-07-19).
        {
            use tauri::Manager;
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.unminimize();
                let _ = win.set_focus();
            }
        }
        let _ = app.emit("oauth://done", ());
    });
    Ok(())
}

/// Google devolve o resultado pela própria chamada, sem depender do evento da
/// WebView depois de o navegador fechar. O GitHub continua no fluxo de eventos
/// porque precisa mostrar o código device-flow durante a autenticação.
#[tauri::command]
async fn oauth_google() -> Result<String, String> {
    run_cli_async(vec!["oauth".into(), "--provider".into(), "google".into()]).await
}

/// Telemetria privada: a UI só pode fornecer os campos estritamente tipados
/// que a API aceita. O worker confirma o consentimento antes de qualquer rede.
#[tauri::command]
async fn telemetry_event(
    event: String,
    app_version: String,
    engine: Option<String>,
    duration_seconds: Option<i64>,
    estimated_cost_micros: Option<i64>,
    error_code: Option<String>,
) -> Result<String, String> {
    let mut args = vec!["telemetry".into(), "--event".into(), event, "--app-version".into(), app_version];
    if let Some(value) = engine { args.extend(["--engine".into(), value]); }
    if let Some(value) = duration_seconds { args.extend(["--duration-seconds".into(), value.to_string()]); }
    if let Some(value) = estimated_cost_micros { args.extend(["--estimated-cost-micros".into(), value.to_string()]); }
    if let Some(value) = error_code { args.extend(["--error-code".into(), value]); }
    run_cli_async(args).await
}

#[tauri::command]
async fn telemetry_overview(payload: String) -> Result<String, String> {
    run_cli_stdin_async(vec!["telemetry-overview".into()], payload).await
}

/// Testa a ligação à base. `mode` opcional ("local"/"vps") testa um modo
/// específico SEM o gravar — o ecrã de perfis valida a config de administrador
/// com isto antes de trocar o modo.
#[tauri::command]
async fn db_check(mode: Option<String>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["db-check".into()];
    if let Some(m) = mode {
        args.push("--mode".into());
        args.push(m);
    }
    run_cli_async(args).await
}

/// Edita o texto clean de uma transcrição. O texto vai por STDIN (pode ser
/// grande e ter caracteres especiais), nunca por argumentos. A raw é intacta.
/// Corre numa thread de bloqueio (não congela a UI).
#[tauri::command]
async fn library_update(
    id: i64, text: String, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args = vec!["library-update".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, Some(text))).await
}

/// Apaga uma transcrição (arquivada no histórico pelo worker).
#[tauri::command]
async fn library_delete(
    id: i64, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["library-delete".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// Marca/desmarca os avisos de validação como revistos.
#[tauri::command]
async fn library_ack(
    id: i64, reopen: bool, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["library-ack".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    if reopen {
        args.push("--reopen".into());
    }
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// Definições de armazenamento em vigor (pasta padrão + organização).
#[tauri::command]
async fn get_settings() -> Result<String, String> {
    run_cli_async(vec!["get-settings".into()]).await
}

/// Altera as definições de armazenamento (pasta padrão dos transcripts e/ou
/// organização por dia/motor). `storage_dir=None` + `clear=true` repõe a
/// pasta de fábrica. Devolve as definições resultantes.
#[tauri::command]
async fn set_settings(
    storage_dir: Option<String>,
    clear_storage_dir: Option<bool>,
    organize: Option<bool>,
    storage_mode: Option<String>,
    telemetry_consent: Option<bool>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["set-settings".into()];
    if clear_storage_dir.unwrap_or(false) {
        args.push("--clear-storage-dir".into());
    } else if let Some(dir) = storage_dir {
        args.push("--storage-dir".into());
        args.push(dir);
    }
    if let Some(org) = organize {
        args.push("--organize".into());
        args.push(if org { "on".into() } else { "off".into() });
    }
    if let Some(mode) = storage_mode {
        args.push("--storage-mode".into());
        args.push(mode);
    }
    if let Some(consent) = telemetry_consent {
        args.push("--telemetry-consent".into());
        args.push(if consent { "on".into() } else { "off".into() });
    }
    run_cli_async(args).await
}

/// Inicia uma transcrição. Não bloqueia: corre o worker numa thread e emite
/// cada linha NDJSON como evento `worker://event`; no fim emite `worker://done`.
#[tauri::command]
fn transcribe(app: AppHandle, engine: String, file: String, dest: Option<String>, user: Option<i64>) -> Result<(), String> {
    std::thread::spawn(move || {
        let mut args: Vec<&str> = vec!["transcribe", "--engine", &engine, "--file", &file];
        if let Some(d) = dest.as_deref() {
            if !d.trim().is_empty() {
                args.push("--dest");
                args.push(d);
            }
        }
        let user_s;
        if let Some(u) = user {
            user_s = u.to_string();
            args.push("--user");
            args.push(&user_s);
        }
        let mut cmd = worker_command(&args);
        cmd.stdout(Stdio::piped()).stderr(Stdio::null());
        with_no_window(&mut cmd);
        let child = cmd.spawn();

        let mut child = match child {
            Ok(c) => c,
            Err(e) => {
                let _ = app.emit(
                    "worker://event",
                    format!("{{\"type\":\"error\",\"message\":\"Falha ao iniciar o worker Python: {e}\"}}"),
                );
                let _ = app.emit("worker://done", ());
                return;
            }
        };

        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                if !line.trim().is_empty() {
                    let _ = app.emit("worker://event", line);
                }
            }
        }
        let _ = child.wait();
        let _ = app.emit("worker://done", ());
    });
    Ok(())
}

/// Guardião do túnel SSH (item 10): processo `tunnel-keep` lançado no arranque
/// que abre o túnel UMA vez e o mantém vivo — as chamadas do worker detetam-no
/// e ligam direto, sem pagar o handshake SSH a cada comando. O stdin dele fica
/// preso a este processo: quando a app morre (até em crash), o pipe fecha e o
/// guardião termina sozinho — sem processos órfãos. O Child fica guardado num
/// static para o stdin não ser largado (drop = EOF = guardião sai).
static TUNNEL_KEEPER: std::sync::Mutex<Option<std::process::Child>> = std::sync::Mutex::new(None);

fn spawn_tunnel_keeper() {
    let mut cmd = worker_command(&["tunnel-keep"]);
    cmd.stdin(Stdio::piped()).stdout(Stdio::null()).stderr(Stdio::null());
    with_no_window(&mut cmd);
    if let Ok(child) = cmd.spawn() {
        *TUNNEL_KEEPER.lock().unwrap() = Some(child);
    }
    // Falhou? Sem drama: cada chamada volta ao túnel próprio (comportamento antigo).
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|_app| {
            // Em thread própria: o spawn é barato, mas não queremos NADA a
            // competir com a inicialização da janela (lição da v0.4.5).
            std::thread::spawn(spawn_tunnel_keeper);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            list_engines, check_key, list_credentials, save_credential, clear_credential,
            get_settings, set_settings, library, library_item, library_update, library_delete, library_ack,
            list_system_fonts, db_check, db_check_secret, account, api_reset, api_admin_factor,
            account_suggest, admin, oauth_start, oauth_google, telemetry_event, telemetry_overview, transcribe
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
