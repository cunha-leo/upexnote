import { useEffect, useMemo, useRef, useState, type ClipboardEvent, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import {
  Mic, LibraryBig, Settings, Palette, PanelLeftClose, PanelLeftOpen,
  Search, ArrowLeft, ArrowRight, Minus, Square, X,
} from "lucide-react";
import "./App.css";

/* Marca UpexNote — balão de conversa + onda sonora (eco do ícone da app),
   pintada com a cor de acento do tema ativo via currentColor. */
function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
      <line x1="9" y1="10" x2="9" y2="13" />
      <line x1="12" y1="8.5" x2="12" y2="14.5" />
      <line x1="15" y1="10" x2="15" y2="13" />
    </svg>
  );
}

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

type View = "transcribe" | "library" | "settings";

// ---------------------------------------------------------------------------
// Aparência — tema (galeria) + densidade. Cada tema é um bloco de variáveis
// CSS em App.css sob [data-theme="…"]; adicionar um tema = bloco novo lá + uma
// entrada aqui. A escolha persiste em localStorage.
// ---------------------------------------------------------------------------
const THEMES: { id: string; label: string }[] = [
  { id: "light", label: "Upex Claro" },
  { id: "github-light", label: "GitHub Light" },
  { id: "dark", label: "Upex Escuro" },
  { id: "github-dark", label: "GitHub Dark" },
  { id: "one-dark", label: "One Dark" },
  { id: "tokyo-night", label: "Tokyo Night" },
  { id: "catppuccin", label: "Catppuccin Mocha" },
  { id: "rose-pine", label: "Rosé Pine" },
  { id: "monokai-pro", label: "Monokai Pro" },
  { id: "nord", label: "Nord" },
  { id: "grafite", label: "Grafite" },
  { id: "oled", label: "Preto OLED" },
];

type Density = "comfortable" | "compact";

function useAppearance() {
  const [theme, setTheme] = useState<string>(() => {
    const saved = localStorage.getItem("upexnote-theme");
    if (saved && THEMES.some((t) => t.id === saved)) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  // Compacto é o default (preferência do utilizador, 2026-07-15); Confortável é opt-in
  const [density, setDensity] = useState<Density>(
    () => (localStorage.getItem("upexnote-density") === "comfortable" ? "comfortable" : "compact")
  );
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("upexnote-theme", theme);
  }, [theme]);
  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
    localStorage.setItem("upexnote-density", density);
  }, [density]);
  return { theme, setTheme, density, setDensity };
}

type Appearance = ReturnType<typeof useAppearance>;

