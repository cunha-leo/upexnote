// Ponte entre a interface (React) e o worker de transcrição (CLI Python).
// A interface chama estes comandos via `invoke`; o `transcribe` transmite os
// eventos NDJSON do worker em tempo real para a janela via eventos Tauri.
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, OnceLock};
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
    // Registro — 2026-08-12 ("encoding quebrado no Caderno"): no Windows, o
    // Python spawnado sem terminal (stdio redirecionado para pipes, não uma
    // consola real) cai para o codepage ANSI da máquina em vez de UTF-8 para
    // ler/escrever stdin/stdout — acentos sobrevivem na prévia (que só passa
    // por NDJSON no stdout) mas corrompem quando o texto volta a entrar por
    // stdin (corpo da nota, anotações, etc.). PYTHONUTF8 força UTF-8 em todo
    // o runtime; PYTHONIOENCODING cobre explicitamente stdin/stdout/stderr.
    cmd.args(cli_args)
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");
    cmd
}

// --------------------------------------------------------------------------
// Fase A da análise arquitetural (2026-08-13): até aqui, CADA comando do
// Caderno/Biblioteca era um processo do SO inteiro do zero — em modo
// desenvolvimento (sem o worker empacotado) isso significa um interpretador
// Python a arrancar e a reimportar tudo a cada clique. O mesmo padrão que já
// usávamos para o túnel SSH (`TUNNEL_KEEPER`, mais abaixo: um processo vivo,
// guardado num static, cujo stdin preso à app garante que morre sozinho
// quando a app fecha — sem processos órfãos) aplica-se agora ao worker em
// si: UM processo Python persistente (`serve`), a receber pedidos por uma
// linha JSON no stdin e a responder por linhas JSON no stdout, em vez de um
// processo por comando.
//
// Comandos sensíveis a isolamento por chamada (oauth, db-check, api-reset,
// account/admin com prova de senha, support, transcribe) continuam a
// spawnar o próprio processo — não passam por aqui. O ganho é exatamente
// nas ações frequentes e curtas do Caderno/Biblioteca, que é onde a
// lentidão era sentida.
struct PersistentWorker {
    child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

static WORKER: OnceLock<Mutex<Option<PersistentWorker>>> = OnceLock::new();
static REQUEST_ID: AtomicU64 = AtomicU64::new(1);

fn worker_slot() -> &'static Mutex<Option<PersistentWorker>> {
    WORKER.get_or_init(|| Mutex::new(None))
}

fn spawn_persistent_worker() -> Result<PersistentWorker, String> {
    let mut cmd = worker_command(&["serve"]);
    // stderr para null (mesmo padrão do TUNNEL_KEEPER): um traceback Python
    // ocasional não pode bloquear o pipe e travar o worker inteiro — os
    // erros de comando já vêm no envelope JSON do stdout de qualquer forma.
    cmd.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    with_no_window(&mut cmd);
    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Falha ao iniciar o worker persistente: {e}"))?;
    let stdin = child.stdin.take().ok_or("worker persistente sem stdin")?;
    let stdout = child.stdout.take().ok_or("worker persistente sem stdout")?;
    Ok(PersistentWorker { child, stdin, stdout: BufReader::new(stdout) })
}

