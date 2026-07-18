import { createContext, useContext, useEffect, useMemo, useRef, useState, type ClipboardEvent, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { getVersion } from "@tauri-apps/api/app";
import {
  Mic, LibraryBig, Settings, Palette, PanelLeftClose, PanelLeftOpen,
  Search, ArrowLeft, ArrowRight, Minus, Square, X,
} from "lucide-react";
import { LANGS, LOCALES, makeT, type Key as I18nKey, type Lang, type TFn } from "./i18n";
import FONTS from "./fonts.json";
import "./App.css";

// ---------------------------------------------------------------------------
// Idioma da UI (item 8) — só o chrome; transcripts e mensagens do worker
// ficam na língua original. Dicionários em i18n.ts; escolha em localStorage.
// ---------------------------------------------------------------------------
type LangCtxValue = { lang: Lang; setLang: (l: Lang) => void; t: TFn; locale: string };
const LangCtx = createContext<LangCtxValue>({ lang: "pt", setLang: () => {}, t: makeT("pt"), locale: LOCALES.pt });
const useLang = () => useContext(LangCtx);

function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem("upexnote-lang");
    return saved === "en" || saved === "es" || saved === "pt" ? saved : "pt";
  });
  useEffect(() => {
    localStorage.setItem("upexnote-lang", lang);
    document.documentElement.setAttribute("lang", LOCALES[lang]);
  }, [lang]);
  const value = useMemo<LangCtxValue>(() => ({ lang, setLang, t: makeT(lang), locale: LOCALES[lang] }), [lang]);
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}

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
const THEMES: { id: string; label?: string; labelKey?: I18nKey }[] = [
  { id: "light", labelKey: "themeUpexLight" },
  { id: "github-light", label: "GitHub Light" },
  { id: "dark", labelKey: "themeUpexDark" },
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

// ---------------------------------------------------------------------------
// Tipografia (item 7) — fonte (empacotadas de fonts.json + instaladas na
// máquina via Rust), tamanho (escala %), peso base e sombra de texto.
// Aplicado por variáveis CSS no <html>; persistido em localStorage.
// ---------------------------------------------------------------------------
type FontPrefs = { id: string; family: string; scale: number; weight: number; shadow: boolean };

const FONT_DEFAULT: FontPrefs = {
  id: FONTS[0].id,
  family: FONTS[0].family,
  scale: 1,
  weight: 400,
  shadow: false,
};

function useFontPrefs() {
  const [prefs, setPrefs] = useState<FontPrefs>(() => {
    try {
      const raw = localStorage.getItem("upexnote-font");
      if (raw) return { ...FONT_DEFAULT, ...JSON.parse(raw) };
    } catch { /* prefs corrompidas → default */ }
    return FONT_DEFAULT;
  });
  useEffect(() => {
    const st = document.documentElement.style;
    st.setProperty("--font-sans", prefs.family);
    st.setProperty("--font-scale", String(prefs.scale));
    st.setProperty("--fw-base", String(prefs.weight));
    st.setProperty("--text-shadow", prefs.shadow ? "0 1px 2px rgba(0, 0, 0, 0.35)" : "none");
    localStorage.setItem("upexnote-font", JSON.stringify(prefs));
  }, [prefs]);
  return { prefs, setPrefs };
}

function TypographyCard({ prefs, setPrefs }: { prefs: FontPrefs; setPrefs: (p: FontPrefs) => void }) {
  const { t } = useLang();
  const [sysFonts, setSysFonts] = useState<string[]>([]);
  useEffect(() => {
    invoke<string[]>("list_system_fonts").then(setSysFonts).catch(() => { /* opcional */ });
  }, []);

  function selectFont(value: string) {
    if (value.startsWith("sys:")) {
      const name = value.slice(4);
      setPrefs({ ...prefs, id: value, family: `'${name}', 'Segoe UI', sans-serif` });
    } else {
      const f = FONTS.find((f) => f.id === value);
      if (f) setPrefs({ ...prefs, id: f.id, family: f.family });
    }
  }

  return (
    <section className="card">
      <h2>{t("typTitle")}</h2>
      <div className="field">
        <label>{t("typFont")}</label>
        <select value={prefs.id} onChange={(e) => selectFont(e.currentTarget.value)}>
          <optgroup label={t("typBundled")}>
            {FONTS.map((f) => (
              <option key={f.id} value={f.id}>{f.label}{f.note ? ` — ${f.note}` : ""}</option>
            ))}
          </optgroup>
          {sysFonts.length > 0 && (
            <optgroup label={t("typSystem")}>
              {sysFonts.map((n) => (
                <option key={n} value={"sys:" + n}>{n}</option>
              ))}
            </optgroup>
          )}
        </select>
        <div className="type-preview" style={{ fontFamily: prefs.family, fontWeight: prefs.weight }}>
          {t("typPreview")}
        </div>
      </div>
      <div className="row wrap" style={{ alignItems: "flex-end" }}>
        <div className="field" style={{ flex: 1, minWidth: 170, marginBottom: 0 }}>
          <label>{t("typSize")} — {Math.round(prefs.scale * 100)}%</label>
          <input
            type="range" min={90} max={115} step={1}
            value={Math.round(prefs.scale * 100)}
            onChange={(e) => setPrefs({ ...prefs, scale: Number(e.currentTarget.value) / 100 })}
          />
        </div>
        <div className="field" style={{ flex: 1, minWidth: 170, marginBottom: 0 }}>
          <label>{t("typWeight")} — {prefs.weight}</label>
          <input
            type="range" min={300} max={600} step={25}
            value={prefs.weight}
            onChange={(e) => setPrefs({ ...prefs, weight: Number(e.currentTarget.value) })}
          />
        </div>
      </div>
      <div className="field" style={{ marginTop: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={prefs.shadow}
            onChange={(e) => setPrefs({ ...prefs, shadow: e.currentTarget.checked })}
            style={{ width: "auto" }}
          />
          <span>{t("typShadow")}</span>
        </label>
      </div>
      <button className="secondary" onClick={() => setPrefs(FONT_DEFAULT)}>{t("typReset")}</button>
    </section>
  );
}

function AppearanceCard({ theme, setTheme, density, setDensity }: Appearance) {
  const { lang, setLang, t } = useLang();
  return (
    <section className="card">
      <h2>{t("appTitle")}</h2>
      <div className="field">
        <label>{t("appTheme")}</label>
        <div className="theme-grid">
          {THEMES.map((th) => (
            <button
              key={th.id}
              data-theme={th.id}
              className={"theme-card" + (theme === th.id ? " selected" : "")}
              onClick={() => setTheme(th.id)}
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
                {theme === th.id && <span className="tc-check">✓</span>}
                {th.label ?? t(th.labelKey!)}
              </span>
            </button>
          ))}
        </div>
      </div>
      <div className="field">
        <label>{t("appDensity")}</label>
        <div className="seg">
          <button className={density === "comfortable" ? "on" : ""} onClick={() => setDensity("comfortable")}>
            {t("appComfortable")}
          </button>
          <button className={density === "compact" ? "on" : ""} onClick={() => setDensity("compact")}>
            {t("appCompact")}
          </button>
        </div>
        <div className="engine-info">{t("appDensityInfo")}</div>
      </div>
      <div className="field">
        <label>{t("appLang")}</label>
        <div className="seg">
          {LANGS.map((l) => (
            <button key={l.id} className={lang === l.id ? "on" : ""} onClick={() => setLang(l.id)}>
              {l.label}
            </button>
          ))}
        </div>
        <div className="engine-info">{t("appLangInfo")}</div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Ecrã de Definições — gerir chaves/credenciais (guardadas no Credential Manager)
// ---------------------------------------------------------------------------
const CREDENTIALS: { name: string; label?: string; labelKey?: I18nKey; hintKey: I18nKey }[] = [
  { name: "ASSEMBLYAI_API_KEY", label: "AssemblyAI API Key", hintKey: "hintAssembly" },
  { name: "OPENAI_API_KEY", label: "OpenAI API Key", hintKey: "hintOpenai" },
  { name: "DEEPGRAM_API_KEY", label: "Deepgram API Key", hintKey: "hintDeepgram" },
  { name: "UPEXNOTE_PG_PASSWORD", labelKey: "credPgLabel", hintKey: "hintPg" },
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

// label/info dos motores vêm do worker em PT — sobrepomos com traduções por
// id; motor desconhecido cai no texto original do worker (fallback seguro)
const ENGINE_I18N: Record<string, { label: I18nKey; info: I18nKey }> = {
  assemblyai: { label: "engLabelAssembly", info: "engInfoAssembly" },
  whisper_openai: { label: "engLabelWhisper", info: "engInfoWhisper" },
  deepgram: { label: "engLabelDeepgram", info: "engInfoDeepgram" },
  gpt4o_openai: { label: "engLabelGpt4o", info: "engInfoGpt4o" },
};

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
function fmtDate(iso: string | null, locale?: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(locale, {
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
  const { t, locale } = useLang();
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
        setError(obj.message || t("libOpenFail"));
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
        setActionMsg(t("savedTick") + (obj.file_updated ? t("fileAlsoUpdated") : ""));
        load(search.trim() || undefined);
      } else {
        setActionMsg(t("errPrefix") + (obj.message || t("errSaveFail")));
      }
    } catch (e) {
      setActionMsg(t("errPrefix") + String(e));
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
        setActionMsg(t("errPrefix") + (obj.message || t("errDeleteFail")));
        setConfirmDel(false);
      }
    } catch (e) {
      setActionMsg(t("errPrefix") + String(e));
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
        setActionMsg(t("errPrefix") + (obj.message || t("errFail")));
      }
    } catch (e) {
      setActionMsg(t("errPrefix") + String(e));
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
          <button className="secondary" onClick={closeDetail} disabled={saving}>{t("back")}</button>
          <h2 style={{ margin: 0, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {detail.source_filename || t("libItemN", { id: detail.id })}
          </h2>
          {!editing && (
            <>
              <button className="secondary" onClick={() => { setEditText(detail.clean_text); setEditing(true); setActionMsg(""); }}>{t("edit")}</button>
              <button className="secondary" onClick={() => navigator.clipboard.writeText(detail.clean_text)}>{t("copy")}</button>
              {!confirmDel ? (
                <button className="secondary btn-danger" onClick={() => setConfirmDel(true)} disabled={saving}>{t("del")}</button>
              ) : (
                <>
                  <span className="muted" style={{ color: "var(--danger)" }}>{t("delConfirm")}</span>
                  <button className="btn-danger-solid" onClick={deleteItem} disabled={saving}>{saving ? t("deleting") : t("delYes")}</button>
                  <button className="secondary" onClick={() => setConfirmDel(false)} disabled={saving}>{t("delNo")}</button>
                </>
              )}
            </>
          )}
          {editing && (
            <>
              <button onClick={saveEdit} disabled={saving}>{saving ? t("saving") : t("save")}</button>
              <button className="secondary" onClick={() => { setEditing(false); setActionMsg(""); }} disabled={saving}>{t("cancel")}</button>
            </>
          )}
        </div>
        <div className="result-head">
          <span
            className="badge badge-id"
            title={t("idTooltip")}
            onClick={() => navigator.clipboard.writeText(String(detail.id))}
          >
            #{detail.id}
          </span>
          <span className="badge">{engLabel(detail.engine)}</span>
          {detail.validation_ok ? (
            <span className="badge ok">{t("valOk")}</span>
          ) : (
            <span
              className={"badge warn-badge" + (detail.warnings_ack ? " ack" : "")}
              onClick={() => setShowWarnings((s) => !s)}
              title={t("warnClickTitle")}
            >
              {detail.warnings_ack ? t("warnReviewed") : t("valWarn")}
            </span>
          )}
          {detail.edited_at && <span className="badge">{t("badgeEdited")}</span>}
          {detail.language && <span className="badge">{t("langBadge", { lang: detail.language })}</span>}
          <span className="badge">{fmtCost(detail.cost_usd)}</span>
          <span className="badge">{fmtDur(detail.duration_s)}</span>
          <span className="badge">{fmtDate(detail.created_at, locale)}</span>
        </div>
        {!detail.validation_ok && showWarnings && (
          <div className="warnings-panel">
            {detail.problems && detail.problems.length > 0 ? (
              <ul>
                {detail.problems.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            ) : (
              <div className="muted">{t("warnEmpty")}</div>
            )}
            <div className="row wrap" style={{ marginTop: 10 }}>
              {!editing && (
                <button
                  className="secondary"
                  onClick={() => { setEditText(detail.clean_text); setEditing(true); setActionMsg(""); }}
                >
                  {t("fixText")}
                </button>
              )}
              <button className="secondary" onClick={toggleAck} disabled={ackBusy}>
                {ackBusy ? "…" : detail.warnings_ack ? t("ackReopen") : t("ackMark")}
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
            ? t("editingHint")
            : detail.clean_path ? t("filePrefix", { path: detail.clean_path }) : ""}
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
          <div className="load-title">{t("libLoadTitle")}</div>
          <div className="muted">{t("libLoadHint")}</div>
        </div>
      )}
      <section className="card">
        <div className="result-head">
          <h2 style={{ margin: 0, flex: 1 }}>{t("libTitle")}</h2>
          {cacheTs && (
            <span className="badge" title={t("libCacheTitle")}>
              {loading ? (
                <><span className="spinner" /> {t("libCacheUpdating", { ts: fmtDate(cacheTs, locale) })}</>
              ) : (
                <>{t("libCache", { ts: fmtDate(cacheTs, locale) })}</>
              )}
            </span>
          )}
          <button className="secondary" onClick={() => load(search.trim() || undefined)} disabled={loading}>
            {loading ? t("libLoadingBtn") : t("libRefresh")}
          </button>
        </div>

        {error && (
          <div className="key-warn">
            {error.includes("db_config") || error.includes("Password")
              ? t("libDbNotConfigured")
              : t("libReadFail", { err: error })}
          </div>
        )}

        {summary && (
          <>
            <div className="stat-grid">
              <div className="stat">
                <div className="stat-val">{summary.total}</div>
                <div className="stat-lbl">{t("statTranscriptions")}</div>
              </div>
              <div className="stat">
                <div className="stat-val">{fmtCost(summary.cost_total)}</div>
                <div className="stat-lbl">{t("statCost")}</div>
              </div>
              <div className="stat">
                <div className="stat-val">{fmtDur(summary.duration_total)}</div>
                <div className="stat-lbl">{t("statAudio")}</div>
              </div>
              <div className="stat">
                <div className="stat-val">{Math.round(summary.proc_avg)}s</div>
                <div className="stat-lbl">{t("statAvg")}</div>
              </div>
            </div>

            {summary.by_engine.length > 0 && (
              <div className="table-scroll" style={{ marginTop: 16 }}>
                <table className="eng-table">
                  <thead>
                    <tr>
                      <th>{t("thEngine")}</th>
                      <th>{t("thCount")}</th>
                      <th>{t("thCost")}</th>
                      <th>{t("thAudio")}</th>
                      <th>{t("thAvg")}</th>
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
              placeholder={t("libSearchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              onKeyDown={(e) => { if (e.key === "Enter") load(search.trim() || undefined); }}
            />
          </div>
          <button className="secondary" onClick={() => load(search.trim() || undefined)} disabled={loading}>{t("libSearchBtn")}</button>
          {search && (
            <button className="secondary" onClick={() => { setSearch(""); load(); }} disabled={loading}>{t("trClear")}</button>
          )}
        </div>

        {loadedOnce && !loading && !error && items.length === 0 && (
          <div className="lib-empty">
            {search ? t("libEmptySearch") : t("libEmpty")}
          </div>
        )}

        <div className="lib-list">
          {items.map((it) => (
            <button key={it.id} className="lib-row" onClick={() => openItem(it.id)}>
              <span
                className={"lib-dot " + (it.validation_ok ? "ok" : it.warnings_ack ? "ack" : "warn")}
                title={it.validation_ok ? t("valOk") : it.warnings_ack ? t("warnReviewed") : t("valWarn")}
              />
              <span className="lib-main">
                <div className="lib-name">{it.source_filename || t("libItemN", { id: it.id })}</div>
                <div className="lib-sub">#{it.id} · {engLabel(it.engine)} · {fmtDate(it.created_at, locale)}{it.language ? " · " + it.language : ""}</div>
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
  storage_mode?: "local" | "vps";
  vps_configured?: boolean;
};

function StorageSettingsCard() {
  const { t } = useLang();
  const [s, setS] = useState<StorageSettings | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const raw = await invoke<string>("get_settings");
      setS(JSON.parse(raw));
    } catch (e) {
      setMsg(t("stoLoadErr", { err: String(e) }));
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
      setMsg(t("errPrefix") + String(e));
    } finally {
      setBusy(false);
    }
  }

  async function chooseFolder() {
    const picked = await open({
      directory: true,
      multiple: false,
      title: t("dlgFolder"),
    });
    if (typeof picked === "string") {
      await apply({ storageDir: picked }, t("stoFolderUpdated"));
    }
  }

  return (
    <section className="card">
      <h2>{t("stoTitle")}</h2>
      <p className="muted" style={{ marginTop: -6, marginBottom: 16 }}>
        {t("stoIntro")}
      </p>
      <div className="field">
        <label>{t("stoModeLabel")}</label>
        <div className="row wrap">
          <span className={"badge " + (s?.storage_mode === "vps" ? "ok" : "")}>
            {s?.storage_mode === "vps" ? "🔒 " + t("stoModeVps") : t("stoModeLocal")}
          </span>
          <button
            className="secondary"
            onClick={() => {
              // limpa perfil + cache da Biblioteca (pertence ao modo atual)
              localStorage.removeItem("upexnote-profile");
              localStorage.removeItem("upexnote-lib-cache");
              window.location.reload();
            }}
          >
            {t("stoSwitchProfile")}
          </button>
        </div>
      </div>
      <div className="field">
        <label>{t("stoFolderLabel")}</label>
        <div className="row">
          <input type="text" readOnly value={s ? s.storage_dir : "…"} />
          <button className="secondary" onClick={chooseFolder} disabled={busy || !s}>{t("trChoose")}</button>
          {s?.storage_dir_custom && (
            <button
              className="secondary"
              onClick={() => apply({ clearStorageDir: true }, t("stoResetMsg"))}
              disabled={busy}
            >
              {t("stoReset")}
            </button>
          )}
        </div>
        {s && !s.storage_dir_custom && (
          <div className="engine-info">{t("stoFactory", { path: s.default_storage_dir })}</div>
        )}
      </div>
      <div className="field">
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={s ? s.organize_by_day_engine : true}
            disabled={busy || !s}
            onChange={(e) => apply({ organize: e.currentTarget.checked }, t("stoOrgUpdated"))}
            style={{ width: "auto" }}
          />
          <span>{t("stoOrganize")}</span>
        </label>
        <div className="engine-info">
          {t("stoOrganizeInfo")}
          {msg ? " — " + msg : ""}
        </div>
      </div>
    </section>
  );
}

function SettingsView({ onChanged }: { onChanged: () => void }) {
  const { t } = useLang();
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
      setMsg((m) => ({ ...m, [name]: t("credWriteFirst") }));
      return;
    }
    setBusy((b) => ({ ...b, [name]: true }));
    try {
      await invoke("save_credential", { name, value });
      setInputs((i) => ({ ...i, [name]: "" }));
      setMsg((m) => ({ ...m, [name]: t("savedTick") }));
      await loadStatuses();
      onChanged();
    } catch (e) {
      setMsg((m) => ({ ...m, [name]: t("errPrefix") + String(e) }));
    } finally {
      setBusy((b) => ({ ...b, [name]: false }));
    }
  }

  async function clear(name: string) {
    setBusy((b) => ({ ...b, [name]: true }));
    try {
      await invoke("clear_credential", { name });
      setMsg((m) => ({ ...m, [name]: t("credRemoved") }));
      await loadStatuses();
      onChanged();
    } catch (e) {
      setMsg((m) => ({ ...m, [name]: t("errPrefix") + String(e) }));
    } finally {
      setBusy((b) => ({ ...b, [name]: false }));
    }
  }

  return (
    <section className="card">
      <h2>{t("setTitle")}</h2>
      <p className="muted" style={{ marginTop: -6, marginBottom: 16 }}>
        {t("setIntro")}
      </p>
      {CREDENTIALS.map((c) => (
        <div className="field cred" key={c.name}>
          <div className="cred-head">
            <label style={{ margin: 0 }}>{c.label ?? t(c.labelKey!)}</label>
            <span className={"badge " + (!loaded ? "" : status[c.name] ? "ok" : "warn")}>
              {!loaded ? t("credChecking") : status[c.name] ? t("credConfigured") : t("credNotConfigured")}
            </span>
          </div>
          <div className="row">
            <input
              type="text"
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
              spellCheck={false}
              placeholder={status[c.name] ? t("credPlaceholderSet") : t("credPlaceholderEmpty")}
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
            <button onClick={() => save(c.name)} disabled={busy[c.name]}>{t("save")}</button>
            {status[c.name] && (
              <button className="secondary" onClick={() => clear(c.name)} disabled={busy[c.name]}>{t("credRemove")}</button>
            )}
          </div>
          <div className="engine-info">
            {t(c.hintKey)}
            {msg[c.name] ? " — " + msg[c.name] : ""}
          </div>
        </div>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Ecrã de perfis (item 13, Fase 1): decide o modo de armazenamento de forma
// EXPLÍCITA (preferência do utilizador — nada de deteção silenciosa).
// Utilizador → SQLite local, zero fricção. Administrador → valida uma ligação
// REAL à VPS antes de trocar (os segredos são a autenticação; sem eles a porta
// não abre a ninguém). O assistente de máquina virgem chega na Fase 1b.
// ---------------------------------------------------------------------------
function ProfileGate({ onDone }: { onDone: (profile: string) => void }) {
  const { t } = useLang();
  const [busy, setBusy] = useState<"" | "user" | "admin">("");
  const [err, setErr] = useState("");

  function finish(profile: string) {
    // cache da Biblioteca pertence ao modo anterior — nunca misturar bases
    localStorage.removeItem("upexnote-lib-cache");
    localStorage.setItem("upexnote-profile", profile);
    onDone(profile);
  }

  async function chooseUser() {
    setBusy("user");
    try {
      await invoke("set_settings", { storageMode: "local" });
    } catch { /* settings é best-effort; o worker cai em local por defeito */ }
    finish("user");
  }

  async function chooseAdmin() {
    setBusy("admin");
    setErr("");
    try {
      const raw = await invoke<string>("db_check", { mode: "vps" });
      const obj = JSON.parse(raw);
      if (obj.ok) {
        await invoke("set_settings", { storageMode: "vps" });
        finish("admin");
        return;
      }
      setErr(obj.message || t("pgAdminFail"));
    } catch {
      setErr(t("pgAdminFail"));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="profile-gate">
      <div className="pg-head">
        <span className="brand-mark"><BrandMark size={30} /></span>
        <div className="wordmark" style={{ fontSize: 22 }}>
          <span className="up">Upex</span><span className="ex">Note</span>
        </div>
      </div>
      <h1 className="pg-title">{t("pgTitle")}</h1>
      <div className="pg-cards">
        <button className="pg-card" onClick={chooseUser} disabled={busy !== ""}>
          <span className="pg-ico"><Mic size={22} strokeWidth={1.75} /></span>
          <span className="pg-name">{t("pgUserTitle")}</span>
          <span className="pg-desc">{t("pgUserDesc")}</span>
        </button>
        <button className="pg-card" onClick={chooseAdmin} disabled={busy !== ""}>
          <span className="pg-ico"><Settings size={22} strokeWidth={1.75} /></span>
          <span className="pg-name">{t("pgAdminTitle")}</span>
          <span className="pg-desc">{t("pgAdminDesc")}</span>
          {busy === "admin" && (
            <span className="pg-busy"><span className="spinner" /> {t("pgChecking")}</span>
          )}
        </button>
      </div>
      {err && <div className="key-warn pg-err">{err}</div>}
      <div className="muted">{t("pgHint")}</div>
    </div>
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
  const { t } = useLang();
  const win = getCurrentWindow();
  // Versão lida do próprio binário (tauri.conf.json) — nunca fica dessincronizada
  const [version, setVersion] = useState("");
  useEffect(() => {
    getVersion().then(setVersion).catch(() => {});
  }, []);
  return (
    <div className="titlebar" data-tauri-drag-region>
      <div className="tb-nav">
        <button className="tb-btn" onClick={onBack} disabled={!canBack} title={t("tbBack")}>
          <ArrowLeft size={15} />
        </button>
        <button className="tb-btn" onClick={onFwd} disabled={!canFwd} title={t("tbFwd")}>
          <ArrowRight size={15} />
        </button>
      </div>
      <div className="tb-title" data-tauri-drag-region>UpexNote</div>
      {version && <span className="tb-version" data-tauri-drag-region>v{version}</span>}
      <div className="tb-controls">
        <button className="tb-btn tb-win" onClick={() => win.minimize()} title={t("tbMin")}>
          <Minus size={15} />
        </button>
        <button className="tb-btn tb-win" onClick={() => win.toggleMaximize()} title={t("tbMax")}>
          <Square size={12} />
        </button>
        <button className="tb-btn tb-win tb-close" onClick={() => win.close()} title={t("tbClose")}>
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
  const { t } = useLang();
  const appearance = useAppearance();
  const font = useFontPrefs();
  // Perfil escolhido no primeiro arranque (user/admin) — null = mostrar o gate
  const [profile, setProfile] = useState<string | null>(
    () => localStorage.getItem("upexnote-profile")
  );
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

  const STAGES = [t("stage0"), t("stage1"), t("stage2"), t("stage3"), t("stage4")];

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
        const msg = obj.message || t("trProcessing");
        setStatus(msg);
        const s = stageFor(msg);
        if (s > 0) setStage((cur) => Math.max(cur, s));
      } else if (obj.type === "result") {
        setResult(obj as ResultData);
        setStatus(obj.ok ? t("trDone") : t("trDoneWarn"));
      } else if (obj.type === "error") {
        setStatus(t("errPrefix") + obj.message);
      }
    });
    const unlistenDone = listen("worker://done", () => setRunning(false));
    return () => {
      unlistenEvent.then((f) => f());
      unlistenDone.then((f) => f());
    };
    // re-subscreve quando o idioma muda, para o t do closure não ficar velho
  }, [t]);

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
    setStatus(t("trStarting"));
    try {
      await invoke("transcribe", { engine: selected.id, file, dest: dest.trim() || null });
    } catch (e) {
      setStatus(t("errPrefix") + String(e));
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
      title: t("dlgDest"),
    });
    if (typeof picked === "string") setDest(picked);
  }

  async function chooseFile() {
    const picked = await open({
      multiple: false,
      directory: false,
      title: t("dlgFile"),
      filters: [
        { name: t("filterMedia"), extensions: ["mp4", "mov", "mkv", "webm", "avi", "wav", "mp3", "m4a", "aac", "flac", "ogg"] },
        { name: t("filterAll"), extensions: ["*"] },
      ],
    });
    if (typeof picked === "string") setFile(picked);
  }

  const navItems: { id: View; icon: ReactNode; label: string }[] = [
    { id: "transcribe", icon: <Mic size={16} strokeWidth={1.75} />, label: t("navTranscribe") },
    { id: "library", icon: <LibraryBig size={16} strokeWidth={1.75} />, label: t("navLibrary") },
    { id: "settings", icon: <Settings size={16} strokeWidth={1.75} />, label: t("navSettings") },
  ];

  if (profile === null) {
    return (
      <div className="shell">
        <Titlebar canBack={false} canFwd={false} onBack={() => {}} onFwd={() => {}} />
        <ProfileGate onDone={setProfile} />
      </div>
    );
  }

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
                <div className="tagline">{t("tagline")}</div>
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
          <button className="nav-item" onClick={() => navTo("settings")} title={t("navAppearanceTitle")}>
            <span className="nav-ico"><Palette size={16} strokeWidth={1.75} /></span>
            {!collapsed && <span>{t("navAppearance")}</span>}
          </button>
          <button className="nav-item" onClick={() => setCollapsed((c) => !c)} title={collapsed ? t("navExpandTitle") : t("navCollapseTitle")}>
            <span className="nav-ico">
              {collapsed ? <PanelLeftOpen size={16} strokeWidth={1.75} /> : <PanelLeftClose size={16} strokeWidth={1.75} />}
            </span>
            {!collapsed && <span>{t("navCollapse")}</span>}
          </button>
          {!collapsed && (
            <div className="sidebar-meta" title="UpexNote © UpexFlow">
              © {new Date().getFullYear()} UpexFlow · upexflow.com
            </div>
          )}
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
                <h2>{t("trTitle")}</h2>

                <div className="field">
                  <label>{t("trFileLabel")}</label>
                  <div className="row">
                    <input
                      type="text"
                      value={file}
                      placeholder={t("trFilePlaceholder")}
                      onChange={(e) => setFile(e.currentTarget.value)}
                    />
                    <button className="secondary" onClick={chooseFile} disabled={running}>{t("trChoose")}</button>
                  </div>
                </div>

                <div className="field">
                  <label>{t("trDestLabel")}</label>
                  <div className="row">
                    <input
                      type="text"
                      value={dest}
                      placeholder={t("trDestPlaceholder")}
                      onChange={(e) => setDest(e.currentTarget.value)}
                    />
                    <button className="secondary" onClick={chooseDest} disabled={running}>{t("trChoose")}</button>
                    {dest && (
                      <button className="secondary" onClick={() => setDest("")} disabled={running}>{t("trClear")}</button>
                    )}
                  </div>
                  {dest && (
                    <div className="engine-info">{t("trDestInfo", { dest })}</div>
                  )}
                </div>

                <div className="field">
                  <label>{t("trEngineLabel")}</label>
                  <select value={engineId} onChange={(e) => setEngineId(e.currentTarget.value)}>
                    {engines.map((e) => (
                      <option key={e.id} value={e.id}>
                        {ENGINE_I18N[e.id] ? t(ENGINE_I18N[e.id].label) : e.label}
                      </option>
                    ))}
                  </select>
                  {selected && (
                    <div className="engine-info">
                      {ENGINE_I18N[selected.id] ? t(ENGINE_I18N[selected.id].info) : selected.info}
                    </div>
                  )}
                  {selected && !selected.key_set && (
                    <div className="key-warn">{t("trKeyMissing", { key: selected.key_name })}</div>
                  )}
                  {loadError && <div className="key-warn">{t("trEnginesError", { err: loadError })}</div>}
                </div>

                <div className="row wrap">
                  <button onClick={startTranscription} disabled={!file || running || !selected}>
                    {running ? t("trRunning") : t("trStart")}
                  </button>
                  {!running && (result || status) && (
                    <button className="secondary" onClick={reset}>{t("trNew")}</button>
                  )}
                  {running && (
                    <div className="status">
                      <span className="spinner" />
                      <span>{STAGES[stage] || status}</span>
                      <span className="elapsed">{t("trElapsed", { t: fmtElapsed(elapsed) })}</span>
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
                          {n === 1 && t("stepSend")}
                          {n === 2 && t("stepSubmit")}
                          {n === 3 && t("stepTranscribe")}
                          {n === 4 && t("stepFinish")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {result && (
                <section className="card">
                  <div className="result-head">
                    <h2 style={{ margin: 0 }}>{t("resTitle")}</h2>
                    <span className={"badge " + (result.ok ? "ok" : "warn")}>
                      {result.ok ? t("valOk") : t("valWarn")}
                    </span>
                    {result.language && <span className="badge">{t("langBadge", { lang: result.language })}</span>}
                    <span className="badge">~${result.cost.toFixed(4)}</span>
                    <span className="badge">{Math.round(result.duration_s / 60)} min</span>
                    <div className="spacer" style={{ flex: 1 }} />
                    <button className="secondary" onClick={copyTranscript}>{t("copyAll")}</button>
                  </div>
                  <pre className="transcript" ref={transcriptRef}>{result.clean_text}</pre>
                  {result.clean_path && (
                    <div className="muted" style={{ marginTop: 8 }}>{t("savedAt", { path: result.clean_path })}</div>
                  )}
                </section>
              )}
          </div>

          <div className={"view-pane" + (view === "library" ? "" : " hidden")}>
            <LibraryView active={view === "library"} />
          </div>

          <div className={"view-pane" + (view === "settings" ? "" : " hidden")}>
            <AppearanceCard {...appearance} />
            <TypographyCard prefs={font.prefs} setPrefs={font.setPrefs} />
            <SettingsView onChanged={loadEngines} />
            <StorageSettingsCard />
          </div>
        </div>
      </main>
      </div>
    </div>
  );
}

// O App consome o contexto de idioma, por isso o export raiz é o provider
export default function Root() {
  return (
    <LangProvider>
      <App />
    </LangProvider>
  );
}
