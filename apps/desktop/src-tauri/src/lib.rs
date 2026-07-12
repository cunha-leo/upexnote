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
/// NOTA: para a app empacotada isto terá de mudar (o worker será um sidecar) —
/// tratado numa fase posterior.
fn worker_dir() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR")); // .../apps/desktop/src-tauri
    p.pop(); // .../apps/desktop
    p.pop(); // .../apps
    p.pop(); // .../ (raiz do repo)
    p.push("services");
    p.push("worker");
    p
}

fn run_cli(args: &[&str]) -> Result<String, String> {
    let mut cmd = Command::new("python");
    cmd.arg("-m").arg("transcription.cli").args(args).current_dir(worker_dir());
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

/// Lista os motores (JSON de uma linha, tal como a CLI devolve).
#[tauri::command]
fn list_engines() -> Result<String, String> {
    run_cli(&["engines"])
}

/// Diz se uma chave está configurada (JSON), sem revelar o valor.
#[tauri::command]
fn check_key(name: String) -> Result<String, String> {
    run_cli(&["check-key", "--name", &name])
}

/// Estado de todas as chaves numa só chamada (o ecrã de Definições usa isto).
#[tauri::command]
fn list_credentials() -> Result<String, String> {
    run_cli(&["list-keys"])
}

/// Guarda uma chave/credencial recebida da interface. O valor é escrito no
/// stdin do worker (nunca em argumentos/linha de comando, que seriam visíveis
/// na lista de processos) e acaba no Windows Credential Manager.
#[tauri::command]
fn save_credential(name: String, value: String) -> Result<String, String> {
    use std::io::Write;
    let mut cmd = Command::new("python");
    cmd.args(["-m", "transcription.cli", "set-key", "--name", &name, "--stdin"])
        .current_dir(worker_dir())
        .stdin(Stdio::piped())
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

/// Inicia uma transcrição. Não bloqueia: corre o worker numa thread e emite
/// cada linha NDJSON como evento `worker://event`; no fim emite `worker://done`.
#[tauri::command]
fn transcribe(app: AppHandle, engine: String, file: String) -> Result<(), String> {
    let dir = worker_dir();
    std::thread::spawn(move || {
        let mut cmd = Command::new("python");
        cmd.args(["-u", "-m", "transcription.cli", "transcribe", "--engine", &engine, "--file", &file])
            .current_dir(dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::null());
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            list_engines, check_key, list_credentials, save_credential, clear_credential, transcribe
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