/// Envia um pedido ao worker persistente (arrancando-o se ainda não existir
/// ou se tiver morrido entretanto) e devolve as linhas de resposta juntas —
/// mesma forma que `run_cli`/`run_cli_stdin_async` sempre devolveram, para
/// não obrigar a mexer nos ~60 comandos Tauri que já esperam este formato.
fn call_worker(argv: Vec<String>, stdin_payload: Option<String>) -> Result<String, String> {
    let slot = worker_slot();
    let mut guard = slot
        .lock()
        .map_err(|_| "lock do worker persistente corrompido".to_string())?;

    let needs_restart = match guard.as_mut() {
        None => true,
        Some(w) => matches!(w.child.try_wait(), Ok(Some(_)) | Err(_)),
    };
    if needs_restart {
        *guard = Some(spawn_persistent_worker()?);
    }

    let req_id = REQUEST_ID.fetch_add(1, Ordering::Relaxed).to_string();
    let req = serde_json::json!({
        "id": req_id,
        "argv": argv,
        "stdin": stdin_payload.unwrap_or_default(),
    });
    let line = req.to_string();

    let result: Result<String, String> = (|| {
        let worker = guard.as_mut().ok_or("worker persistente indisponível")?;
        worker.stdin.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
        worker.stdin.write_all(b"\n").map_err(|e| e.to_string())?;
        worker.stdin.flush().map_err(|e| e.to_string())?;

        let mut collected: Vec<String> = Vec::new();
        loop {
            let mut resp_line = String::new();
            let n = worker
                .stdout
                .read_line(&mut resp_line)
                .map_err(|e| e.to_string())?;
            if n == 0 {
                return Err("worker persistente fechou o stdout inesperadamente".to_string());
            }
            let resp_line = resp_line.trim();
            if resp_line.is_empty() {
                continue;
            }
            let obj: serde_json::Value = serde_json::from_str(resp_line)
                .map_err(|e| format!("resposta inválida do worker persistente: {e}"))?;
            // o mutex serializa pedidos — uma resposta com outro id não
            // deveria acontecer, mas ignora-se em vez de confundir com o
            // pedido atual, por segurança.
            if obj.get("id").and_then(|v| v.as_str()) != Some(req_id.as_str()) {
                continue;
            }
            if let Some(l) = obj.get("line").and_then(|v| v.as_str()) {
                collected.push(l.to_string());
            }
            if obj.get("done").and_then(|v| v.as_bool()) == Some(true) {
                break;
            }
        }
        // um comando que termina sem emitir nenhuma linha é sinal de algo
        // errado no handler Python (todo `cmd_*` emite pelo menos uma linha,
        // sucesso ou erro) — mantém o mesmo contrato de erro que
        // `run_cli`/`run_cli_stdin_async` sempre tiveram para stdout vazio.
        if collected.is_empty() {
            return Err("o worker não devolveu nenhuma resposta para este comando".to_string());
        }
        Ok(collected.join("\n"))
    })();

    // comunicação falhou (pipe partido, worker crashou a meio, etc.): mata
    // o que sobrar e limpa o slot, para a PRÓXIMA chamada rearrancar do
    // zero em vez de continuar a bater contra um worker morto.
    if result.is_err() {
        if let Some(mut w) = guard.take() {
            let _ = w.child.kill();
        }
    }
    result
}

fn run_cli(args: &[&str]) -> Result<String, String> {
    call_worker(args.iter().map(|s| s.to_string()).collect(), None)
}

/// Versão assíncrona: corre `call_worker` numa thread de bloqueio, para não
/// congelar a UI à espera da resposta. Comandos síncronos de Tauri correm na
/// thread principal e bloqueariam a janela toda durante esse tempo.
async fn run_cli_async(args: Vec<String>) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || call_worker(args, None))
        .await
        .map_err(|e| format!("erro na thread do worker: {e}"))?
}

async fn run_cli_stdin_async(args: Vec<String>, payload: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || call_worker(args, Some(payload)))
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
    const OPS: [&str; 5] = ["register", "login", "oauth-login", "update", "profile"];
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

