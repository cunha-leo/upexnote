import { useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

type Engine = {
  id: string;
  label: string;
  info: string;
  primary: boolean;
  key_name: string;
  key_set: boolean;
};

type ResultData = {
  ok: boolean;
  clean_text: string;
  clean_path: string;
  cost: number;
  duration_s: number;
  problems: string[];
  language: string | null;
};

type View = "transcribe" | "settings";

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("upexnote-theme") as "light" | "dark") ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("upexnote-theme", theme);
  }, [theme]);
  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}

// ---------------------------------------------------------------------------
// Ecrã de Definições — gerir chaves/credenciais (guardadas no Credential Manager)
// ---------------------------------------------------------------------------
const CREDENTIALS = [
  { name: "ASSEMBLYAI_API_KEY", label: "AssemblyAI API Key", hint: "Motor principal. Obtém em console.assemblyai.com" },
  { name: "OPENAI_API_KEY", label: "OpenAI API Key", hint: "whisper-1 / gpt-4o. Obtém em platform.openai.com" },
  { name: "DEEPGRAM_API_KEY", label: "Deepgram API Key", hint: "Obtém em console.deepgram.com" },
  { name: "UPEXNOTE_PG_PASSWORD", label: "Password do Postgres (VPS)", hint: "Para gravar o histórico/backup na base de dados" },
];

type StorageSettings = {
  storage_dir: string;
  storage_dir_custom: boolean;
  default_storage_dir: string;
  organize_by_day_engine: boolean;
};

