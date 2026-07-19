import { createContext, Fragment, useContext, useEffect, useMemo, useRef, useState, type ClipboardEvent, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { getVersion } from "@tauri-apps/api/app";
import {
  Mic, LibraryBig, Settings, Palette, PanelLeftClose, PanelLeftOpen,
  Search, ArrowLeft, ArrowRight, Minus, Square, X, LogOut, ShieldCheck,
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

type View = "transcribe" | "library" | "settings" | "admin";

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
  // Presentes só na vista de ADMIN (o worker junta o dono a cada item)
  owner_email?: string | null;
  owner_username?: string | null;
  owner_provider?: string | null;
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

// Sessão da conta (isolamento por utilizador, 2026-07-19): guarda QUEM está
// dentro (pk da tabela users), em QUE modo (local/vps) e o role. Toda a
// Biblioteca e transcrição enviam o id — o worker filtra por ele.
type Session = {
  profile: "user" | "admin";
  mode: "local" | "vps";
  id: number | null;
  email: string;
  user_id: string | null;
  role: string;
};

function getSession(): Session | null {
  try {
    const s = JSON.parse(localStorage.getItem("upexnote-session") || "null");
    return s && s.profile ? (s as Session) : null;
  } catch {
    return null;
  }
}

// Cache local da Biblioteca (lista + resumo, SEM textos) para a app abrir já
// com os últimos dados em vez de "resetar" a cada arranque — padrão
// stale-while-revalidate. A chave inclui modo+conta: a cache de uma conta
// NUNCA aparece a outra (mesma regra de isolamento da base).
const LIB_CACHE_PREFIX = "upexnote-lib-cache";
type LibCache = { ts: string; summary: LibSummary; items: LibItem[] };

function libCacheKey(): string {
  const s = getSession();
  return `${LIB_CACHE_PREFIX}::${s?.mode || "?"}::${s?.id ?? "?"}`;
}

function clearLibCaches() {
  for (const k of Object.keys(localStorage)) {
    if (k.startsWith(LIB_CACHE_PREFIX) || k.startsWith("upexnote-admin-cache")) localStorage.removeItem(k);
  }
}

function readLibCache(): LibCache | null {
  try {
    const raw = localStorage.getItem(libCacheKey());
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
      const raw = await invoke<string>("library", {
        search: searchTerm ?? null, user: getSession()?.id ?? null,
      });
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
              libCacheKey(),
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
      const raw = await invoke<string>("library_item", { id, user: getSession()?.id ?? null });
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
      const raw = await invoke<string>("library_update", { id: detail.id, text: editText, user: getSession()?.id ?? null });
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
      const raw = await invoke<string>("library_delete", { id: detail.id, user: getSession()?.id ?? null });
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
      const raw = await invoke<string>("library_ack", { id: detail.id, reopen, user: getSession()?.id ?? null });
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
          {"owner_email" in detail && (
            <span
              className="badge"
              title={detail.owner_provider ? t("libOwnerVia", { provider: detail.owner_provider }) : undefined}
            >
              {detail.owner_email || t("libOwnerNone")}
            </span>
          )}
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
                <div className="lib-sub">
                  #{it.id} · {engLabel(it.engine)} · {fmtDate(it.created_at, locale)}{it.language ? " · " + it.language : ""}
                  {"owner_email" in it && (
                    <span className="lib-owner" title={it.owner_provider ? t("libOwnerVia", { provider: it.owner_provider }) : undefined}>
                      {" · "}{it.owner_email || t("libOwnerNone")}
                    </span>
                  )}
                </div>
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
        <span className={"badge " + (s?.storage_mode === "vps" ? "ok" : "")}>
          {s?.storage_mode === "vps" ? "🔒 " + t("stoModeVps") : t("stoModeLocal")}
        </span>
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
        <div className="engine-info">{t("cloudHint")}</div>
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
// Login (item 13 — apresentação padrão de mercado, 2026-07-18): cartão de
// e-mail+senha como toda app profissional; conta LOCAL nesta fase (hash+salt
// via Web Crypto — a identidade migra para a API na Fase 2). "Entrar como
// administrador" é um link discreto que valida a ligação real por trás, sem
// UMA palavra sobre infraestrutura no ecrã (regra do utilizador).
// WebView2 desta máquina: type="password" crasha → máscara via CSS.
// ---------------------------------------------------------------------------
// Contas vivem na tabela `users` do banco do modo ativo (worker valida tudo;
// senhas por stdin, PBKDF2 no worker). O frontend só orquestra os ecrãs.
type AccountUser = { id: number; user_id: string; email: string; role: string };
type OauthPayload = {
  auth_provider: string; provider_id: string; email: string;
  first_name?: string; last_name?: string; provider_scopes?: string;
};

const GithubMark = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
  </svg>
);

const GoogleG = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M21.6 12.2c0-.7-.06-1.4-.18-2H12v3.9h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.4z" />
    <path d="M12 22c2.7 0 5-.9 6.6-2.4l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22z" opacity=".8" />
    <path d="M6.4 14a6 6 0 0 1 0-3.8V7.6H3.1a10 10 0 0 0 0 8.9L6.4 14z" opacity=".6" />
    <path d="M12 6c1.5 0 2.8.5 3.8 1.5L18.7 5A10 10 0 0 0 3.1 7.6L6.4 10c.8-2.3 3-4 5.6-4z" opacity=".9" />
  </svg>
);

function LoginGate({ onDone }: { onDone: (session: string) => void }) {
  const { t } = useLang();
  // Login é SEMPRE o primeiro ecrã (padrão de mercado); criar conta é via link.
  // E-mail NUNCA pré-preenchido (após logout, a pessoa decide a conta).
  const [screen, setScreen] = useState<"login" | "create" | "reset" | "precad" | "welcome">("login");
  // Conta acabada de criar, à espera do ecrã de boas-vindas (orientações)
  const [pendingUser, setPendingUser] = useState<AccountUser | null>(null);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [userId, setUserId] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [avail, setAvail] = useState<{ available: boolean; suggestions: string[] } | null>(null);
  const [oauthPending, setOauthPending] = useState<OauthPayload | null>(null);
  const [oauthMsg, setOauthMsg] = useState("");
  const [ghCode, setGhCode] = useState("");
  const [busy, setBusy] = useState<"" | "form" | "admin" | "google" | "github">("");
  const [err, setErr] = useState("");

  // Alvo da entrada: utilizador (conta pessoal, base local) ou administrador
  // (conta na base central + prova da credencial). Mesmos 3 métodos nos dois.
  const [target, setTarget] = useState<"user" | "admin">("user");
  const [adminPw, setAdminPw] = useState("");
  // Refs para os handlers assíncronos (o listener de OAuth vive fora do render)
  const targetRef = useRef(target);
  targetRef.current = target;
  const adminPwRef = useRef(adminPw);
  adminPwRef.current = adminPw;
  const accMode = target === "admin" ? "vps" : "local";

  function finish(profile: "user" | "admin", user?: AccountUser | null) {
    clearLibCaches(); // cache é por conta/modo — nunca herdar de outra sessão
    localStorage.setItem(
      "upexnote-session",
      JSON.stringify({
        profile,
        mode: profile === "admin" ? "vps" : "local",
        id: user?.id ?? null,
        email: user?.email || email,
        user_id: user?.user_id || null,
        role: user?.role || (profile === "admin" ? "admin" : "user"),
      })
    );
    onDone(profile);
  }

  // Fluxo admin: a credencial digitada segue DENTRO do payload de login/registo
  // e o worker eleva no MESMO processo (identidade + prova numa só ida à base
  // — dois spawns sequenciais duplicavam a latência; 2026-07-19).
  async function finishAdmin(user: AccountUser) {
    try { await invoke("set_settings", { storageMode: "vps" }); } catch { /* best-effort */ }
    finish("admin", user);
  }

  function mapErr(code?: string): string {
    if (code === "email_taken") return t("loginErrEmailTaken");
    if (code === "user_id_taken") return t("loginErrUserIdTaken");
    if (code === "invalid_admin_credentials") return t("loginAdminFail");
    return t("loginErrWrong");
  }

  // Disponibilidade do user_id (debounce) — padrão de app moderna
  useEffect(() => {
    if ((screen !== "create" && screen !== "precad") || userId.trim().length < 3) {
      setAvail(null);
      return;
    }
    const id = setTimeout(async () => {
      try {
        const raw = await invoke<string>("account_suggest", { userId: userId.trim(), mode: accMode });
        const obj = JSON.parse(raw);
        setAvail({ available: !!obj.available, suggestions: obj.suggestions || [] });
      } catch { /* silencioso */ }
    }, 450);
    return () => clearTimeout(id);
  }, [userId, screen, accMode]);

  // Eventos do fluxo OAuth (o device flow do GitHub mostra um código).
  // processingRef: entre o fim do processo OAuth e o fim da validação da conta
  // há 2-3 chamadas à base — o "done" do OAuth NÃO pode limpar o estado ocupado
  // nesse intervalo (parecia erro/silêncio; visto na validação da v0.18.1).
  const processingRef = useRef(false);
  useEffect(() => {
    const unEvent = listen<string>("oauth://event", async (ev) => {
      let obj: any;
      try { obj = JSON.parse(ev.payload); } catch { return; }
      if (obj.type === "progress") {
        setOauthMsg(obj.message || t("loginOauthWaiting"));
        if (obj.user_code) setGhCode(obj.user_code);
      } else if (obj.type === "oauth") {
        processingRef.current = true;
        setGhCode("");
        setOauthMsg(t("loginFinishing"));
        const adm = targetRef.current === "admin";
        const raw = await invoke<string>("account", {
          op: "oauth-login", mode: adm ? "vps" : "local",
          payload: JSON.stringify(adm ? { ...obj, admin_secret: adminPwRef.current } : obj),
        });
        const res = JSON.parse(raw);
        if (res.ok && !res.new) {
          if (adm) { await finishAdmin(res.user); return; }
          // fixa o modo local EXPLICITAMENTE — a conta pessoal nunca pode
          // depender do default da máquina (bug real de 2026-07-19)
          try { await invoke("set_settings", { storageMode: "local" }); } catch { /* best-effort */ }
          finish("user", res.user);
          return;
        }
        if (res.ok && res.new) {
          processingRef.current = false;
          setBusy("");
          setOauthMsg("");
          setOauthPending(obj as OauthPayload);
          setEmail(obj.email || "");
          setFirstName(obj.first_name || "");
          setLastName(obj.last_name || "");
          setUserId((obj.email || "").split("@")[0].replace(/[^a-z0-9._-]/gi, "").toLowerCase());
          setErr("");
          setScreen("precad");
        }
        if (!res.ok) {
          processingRef.current = false;
          setBusy(""); setOauthMsg("");
          setErr(res.error === "invalid_admin_credentials" ? t("loginAdminFail") : t("loginErrWrong"));
        }
      } else if (obj.type === "error") {
        processingRef.current = false;
        setBusy(""); setOauthMsg("");
        setErr(obj.error === "oauth_not_configured" ? t("loginOauthNotConfigured") : t("loginErrWrong"));
      }
    });
    const unDone = listen("oauth://done", () => {
      // Só limpa se NÃO houver validação de conta em curso (o fim do processo
      // OAuth chega antes das chamadas à base terminarem).
      if (!processingRef.current) { setBusy(""); setOauthMsg(""); setGhCode(""); }
    });
    return () => { unEvent.then((f) => f()); unDone.then((f) => f()); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t]);

  async function social(provider: "google" | "github") {
    if (target === "admin" && !adminPw) { setErr(t("loginAdminNeedPw")); return; }
    setErr(""); setOauthMsg(t("loginOauthWaiting")); setBusy(provider);
    try { await invoke("oauth_start", { provider }); } catch { setBusy(""); setErr(t("loginErrWrong")); }
  }

  async function submit() {
    setErr("");
    const mail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return setErr(t("loginErrEmail"));
    if (screen === "create" || screen === "reset") {
      if (pw.length < 6) return setErr(t("loginErrPwShort"));
      if (pw !== pw2) return setErr(t("loginErrPwMatch"));
    }
    if (target === "admin" && !adminPw) return setErr(t("loginAdminNeedPw"));
    setBusy("form");
    try {
      // No alvo admin, a credencial digitada segue no payload e o worker eleva
      // no mesmo processo — a resposta já vem com role=admin.
      const adminExtra = target === "admin" ? { admin_secret: adminPw } : {};
      let res: any;
      if (screen === "login") {
        res = JSON.parse(await invoke<string>("account", {
          op: "login", mode: accMode,
          payload: JSON.stringify({ email: mail, password: pw, ...adminExtra }),
        }));
      } else if (screen === "reset") {
        res = JSON.parse(await invoke<string>("account", {
          op: "reset", mode: accMode, payload: JSON.stringify({ email: mail, password: pw }),
        }));
        if (res.ok) {
          res = JSON.parse(await invoke<string>("account", {
            op: "login", mode: accMode,
            payload: JSON.stringify({ email: mail, password: pw, ...adminExtra }),
          }));
        }
      } else {
        // create / precad → registo completo na tabela users
        res = JSON.parse(await invoke<string>("account", {
          op: "register",
          mode: accMode,
          payload: JSON.stringify({
            email: mail,
            user_id: userId.trim(),
            first_name: firstName.trim() || null,
            last_name: lastName.trim() || null,
            password: screen === "create" ? pw : undefined,
            auth_provider: oauthPending?.auth_provider || "email",
            provider_id: oauthPending?.provider_id,
            provider_scopes: oauthPending?.provider_scopes,
            ...adminExtra,
          }),
        }));
      }
      if (res.ok) {
        if (target === "admin") {
          await finishAdmin(res.user);
          return;
        }
        try { await invoke("set_settings", { storageMode: "local" }); } catch { /* best-effort */ }
        if (screen === "create" || screen === "precad") {
          // Conta NOVA → ecrã de boas-vindas com orientações (só uma vez;
          // logins seguintes entram direto). Futuro: consentimento de
          // telemetria (RGPD) encaixa aqui quando a Fase 2 chegar.
          setPendingUser(res.user);
          setScreen("welcome");
          return;
        }
        finish("user", res.user);
        return;
      }
      setErr(mapErr(res.error));
    } catch {
      setErr(t("loginErrWrong"));
    } finally {
      setBusy("");
    }
  }

  function maskedPaste(setter: (v: string) => void) {
    return (e: ClipboardEvent<HTMLInputElement>) => {
      e.preventDefault();
      setter(e.clipboardData.getData("text"));
    };
  }

  return (
    <div className="profile-gate">
      <div className="pg-head">
        <span className="brand-mark"><BrandMark size={28} /></span>
        <div className="wordmark" style={{ fontSize: 20 }}>
          <span className="up">Upex</span><span className="ex">Note</span>
        </div>
      </div>
      {screen === "welcome" ? (
        <div className="login-card">
          <h1 className="pg-title">{t("welcomeTitle")}</h1>
          <ul className="welcome-list">
            <li>{t("welcomeTipPrivacy")}</li>
            <li>{t("welcomeTipFolder")}</li>
            <li>{t("welcomeTipEngines")}</li>
          </ul>
          <button style={{ width: "100%" }} onClick={() => finish("user", pendingUser)}>
            {t("welcomeStart")}
          </button>
        </div>
      ) : (
      <div className="login-card">
        <h1 className="pg-title">
          {screen === "create" ? t("loginCreateTitle") : screen === "precad" ? t("loginPrecadTitle")
            : target === "admin" ? t("loginAdminTitle") : t("loginTitle")}
        </h1>
        {target === "admin" && (
          <div className="field" style={{ marginBottom: 12 }}>
            <label>{t("loginAdminPw")}</label>
            <input
              type="text" className="pw-mask" autoComplete="off" spellCheck={false}
              value={adminPw}
              onChange={(e) => setAdminPw(e.currentTarget.value)}
              onPaste={maskedPaste(setAdminPw)}
            />
            <div className="engine-info">{t("loginAdminHint")}</div>
          </div>
        )}
        {screen !== "precad" && (
          <>
            <button className="secondary social-btn" onClick={() => social("google")} disabled={busy !== ""}>
              {busy === "google" ? <span className="spinner" /> : <GoogleG />} {t("loginWithGoogle")}
            </button>
            <button className="secondary social-btn" onClick={() => social("github")} disabled={busy !== ""}>
              {busy === "github" ? <span className="spinner" /> : <GithubMark />} {t("loginWithGithub")}
            </button>
            {(busy === "google" || busy === "github") && (
              <div className="muted" style={{ textAlign: "center" }}>
                {oauthMsg}
                {ghCode && (
                  <div
                    className="gh-code-box"
                    onClick={() => navigator.clipboard.writeText(ghCode)}
                    title={t("copy")}
                  >
                    <div className="gh-code-hint">{t("loginGithubCodeHint")}</div>
                    <div className="gh-code-big">{ghCode}</div>
                  </div>
                )}
              </div>
            )}
            <div className="login-divider"><span>{t("loginOr")}</span></div>
          </>
        )}
        {screen === "reset" && <div className="muted" style={{ textAlign: "left" }}>{t("loginResetInfo")}</div>}
        <div className="field" style={{ marginBottom: 10 }}>
          <label>{t("loginEmail")}</label>
          <input
            type="text" autoComplete="off" spellCheck={false}
            value={email}
            readOnly={screen === "precad"}
            onChange={(e) => setEmail(e.currentTarget.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
          />
        </div>
        {(screen === "create" || screen === "precad") && (
          <>
            <div className="field" style={{ marginBottom: 10 }}>
              <label>{t("loginUserId")}</label>
              <input
                type="text" autoComplete="off" spellCheck={false}
                value={userId}
                onChange={(e) =>
                  setUserId(e.currentTarget.value.toLowerCase().replace(/[^a-z0-9._-]/g, ""))
                }
              />
              {avail && (
                <div className="engine-info">
                  {avail.available ? t("loginUserIdOk") : (
                    <>
                      {t("loginUserIdTaken")}{" "}
                      {avail.suggestions.map((s) => (
                        <button key={s} className="link-btn" onClick={() => setUserId(s)}>{s}</button>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="row" style={{ marginBottom: 10 }}>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>{t("loginFirstName")}</label>
                <input type="text" autoComplete="off" spellCheck={false} value={firstName}
                  onChange={(e) => setFirstName(e.currentTarget.value)} />
              </div>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>{t("loginLastName")}</label>
                <input type="text" autoComplete="off" spellCheck={false} value={lastName}
                  onChange={(e) => setLastName(e.currentTarget.value)} />
              </div>
            </div>
          </>
        )}
        {screen !== "precad" && (
          <div className="field" style={{ marginBottom: 10 }}>
            <label>{t("loginPassword")}</label>
            <input
              type="text" className="pw-mask" autoComplete="off" spellCheck={false}
              value={pw}
              onChange={(e) => setPw(e.currentTarget.value)}
              onPaste={maskedPaste(setPw)}
              onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            />
          </div>
        )}
        {(screen === "create" || screen === "reset") && (
          <div className="field" style={{ marginBottom: 10 }}>
            <label>{t("loginPasswordConfirm")}</label>
            <input
              type="text" className="pw-mask" autoComplete="off" spellCheck={false}
              value={pw2}
              onChange={(e) => setPw2(e.currentTarget.value)}
              onPaste={maskedPaste(setPw2)}
              onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            />
          </div>
        )}
        {err && <div className="key-warn" style={{ marginBottom: 8 }}>{err}</div>}
        <button style={{ width: "100%" }} onClick={submit} disabled={busy !== ""}>
          {busy === "form" ? t("loginChecking") : screen === "login" ? t("loginBtn")
            : screen === "reset" ? t("loginResetBtn") : screen === "precad" ? t("loginFinish") : t("loginCreateBtn")}
        </button>
        <div className="login-links">
          {/* "Esqueci a senha" REMOVIDO até haver reset com verificação real por
              e-mail (código enviado) — um reset local aberto era anti-segurança
              (feedback do utilizador, 2026-07-18). Chega com a infra de e-mail. */}
          {screen === "login" ? (
            <button className="link-btn" onClick={() => { setErr(""); setScreen("create"); }}>{t("loginNoAccount")}</button>
          ) : screen !== "precad" ? (
            <button className="link-btn" onClick={() => { setErr(""); setScreen("login"); }}>{t("loginHaveAccount")}</button>
          ) : null}
        </div>
      </div>
      )}
      {screen !== "welcome" && (
        <button
          className="link-btn login-admin"
          onClick={() => {
            setErr(""); setAdminPw(""); setScreen("login");
            setTarget(target === "admin" ? "user" : "admin");
          }}
          disabled={busy !== ""}
        >
          {target === "admin" ? t("loginUserLink") : t("loginAdminLink")}
        </button>
      )}
    </div>
  );
}

// Perfil na sidebar (padrão das plataformas): avatar com inicial + identidade
// da sessão + sair. O logout vive AQUI, não nas definições de armazenamento.
function SidebarProfile({ collapsed }: { collapsed: boolean }) {
  const { t } = useLang();
  const sess = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("upexnote-session") || "null");
    } catch {
      return null;
    }
  }, []);
  if (!sess) return null;
  const name: string = sess.user_id || sess.email || "admin";
  const initial = (name[0] || "?").toUpperCase();
  function logout() {
    localStorage.removeItem("upexnote-session");
    clearLibCaches();
    window.location.reload();
  }
  return (
    <div className={"side-profile" + (collapsed ? " collapsed" : "")}>
      <span className="avatar" title={sess.email || name}>{initial}</span>
      {!collapsed && (
        <span className="sp-main">
          <span className="sp-name">{name}</span>
          {sess.profile === "admin" && <span className="sp-role">admin</span>}
        </span>
      )}
      {!collapsed && (
        <button className="tb-btn" onClick={logout} title={t("stoLogout")}>
          <LogOut size={15} strokeWidth={1.75} />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Administração (2026-07-19, só role=admin): utilizadores (CRUD auditado),
// atividade (access_events com filtros) e auditoria (audit_log). O worker
// revalida o ator na base em TODAS as operações — a aba é só a janela.
// ---------------------------------------------------------------------------
type AdmUser = {
  id: number; user_id: string; email: string; first_name: string | null; last_name: string | null;
  auth_provider: string; role: string; created_at: string | null; last_login_at: string | null;
  deleted_at: string | null; transcription_count: number;
};
type AdmEvent = {
  id: number; occurred_at: string | null; event: string; ok: boolean | number | null;
  email: string | null; user_id: number | null; detail: string | null; app_version: string | null; host: string | null;
};
type AdmAudit = {
  id: number; occurred_at: string | null; actor_user_id: number | null; action: string;
  table_name: string; record_id: number | null; snapshot: Record<string, unknown> | null;
};

// Cache SWR da aba (mesmo padrão da Biblioteca v0.8.1): abre instantânea com
// os últimos dados guardados; a atualização corre em fundo. Por modo+conta.
const ADM_CACHE_PREFIX = "upexnote-admin-cache";
type AdmData = { users: AdmUser[]; events: AdmEvent[]; audit: AdmAudit[] };

function admCacheKey(): string {
  const s = getSession();
  return `${ADM_CACHE_PREFIX}::${s?.mode || "?"}::${s?.id ?? "?"}`;
}

function AdminView({ active }: { active: boolean }) {
  const { t, locale } = useLang();
  const sess = getSession();
  const [tab, setTab] = useState<"users" | "activity" | "audit">("users");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [data, setData] = useState<AdmData>({ users: [], events: [], audit: [] });
  const [cacheTs, setCacheTs] = useState<string | null>(null);

  const [uSearch, setUSearch] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  // Edição COMPLETA do registo (não ações por campo): e-mail, username, nomes,
  // role — tudo ancorado no id imutável, que arrasta as outras tabelas.
  const [editUser, setEditUser] = useState<{
    id: number; email: string; user_id: string; first_name: string; last_name: string; role: string;
  } | null>(null);
  const [confirmDel, setConfirmDel] = useState<{ id: number; purge: boolean } | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [cEmail, setCEmail] = useState("");
  const [cUser, setCUser] = useState("");
  const [cPw, setCPw] = useState("");
  const [notice, setNotice] = useState("");

  const [period, setPeriod] = useState<"day" | "week" | "month" | "all">("week");
  const [aTable, setATable] = useState("");
  const [aId, setAId] = useState("");
  const [openSnap, setOpenSnap] = useState<number | null>(null);

  async function call(op: string, payload: Record<string, unknown>) {
    const raw = await invoke<string>("admin", {
      op, mode: sess?.mode ?? null,
      payload: JSON.stringify({ actor: sess?.id ?? null, ...payload }),
    });
    const r = JSON.parse(raw);
    // erro do worker sem campo ok → normaliza para a UI nunca engolir falhas
    if (r.type === "error" && r.ok === undefined) return { ok: false, error: r.message };
    return r;
  }

  // UMA chamada única traz tudo (1 processo do worker, 1 ligação); os filtros
  // são todos locais e instantâneos — nada de round-trips por pesquisa.
  async function loadOverview() {
    setBusy(true); setErr("");
    try {
      const r = await call("overview", {});
      if (r.ok) {
        const fresh = { users: r.users || [], events: r.events || [], audit: r.audit || [] };
        setData(fresh);
        setCacheTs(null);
        try {
          localStorage.setItem(admCacheKey(), JSON.stringify({ ts: new Date().toISOString(), ...fresh }));
        } catch { /* cache é best-effort */ }
      } else setErr(r.error || r.message || "");
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  useEffect(() => {
    if (active && !loadedOnce) {
      setLoadedOnce(true);
      try {
        const c = JSON.parse(localStorage.getItem(admCacheKey()) || "null");
        if (c && c.users) {
          setData({ users: c.users, events: c.events || [], audit: c.audit || [] });
          setCacheTs(c.ts || null);
        }
      } catch { /* sem cache */ }
      loadOverview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, loadedOnce]);

  // Filtros locais (live, a cada tecla — sem tocar na base)
  const usersFiltered = useMemo(() => {
    const q = uSearch.trim().toLowerCase();
    return data.users.filter((u) =>
      (showDeleted || !u.deleted_at) &&
      (!q || u.email.toLowerCase().includes(q) || u.user_id.toLowerCase().includes(q)));
  }, [data.users, uSearch, showDeleted]);

  const sinceMs = period === "all" ? 0 : Date.now() - (period === "day" ? 1 : period === "week" ? 7 : 30) * 86400000;
  const eventsFiltered = useMemo(
    () => data.events.filter((ev) => !sinceMs || (ev.occurred_at && Date.parse(ev.occurred_at) >= sinceMs)),
    [data.events, sinceMs]);
  const counts = useMemo(() => {
    const m = new Map<string, { event: string; ok: boolean | number | null; n: number }>();
    for (const ev of eventsFiltered) {
      const k = `${ev.event}::${ev.ok ? 1 : 0}`;
      const cur = m.get(k) || { event: ev.event, ok: ev.ok, n: 0 };
      cur.n += 1;
      m.set(k, cur);
    }
    return [...m.values()].sort((a, b) => a.event.localeCompare(b.event));
  }, [eventsFiltered]);

  const auditFiltered = useMemo(() => {
    const tq = aTable.trim().toLowerCase();
    return data.audit.filter((a) =>
      (!tq || a.table_name.toLowerCase().includes(tq)) &&
      (!aId.trim() || String(a.record_id) === aId.trim()));
  }, [data.audit, aTable, aId]);

  function mapAdmErr(code?: string): string {
    if (code === "email_taken") return t("loginErrEmailTaken");
    if (code === "user_id_taken") return t("loginErrUserIdTaken");
    if (code === "cannot_change_own_role") return t("admNoSelfRole");
    if (code === "last_admin") return t("admLastAdmin");
    return t("errPrefix") + (code || "");
  }

  async function saveEdit() {
    if (!editUser) return;
    setBusy(true); setErr(""); setNotice("");
    try {
      const r = await call("update-user", {
        id: editUser.id,
        fields: {
          email: editUser.email.trim(),
          user_id: editUser.user_id.trim(),
          first_name: editUser.first_name.trim() || null,
          last_name: editUser.last_name.trim() || null,
          role: editUser.role,
        },
      });
      if (r.ok) { setEditUser(null); setNotice(t("admSaved")); setUSearch(""); loadOverview(); }
      else setErr(mapAdmErr(r.error));
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  async function doDelete() {
    if (!confirmDel) return;
    setBusy(true); setErr(""); setNotice("");
    try {
      const r = await call("delete-user", { id: confirmDel.id, purge: confirmDel.purge });
      if (r.ok) {
        setNotice(t(confirmDel.purge ? "admPurged" : "admDeletedOk", { n: r.cascade ?? 0 }));
        setConfirmDel(null);
        setUSearch(""); // volta à tabela completa — nunca deixar um filtro antigo esconder o resultado
        loadOverview();
      } else {
        setErr(r.error === "cannot_delete_self" ? t("admNoSelfDelete") : t("errPrefix") + (r.error || ""));
        setConfirmDel(null);
      }
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  async function createUser() {
    setBusy(true); setErr(""); setNotice("");
    try {
      const r = await call("create-user", {
        user: { email: cEmail.trim(), user_id: cUser.trim(), password: cPw, auth_provider: "email" },
      });
      if (r.ok) { setNotice(t("admCreated")); setShowCreate(false); setCEmail(""); setCUser(""); setCPw(""); setUSearch(""); loadOverview(); }
      else setErr(r.error === "email_taken" ? t("loginErrEmailTaken")
        : r.error === "user_id_taken" ? t("loginErrUserIdTaken")
        : r.error === "password_required" ? t("loginErrPwShort") : t("errPrefix") + (r.error || ""));
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  const evOk = (v: boolean | number | null) => v === true || v === 1;

  return (
    <section className="card">
      <h2>{t("navAdmin")}</h2>
      <div className="row" style={{ marginBottom: 14, gap: 6 }}>
        {(["users", "activity", "audit"] as const).map((tb) => (
          <button key={tb} className={tab === tb ? "" : "secondary"} onClick={() => {
            setTab(tb); setErr(""); setNotice("");
          }}>
            {t(tb === "users" ? "admTabUsers" : tb === "activity" ? "admTabActivity" : "admTabAudit")}
          </button>
        ))}
        <span style={{ flex: 1 }} />
        {cacheTs && <span className="muted" title={t("libCacheTitle")}>{t("libCacheUpdating", { ts: fmtDate(cacheTs, locale) })}</span>}
        <button className="secondary" onClick={loadOverview} disabled={busy}>
          {busy ? <span className="spinner" /> : t("libRefresh")}
        </button>
      </div>
      {err && <div className="key-warn" style={{ marginBottom: 10 }}>{err}</div>}
      {notice && <div className="engine-info" style={{ marginBottom: 10 }}>{notice}</div>}

      {tab === "users" && (
        <>
          <div className="row wrap" style={{ marginBottom: 10 }}>
            <input
              type="text" style={{ flex: 1, minWidth: 220 }} placeholder={t("admSearchPh")}
              value={uSearch}
              onChange={(e) => setUSearch(e.currentTarget.value)}
            />
            <label className="row" style={{ gap: 6, alignItems: "center" }}>
              <input type="checkbox" checked={showDeleted}
                onChange={(e) => setShowDeleted(e.currentTarget.checked)} />
              {t("admShowDeleted")}
            </label>
            <button className="secondary" onClick={() => setShowCreate((s) => !s)}>{t("admNewUser")}</button>
          </div>
          {showCreate && (
            <div className="row wrap" style={{ marginBottom: 12, alignItems: "flex-end" }}>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>{t("loginEmail")}</label>
                <input type="text" value={cEmail} onChange={(e) => setCEmail(e.currentTarget.value)} />
              </div>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>{t("loginUserId")}</label>
                <input type="text" value={cUser}
                  onChange={(e) => setCUser(e.currentTarget.value.toLowerCase().replace(/[^a-z0-9._-]/g, ""))} />
              </div>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>{t("loginPassword")}</label>
                <input type="text" className="pw-mask" value={cPw} onChange={(e) => setCPw(e.currentTarget.value)} />
              </div>
              <button onClick={createUser} disabled={busy}>{t("admCreateBtn")}</button>
            </div>
          )}
          <div className="table-scroll">
            <table className="eng-table">
              <thead>
                <tr>
                  <th>ID</th><th>{t("loginUserId")}</th><th>{t("loginEmail")}</th>
                  <th>{t("admColProvider")}</th><th>{t("admColRole")}</th>
                  <th>{t("admColTx")}</th><th>{t("admColLast")}</th><th>{t("admColActions")}</th>
                </tr>
              </thead>
              <tbody>
                {usersFiltered.map((u) => (
                  <tr key={u.id} style={u.deleted_at ? { opacity: 0.55 } : undefined}>
                    <td>#{u.id}</td>
                    <td>{u.user_id}</td>
                    <td>
                      {u.email}{u.deleted_at && <span className="badge" style={{ marginLeft: 6 }}>{t("admDeletedBadge")}</span>}
                    </td>
                    <td>{u.auth_provider}</td>
                    <td>{u.role}</td>
                    <td>{u.transcription_count}</td>
                    <td>{fmtDate(u.last_login_at, locale)}</td>
                    <td>
                      {!u.deleted_at ? (
                        <span className="row" style={{ gap: 6 }}>
                          <button className="secondary" onClick={() => {
                            setErr("");
                            setEditUser({
                              id: u.id, email: u.email, user_id: u.user_id,
                              first_name: u.first_name || "", last_name: u.last_name || "", role: u.role,
                            });
                          }}>
                            {t("admEdit")}
                          </button>
                          <button className="secondary" onClick={() => setConfirmDel({ id: u.id, purge: false })}>{t("admDelete")}</button>
                          <button className="secondary" onClick={() => setConfirmDel({ id: u.id, purge: true })}>{t("admPurge")}</button>
                        </span>
                      ) : (
                        <button className="secondary" onClick={() => setConfirmDel({ id: u.id, purge: true })}>{t("admPurge")}</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {usersFiltered.length === 0 && (
            <div className="muted" style={{ marginTop: 10 }}>
              {data.users.length > 0 ? (
                <>
                  {t("admNoMatch")}{" "}
                  <button className="link-btn" onClick={() => { setUSearch(""); setShowDeleted(false); }}>
                    {t("admClearFilter")}
                  </button>
                </>
              ) : busy ? t("loginChecking") : t("admNoEvents")}
            </div>
          )}
          <div className="engine-info" style={{ marginTop: 8 }}>{t("admCascadeNote")}</div>
          {editUser && (
            <div className="modal-overlay" onClick={() => setEditUser(null)}>
              <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                <h3 style={{ margin: "0 0 4px" }}>{t("admEditTitle")}</h3>
                <div className="muted" style={{ marginBottom: 14 }}>#{editUser.id}</div>
                <div className="field" style={{ marginBottom: 10 }}>
                  <label>{t("loginEmail")}</label>
                  <input type="text" value={editUser.email}
                    onChange={(e) => setEditUser({ ...editUser, email: e.currentTarget.value })} />
                </div>
                <div className="field" style={{ marginBottom: 10 }}>
                  <label>{t("loginUserId")}</label>
                  <input type="text" value={editUser.user_id}
                    onChange={(e) => setEditUser({ ...editUser, user_id: e.currentTarget.value.toLowerCase().replace(/[^a-z0-9._-]/g, "") })} />
                </div>
                <div className="row" style={{ marginBottom: 10 }}>
                  <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                    <label>{t("loginFirstName")}</label>
                    <input type="text" value={editUser.first_name}
                      onChange={(e) => setEditUser({ ...editUser, first_name: e.currentTarget.value })} />
                  </div>
                  <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                    <label>{t("loginLastName")}</label>
                    <input type="text" value={editUser.last_name}
                      onChange={(e) => setEditUser({ ...editUser, last_name: e.currentTarget.value })} />
                  </div>
                </div>
                <div className="field" style={{ marginBottom: 16 }}>
                  <label>{t("admColRole")}</label>
                  <select value={editUser.role}
                    disabled={editUser.id === (sess?.id ?? -1)}
                    onChange={(e) => setEditUser({ ...editUser, role: e.currentTarget.value })}>
                    <option value="user">user</option>
                    <option value="admin">admin</option>
                  </select>
                  {editUser.id === (sess?.id ?? -1) && (
                    <div className="engine-info">{t("admNoSelfRole")}</div>
                  )}
                </div>
                <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
                  <button className="secondary" onClick={() => setEditUser(null)} disabled={busy}>{t("cancel")}</button>
                  <button onClick={saveEdit} disabled={busy}>
                    {busy ? <span className="spinner" /> : t("save")}
                  </button>
                </div>
              </div>
            </div>
          )}
          {confirmDel && (() => {
            const target = data.users.find((u) => u.id === confirmDel.id);
            return (
              <div className="modal-overlay" onClick={() => setConfirmDel(null)}>
                <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                  <h3 style={{ margin: "0 0 6px" }}>{t(confirmDel.purge ? "admPurge" : "admDelete")}</h3>
                  <div style={{ marginBottom: 6 }}><b>{target?.email || `#${confirmDel.id}`}</b></div>
                  <p className="muted" style={{ margin: "0 0 16px" }}>
                    {t(confirmDel.purge ? "admPurgeConfirm" : "admDeleteConfirm")}
                  </p>
                  <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
                    <button className="secondary" onClick={() => setConfirmDel(null)} disabled={busy}>{t("cancel")}</button>
                    <button onClick={doDelete} disabled={busy}>
                      {busy ? <span className="spinner" /> : t("admConfirm")}
                    </button>
                  </div>
                </div>
              </div>
            );
          })()}
        </>
      )}

      {tab === "activity" && (
        <>
          <div className="row wrap" style={{ marginBottom: 10 }}>
            {(["day", "week", "month", "all"] as const).map((p) => (
              <button key={p} className={period === p ? "" : "secondary"} onClick={() => setPeriod(p)}>
                {t(p === "day" ? "admPeriodDay" : p === "week" ? "admPeriodWeek" : p === "month" ? "admPeriodMonth" : "admPeriodAll")}
              </button>
            ))}
          </div>
          <div className="row wrap" style={{ marginBottom: 12 }}>
            {counts.map((c, i) => (
              <span key={i} className={"badge " + (evOk(c.ok) ? "ok" : "warn")}>
                {c.event} · {evOk(c.ok) ? t("admOk") : t("admFail")} · {c.n}
              </span>
            ))}
            {counts.length === 0 && <span className="muted">{t("admNoEvents")}</span>}
          </div>
          <div className="table-scroll">
            <table className="eng-table">
              <thead>
                <tr><th>{t("admColWhen")}</th><th>{t("admColEvent")}</th><th>{t("loginEmail")}</th><th>{t("admColDetail")}</th></tr>
              </thead>
              <tbody>
                {eventsFiltered.map((ev) => (
                  <tr key={ev.id}>
                    <td>{fmtDate(ev.occurred_at, locale)}</td>
                    <td><span className={"badge " + (evOk(ev.ok) ? "ok" : "warn")}>{ev.event}</span></td>
                    <td>{ev.email || "—"}</td>
                    <td>{ev.detail || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "audit" && (
        <>
          <div className="row wrap" style={{ marginBottom: 10 }}>
            <input type="text" style={{ width: 180 }} placeholder={t("admAuditTable")}
              value={aTable} onChange={(e) => setATable(e.currentTarget.value)} />
            <input type="text" style={{ width: 120 }} placeholder={t("admAuditId")}
              value={aId} onChange={(e) => setAId(e.currentTarget.value.replace(/\D/g, ""))} />
          </div>
          <div className="table-scroll">
            <table className="eng-table">
              <thead>
                <tr><th>{t("admColWhen")}</th><th>{t("admColAction")}</th><th>{t("admAuditTable")}</th><th>ID</th><th>{t("admColActor")}</th><th></th></tr>
              </thead>
              <tbody>
                {auditFiltered.map((a) => (
                  <Fragment key={a.id}>
                    <tr>
                      <td>{fmtDate(a.occurred_at, locale)}</td>
                      <td><span className="badge">{a.action}</span></td>
                      <td>{a.table_name}</td>
                      <td>#{a.record_id}</td>
                      <td>{a.actor_user_id != null ? `#${a.actor_user_id}` : "—"}</td>
                      <td>
                        <button className="secondary" onClick={() => setOpenSnap(openSnap === a.id ? null : a.id)}>
                          {t("admSnapshot")}
                        </button>
                      </td>
                    </tr>
                    {openSnap === a.id && (
                      <tr>
                        <td colSpan={6}>
                          <pre style={{ whiteSpace: "pre-wrap", fontSize: "var(--fs-sm)", margin: 0 }}>
                            {JSON.stringify(a.snapshot, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
          {auditFiltered.length === 0 && <div className="muted" style={{ marginTop: 8 }}>{t("admNoAudit")}</div>}
        </>
      )}
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
  // Sessão iniciada (user/admin) — null = mostrar o login
  const [session, setSession] = useState<string | null>(() => {
    try {
      const raw = localStorage.getItem("upexnote-session");
      if (raw) return (JSON.parse(raw).profile as string) || null;
    } catch { /* sessão corrompida → login */ }
    localStorage.removeItem("upexnote-profile"); // chave da v0.12.0, obsoleta
    return null;
  });
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
      try { localStorage.setItem("upexnote-engines", raw); } catch { /* cache é best-effort */ }
    } catch (e) {
      setLoadError(String(e));
    }
  }

  useEffect(() => {
    // SWR: o seletor de motores pinta-se JÁ com a última lista guardada (o
    // worker demora segundos a arrancar a frio e deixava o campo vazio); o
    // load real corre em fundo e atualiza estado das chaves/motores novos.
    try {
      const cached = JSON.parse(localStorage.getItem("upexnote-engines") || "null");
      const list: Engine[] = cached?.engines || [];
      if (list.length) {
        setEngines(list);
        setEngineId((cur) => cur || list.find((e) => e.primary)?.id || list[0]?.id || "");
      }
    } catch { /* sem cache */ }
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
      await invoke("transcribe", { engine: selected.id, file, dest: dest.trim() || null, user: getSession()?.id ?? null });
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
  // A aba de Administração só existe para sessões admin (o worker revalida na
  // base de qualquer forma — isto é apresentação, não segurança).
  if (getSession()?.role === "admin") {
    navItems.push({ id: "admin", icon: <ShieldCheck size={16} strokeWidth={1.75} />, label: t("navAdmin") });
  }

  if (session === null) {
    return (
      <div className="shell">
        <Titlebar canBack={false} canFwd={false} onBack={() => {}} onFwd={() => {}} />
        <LoginGate onDone={setSession} />
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
          <SidebarProfile collapsed={collapsed} />
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
                  {dest ? (
                    <div className="engine-info">{t("trDestInfo", { dest })}</div>
                  ) : (
                    <div className="engine-info">{t("cloudHint")}</div>
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

          {getSession()?.role === "admin" && (
            <div className={"view-pane" + (view === "admin" ? "" : " hidden")}>
              <AdminView active={view === "admin"} />
            </div>
          )}

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