/// Support requests use the central API. Customer identity secrets are held by
/// the worker in Windows Credential Manager; the UI only supplies profile and
/// ticket fields through stdin.
#[tauri::command]
async fn support(op: String, payload: String) -> Result<String, String> {
    const OPS: [&str; 11] = ["identity", "create", "list", "detail", "comment", "attachment", "admin-list", "admin-detail", "admin-comment", "admin-status", "admin-assignment"];
    if !OPS.contains(&op.as_str()) {
        return Err(format!("operaÃ§Ã£o de suporte desconhecida: {op}"));
    }
    run_cli_stdin_async(vec![format!("support-{op}")], payload).await
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
    const OPS: [&str; 12] = ["overview", "users", "create-user", "update-user", "delete-user", "events", "audit", "data-catalog", "data-table", "data-query", "data-sql", "data-saved-queries"];
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

/// Motores de FORMATAÇÃO (clean → documento estruturado, ADF-01), com modelo,
/// custo estimado por hora de transcript e se a chave já está configurada.
/// Deliberadamente separado de `list_engines` (áudio → texto): são etapas
/// diferentes do pipeline, com chaves categorizadas por finalidade, e a UI
/// mostra-as em secções próprias. Sem motor padrão, por decisão de 06/08/2026.
#[tauri::command]
async fn format_engines() -> Result<String, String> {
    run_cli_async(vec!["format-engines".into()]).await
}

/// Um documento estruturado completo — hub, blocos, glossário e métricas —
/// para o leitor do passo 2. Espelha `library_item`: mesma prova de MFA, mesmo
/// isolamento por utilizador. `async` para não congelar a janela enquanto o
/// worker consulta a base pelo túnel.
#[tauri::command]
async fn document_item(
    id: i64, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["document-item".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// Apaga um documento estruturado. É soft-delete com snapshot em
/// `documents_history` (feito pelo worker); o transcript de origem fica
/// intacto, porque o documento é uma camada derivada dele.
#[tauri::command]
async fn document_delete(
    id: i64, user: Option<i64>, admin_email: Option<String>, admin_token: Option<String>
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["document-delete".into(), "--json-stdin".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_stdin_async(args, admin_proof_json(admin_email, admin_token, None)).await
}

/// ADF-02 fatia 3 (fundação `notebooks`): coleção padrão, árvore, nota vazia.
/// Domínio pessoal/dono-apenas nesta fatia (sem navegação admin entre
/// utilizadores ainda) — por isso mais simples que library/document: sem
/// `--json-stdin`/prova de MFA, só `--user` (mesmo espírito de `get_settings`).

/// Garante (cria se preciso) a coleção padrão do Caderno do utilizador.
#[tauri::command]
async fn notebook_ensure_default(user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-ensure-default".into()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Árvore completa (coleções + notas) do Caderno do utilizador.
#[tauri::command]
async fn notebook_tree(user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-tree".into()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Cria pasta/projeto/caderno/seção.
#[tauri::command]
async fn notebook_collection_create(
    title: String, kind: Option<String>, parent_id: Option<i64>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-collection-create".into(), "--title".into(), title];
    args.push("--kind".into());
    args.push(kind.unwrap_or_else(|| "notebook".into()));
    if let Some(pid) = parent_id {
        args.push("--parent-id".into());
        args.push(pid.to_string());
    }
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Apaga uma coleção e as suas descendentes/notas (soft-delete em cascata).
#[tauri::command]
async fn notebook_collection_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-collection-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Cria uma nota vazia numa coleção.
#[tauri::command]
async fn notebook_note_create(
    collection_id: i64, title: Option<String>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-note-create".into(), "--collection-id".into(), collection_id.to_string(),
    ];
    if let Some(t) = title {
        args.push("--title".into());
        args.push(t);
    }
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Uma nota completa (título + corpo).
#[tauri::command]
async fn notebook_note_item(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-item".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Abrir nota: item + anotações + referências + links + keywords + glossário
/// numa só chamada — antes eram 6 spawns de processo separados (análise
/// arquitetural 2026-08-13, fase B).
#[tauri::command]
async fn notebook_note_open(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-open".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Edita título e/ou corpo de uma nota. O corpo (potencialmente grande) vai
/// por STDIN, nunca por argumento — mesmo cuidado de `library_update`.
#[tauri::command]
async fn notebook_note_update(
    id: i64, title: Option<String>, body: Option<String>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-update".into(), "--id".into(), id.to_string()];
    if let Some(t) = title {
        args.push("--title".into());
        args.push(t);
    }
    push_user(&mut args, user);
    match body {
        Some(b) => {
            args.push("--stdin-body".into());
            run_cli_stdin_async(args, b).await
        }
        None => run_cli_async(args).await,
    }
}

/// Apaga uma nota (arquivada no histórico pelo worker).
#[tauri::command]
async fn notebook_note_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// ADF-02 fatia 4 ("Passagem controlada"): copia a prévia (documento
/// estruturado) para uma nota nova em `notebooks`, com linhagem — nunca uma
/// referência viva; a prévia em `documents` fica intacta. Idempotente: um
/// segundo clique devolve a nota já criada em vez de duplicar.
#[tauri::command]
async fn notebook_save_document(
    document_id: i64, collection_id: Option<i64>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-save-document".into(), "--document-id".into(), document_id.to_string(),
    ];
    if let Some(cid) = collection_id {
        args.push("--collection-id".into());
        args.push(cid.to_string());
    }
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// ADF-02 fatia 5 ("Editor rico essencial"): versões recuperáveis da nota —
/// snapshot manual (não a cada autosave), listar, restaurar.
#[tauri::command]
async fn notebook_note_version_create(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-version-create".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_note_versions(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-note-versions".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_note_version_restore(note_id: i64, version_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-note-version-restore".into(), "--note-id".into(), note_id.to_string(),
        "--version-id".into(), version_id.to_string(),
    ];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// ADF-02 fatia 6 ("Anotações e referências"): comentário ancorado a um
/// trecho da nota (âncora híbrida) e referência de estudo solta. O corpo do
/// comentário vai por STDIN (pode ser longo/ter qualquer carácter); a
/// seleção/contexto vão como argumentos (curtos, controlados pela UI).
#[tauri::command]
async fn notebook_annotation_create(
    note_id: i64, body: String, block_id: Option<String>, start_offset: Option<i64>,
    end_offset: Option<i64>, selected_text: Option<String>, context_snippet: Option<String>,
    user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-annotation-create".into(), "--note-id".into(), note_id.to_string()];
    if let Some(b) = block_id { args.push("--block-id".into()); args.push(b); }
    if let Some(s) = start_offset { args.push("--start-offset".into()); args.push(s.to_string()); }
    if let Some(e) = end_offset { args.push("--end-offset".into()); args.push(e.to_string()); }
    if let Some(s) = selected_text { args.push("--selected-text".into()); args.push(s); }
    if let Some(c) = context_snippet { args.push("--context-snippet".into()); args.push(c); }
    push_user(&mut args, user);
    run_cli_stdin_async(args, body).await
}

#[tauri::command]
async fn notebook_annotation_list(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-annotation-list".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_annotation_resolve(id: i64, reopen: Option<bool>, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-annotation-resolve".into(), "--id".into(), id.to_string()];
    if reopen.unwrap_or(false) { args.push("--reopen".into()); }
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_annotation_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-annotation-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_reference_create(
    note_id: i64, title: Option<String>, url: Option<String>, note_text: Option<String>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-reference-create".into(), "--note-id".into(), note_id.to_string()];
    if let Some(t) = title { args.push("--title".into()); args.push(t); }
    if let Some(u) = url { args.push("--url".into()); args.push(u); }
    if let Some(n) = note_text { args.push("--note-text".into()); args.push(n); }
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_reference_list(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-reference-list".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_reference_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-reference-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Backlinks (11/08/2026): ligação direcionada nota→nota escolhida
/// explicitamente pelo utilizador.
#[tauri::command]
async fn notebook_link_create(from_note_id: i64, to_note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-link-create".into(),
        "--from-note-id".into(), from_note_id.to_string(),
        "--to-note-id".into(), to_note_id.to_string(),
    ];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_links(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-links".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_link_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-link-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// ADF-02 fatia 7 ("Dicionário e glossário"): palavra-chave solta e
/// definição vinculada à nota.
#[tauri::command]
async fn notebook_keyword_create(note_id: i64, term: String, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-keyword-create".into(), "--note-id".into(), note_id.to_string(), "--term".into(), term];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_keyword_list(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-keyword-list".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_keyword_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-keyword-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_glossary_create(
    note_id: i64, term: String, definition: String, source: Option<String>, language: Option<String>,
    user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-glossary-create".into(), "--note-id".into(), note_id.to_string(),
        "--term".into(), term, "--definition".into(), definition,
    ];
    if let Some(s) = source { args.push("--source".into()); args.push(s); }
    if let Some(l) = language { args.push("--language".into()); args.push(l); }
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_glossary_list(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-glossary-list".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_glossary_delete(id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-glossary-delete".into(), "--id".into(), id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// ADF-02 fatia 8 ("Exportação e pacote para IA"): conteúdo montado a partir
/// das camadas escolhidas — `layers` é uma lista separada por vírgulas
/// (body,annotations,references,glossary,lineage), nunca "tudo por defeito".
#[tauri::command]
async fn notebook_export(
    note_id: i64, layers: Option<String>, format: Option<String>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-export".into(), "--note-id".into(), note_id.to_string()];
    if let Some(l) = layers { args.push("--layers".into()); args.push(l); }
    if let Some(f) = format { args.push("--format".into()); args.push(f); }
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_context_package_create(
    note_id: i64, layers: Option<String>, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-context-package-create".into(), "--note-id".into(), note_id.to_string()];
    if let Some(l) = layers { args.push("--layers".into()); args.push(l); }
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_context_packages(note_id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec!["notebook-context-packages".into(), "--note-id".into(), note_id.to_string()];
    push_user(&mut args, user);
    run_cli_async(args).await
}

#[tauri::command]
async fn notebook_context_package_item(note_id: i64, id: i64, user: Option<i64>) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "notebook-context-package-item".into(), "--note-id".into(), note_id.to_string(), "--id".into(), id.to_string(),
    ];
    push_user(&mut args, user);
    run_cli_async(args).await
}

/// Exportação de facto para disco (pedido do Leonardo: o botão "Exportar" tem
/// de gravar um ficheiro de verdade escolhido pelo utilizador — não só copiar
/// texto para a área de transferência e mostrar numa caixinha). O caminho vem
/// sempre do diálogo nativo `save()` do plugin dialog (já autorizado por
/// `dialog:allow-save`); estes dois comandos só gravam bytes/texto nesse
/// caminho — sem tocar no worker Python, o `.docx` é montado no frontend
/// (biblioteca `docx`) porque não há `python-docx` instalado no worker e não
/// dava para validar um build novo do PyInstaller nesta sessão de trabalho.
#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_binary_file(path: String, data: Vec<u8>) -> Result<(), String> {
    std::fs::write(&path, data).map_err(|e| e.to_string())
}

/// Formatação retroativa (o botão "Formatar" na Biblioteca e no fim do
/// Transcribe): parte de uma transcrição já existente, corre o gate raw↔clean
/// e persiste o documento estruturado.
///
/// Ao contrário dos três acima, este NÃO devolve um JSON de uma vez: o worker
/// emite NDJSON progressivo (`start` → `progress`* → `validation` →
/// `format_result` ou `error`), porque a chamada ao motor demora. Segue por
/// isso o modelo do `transcribe` — thread própria e eventos — e não
/// `run_cli_async`, que só devolveria no fim.
///
/// Usa canal próprio (`document://event`/`document://done`) em vez do
/// `worker://` do `transcribe`: os dois podem estar vivos ao mesmo tempo e os
/// eventos não se podem misturar na janela.
#[tauri::command]
fn document_generate(
    app: AppHandle,
    transcription_id: i64,
    engine: String,
    profile: Option<String>,
    user: Option<i64>,
) -> Result<(), String> {
    std::thread::spawn(move || {
        // Donos das strings antes de emprestar para o vetor de argumentos.
        let id_s = transcription_id.to_string();
        let profile_s = profile.unwrap_or_default();
        let user_s = user.map(|u| u.to_string()).unwrap_or_default();

        let mut args: Vec<&str> = vec![
            "document-generate",
            "--transcription-id",
            &id_s,
            "--engine",
            &engine,
        ];
        if !profile_s.trim().is_empty() {
            args.push("--profile");
            args.push(&profile_s);
        }
        if !user_s.is_empty() {
            args.push("--user");
            args.push(&user_s);
        }

        let mut cmd = worker_command(&args);
        cmd.stdout(Stdio::piped()).stderr(Stdio::null());
        with_no_window(&mut cmd);

        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                let _ = app.emit(
                    "document://event",
                    format!("{{\"type\":\"error\",\"message\":\"Falha ao iniciar o worker Python: {e}\"}}"),
                );
                let _ = app.emit("document://done", ());
                return;
            }
        };

        if let Some(stdout) = child.stdout.take() {
            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                if !line.trim().is_empty() {
                    let _ = app.emit("document://event", line);
                }
            }
        }
        let _ = child.wait();
        let _ = app.emit("document://done", ());
    });
    Ok(())
}

/// Guarda (retry) um documento estruturado JÁ GERADO — recuperação sem
/// chamar a IA de novo quando a gravação inicial falhou (ver Registro —
/// 2026-08-11, "documento gerado mas não gravado"). O JSON do documento (e
/// uso de tokens) vai por STDIN; os campos curtos vão como argumentos.
#[tauri::command]
async fn document_save(
    transcription_id: i64, engine: String, profile: String, payload: String, user: Option<i64>,
) -> Result<String, String> {
    let mut args: Vec<String> = vec![
        "document-save".into(),
        "--transcription-id".into(), transcription_id.to_string(),
        "--engine".into(), engine,
        "--profile".into(), profile,
    ];
    push_user(&mut args, user);
    run_cli_stdin_async(args, payload).await
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
            format_engines, document_item, document_delete, document_generate, document_save,
            notebook_ensure_default, notebook_tree, notebook_collection_create, notebook_collection_delete,
            notebook_note_create, notebook_note_item, notebook_note_open, notebook_note_update, notebook_note_delete,
            notebook_save_document,
            notebook_note_version_create, notebook_note_versions, notebook_note_version_restore,
            notebook_annotation_create, notebook_annotation_list, notebook_annotation_resolve, notebook_annotation_delete,
            notebook_reference_create, notebook_reference_list, notebook_reference_delete,
            notebook_link_create, notebook_links, notebook_link_delete,
            notebook_keyword_create, notebook_keyword_list, notebook_keyword_delete,
            notebook_glossary_create, notebook_glossary_list, notebook_glossary_delete,
            notebook_export, notebook_context_package_create, notebook_context_packages, notebook_context_package_item,
            write_text_file, write_binary_file,
            list_system_fonts, db_check, db_check_secret, account, api_reset, api_admin_factor,
            account_suggest, admin, oauth_start, oauth_google, telemetry_event, telemetry_overview, support, transcribe
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