function AppearanceCard({ theme, setTheme, density, setDensity }: Appearance) {
  return (
    <section className="card">
      <h2>Aparência</h2>
      <div className="field">
        <label>Tema</label>
        <div className="theme-grid">
          {THEMES.map((t) => (
            <button
              key={t.id}
              data-theme={t.id}
              className={"theme-card" + (theme === t.id ? " selected" : "")}
              onClick={() => setTheme(t.id)}
            >
              <span className="tc-preview">
                <span className="tc-side" />
                <span className="tc-body">
                  <span className="tc-line accent" />
                  <span className="tc-line" />
                  <span className="tc-line dim" />
                </span>
              </span>
              <span className="tc-name">
                {theme === t.id && <span className="tc-check">✓</span>}
                {t.label}
              </span>
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label>Densidade</label>
        <div className="seg">
          <button className={density === "comfortable" ? "on" : ""} onClick={() => setDensity("comfortable")}>
            Confortável
          </button>
          <button className={density === "compact" ? "on" : ""} onClick={() => setDensity("compact")}>
            Compacto
          </button>
        </div>
        <div className="engine-info">
          Compacto reduz tamanhos de letra e espaçamentos — mais conteúdo no ecrã. O zoom (Ctrl + scroll)
          continua disponível por cima de qualquer densidade.
        </div>
      </div>
    </section>
  );
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

// ---------------------------------------------------------------------------
// Biblioteca — histórico e dashboards a partir da tabela `transcriptions`
// ---------------------------------------------------------------------------
type LibItem = {
  id: number;
  created_at: string | null;
  engine: string;
  source_filename: string | null;
  language: string | null;
  duration_s: number | null;
  cost_usd: number | null;
  processing_s: number | null;
  validation_ok: boolean | null;
  warnings_ack: boolean | null;
  clean_path: string | null;
};
type LibEngine = { engine: string; count: number; cost: number; duration: number; proc_avg: number };
type LibSummary = {
  total: number;
  cost_total: number;
  duration_total: number;
  proc_avg: number;
  first_at: string | null;
  last_at: string | null;
  by_engine: LibEngine[];
};
type LibDetail = LibItem & { source_path: string | null; problems: string[]; clean_text: string; edited_at: string | null };

const ENGINE_LABELS: Record<string, string> = {
  assemblyai: "AssemblyAI",
  whisper_openai: "whisper-1",
  deepgram: "Deepgram",
  gpt4o_openai: "gpt-4o",
};
const engLabel = (id: string) => ENGINE_LABELS[id] || id;

function fmtCost(v: number | null): string {
  if (v == null) return "—";
  return "$" + v.toFixed(v < 1 ? 4 : 2);
}
function fmtDur(sec: number | null): string {
  if (sec == null) return "—";
  const m = Math.round(sec / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}min`;
}
function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// Cache local da Biblioteca (lista + resumo, SEM textos) para a app abrir já
// com os últimos dados em vez de "resetar" a cada arranque — padrão
// stale-while-revalidate: mostra o guardado, atualiza em fundo pelo túnel.
const LIB_CACHE_KEY = "upexnote-lib-cache";
type LibCache = { ts: string; summary: LibSummary; items: LibItem[] };

function readLibCache(): LibCache | null {
  try {
    const raw = localStorage.getItem(LIB_CACHE_KEY);
    if (!raw) return null;
    const c = JSON.parse(raw) as LibCache;
    return c && c.summary ? c : null;
  } catch {
    return null;
  }
}

function LibraryView({ active }: { active: boolean }) {
  const [summary, setSummary] = useState<LibSummary | null>(null);
  const [items, setItems] = useState<LibItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<LibDetail | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);
  const [actionMsg, setActionMsg] = useState("");
  const [confirmDel, setConfirmDel] = useState(false);
  const [showWarnings, setShowWarnings] = useState(false);
  const [ackBusy, setAckBusy] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);
  // Quando != null, o que está no ecrã veio da cache local (desta data);
  // limpa-se assim que uma atualização fresca chega do túnel.
  const [cacheTs, setCacheTs] = useState<string | null>(null);
  const editRef = useRef<HTMLTextAreaElement>(null);

  async function load(searchTerm?: string) {
    setLoading(true);
    setError("");
    try {
      const raw = await invoke<string>("library", { search: searchTerm ?? null });
      const obj = JSON.parse(raw);
      if (obj.type === "error") {
        setError(obj.message);
        // Com cache no ecrã, um refresh falhado não apaga o que o utilizador vê
        if (!cacheTs) {
          setSummary(null);
          setItems([]);
        }
      } else {
        setSummary(obj.summary);
        setItems(obj.items || []);
        setCacheTs(null);
        // Só a lista completa vai para a cache (não resultados de pesquisa)
        if (!searchTerm) {
          try {
            localStorage.setItem(
              LIB_CACHE_KEY,
              JSON.stringify({ ts: new Date().toISOString(), summary: obj.summary, items: obj.items || [] })
            );
          } catch { /* cache é best-effort */ }
        }
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    // Só carrega quando a aba é aberta pela primeira vez — não no arranque
    // da app (o primeiro invoke abre um túnel SSH pesado; em paralelo com a
    // inicialização da janela deixava-a sem resposta). Se houver cache da
    // última sessão, mostra-a IMEDIATAMENTE e o load() vira refresh em fundo.
    if (active && !loadedOnce) {
      setLoadedOnce(true);
      const cached = readLibCache();
      if (cached) {
        setSummary(cached.summary);
        setItems(cached.items);
        setCacheTs(cached.ts);
      }
      load();
    }
  }, [active, loadedOnce]);

  function closeDetail() {
    setDetail(null);
    setEditing(false);
    setConfirmDel(false);
    setShowWarnings(false);
    setActionMsg("");
  }

  async function openItem(id: number) {
    setOpeningId(id);
    setActionMsg("");
    try {
      const raw = await invoke<string>("library_item", { id });
      const obj = JSON.parse(raw);
      if (obj.type === "library_item") {
        setDetail(obj.item);
        setEditing(false);
        setConfirmDel(false);
        setShowWarnings(false);
        setEditText(obj.item.clean_text);
      } else {
        setError(obj.message || "Falha a abrir a transcrição.");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setOpeningId(null);
    }
  }

  async function saveEdit() {
    if (!detail) return;
    setSaving(true);
    setActionMsg("");
    try {
      const raw = await invoke<string>("library_update", { id: detail.id, text: editText });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        setDetail({ ...detail, clean_text: editText, edited_at: new Date().toISOString() });
        setEditing(false);
        setActionMsg("Guardado ✓" + (obj.file_updated ? " (ficheiro também atualizado)" : ""));
        load(search.trim() || undefined);
      } else {
        setActionMsg("Erro: " + (obj.message || "falha ao guardar"));
      }
    } catch (e) {
      setActionMsg("Erro: " + String(e));
    } finally {
      setSaving(false);
    }
  }

  async function deleteItem() {
    if (!detail) return;
    setSaving(true);
    setActionMsg("");
    try {
      const raw = await invoke<string>("library_delete", { id: detail.id });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        closeDetail();
        load(search.trim() || undefined);
      } else {
        setActionMsg("Erro: " + (obj.message || "falha ao apagar"));
        setConfirmDel(false);
      }
    } catch (e) {
      setActionMsg("Erro: " + String(e));
      setConfirmDel(false);
    } finally {
      setSaving(false);
    }
  }

  async function toggleAck() {
    if (!detail) return;
    setAckBusy(true);
    try {
      const reopen = !!detail.warnings_ack;
      const raw = await invoke<string>("library_ack", { id: detail.id, reopen });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        setDetail({ ...detail, warnings_ack: !reopen });
        load(search.trim() || undefined);
      } else {
        setActionMsg("Erro: " + (obj.message || "falha"));
      }
    } catch (e) {
      setActionMsg("Erro: " + String(e));
    } finally {
      setAckBusy(false);
    }
  }

  // Colar intercetado (a WebView2 desta máquina crasha no colar nativo).
  function onEditPaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    e.preventDefault();
    const text = e.clipboardData.getData("text");
    const el = e.currentTarget;
    const start = el.selectionStart ?? editText.length;
    const end = el.selectionEnd ?? editText.length;
    const next = editText.slice(0, start) + text + editText.slice(end);
    setEditText(next);
    const pos = start + text.length;
    requestAnimationFrame(() => {
      if (editRef.current) editRef.current.selectionStart = editRef.current.selectionEnd = pos;
    });
  }

  // Vista de detalhe (uma transcrição, com texto)
  if (detail) {
    return (
      <section className="card">
        <div className="detail-head">
          <button className="secondary" onClick={closeDetail} disabled={saving}>← Voltar</button>
          <h2 style={{ margin: 0, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {detail.source_filename || `Transcrição #${detail.id}`}
          </h2>
          {!editing && (
            <>
              <button className="secondary" onClick={() => { setEditText(detail.clean_text); setEditing(true); setActionMsg(""); }}>Editar</button>
              <button className="secondary" onClick={() => navigator.clipboard.writeText(detail.clean_text)}>Copiar</button>
              {!confirmDel ? (
                <button className="secondary btn-danger" onClick={() => setConfirmDel(true)} disabled={saving}>Apagar</button>
              ) : (
                <>
                  <span className="muted" style={{ color: "var(--danger)" }}>Apagar mesmo?</span>
                  <button className="btn-danger-solid" onClick={deleteItem} disabled={saving}>{saving ? "A apagar…" : "Sim, apagar"}</button>
                  <button className="secondary" onClick={() => setConfirmDel(false)} disabled={saving}>Não</button>
                </>
              )}
            </>
          )}
          {editing && (
            <>
              <button onClick={saveEdit} disabled={saving}>{saving ? "A guardar…" : "Guardar"}</button>
              <button className="secondary" onClick={() => { setEditing(false); setActionMsg(""); }} disabled={saving}>Cancelar</button>
            </>
          )}
        </div>
        <div className="result-head">
          <span
            className="badge badge-id"
            title="Clica para copiar o id (útil para filtrar no DBeaver: WHERE id = …)"
            onClick={() => navigator.clipboard.writeText(String(detail.id))}
          >
            #{detail.id}
          </span>
          <span className="badge">{engLabel(detail.engine)}</span>
          {detail.validation_ok ? (
            <span className="badge ok">✓ Validação OK</span>
          ) : (
            <span
              className={"badge warn-badge" + (detail.warnings_ack ? " ack" : "")}
              onClick={() => setShowWarnings((s) => !s)}
              title="Clica para ver o(s) aviso(s)"
            >
              {detail.warnings_ack ? "✓ Aviso revisto" : "⚠ Com avisos"}
            </span>
          )}
          {detail.edited_at && <span className="badge">editado</span>}
          {detail.language && <span className="badge">idioma: {detail.language}</span>}
          <span className="badge">{fmtCost(detail.cost_usd)}</span>
          <span className="badge">{fmtDur(detail.duration_s)}</span>
          <span className="badge">{fmtDate(detail.created_at)}</span>
        </div>
        {!detail.validation_ok && showWarnings && (
          <div className="warnings-panel">
            {detail.problems && detail.problems.length > 0 ? (
              <ul>
                {detail.problems.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            ) : (
              <div className="muted">Sem detalhe guardado para este aviso.</div>
            )}
            <div className="row wrap" style={{ marginTop: 10 }}>
              {!editing && (
                <button
                  className="secondary"
                  onClick={() => { setEditText(detail.clean_text); setEditing(true); setActionMsg(""); }}
                >
                  Corrigir texto
                </button>
              )}
              <button className="secondary" onClick={toggleAck} disabled={ackBusy}>
                {ackBusy ? "…" : detail.warnings_ack ? "Reabrir aviso" : "Marcar como revisto"}
              </button>
            </div>
          </div>
        )}
        {editing ? (
          <textarea
            ref={editRef}
            className="transcript edit-area"
            value={editText}
            onChange={(e) => setEditText(e.currentTarget.value)}
            onPaste={onEditPaste}
            spellCheck={false}
          />
        ) : (
          <pre className="transcript">{detail.clean_text}</pre>
        )}
        {actionMsg && <div className="muted" style={{ marginTop: 8 }}>{actionMsg}</div>}
        <div className="muted" style={{ marginTop: 8 }}>
          {editing
            ? "A editar a versão de leitura (clean). O texto bruto (raw) fica sempre intacto; a versão anterior vai para o histórico ao guardar."
            : detail.clean_path ? "Ficheiro: " + detail.clean_path : ""}
        </div>
      </section>
    );
  }

  return (
    <div className="lib-pane">
      {/* Primeira carga: o túnel SSH demora uns segundos — sem isto o ecrã
          fica mudo e parece travado. O overlay conduz o utilizador. */}
      {loading && !summary && (
        <div className="load-overlay">
          <span className="spinner big" />
          <div className="load-title">A carregar a Biblioteca…</div>
          <div className="muted">
            A primeira ligação abre um túnel seguro até à tua base de dados — pode demorar alguns segundos.
          </div>
        </div>
      )}
      <section className="card">
        <div className="result-head">
          <h2 style={{ margin: 0, flex: 1 }}>Biblioteca</h2>
          {cacheTs && (
            <span className="badge" title="A mostrar a última sessão guardada nesta máquina enquanto a versão atual chega da base de dados">
              {loading ? <><span className="spinner" /> dados de {fmtDate(cacheTs)} · a atualizar…</> : <>dados de {fmtDate(cacheTs)}</>}
            </span>
          )}
          <button className="secondary" onClick={() => load(search.trim() || undefined)} disabled={loading}>
            {loading ? "A carregar…" : "Atualizar"}
          </button>
        </div>

        {error && (
          <div className="key-warn">
            {error.includes("db_config") || error.includes("Password")
              ? "A base de dados não está configurada — abre Definições para ligar ao Postgres."
              : "Não consegui ler a Biblioteca: " + error}
          </div>
        )}

        {summary && (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-val">{summary.total}</div>
                <div className="stat-lbl">transcrições</div>
              </div>
              <div className="stat">
                <div className="stat-val">{fmtCost(summary.cost_total)}</div>
                <div className="stat-lbl">custo total</div>
              </div>
              <div className="stat">
                <div className="stat-val">{fmtDur(summary.duration_total)}</div>
                <div className="stat-lbl">áudio processado</div>
              </div>
              <div className="stat">
                <div className="stat-val">{Math.round(summary.proc_avg)}s</div>
                <div className="stat-lbl">tempo médio</div>
              </div>
            </div>

            {summary.by_engine.length > 0 && (
              <div className="table-scroll" style={{ marginTop: 16 }}>
                <table className="eng-table">
                  <thead>
                    <tr>
                      <th>Motor</th>
                      <th>Transcrições</th>
                      <th>Custo</th>
                      <th>Áudio</th>
                      <th>Tempo médio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_engine.map((e) => (
                      <tr key={e.engine}>
                        <td>{engLabel(e.engine)}</td>
                        <td>{e.count}</td>
                        <td>{fmtCost(e.cost)}</td>
                        <td>{fmtDur(e.duration)}</td>
                        <td>{Math.round(e.proc_avg)}s</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      <section className="card">
        <div className="lib-toolbar">
          <div className="input-icon">
            <Search size={14} strokeWidth={2} />
            <input
              type="text"
              placeholder="Pesquisar por nome do ficheiro…"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              onKeyDown={(e) => { if (e.key === "Enter") load(search.trim() || undefined); }}
            />
          </div>
          <button className="secondary" onClick={() => load(search.trim() || undefined)} disabled={loading}>Pesquisar</button>
          {search && (
            <button className="secondary" onClick={() => { setSearch(""); load(); }} disabled={loading}>Limpar</button>
          )}
        </div>

        {loadedOnce && !loading && !error && items.length === 0 && (
          <div className="lib-empty">
            {search ? "Nenhuma transcrição corresponde à pesquisa." : "Ainda não há transcrições no histórico."}
          </div>
        )}

        <div className="lib-list">
          {items.map((it) => (
            <button key={it.id} className="lib-row" onClick={() => openItem(it.id)}>
              <span
                className={"lib-dot " + (it.validation_ok ? "ok" : it.warnings_ack ? "ack" : "warn")}
                title={it.validation_ok ? "Validação OK" : it.warnings_ack ? "Aviso revisto" : "Com avisos"}
              />
              <span className="lib-main">
                <div className="lib-name">{it.source_filename || `Transcrição #${it.id}`}</div>
                <div className="lib-sub">#{it.id} · {engLabel(it.engine)} · {fmtDate(it.created_at)}{it.language ? " · " + it.language : ""}</div>
              </span>
              <span className="lib-meta">
                {openingId === it.id ? (
                  <span className="spinner" />
                ) : (
                  <>
                    <span className="badge">{fmtDur(it.duration_s)}</span>
                    <span className="badge">{fmtCost(it.cost_usd)}</span>
                  </>
                )}
              </span>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

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
// Barra de título custom — a janela é criada sem decoração nativa
// (decorations:false), por isso a tarja do Windows desaparece e esta barra,
// pintada com as cores do tema, assume arrastar/min/max/fechar.
// ---------------------------------------------------------------------------
function Titlebar({
  canBack, canFwd, onBack, onFwd,
}: { canBack: boolean; canFwd: boolean; onBack: () => void; onFwd: () => void }) {
  const win = getCurrentWindow();
  return (
    <div className="titlebar" data-tauri-drag-region>
      <div className="tb-nav">
        <button className="tb-btn" onClick={onBack} disabled={!canBack} title="Voltar">
          <ArrowLeft size={15} />
        </button>
        <button className="tb-btn" onClick={onFwd} disabled={!canFwd} title="Avançar">
          <ArrowRight size={15} />
        </button>
      </div>
      <div className="tb-title" data-tauri-drag-region>UpexNote</div>
      <div className="tb-controls">
        <button className="tb-btn tb-win" onClick={() => win.minimize()} title="Minimizar">
          <Minus size={15} />
        </button>
        <button className="tb-btn tb-win" onClick={() => win.toggleMaximize()} title="Maximizar / Restaurar">
          <Square size={12} />
        </button>
        <button className="tb-btn tb-win tb-close" onClick={() => win.close()} title="Fechar">
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App — layout com menu lateral + roteamento de vistas
// ---------------------------------------------------------------------------
function App() {
  const appearance = useAppearance();
  const [view, setView] = useState<View>("transcribe");
  // Histórico de vistas para as setas voltar/avançar da barra de título
  const [histBack, setHistBack] = useState<View[]>([]);
  const [histFwd, setHistFwd] = useState<View[]>([]);
  function navTo(v: View) {
    if (v === view) return;
    setHistBack((h) => [...h, view]);
    setHistFwd([]);
    setView(v);
  }
  function goBack() {
    if (!histBack.length) return;
    const prev = histBack[histBack.length - 1];
    setHistBack((h) => h.slice(0, -1));
    setHistFwd((f) => [view, ...f]);
    setView(prev);
  }
  function goFwd() {
    if (!histFwd.length) return;
    const next = histFwd[0];
    setHistFwd((f) => f.slice(1));
    setHistBack((h) => [...h, view]);
    setView(next);
  }
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

  const navItems: { id: View; icon: ReactNode; label: string }[] = [
    { id: "transcribe", icon: <Mic size={16} strokeWidth={1.75} />, label: "Transcrever" },
    { id: "library", icon: <LibraryBig size={16} strokeWidth={1.75} />, label: "Biblioteca" },
    { id: "settings", icon: <Settings size={16} strokeWidth={1.75} />, label: "Definições" },
  ];

  return (
    <div className="shell">
      <Titlebar canBack={histBack.length > 0} canFwd={histFwd.length > 0} onBack={goBack} onFwd={goFwd} />
      <div className="layout">
      <aside className={"sidebar" + (collapsed ? " collapsed" : "")}>
        <div className="sidebar-brand">
          {collapsed ? (
            <span className="brand-mark"><BrandMark /></span>
          ) : (
            <div className="brand-row">
              <span className="brand-mark"><BrandMark /></span>
              <div>
                <div className="wordmark"><span className="up">Upex</span><span className="ex">Note</span></div>
                <div className="tagline">Transcreva, organize e explore.</div>
              </div>
            </div>
          )}
        </div>

        <nav className="nav">
          {navItems.map((it) => (
            <button
              key={it.id}
              className={"nav-item" + (view === it.id ? " active" : "")}
              onClick={() => navTo(it.id)}
              title={it.label}
            >
              <span className="nav-ico">{it.icon}</span>
              {!collapsed && <span>{it.label}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button className="nav-item" onClick={() => navTo("settings")} title="Aparência (tema e densidade)">
            <span className="nav-ico"><Palette size={16} strokeWidth={1.75} /></span>
            {!collapsed && <span>Aparência</span>}
          </button>
          <button className="nav-item" onClick={() => setCollapsed((c) => !c)} title={collapsed ? "Expandir menu" : "Recolher menu"}>
            <span className="nav-ico">
              {collapsed ? <PanelLeftOpen size={16} strokeWidth={1.75} /> : <PanelLeftClose size={16} strokeWidth={1.75} />}
            </span>
            {!collapsed && <span>Recolher</span>}
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="body">
          {/* As três vistas ficam sempre montadas (só escondidas via CSS) para
              não perderem o estado ao trocar de aba — antes, o React destruía
              e recriava cada vista do zero, obrigando a Biblioteca a recarregar
              tudo pelo túnel SSH sempre que voltavas a ela. */}
          <div className={"view-pane" + (view === "transcribe" ? "" : " hidden")}>
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
          </div>

          <div className={"view-pane" + (view === "library" ? "" : " hidden")}>
            <LibraryView active={view === "library"} />
          </div>

          <div className={"view-pane" + (view === "settings" ? "" : " hidden")}>
            <AppearanceCard {...appearance} />
            <SettingsView onChanged={loadEngines} />
            <StorageSettingsCard />
          </div>
        </div>
      </main>
      </div>
    </div>
  );
}

export default App;
