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

function App() {
  const { theme, toggle } = useTheme();
  const [engines, setEngines] = useState<Engine[]>([]);
  const [engineId, setEngineId] = useState<string>("");
  const [file, setFile] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [stage, setStage] = useState<number>(0);
  const [elapsed, setElapsed] = useState<number>(0);
  const [result, setResult] = useState<ResultData | null>(null);
  const [loadError, setLoadError] = useState<string>("");
  const transcriptRef = useRef<HTMLPreElement>(null);

  const selected = useMemo(
    () => engines.find((e) => e.id === engineId),
    [engines, engineId]
  );

  const STAGES = [
    "A preparar…",
    "A enviar o ficheiro para a nuvem…",
    "Ficheiro enviado. A submeter o pedido…",
    "A transcrever na nuvem… (costuma demorar 1–2 min)",
    "A finalizar e validar…",
  ];

  // Converte a mensagem crua do worker numa etapa amigável (1..4).
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
    const unlistenDone = listen("worker://done", () => {
      setRunning(false);
    });
    return () => {
      unlistenEvent.then((f) => f());
      unlistenDone.then((f) => f());
    };
  }, []);

  // Cronómetro enquanto a transcrição corre.
  useEffect(() => {
    if (!running) return;
    const started = Date.now();
    setElapsed(0);
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [running]);

  async function startTranscription() {
    if (!file || !selected || running) return;
    setRunning(true);
    setResult(null);
    setStage(1);
    setStatus("A iniciar…");
    try {
      await invoke("transcribe", { engine: selected.id, file });
    } catch (e) {
      setStatus("Erro: " + String(e));
      setRunning(false);
    }
  }

  function copyTranscript() {
    if (result) navigator.clipboard.writeText(result.clean_text);
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

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="wordmark">
            <span className="up">Upex</span><span className="ex">Note</span>
          </div>
          <div className="tagline">Transcreva, organize e explore suas conversas.</div>
        </div>
        <div className="spacer" />
        <button className="theme-toggle" onClick={toggle}>
          {theme === "dark" ? "☀ Claro" : "🌙 Escuro"}
        </button>
      </header>

      <main className="body">
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
              <button className="secondary" onClick={chooseFile} disabled={running}>
                Escolher…
              </button>
            </div>
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
                ⚠ A chave {selected.key_name} ainda não está configurada — a transcrição vai falhar até a configurares.
              </div>
            )}
            {loadError && (
              <div className="key-warn">Não consegui carregar os motores: {loadError}</div>
            )}
          </div>

          <div className="row wrap">
            <button onClick={startTranscription} disabled={!file || running || !selected}>
              {running ? "A transcrever…" : "Transcrever"}
            </button>
            {running && (
              <div className="status">
                <span className="spinner" />
                <span>{STAGES[stage] || status}</span>
                <span className="elapsed">decorrido {fmtElapsed(elapsed)}</span>
              </div>
            )}
            {!running && status && (
              <div className="status"><span>{status}</span></div>
            )}
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
      </main>
    </div>
  );
}

export default App;