function StorageSettingsCard() {
  const [s, setS] = useState<StorageSettings | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const raw = await invoke<string>("get_settings");
      setS(JSON.parse(raw));
    } catch (e) {
      setMsg("Erro a carregar: " + String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function apply(args: Record<string, unknown>, okMsg: string) {
    setBusy(true);
    setMsg("");
    try {
      const raw = await invoke<string>("set_settings", args);
      setS(JSON.parse(raw));
      setMsg(okMsg);
    } catch (e) {
      setMsg("Erro: " + String(e));
    } finally {
      setBusy(false);
    }
  }

  async function chooseFolder() {
    const picked = await open({
      directory: true,
      multiple: false,
      title: "Escolhe a pasta padrão dos transcripts",
    });
    if (typeof picked === "string") {
      await apply({ storageDir: picked }, "Pasta padrão atualizada ✓");
    }
  }

  return (
    <section className="card">
      <h2>Transcrições — Onde guardar</h2>
      <p className="muted" style={{ marginTop: -6, marginBottom: 16 }}>
        Os transcripts são gravados na pasta que escolheres — a tua estrutura manda. Podes ainda trocar
        pontualmente no ecrã Transcrever ("Guardar em…").
      </p>
      <div className="field">
        <label>Pasta padrão</label>
        <div className="row">
          <input type="text" readOnly value={s ? s.storage_dir : "a carregar…"} />
          <button className="secondary" onClick={chooseFolder} disabled={busy || !s}>Escolher…</button>
          {s?.storage_dir_custom && (
            <button
              className="secondary"
              onClick={() => apply({ clearStorageDir: true }, "Reposta a pasta padrão de fábrica.")}
              disabled={busy}
            >
              Repor padrão
            </button>
          )}
        </div>
        {s && !s.storage_dir_custom && (
          <div className="engine-info">Padrão de fábrica: {s.default_storage_dir}</div>
        )}
      </div>
      <div className="field">
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={s ? s.organize_by_day_engine : true}
            disabled={busy || !s}
            onChange={(e) => apply({ organize: e.currentTarget.checked }, "Organização atualizada ✓")}
            style={{ width: "auto" }}
          />
          <span>Organizar em subpastas por dia e motor (ex.: 2026-07-14\assemblyai\)</span>
        </label>
        <div className="engine-info">
          Desligado: os ficheiros ficam diretamente na pasta padrão. O nome já inclui origem, data,
          motor e tipo, por isso identificam-se sozinhos.
          {msg ? " — " + msg : ""}
        </div>
      </div>
    </section>
  );
}

function SettingsView({ onChanged }: { onChanged: () => void }) {
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [loaded, setLoaded] = useState(false);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  async function loadStatuses() {
    try {
      const raw = await invoke<string>("list_credentials");
      const obj = JSON.parse(raw);
      const map: Record<string, boolean> = {};
      (obj.keys || []).forEach((k: any) => {
        map[k.name] = !!k.key_set;
      });
      setStatus(map);
    } catch {
      /* ignora */
    } finally {
      setLoaded(true);
    }
  }
  useEffect(() => {
    loadStatuses();
  }, []);

  async function save(name: string) {
    const value = (inputs[name] || "").trim();
    if (!value) {
      setMsg((m) => ({ ...m, [name]: "Escreve um valor primeiro." }));
      return;
    }
    setBusy((b) => ({ ...b, [name]: true }));
    try {
      await invoke("save_credential", { name, value });
      setInputs((i) => ({ ...i, [name]: "" }));
      setMsg((m) => ({ ...m, [name]: "Guardada ✓" }));
      await loadStatuses();
      onChanged();
    } catch (e) {
      setMsg((m) => ({ ...m, [name]: "Erro: " + String(e) }));
    } finally {
      setBusy((b) => ({ ...b, [name]: false }));
    }
  }

  async function clear(name: string) {
    setBusy((b) => ({ ...b, [name]: true }));
    try {
      await invoke("clear_credential", { name });
      setMsg((m) => ({ ...m, [name]: "Removida." }));
      await loadStatuses();
      onChanged();
    } catch (e) {
      setMsg((m) => ({ ...m, [name]: "Erro: " + String(e) }));
    } finally {
      setBusy((b) => ({ ...b, [name]: false }));
    }
  }

  return (
    <section className="card">
      <h2>Definições — Chaves e credenciais</h2>
      <p className="muted" style={{ marginTop: -6, marginBottom: 16 }}>
        Guardadas no Windows Credential Manager (o cofre encriptado do Windows), nunca em ficheiros nem no
        código. O valor nunca é mostrado depois de guardado.
      </p>
      {CREDENTIALS.map((c) => (
        <div className="field cred" key={c.name}>
          <div className="cred-head">
            <label style={{ margin: 0 }}>{c.label}</label>
            <span className={"badge " + (!loaded ? "" : status[c.name] ? "ok" : "warn")}>
              {!loaded ? "a verificar…" : status[c.name] ? "Configurada" : "Não configurada"}
            </span>
          </div>
          <div className="row">
            <input
              type="text"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              placeholder={status[c.name] ? "configurada — escreve para substituir" : "Cola aqui o valor…"}
              value={inputs[c.name] || ""}
              onPaste={(e) => {
                // Intercetamos o colar e inserimos o texto nós próprios, para
                // não passar pelo "colar nativo" da WebView2 (que crasha nesta
                // máquina). Substitui o valor pelo texto colado (limpo).
                e.preventDefault();
                const text = e.clipboardData.getData("text");
                setInputs((i) => ({ ...i, [c.name]: text.trim() }));
              }}
              onChange={(e) => setInputs((i) => ({ ...i, [c.name]: e.currentTarget.value }))}
            />
            <button onClick={() => save(c.name)} disabled={busy[c.name]}>Guardar</button>
            {status[c.name] && (
              <button className="secondary" onClick={() => clear(c.name)} disabled={busy[c.name]}>Remover</button>
            )}
          </div>
          <div className="engine-info">
            {c.hint}
            {msg[c.name] ? " — " + msg[c.name] : ""}
          </div>
        </div>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------------------
// App — layout com menu lateral + roteamento de vistas
// ---------------------------------------------------------------------------
function App() {
  const { theme, toggle } = useTheme();
  const [view, setView] = useState<View>("transcribe");
  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem("upexnote-sidebar") === "collapsed"
  );
  useEffect(() => {
    localStorage.setItem("upexnote-sidebar", collapsed ? "collapsed" : "open");
  }, [collapsed]);

  const [engines, setEngines] = useState<Engine[]>([]);
  const [engineId, setEngineId] = useState<string>("");
  const [file, setFile] = useState<string>("");
  const [dest, setDest] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [stage, setStage] = useState<number>(0);
  const [elapsed, setElapsed] = useState<number>(0);
  const [result, setResult] = useState<ResultData | null>(null);
  const [loadError, setLoadError] = useState<string>("");
  const transcriptRef = useRef<HTMLPreElement>(null);

  const selected = useMemo(() => engines.find((e) => e.id === engineId), [engines, engineId]);

  const STAGES = [
    "A preparar…",
    "A enviar o ficheiro para a nuvem…",
    "Ficheiro enviado. A submeter o pedido…",
    "A transcrever na nuvem… (costuma demorar 1–2 min)",
    "A finalizar e validar…",
  ];

  function stageFor(msg: string): number {
    const m = msg.toLowerCase();
    if (m.includes("guardado") || m.includes("valida") || m.includes("custo") || m.includes("tempo total")) return 4;
    if (m.includes("submetido") || m.includes("aguardar") || m.includes("estado:")) return 3;
    if (m.includes("upload conclu") || m.includes("submeter")) return 2;
    if (m.includes("carregar") || m.includes("iniciar") || m.includes("preparar")) return 1;
    return 0;
  }

  function fmtElapsed(s: number): string {
    const mm = Math.floor(s / 60).toString().padStart(2, "0");
    const ss = (s % 60).toString().padStart(2, "0");
    return `${mm}:${ss}`;
  }

  async function loadEngines() {
    try {
      const raw = await invoke<string>("list_engines");
      const parsed = JSON.parse(raw);
      const list: Engine[] = parsed.engines || [];
      setEngines(list);
      setEngineId((cur) => cur || list.find((e) => e.primary)?.id || list[0]?.id || "");
      setLoadError("");
    } catch (e) {
      setLoadError(String(e));
    }
  }

  useEffect(() => {
    loadEngines();
  }, []);

  useEffect(() => {
    const unlistenEvent = listen<string>("worker://event", (ev) => {
      let obj: any;
      try {
        obj = JSON.parse(ev.payload);
      } catch {
        return;
      }
      if (obj.type === "progress" || obj.type === "start") {
        const msg = obj.message || "A processar…";
        setStatus(msg);
        const s = stageFor(msg);
        if (s > 0) setStage((cur) => Math.max(cur, s));
      } else if (obj.type === "result") {
        setResult(obj as ResultData);
        setStatus(obj.ok ? "Concluído." : "Concluído com avisos.");
      } else if (obj.type === "error") {
        setStatus("Erro: " + obj.message);
      }
    });
    const unlistenDone = listen("worker://done", () => setRunning(false));
    return () => {
      unlistenEvent.then((f) => f());
      unlistenDone.then((f) => f());
    };
  }, []);

  useEffect(() => {
    if (!running) return;
    const started = Date.now();
    setElapsed(0);
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [running]);

  function reset() {
    setFile("");
    setDest("");
    setResult(null);
    setStatus("");
    setStage(0);
    setElapsed(0);
  }

  async function startTranscription() {
    if (!file || !selected || running) return;
    setRunning(true);
    setResult(null);
    setStage(1);
    setStatus("A iniciar…");
    try {
      await invoke("transcribe", { engine: selected.id, file, dest: dest.trim() || null });
    } catch (e) {
      setStatus("Erro: " + String(e));
      setRunning(false);
    }
  }

  function copyTranscript() {
    if (result) navigator.clipboard.writeText(result.clean_text);
  }

  async function chooseDest() {
    const picked = await open({
      directory: true,
      multiple: false,
      title: "Guardar o transcript em…",
    });
    if (typeof picked === "string") setDest(picked);
  }

  async function chooseFile() {
    const picked = await open({
      multiple: false,
      directory: false,
      title: "Escolhe o vídeo ou áudio",
      filters: [
        { name: "Vídeo / Áudio", extensions: ["mp4", "mov", "mkv", "webm", "avi", "wav", "mp3", "m4a", "aac", "flac", "ogg"] },
        { name: "Todos os ficheiros", extensions: ["*"] },
      ],
    });
    if (typeof picked === "string") setFile(picked);
  }

  const navItems: { id: View; icon: string; label: string }[] = [
    { id: "transcribe", icon: "🎙", label: "Transcrever" },
    { id: "settings", icon: "⚙", label: "Definições" },
  ];

  return (
    <div className="layout">
      <aside className={"sidebar" + (collapsed ? " collapsed" : "")}>
        <div className="sidebar-brand">
          {collapsed ? (
            <span className="logo-mini">U</span>
          ) : (
            <>
              <div className="wordmark"><span className="up">Upex</span><span className="ex">Note</span></div>
              <div className="tagline">Transcreva, organize e explore.</div>
            </>
          )}
        </div>

        <nav className="nav">
          {navItems.map((it) => (
            <button
              key={it.id}
              className={"nav-item" + (view === it.id ? " active" : "")}
              onClick={() => setView(it.id)}
              title={it.label}
            >
              <span className="nav-ico">{it.icon}</span>
              {!collapsed && <span>{it.label}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button className="nav-item" onClick={toggle} title="Tema">
            <span className="nav-ico">{theme === "dark" ? "☀" : "🌙"}</span>
            {!collapsed && <span>{theme === "dark" ? "Tema claro" : "Tema escuro"}</span>}
          </button>
          <button className="nav-item" onClick={() => setCollapsed((c) => !c)} title="Recolher menu">
            <span className="nav-ico">{collapsed ? "»" : "«"}</span>
            {!collapsed && <span>Recolher</span>}
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="body">
          {view === "transcribe" && (
            <>
              <section className="card">
                <h2>Transcrever</h2>

                <div className="field">
                  <label>Vídeo ou áudio</label>
                  <div className="row">
                    <input
                      type="text"
                      value={file}
                      placeholder="Escolhe um ficheiro ou cola aqui o caminho…"
                      onChange={(e) => setFile(e.currentTarget.value)}
                    />
                    <button className="secondary" onClick={chooseFile} disabled={running}>Escolher…</button>
                  </div>
                </div>

                <div className="field">
                  <label>Guardar em (opcional — só desta vez)</label>
                  <div className="row">
                    <input
                      type="text"
                      value={dest}
                      placeholder="Vazio = pasta padrão das Definições"
                      onChange={(e) => setDest(e.currentTarget.value)}
                    />
                    <button className="secondary" onClick={chooseDest} disabled={running}>Escolher…</button>
                    {dest && (
                      <button className="secondary" onClick={() => setDest("")} disabled={running}>Limpar</button>
                    )}
                  </div>
                  {dest && (
                    <div className="engine-info">Os ficheiros desta transcrição vão diretos para: {dest}</div>
                  )}
                </div>

                <div className="field">
                  <label>Motor de transcrição</label>
                  <select value={engineId} onChange={(e) => setEngineId(e.currentTarget.value)}>
                    {engines.map((e) => (
                      <option key={e.id} value={e.id}>{e.label}</option>
                    ))}
                  </select>
                  {selected && <div className="engine-info">{selected.info}</div>}
                  {selected && !selected.key_set && (
                    <div className="key-warn">
                      ⚠ A chave {selected.key_name} ainda não está configurada — abre <b>Definições</b> para a guardar.
                    </div>
                  )}
                  {loadError && <div className="key-warn">Não consegui carregar os motores: {loadError}</div>}
                </div>

                <div className="row wrap">
                  <button onClick={startTranscription} disabled={!file || running || !selected}>
                    {running ? "A transcrever…" : "Transcrever"}
                  </button>
                  {!running && (result || status) && (
                    <button className="secondary" onClick={reset}>Novo</button>
                  )}
                  {running && (
                    <div className="status">
                      <span className="spinner" />
                      <span>{STAGES[stage] || status}</span>
                      <span className="elapsed">decorrido {fmtElapsed(elapsed)}</span>
                    </div>
                  )}
                  {!running && status && <div className="status"><span>{status}</span></div>}
                </div>

                {running && (
                  <div className="stepper">
                    {[1, 2, 3, 4].map((n) => (
                      <div key={n} className={"step" + (stage >= n ? " done" : "") + (stage === n ? " active" : "")}>
                        <span className="dot" />
                        <span className="step-label">
                          {n === 1 && "Enviar"}
                          {n === 2 && "Submeter"}
                          {n === 3 && "Transcrever"}
                          {n === 4 && "Finalizar"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {result && (
                <section className="card">
                  <div className="result-head">
                    <h2 style={{ margin: 0 }}>Resultado</h2>
                    <span className={"badge " + (result.ok ? "ok" : "warn")}>
                      {result.ok ? "✓ Validação OK" : "⚠ Com avisos"}
                    </span>
                    {result.language && <span className="badge">idioma: {result.language}</span>}
                    <span className="badge">~${result.cost.toFixed(4)}</span>
                    <span className="badge">{Math.round(result.duration_s / 60)} min</span>
                    <div className="spacer" style={{ flex: 1 }} />
                    <button className="secondary" onClick={copyTranscript}>Copiar tudo</button>
                  </div>
                  <pre className="transcript" ref={transcriptRef}>{result.clean_text}</pre>
                  {result.clean_path && (
                    <div className="muted" style={{ marginTop: 8 }}>Guardado em: {result.clean_path}</div>
                  )}
                </section>
              )}
            </>
          )}

          {view === "settings" && (
            <>
              <SettingsView onChanged={loadEngines} />
              <StorageSettingsCard />
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
