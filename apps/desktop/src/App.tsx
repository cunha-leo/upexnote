import { createContext, Fragment, useContext, useEffect, useMemo, useRef, useState, type ClipboardEvent, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { getVersion } from "@tauri-apps/api/app";
import CodeMirror from "@uiw/react-codemirror";
import { PostgreSQL, sql as sqlLanguage } from "@codemirror/lang-sql";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorView } from "@codemirror/view";
import { tags } from "@lezer/highlight";
import type { Extension } from "@codemirror/state";
import { format as formatSql } from "sql-formatter";
import {
  Mic, LibraryBig, Settings, Palette, PanelLeftClose, PanelLeftOpen,
  Search, ArrowLeft, ArrowRight, Minus, Square, X, LogOut, ShieldCheck,
  Eye, EyeOff, CircleCheck, CircleX, MessageCircle, ChevronDown, ChevronRight, Pencil, Archive, Trash2,
  Users, Activity, FileText, BarChart3, LifeBuoy, RefreshCw, UserRound,
  Database, Table2, Columns3, KeyRound, LockKeyhole, Filter, ChevronsLeft, ChevronsRight, Plus, Play, Code2,
  Save, FolderOpen, ArchiveRestore, Clock3, Copy, Network, BookOpen,
} from "lucide-react";
import { LANGS, LOCALES, makeT, type Key as I18nKey, type Lang, type TFn } from "./i18n";
import ErDiagram, { type ErScope } from "./ErDiagram";
import DocumentReader, { type DocDetail, type DocRef } from "./DocumentReader";
import FONTS from "./fonts.json";
import "@fontsource/ibm-plex-mono/400.css";
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

type SecretValidation = "valid" | "invalid";
type SecretInputProps = {
  value: string;
  onChange: (value: string) => void;
  onPaste?: (event: ClipboardEvent<HTMLInputElement>) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLInputElement>) => void;
  placeholder?: string;
  autoComplete?: string;
  disabled?: boolean;
  validation?: SecretValidation;
  validationMessage?: string;
};

/**
 * Campo sensível compatível com a WebView2 desta máquina. O input permanece
 * type="text"; a máscara visual é ligada/desligada sem acionar o caminho
 * nativo de password/paste que já demonstrou instabilidade.
 */
function SecretInput({
  value, onChange, onPaste, onKeyDown, placeholder, autoComplete = "off",
  disabled = false, validation, validationMessage,
}: SecretInputProps) {
  const { t } = useLang();
  const [revealed, setRevealed] = useState(false);
  const revealLabel = revealed ? t("secretHide") : t("secretShow");
  useEffect(() => {
    if (!value) setRevealed(false);
  }, [value]);

  return (
    <div className="secret-field">
      <div className={`secret-input${validation ? ` is-${validation}` : ""}`}>
        <input
          type="text"
          className={revealed ? undefined : "pw-mask"}
          autoComplete={autoComplete}
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          placeholder={placeholder}
          value={value}
          disabled={disabled}
          aria-invalid={validation === "invalid" ? true : undefined}
          onChange={(e) => onChange(e.currentTarget.value)}
          onPaste={onPaste}
          onKeyDown={onKeyDown}
        />
        <div className="secret-input-actions">
          {validation === "valid" && (
            <span className="secret-validation valid" title={validationMessage} aria-label={validationMessage}>
              <CircleCheck size={17} aria-hidden="true" />
            </span>
          )}
          {validation === "invalid" && (
            <span className="secret-validation invalid" title={validationMessage} aria-label={validationMessage}>
              <CircleX size={17} aria-hidden="true" />
            </span>
          )}
          <button
            type="button"
            className="secret-toggle"
            aria-label={revealLabel}
            title={revealLabel}
            aria-pressed={revealed}
            disabled={disabled}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => setRevealed((current) => !current)}
          >
            {revealed ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
          </button>
        </div>
      </div>
      {validation && validationMessage && (
        <div className={`secret-feedback ${validation}`} role="status">
          {validation === "valid" ? <CircleCheck size={13} aria-hidden="true" /> : <CircleX size={13} aria-hidden="true" />}
          <span>{validationMessage}</span>
        </div>
      )}
    </div>
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

type FormatEngine = {
  id: string;
  label: string;
  info: string;
  key_name: string;
  key_set: boolean;
  cost_hora_brl: number | string | null;
};

type PreviewProfile = "detalhado" | "resumo_tecnico" | "estudo";

type LibraryOpenRequest = {
  transcriptionId: number;
  openPreviewComposer: boolean;
  nonce: number;
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

type View = "transcribe" | "library" | "notebooks" | "support" | "settings" | "admin";
type AdminSection = "users" | "activity" | "audit" | "telemetry" | "support" | "data-studio";

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
type LibDetail = LibItem & {
  source_path: string | null; problems: string[]; clean_text: string; edited_at: string | null;
  // ADF-01: documentos estruturados ja gerados a partir deste transcript.
  // Vem de library_item (aditivo) — instalacoes antigas podem nao trazer.
  documents?: DocRef[];
};

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

const PREVIEW_PROFILE_I18N: Record<PreviewProfile, I18nKey> = {
  detalhado: "docProfileDetalhado",
  resumo_tecnico: "docProfileResumo",
  estudo: "docProfileEstudo",
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
  first_name?: string | null;
  last_name?: string | null;
  auth_provider?: string | null;
  created_at?: string | null;
  last_login_at?: string | null;
  admin_token?: string;
  admin_expires_at?: string;
};

function getSession(): Session | null {
  try {
    const s = JSON.parse(localStorage.getItem("upexnote-session") || "null");
    if (s?.profile === "admin" && (!s.admin_token || !s.admin_expires_at
      || Date.parse(s.admin_expires_at) <= Date.now())) {
      localStorage.removeItem("upexnote-session");
      return null;
    }
    return s && s.profile ? (s as Session) : null;
  } catch {
    return null;
  }
}

function adminProof() {
  const s = getSession();
  return {
    adminEmail: s?.profile === "admin" ? s.email : null,
    adminToken: s?.profile === "admin" ? s.admin_token || null : null,
  };
}

function MfaSettingsCard() {
  const { t } = useLang();
  const session = getSession();
  const [enrolled, setEnrolled] = useState<boolean | null>(null);
  const [qr, setQr] = useState("");
  const [manualKey, setManualKey] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<"" | "status" | "enroll" | "confirm">("");
  const [message, setMessage] = useState("");

  async function refreshStatus() {
    if (session?.profile !== "admin" || !session.admin_token) return;
    setBusy("status");
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "validate",
        payload: JSON.stringify({
          email: session.email, elevation_token: session.admin_token,
        }),
      }));
      setEnrolled(Boolean(res.ok && res.valid && res.totp_enrolled));
    } catch {
      setMessage(t("mfaSettingsError"));
    } finally {
      setBusy("");
    }
  }

  useEffect(() => { void refreshStatus(); }, []);

  async function beginEnrollment() {
    if (session?.profile !== "admin" || !session.admin_token) return;
    setBusy("enroll"); setMessage("");
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "totp-enroll",
        payload: JSON.stringify({
          email: session.email, elevation_token: session.admin_token,
        }),
      }));
      if (!res.ok || !res.qr_data_url) throw new Error("invalid_response");
      setQr(res.qr_data_url);
      setManualKey(res.manual_key || "");
      setCode("");
    } catch {
      setMessage(t("mfaSettingsError"));
    } finally {
      setBusy("");
    }
  }

  async function confirmEnrollment() {
    if (session?.profile !== "admin" || !session.admin_token || !/^\d{6}$/.test(code)) {
      setMessage(t("loginErrCode")); return;
    }
    setBusy("confirm"); setMessage("");
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "totp-confirm",
        payload: JSON.stringify({
          email: session.email, elevation_token: session.admin_token, code,
        }),
      }));
      if (!res.ok) throw new Error("invalid_code");
      setEnrolled(true); setQr(""); setManualKey(""); setCode("");
      setMessage(t("mfaSettingsUpdated"));
    } catch {
      setMessage(t("loginMfaInvalid"));
    } finally {
      setBusy("");
    }
  }

  if (session?.profile !== "admin") return null;
  return (
    <section className="card">
      <h2>{t("mfaSettingsTitle")}</h2>
      <p className="engine-info">{t("mfaSettingsInfo")}</p>
      <div className="row wrap" style={{ alignItems: "center", marginBottom: 10 }}>
        <span className={"badge " + (enrolled ? "ok" : "warn")}>
          {busy === "status" || enrolled === null
            ? t("credChecking") : enrolled ? t("mfaSettingsOn") : t("mfaSettingsOff")}
        </span>
        {!qr && (
          <button className="secondary" onClick={beginEnrollment} disabled={busy !== ""}>
            {busy === "enroll" ? t("mfaSettingsStarting")
              : enrolled ? t("mfaSettingsReplace") : t("mfaSettingsSetup")}
          </button>
        )}
      </div>
      <p className="engine-info">{t("mfaSettingsFallback")}</p>
      {qr && (
        <div className="totp-enrollment totp-settings">
          <div className="muted">{t("mfaSettingsQrHint")}</div>
          <img className="totp-qr" src={qr} alt={t("loginMfaQrAlt")} />
          <div className="totp-manual">
            <span>{t("loginMfaManualKey")}</span>
            <button className="link-btn" onClick={() => navigator.clipboard.writeText(manualKey)}>
              {manualKey}
            </button>
          </div>
          <div className="field" style={{ width: "100%", marginBottom: 0 }}>
            <label>{t("loginMfaConfirmCode")}</label>
            <input
              type="text" inputMode="numeric" autoComplete="one-time-code" spellCheck={false}
              value={code} maxLength={6}
              onChange={(e) => setCode(e.currentTarget.value.replace(/\D/g, "").slice(0, 6))}
              onPaste={(e) => {
                e.preventDefault();
                setCode(e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6));
              }}
              onKeyDown={(e) => { if (e.key === "Enter") void confirmEnrollment(); }}
            />
          </div>
          <div className="row" style={{ width: "100%" }}>
            <button onClick={confirmEnrollment} disabled={busy !== "" || code.length !== 6}>
              {busy === "confirm" ? t("mfaSettingsConfirming") : t("loginMfaConfirmBtn")}
            </button>
            <button className="secondary" onClick={() => {
              setQr(""); setManualKey(""); setCode(""); setMessage("");
            }} disabled={busy !== ""}>{t("cancel")}</button>
          </div>
        </div>
      )}
      {message && <div className="login-success" role="status">{message}</div>}
    </section>
  );
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

function LibraryView({
  active,
  openRequest,
  onOpenRequestHandled,
}: {
  active: boolean;
  openRequest: LibraryOpenRequest | null;
  onOpenRequestHandled: () => void;
}) {
  const { t, locale } = useLang();
  const [summary, setSummary] = useState<LibSummary | null>(null);
  const [items, setItems] = useState<LibItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<LibDetail | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [docDetail, setDocDetail] = useState<DocDetail | null>(null);
  const [openingDocId, setOpeningDocId] = useState<number | null>(null);
  const [previewComposerOpen, setPreviewComposerOpen] = useState(false);
  const [formatEngines, setFormatEngines] = useState<FormatEngine[]>([]);
  const [formatEngineId, setFormatEngineId] = useState("");
  const [previewProfile, setPreviewProfile] = useState<PreviewProfile>("detalhado");
  const [formatEnginesLoading, setFormatEnginesLoading] = useState(false);
  const [formatEnginesError, setFormatEnginesError] = useState("");
  const [previewGenerating, setPreviewGenerating] = useState(false);
  const [previewStatus, setPreviewStatus] = useState("");
  const [previewValidationOk, setPreviewValidationOk] = useState<boolean | null>(null);
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
        search: searchTerm ?? null, user: getSession()?.id ?? null, ...adminProof(),
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
    setDocDetail(null);
    setEditing(false);
    setConfirmDel(false);
    setShowWarnings(false);
    setActionMsg("");
    setPreviewComposerOpen(false);
    setPreviewStatus("");
    setPreviewValidationOk(null);
  }

  /** Abre um documento estruturado ja gerado (so leitura, ADF-01 passo 2). */
  async function openDocument(id: number) {
    setOpeningDocId(id);
    setActionMsg("");
    try {
      const raw = await invoke<string>("document_item", {
        id, user: getSession()?.id ?? null, ...adminProof(),
      });
      const obj = JSON.parse(raw);
      if (obj.type === "document_item") {
        setDocDetail(obj.item as DocDetail);
      } else {
        setError(obj.message || t("docOpenFail"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setOpeningDocId(null);
    }
  }

  async function openItem(id: number) {
    setDocDetail(null);
    setOpeningId(id);
    setActionMsg("");
    try {
      const raw = await invoke<string>("library_item", {
        id, user: getSession()?.id ?? null, ...adminProof(),
      });
      const obj = JSON.parse(raw);
      if (obj.type === "library_item") {
        setDetail(obj.item);
        setEditing(false);
        setConfirmDel(false);
        setShowWarnings(false);
        setEditText(obj.item.clean_text);
        setPreviewStatus("");
        setPreviewValidationOk(null);
      } else {
        setError(obj.message || t("libOpenFail"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setOpeningId(null);
    }
  }

  async function loadFormatEngines() {
    if (formatEnginesLoading) return;
    setFormatEnginesLoading(true);
    setFormatEnginesError("");
    try {
      const raw = await invoke<string>("format_engines");
      const obj = JSON.parse(raw);
      if (obj.type !== "format_engines") {
        setFormatEnginesError(obj.message || t("previewEnginesFail"));
        return;
      }
      const list = (obj.engines || []) as FormatEngine[];
      setFormatEngines(list);
      setFormatEngineId((current) => current || list.find((engine) => engine.key_set)?.id || list[0]?.id || "");
    } catch (e) {
      setFormatEnginesError(String(e));
    } finally {
      setFormatEnginesLoading(false);
    }
  }

  async function openPreviewComposer() {
    setPreviewComposerOpen(true);
    setPreviewStatus("");
    setPreviewValidationOk(null);
    if (!formatEngines.length) await loadFormatEngines();
  }

  async function generatePreview() {
    if (!detail || previewGenerating) return;
    const engine = formatEngines.find((item) => item.id === formatEngineId);
    if (!engine?.key_set) return;
    setPreviewGenerating(true);
    setPreviewValidationOk(null);
    setPreviewStatus(t("previewStarting"));
    setError("");
    try {
      await invoke("document_generate", {
        transcriptionId: detail.id,
        engine: engine.id,
        profile: previewProfile,
        user: getSession()?.id ?? null,
      });
    } catch (e) {
      setPreviewGenerating(false);
      setPreviewStatus(t("previewGenerateFail", { err: String(e) }));
    }
  }

  useEffect(() => {
    const unlistenEvent = listen<string>("document://event", (event) => {
      let obj: any;
      try {
        obj = JSON.parse(event.payload);
      } catch {
        return;
      }
      if (obj.type === "start") {
        setPreviewStatus(t("previewStarting"));
      } else if (obj.type === "progress") {
        setPreviewStatus(obj.message || t("previewGenerating"));
      } else if (obj.type === "validation") {
        setPreviewValidationOk(Boolean(obj.ok));
        setPreviewStatus(obj.ok ? t("previewValidationOk") : t("previewValidationFail"));
      } else if (obj.type === "format_result") {
        setPreviewGenerating(false);
        setPreviewStatus(t("previewGenerated"));
        const documentId = Number(obj.document_id);
        const transcriptId = detail?.id;
        if (transcriptId) {
          void (async () => {
            await openItem(transcriptId);
            if (Number.isFinite(documentId) && documentId > 0) await openDocument(documentId);
          })();
        }
      } else if (obj.type === "error") {
        setPreviewGenerating(false);
        setPreviewStatus(t("previewGenerateFail", { err: obj.message || t("errFail") }));
      }
    });
    const unlistenDone = listen("document://done", () => setPreviewGenerating(false));
    return () => {
      unlistenEvent.then((dispose) => dispose());
      unlistenDone.then((dispose) => dispose());
    };
  }, [t, detail?.id]);

  useEffect(() => {
    if (!active || !openRequest) return;
    let cancelled = false;
    void (async () => {
      await openItem(openRequest.transcriptionId);
      if (!cancelled && openRequest.openPreviewComposer) await openPreviewComposer();
      if (!cancelled) onOpenRequestHandled();
    })();
    return () => { cancelled = true; };
    // A nonce representa uma solicitação deliberada, inclusive quando o ID se repete.
  }, [active, openRequest?.nonce]);

  async function saveEdit() {
    if (!detail) return;
    setSaving(true);
    setActionMsg("");
    try {
      const raw = await invoke<string>("library_update", {
        id: detail.id, text: editText, user: getSession()?.id ?? null, ...adminProof(),
      });
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
      const raw = await invoke<string>("library_delete", {
        id: detail.id, user: getSession()?.id ?? null, ...adminProof(),
      });
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
      const raw = await invoke<string>("library_ack", {
        id: detail.id, reopen, user: getSession()?.id ?? null, ...adminProof(),
      });
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

  const selectedFormatEngine = formatEngines.find((engine) => engine.id === formatEngineId) || null;

  // Vista do documento estruturado (so leitura) — tem precedencia sobre o
  // detalhe do transcript, e o "voltar" dela devolve ao transcript de origem.
  if (detail && docDetail) {
    return (
      <DocumentReader
        doc={docDetail}
        t={t}
        locale={locale}
        onBack={() => setDocDetail(null)}
        engineLabel={engLabel}
        fmtDate={fmtDate}
      />
    );
  }

  // Vista de detalhe (uma transcrição, com texto)
  if (detail) {
    return (
      <section className="card">
        <div className="detail-head">
          <button className="secondary" onClick={closeDetail} disabled={saving}>{t("back")}</button>
          <h2 className="detail-title" title={detail.source_filename || undefined}>
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
        {error && (
          <div className="key-warn" role="alert">
            {t("libReadFail", { err: error })}
          </div>
        )}
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
        <section className="preview-section" aria-labelledby="preview-section-title">
          <div className="preview-section-head">
            <div className="preview-section-copy">
              <span className="preview-kicker">{t("previewKicker")}</span>
              <h3 id="preview-section-title">{t("previewTitle")}</h3>
              <p>{detail.documents?.length ? t("previewHelpReady") : t("previewHelpEmpty")}</p>
            </div>
            <button
              className="secondary preview-create"
              onClick={() => previewComposerOpen ? setPreviewComposerOpen(false) : void openPreviewComposer()}
              disabled={previewGenerating}
              aria-expanded={previewComposerOpen}
            >
              <Plus size={15} aria-hidden="true" />
              {previewComposerOpen
                ? t("previewCancel")
                : detail.documents?.length ? t("previewCreateAnother") : t("previewCreate")}
            </button>
          </div>

          {detail.documents && detail.documents.length > 0 ? (
            <div className="preview-list">
              {detail.documents.map((documentRef) => (
                <button
                  key={documentRef.id}
                  className="preview-item"
                  onClick={() => openDocument(documentRef.id)}
                  disabled={openingDocId !== null || previewGenerating}
                  title={documentRef.title || undefined}
                >
                  <span className="preview-item-icon"><FileText size={17} aria-hidden="true" /></span>
                  <span className="preview-item-copy">
                    <strong>
                      {openingDocId === documentRef.id
                        ? t("docOpening")
                        : (documentRef.title || t("docTitleFallback", { id: documentRef.id }))}
                    </strong>
                    <span>
                      {documentRef.profile && t(PREVIEW_PROFILE_I18N[documentRef.profile as PreviewProfile] || "docProfileDetalhado")}
                      {documentRef.engine ? ` · ${documentRef.engine}` : ""}
                      {documentRef.created_at ? ` · ${fmtDate(documentRef.created_at, locale)}` : ""}
                    </span>
                  </span>
                  <span className="preview-readonly">{t("previewReadOnly")}</span>
                  <ChevronRight size={16} aria-hidden="true" />
                </button>
              ))}
            </div>
          ) : !previewComposerOpen && (
            <div className="preview-empty">
              <FileText size={18} aria-hidden="true" />
              <span>{t("previewEmpty")}</span>
            </div>
          )}

          {previewComposerOpen && (
            <div className="preview-composer">
              <div className="preview-composer-intro">
                <strong>{t("previewComposerTitle")}</strong>
                <span>{t("previewComposerHelp")}</span>
              </div>
              {formatEnginesLoading ? (
                <div className="status"><span className="spinner" /> {t("previewEnginesLoading")}</div>
              ) : (
                <div className="preview-composer-grid">
                  <label>
                    <span>{t("previewEngineLabel")}</span>
                    <select value={formatEngineId} onChange={(event) => setFormatEngineId(event.currentTarget.value)} disabled={previewGenerating}>
                      {formatEngines.map((engine) => (
                        <option key={engine.id} value={engine.id}>{engine.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>{t("previewProfileLabel")}</span>
                    <select value={previewProfile} onChange={(event) => setPreviewProfile(event.currentTarget.value as PreviewProfile)} disabled={previewGenerating}>
                      {(Object.keys(PREVIEW_PROFILE_I18N) as PreviewProfile[]).map((profile) => (
                        <option key={profile} value={profile}>{t(PREVIEW_PROFILE_I18N[profile])}</option>
                      ))}
                    </select>
                  </label>
                </div>
              )}
              {selectedFormatEngine && (
                <div className="preview-engine-info">
                  <span>{selectedFormatEngine.info}</span>
                  <strong>
                    {selectedFormatEngine.cost_hora_brl == null
                      ? t("previewCostUnknown")
                      : t("previewCostHour", {
                          cost: typeof selectedFormatEngine.cost_hora_brl === "number"
                            ? selectedFormatEngine.cost_hora_brl.toFixed(2)
                            : selectedFormatEngine.cost_hora_brl,
                        })}
                  </strong>
                </div>
              )}
              {selectedFormatEngine && !selectedFormatEngine.key_set && (
                <div className="key-warn" role="alert">{t("previewKeyMissing", { key: selectedFormatEngine.key_name })}</div>
              )}
              {formatEnginesError && <div className="key-warn" role="alert">{t("previewEnginesError", { err: formatEnginesError })}</div>}
              <div className="preview-composer-actions">
                <button
                  onClick={generatePreview}
                  disabled={previewGenerating || formatEnginesLoading || !selectedFormatEngine?.key_set}
                >
                  {previewGenerating ? <><span className="spinner" /> {t("previewGenerating")}</> : t("previewGenerate")}
                </button>
                <span>{t("previewPaidAction")}</span>
              </div>
              {previewStatus && (
                <div className={`preview-status${previewValidationOk === false ? " error" : ""}`} role="status">
                  {previewStatus}
                </div>
              )}
            </div>
          )}
        </section>
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

// ADF-02 fatia 3 (fundação `notebooks`, ver docs/NOTEBOOK_ARCHITECTURE.md
// secções 6, 7 e 14): árvore de coleções (pasta/projeto/caderno/secção) +
// nota vazia. Deliberadamente simples — sem editor rico (fatia 5), sem
// "Salvar no Caderno" a partir da prévia (fatia 4): só criar/abrir/editar/
// apagar uma nota de texto simples dentro da árvore.
type NBCollection = {
  id: number;
  parent_id: number | null;
  kind: "folder" | "project" | "notebook" | "section";
  title: string;
  position: number;
  created_at: string;
};
type NBNote = {
  id: number;
  collection_id: number;
  title: string | null;
  created_at: string;
  edited_at: string | null;
};
type NBNoteDetail = {
  id: number;
  collection_id: number;
  title: string | null;
  body: string | null;
};

function NotebooksView({ active }: { active: boolean }) {
  const { t } = useLang();
  const [collections, setCollections] = useState<NBCollection[]>([]);
  const [notes, setNotes] = useState<NBNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [busyCollectionId, setBusyCollectionId] = useState<number | null>(null);
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);
  const [noteDetail, setNoteDetail] = useState<NBNoteDetail | null>(null);
  const [noteTitle, setNoteTitle] = useState("");
  const [noteBody, setNoteBody] = useState("");
  const [noteLoading, setNoteLoading] = useState(false);
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteDirty, setNoteDirty] = useState(false);
  const [confirmDeleteNote, setConfirmDeleteNote] = useState(false);
  const [confirmDeleteCollection, setConfirmDeleteCollection] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      // Garante a coleção padrão antes de listar — primeira utilização nunca
      // mostra uma árvore vazia sem destino possível para a primeira nota.
      await invoke<string>("notebook_ensure_default", { user: getSession()?.id ?? null });
      const raw = await invoke<string>("notebook_tree", { user: getSession()?.id ?? null });
      const obj = JSON.parse(raw);
      if (obj.type === "error") {
        setError(obj.message);
      } else {
        setCollections(obj.collections || []);
        setNotes(obj.notes || []);
        setExpanded((prev) => {
          if (prev.size) return prev;
          return new Set((obj.collections || []).filter((c: NBCollection) => c.parent_id === null).map((c: NBCollection) => c.id));
        });
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (active && !loadedOnce) {
      setLoadedOnce(true);
      load();
    }
  }, [active, loadedOnce]);

  function toggleExpanded(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function openNote(id: number) {
    setSelectedNoteId(id);
    setNoteLoading(true);
    setNoteDetail(null);
    setConfirmDeleteNote(false);
    try {
      const raw = await invoke<string>("notebook_note_item", { id, user: getSession()?.id ?? null });
      const obj = JSON.parse(raw);
      if (obj.type === "notebook_note_item") {
        const item = obj.item as NBNoteDetail;
        setNoteDetail(item);
        setNoteTitle(item.title || "");
        setNoteBody(item.body || "");
        setNoteDirty(false);
      } else {
        setError(obj.message || t("nbOpenFail"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setNoteLoading(false);
    }
  }

  async function createNote(collectionId: number) {
    setBusyCollectionId(collectionId);
    setError("");
    try {
      const raw = await invoke<string>("notebook_note_create", {
        collectionId, title: null, user: getSession()?.id ?? null,
      });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        await load();
        await openNote(obj.id);
      } else {
        setError(obj.message || t("nbCreateFail"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyCollectionId(null);
    }
  }

  async function createCollection(parentId: number | null, kind: NBCollection["kind"]) {
    const title = window.prompt(t("nbNewCollectionPrompt"));
    if (!title || !title.trim()) return;
    setError("");
    try {
      const raw = await invoke<string>("notebook_collection_create", {
        title: title.trim(), kind, parentId, user: getSession()?.id ?? null,
      });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        if (parentId !== null) setExpanded((prev) => new Set(prev).add(parentId));
        await load();
      } else {
        setError(obj.message || t("nbCreateFail"));
      }
    } catch (e) {
      setError(String(e));
    }
  }

  async function deleteCollection(id: number) {
    setError("");
    try {
      const raw = await invoke<string>("notebook_collection_delete", { id, user: getSession()?.id ?? null });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        setConfirmDeleteCollection(null);
        if (selectedNoteId && notes.find((n) => n.id === selectedNoteId)?.collection_id === id) {
          setSelectedNoteId(null);
          setNoteDetail(null);
        }
        await load();
      } else {
        setError(obj.message || t("nbDeleteFail"));
      }
    } catch (e) {
      setError(String(e));
    }
  }

  async function saveNote() {
    if (!noteDetail) return;
    setNoteSaving(true);
    setError("");
    try {
      const raw = await invoke<string>("notebook_note_update", {
        id: noteDetail.id, title: noteTitle, body: noteBody, user: getSession()?.id ?? null,
      });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        setNoteDirty(false);
        setNoteDetail({ ...noteDetail, title: noteTitle, body: noteBody });
        await load();
      } else {
        setError(obj.message || t("nbSaveFail"));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setNoteSaving(false);
    }
  }

  async function deleteNote() {
    if (!noteDetail) return;
    setError("");
    try {
      const raw = await invoke<string>("notebook_note_delete", { id: noteDetail.id, user: getSession()?.id ?? null });
      const obj = JSON.parse(raw);
      if (obj.type === "ok") {
        setSelectedNoteId(null);
        setNoteDetail(null);
        setConfirmDeleteNote(false);
        await load();
      } else {
        setError(obj.message || t("nbDeleteFail"));
      }
    } catch (e) {
      setError(String(e));
    }
  }

  const childrenOf = (parentId: number | null) =>
    collections.filter((c) => c.parent_id === parentId).sort((a, b) => a.position - b.position || a.id - b.id);
  const notesOf = (collectionId: number) => notes.filter((n) => n.collection_id === collectionId);

  const KIND_LABEL: Record<NBCollection["kind"], string> = {
    folder: t("nbKindFolder"), project: t("nbKindProject"),
    notebook: t("nbKindNotebook"), section: t("nbKindSection"),
  };

  function renderCollection(c: NBCollection, depth: number) {
    const kids = childrenOf(c.id);
    const items = notesOf(c.id);
    const isOpen = expanded.has(c.id);
    return (
      <div key={c.id} className="nb-node" style={{ marginLeft: depth * 14 }}>
        <div className="nb-node-row">
          <button className="nb-node-toggle" onClick={() => toggleExpanded(c.id)} title={isOpen ? t("nbCollapse") : t("nbExpand")}>
            {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
          <span className="nb-node-title">{c.title}</span>
          <span className="nb-node-kind">{KIND_LABEL[c.kind]}</span>
          <span className="nb-node-actions">
            <button className="nb-icon-btn" title={t("nbNewNote")} disabled={busyCollectionId === c.id}
              onClick={() => createNote(c.id)}><Plus size={13} /></button>
            <button className="nb-icon-btn" title={t("nbNewSubcollection")}
              onClick={() => createCollection(c.id, "section")}><FolderOpen size={13} /></button>
            <button className="nb-icon-btn nb-icon-danger" title={t("nbDeleteCollection")}
              onClick={() => setConfirmDeleteCollection(c.id)}><Trash2 size={13} /></button>
          </span>
        </div>
        {confirmDeleteCollection === c.id && (
          <div className="nb-confirm" style={{ marginLeft: 20 }}>
            <span>{t("nbDeleteCollectionConfirm")}</span>
            <button className="btn-danger-solid" onClick={() => deleteCollection(c.id)}>{t("nbDelete")}</button>
            <button onClick={() => setConfirmDeleteCollection(null)}>{t("cancel")}</button>
          </div>
        )}
        {isOpen && (
          <div className="nb-node-children">
            {items.map((n) => (
              <button key={n.id} className={"nb-note-row" + (selectedNoteId === n.id ? " active" : "")}
                style={{ marginLeft: (depth + 1) * 14 }} onClick={() => openNote(n.id)}>
                <StickyNoteIcon />
                <span>{n.title || t("nbUntitled")}</span>
              </button>
            ))}
            {kids.map((k) => renderCollection(k, depth + 1))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="nb-workspace">
      <div className="nb-sidebar">
        <div className="nb-sidebar-header">
          <h3>{t("navNotebooks")}</h3>
          <button className="nb-icon-btn" title={t("nbNewCollection")} onClick={() => createCollection(null, "notebook")}>
            <Plus size={14} />
          </button>
        </div>
        {loading && !collections.length ? (
          <div className="nb-loading">{t("nbLoading")}</div>
        ) : error && !collections.length ? (
          <div className="nb-error">{error}</div>
        ) : !collections.length ? (
          <div className="nb-empty">{t("nbEmpty")}</div>
        ) : (
          <div className="nb-tree">{childrenOf(null).map((c) => renderCollection(c, 0))}</div>
        )}
      </div>
      <div className="nb-editor">
        {error && <div className="nb-error">{error}</div>}
        {!selectedNoteId ? (
          <div className="nb-empty nb-editor-empty">{t("nbSelectNote")}</div>
        ) : noteLoading ? (
          <div className="nb-loading">{t("nbLoading")}</div>
        ) : noteDetail ? (
          <div className="nb-note-editor">
            <input
              className="nb-note-title-input"
              value={noteTitle}
              placeholder={t("nbNoteTitlePlaceholder")}
              onChange={(e) => { setNoteTitle(e.target.value); setNoteDirty(true); }}
            />
            <textarea
              className="nb-note-body-input"
              value={noteBody}
              onChange={(e) => { setNoteBody(e.target.value); setNoteDirty(true); }}
            />
            <div className="nb-note-editor-actions">
              <button disabled={!noteDirty || noteSaving} onClick={saveNote}>
                {noteSaving ? t("nbSaving") : t("nbSave")}
              </button>
              {!confirmDeleteNote ? (
                <button className="btn-danger" onClick={() => setConfirmDeleteNote(true)}>{t("nbDeleteNote")}</button>
              ) : (
                <>
                  <span>{t("nbDeleteNoteConfirm")}</span>
                  <button className="btn-danger-solid" onClick={deleteNote}>{t("nbDelete")}</button>
                  <button onClick={() => setConfirmDeleteNote(false)}>{t("cancel")}</button>
                </>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function StickyNoteIcon() {
  return <FileText size={13} />;
}

type StorageSettings = {
  storage_dir: string;
  storage_dir_custom: boolean;
  default_storage_dir: string;
  organize_by_day_engine: boolean;
  storage_mode?: "local" | "vps";
  vps_configured?: boolean;
  telemetry_consent?: boolean;
  telemetry_consent_set?: boolean;
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
      <div className="field">
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={!!s?.telemetry_consent} disabled={busy || !s}
            onChange={(e) => apply({ telemetryConsent: e.currentTarget.checked }, t("savedTick"))} style={{ width: "auto" }} />
          <span>{t("telemetryOptIn")}</span>
        </label>
        <div className="engine-info">{t("telemetryInfo")}</div>
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
            <SecretInput
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
              onChange={(value) => setInputs((i) => ({ ...i, [c.name]: value }))}
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
type AccountUser = {
  id: number; user_id: string; email: string; role: string;
  first_name?: string | null; last_name?: string | null;
  auth_provider?: string | null; created_at?: string | null; last_login_at?: string | null;
};
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
  const [screen, setScreen] = useState<
    "login" | "create" | "resetRequest" | "resetVerify" | "resetComplete" |
    "adminMfa" | "adminTotpEnroll" | "precad" | "welcome"
  >("login");
  // Conta acabada de criar, à espera do ecrã de boas-vindas (orientações)
  const [pendingUser, setPendingUser] = useState<AccountUser | null>(null);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [pendingAdminUser, setPendingAdminUser] = useState<AccountUser | null>(null);
  const [adminFactor, setAdminFactor] = useState<"email" | "totp">("email");
  const [adminToken, setAdminToken] = useState("");
  const [adminTokenExpires, setAdminTokenExpires] = useState(0);
  const [totpQr, setTotpQr] = useState("");
  const [totpManualKey, setTotpManualKey] = useState("");
  const [userId, setUserId] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [avail, setAvail] = useState<{ available: boolean; suggestions: string[] } | null>(null);
  const [oauthPending, setOauthPending] = useState<OauthPayload | null>(null);
  const [oauthMsg, setOauthMsg] = useState("");
  const [ghCode, setGhCode] = useState("");
  const [busy, setBusy] = useState<"" | "form" | "admin" | "google" | "github">("");
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");

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

  function finish(
    profile: "user" | "admin", user?: AccountUser | null,
    elevationToken?: string, expiresIn?: number,
  ) {
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
        first_name: user?.first_name || null,
        last_name: user?.last_name || null,
        auth_provider: user?.auth_provider || null,
        created_at: user?.created_at || null,
        last_login_at: user?.last_login_at || null,
        admin_token: profile === "admin" ? elevationToken : undefined,
        admin_expires_at: profile === "admin" && expiresIn
          ? new Date(Date.now() + expiresIn * 1000).toISOString() : undefined,
      })
    );
    onDone(profile);
  }

  // Fluxo admin: a credencial digitada segue DENTRO do payload de login/registo
  // e o worker eleva no MESMO processo (identidade + prova numa só ida à base
  // — dois spawns sequenciais duplicavam a latência; 2026-07-19).
  async function finishAdmin(user: AccountUser, token: string, expiresIn: number) {
    try { await invoke("set_settings", { storageMode: "vps" }); } catch { /* best-effort */ }
    finish("admin", user, token, expiresIn);
  }

  async function beginAdminMfa(user: AccountUser, preferEmail = false) {
    setBusy("admin"); setErr(""); setNotice("");
    setEmail(user.email);
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "challenge",
        payload: JSON.stringify({
          email: user.email, admin_secret: adminPwRef.current, prefer_email: preferEmail,
        }),
      }));
      if (!res.ok) { setErr(t("loginMfaService")); return; }
      setPendingAdminUser(user);
      setAdminFactor(res.factor === "totp" ? "totp" : "email");
      setResetCode("");
      setScreen("adminMfa");
      setNotice(res.factor === "totp" ? t("loginMfaTotpReady") : t("loginMfaEmailSent"));
    } catch {
      setErr(t("loginMfaService"));
    } finally {
      setBusy("");
    }
  }

  async function verifyAdminMfa() {
    if (!pendingAdminUser || !/^\d{6}$/.test(resetCode)) {
      setErr(t("loginErrCode")); return;
    }
    setBusy("form"); setErr(""); setNotice("");
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "verify",
        payload: JSON.stringify({ email: pendingAdminUser.email, code: resetCode }),
      }));
      if (!res.ok || !res.elevation_token) { setErr(t("loginMfaInvalid")); return; }
      if (res.factor === "email" && !res.totp_enrolled) {
        setAdminToken(res.elevation_token);
        setAdminTokenExpires(Number(res.expires_in) || 28800);
        try {
          const enrollment = JSON.parse(await invoke<string>("api_admin_factor", {
            op: "totp-enroll",
            payload: JSON.stringify({
              email: pendingAdminUser.email, elevation_token: res.elevation_token,
            }),
          }));
          if (enrollment.ok && enrollment.qr_data_url) {
            setTotpQr(enrollment.qr_data_url);
            setTotpManualKey(enrollment.manual_key || "");
            setResetCode("");
            setScreen("adminTotpEnroll");
            return;
          }
        } catch { /* e-mail já validou o 3.º fator; cadastro pode ser tentado depois */ }
      }
      await finishAdmin(pendingAdminUser, res.elevation_token, Number(res.expires_in) || 28800);
    } catch {
      setErr(t("loginMfaService"));
    } finally {
      setBusy("");
    }
  }

  async function confirmTotpEnrollment() {
    if (!pendingAdminUser || !adminToken || !/^\d{6}$/.test(resetCode)) {
      setErr(t("loginErrCode")); return;
    }
    setBusy("form"); setErr("");
    try {
      const res = JSON.parse(await invoke<string>("api_admin_factor", {
        op: "totp-confirm",
        payload: JSON.stringify({
          email: pendingAdminUser.email, elevation_token: adminToken, code: resetCode,
        }),
      }));
      if (!res.ok) { setErr(t("loginMfaInvalid")); return; }
      await finishAdmin(pendingAdminUser, adminToken, adminTokenExpires || 28800);
    } catch {
      setErr(t("loginMfaService"));
    } finally {
      setBusy("");
    }
  }

  function mapErr(code?: string): string {
    if (code === "email_taken") return t("loginErrEmailTaken");
    if (code === "user_id_taken") return t("loginErrUserIdTaken");
    if (code === "invalid_admin_credentials") return t("loginAdminFail");
    if (code === "not_admin") return t("loginAdminRoleRequired");
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
  async function completeOauth(obj: any) {
    processingRef.current = true;
    setGhCode("");
    setOauthMsg(t("loginFinishing"));
    try {
      const adm = targetRef.current === "admin";
      const raw = await invoke<string>("account", {
        op: "oauth-login", mode: adm ? "vps" : "local",
        payload: JSON.stringify(adm ? { ...obj, admin_secret: adminPwRef.current } : obj),
      });
      const res = JSON.parse(raw);
      if (res.ok && !res.new) {
        if (adm) { await beginAdminMfa(res.user); return; }
        try { await invoke("set_settings", { storageMode: "local" }); } catch { /* best-effort */ }
        finish("user", res.user);
        return;
      }
      if (res.ok && res.new) {
        processingRef.current = false;
        setBusy(""); setOauthMsg("");
        setOauthPending(obj as OauthPayload);
        setEmail(obj.email || "");
        setFirstName(obj.first_name || "");
        setLastName(obj.last_name || "");
        setUserId((obj.email || "").split("@")[0].replace(/[^a-z0-9._-]/gi, "").toLowerCase());
        setErr(""); setScreen("precad");
        return;
      }
      processingRef.current = false;
      setBusy(""); setOauthMsg("");
      setErr(res.error === "invalid_admin_credentials" ? t("loginAdminFail")
        : res.error === "not_admin" ? t("loginAdminRoleRequired") : t("loginErrWrong"));
    } catch {
      processingRef.current = false;
      setBusy(""); setOauthMsg(""); setErr(t("loginErrWrong"));
    }
  }
  useEffect(() => {
    const unEvent = listen<string>("oauth://event", async (ev) => {
      let obj: any;
      try { obj = JSON.parse(ev.payload); } catch { return; }
      if (obj.type === "progress") {
        setOauthMsg(obj.message || t("loginOauthWaiting"));
        if (obj.user_code) setGhCode(obj.user_code);
      } else if (obj.type === "oauth") {
        await completeOauth(obj);
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
    processingRef.current = false;
    try {
      if (provider === "google") {
        const raw = await invoke<string>("oauth_google");
        const lines = raw.trim().split(/\r?\n/).filter(Boolean);
        const obj = JSON.parse(lines[lines.length - 1] || "");
        if (obj.type === "oauth") await completeOauth(obj);
        else throw new Error("OAuth Google sem resultado válido");
        return;
      }
      await invoke("oauth_start", { provider });
    } catch {
      processingRef.current = false;
      setBusy(""); setOauthMsg(""); setErr(t("loginErrWrong"));
    }
  }

  async function submit() {
    setErr("");
    const mail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return setErr(t("loginErrEmail"));
    if (screen === "create") {
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
          await beginAdminMfa(res.user);
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

  async function requestPasswordReset() {
    setErr(""); setNotice("");
    const mail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail)) return setErr(t("loginErrEmail"));
    setBusy("form");
    try {
      const res = JSON.parse(await invoke<string>("api_reset", {
        op: "request", payload: JSON.stringify({ email: mail }),
      }));
      if (!res.ok) return setErr(t("loginResetService"));
      setEmail(mail);
      setResetCode("");
      setScreen("resetVerify");
      setNotice(t("loginResetSent"));
    } catch {
      setErr(t("loginResetService"));
    } finally {
      setBusy("");
    }
  }

  async function verifyPasswordReset() {
    setErr(""); setNotice("");
    if (!/^\d{6}$/.test(resetCode)) return setErr(t("loginErrCode"));
    setBusy("form");
    try {
      const res = JSON.parse(await invoke<string>("api_reset", {
        op: "verify",
        payload: JSON.stringify({ email: email.trim().toLowerCase(), code: resetCode }),
      }));
      if (!res.ok || !res.reset_token) return setErr(t("loginResetInvalid"));
      setResetToken(res.reset_token);
      setPw(""); setPw2("");
      setScreen("resetComplete");
    } catch {
      setErr(t("loginResetService"));
    } finally {
      setBusy("");
    }
  }

  async function completePasswordReset() {
    setErr(""); setNotice("");
    if (pw.length < 8) return setErr(t("loginResetPwShort"));
    if (pw !== pw2) return setErr(t("loginErrPwMatch"));
    setBusy("form");
    try {
      const res = JSON.parse(await invoke<string>("api_reset", {
        op: "complete",
        payload: JSON.stringify({
          email: email.trim().toLowerCase(), reset_token: resetToken, new_password: pw,
        }),
      }));
      if (!res.ok) return setErr(t("loginResetInvalid"));
      setPw(""); setPw2(""); setResetCode(""); setResetToken("");
      setScreen("login");
      setNotice(t("loginResetDone"));
    } catch {
      setErr(t("loginResetService"));
    } finally {
      setBusy("");
    }
  }

  function primarySubmit() {
    if (screen === "resetRequest") return requestPasswordReset();
    if (screen === "resetVerify") return verifyPasswordReset();
    if (screen === "resetComplete") return completePasswordReset();
    if (screen === "adminMfa") return verifyAdminMfa();
    if (screen === "adminTotpEnroll") return confirmTotpEnrollment();
    return submit();
  }

  function maskedPaste(setter: (v: string) => void) {
    return (e: ClipboardEvent<HTMLInputElement>) => {
      e.preventDefault();
      setter(e.clipboardData.getData("text"));
    };
  }

  const passwordMinimum = screen === "resetComplete" ? 8 : 6;
  const passwordStarted = pw.length > 0;
  const passwordValid = pw.length >= passwordMinimum;
  const confirmationStarted = pw2.length > 0;
  const confirmationValid = confirmationStarted && pw2 === pw;
  const formBusyLabel = screen === "login" ? t("loginSigningIn")
    : screen === "resetRequest" ? t("loginResetRequestBusy")
    : screen === "resetVerify" ? t("loginResetVerifyBusy")
    : screen === "resetComplete" ? t("loginResetCompleteBusy")
    : screen === "adminMfa" ? t("loginMfaVerifyBusy")
    : screen === "adminTotpEnroll" ? t("loginMfaEnrollBusy")
    : screen === "create" ? t("loginCreating") : t("loginChecking");

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
            : screen === "resetComplete" ? t("loginResetNewTitle")
            : screen === "adminMfa" ? t("loginMfaTitle")
            : screen === "adminTotpEnroll" ? t("loginMfaEnrollTitle")
            : screen === "resetRequest" || screen === "resetVerify" ? t("loginResetTitle")
            : target === "admin" ? t("loginAdminTitle") : t("loginTitle")}
        </h1>
        {target === "admin" && (screen === "login" || screen === "create") && (
          <div className="field" style={{ marginBottom: 12 }}>
            <label>{t("loginAdminPw")}</label>
            <SecretInput
              value={adminPw}
              onChange={setAdminPw}
              onPaste={maskedPaste(setAdminPw)}
            />
            <div className="engine-info">{t("loginAdminHint")}</div>
          </div>
        )}
        {(screen === "login" || screen === "create") && (
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
        {screen === "resetRequest" && <div className="muted" style={{ textAlign: "left" }}>{t("loginResetInfo")}</div>}
        {screen === "resetVerify" && <div className="muted" style={{ textAlign: "left" }}>{t("loginResetCodeHint")}</div>}
        {screen === "adminMfa" && (
          <div className="muted" style={{ textAlign: "left" }}>
            {adminFactor === "totp" ? t("loginMfaTotpHint") : t("loginMfaEmailHint")}
          </div>
        )}
        {screen === "adminTotpEnroll" && (
          <div className="totp-enrollment">
            <div className="muted">{t("loginMfaEnrollHint")}</div>
            <img className="totp-qr" src={totpQr} alt={t("loginMfaQrAlt")} />
            <div className="totp-manual">
              <span>{t("loginMfaManualKey")}</span>
              <button className="link-btn" onClick={() => navigator.clipboard.writeText(totpManualKey)}>
                {totpManualKey}
              </button>
            </div>
          </div>
        )}
        <div className="field" style={{ marginBottom: 10 }}>
          <label>{t("loginEmail")}</label>
          <input
            type="text" autoComplete="off" spellCheck={false}
            value={email}
            readOnly={screen === "precad" || screen === "resetVerify" || screen === "resetComplete"
              || screen === "adminMfa" || screen === "adminTotpEnroll"}
            onChange={(e) => setEmail(e.currentTarget.value)}
            onKeyDown={(e) => { if (e.key === "Enter") primarySubmit(); }}
          />
        </div>
        {(screen === "resetVerify" || screen === "adminMfa" || screen === "adminTotpEnroll") && (
          <div className="field" style={{ marginBottom: 10 }}>
            <label>{screen === "adminMfa" && adminFactor === "totp"
              ? t("loginMfaTotpCode") : screen === "adminTotpEnroll"
                ? t("loginMfaConfirmCode") : t("loginResetCode")}</label>
            <input
              type="text" inputMode="numeric" autoComplete="one-time-code" spellCheck={false}
              value={resetCode}
              maxLength={6}
              onChange={(e) => setResetCode(e.currentTarget.value.replace(/\D/g, "").slice(0, 6))}
              onPaste={(e) => {
                e.preventDefault();
                setResetCode(e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6));
              }}
              onKeyDown={(e) => { if (e.key === "Enter") primarySubmit(); }}
            />
          </div>
        )}
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
        {(screen === "login" || screen === "create" || screen === "resetComplete") && (
          <div className="field" style={{ marginBottom: 10 }}>
            <label>{t("loginPassword")}</label>
            <SecretInput
              key={`password-${screen}`}
              value={pw}
              onChange={setPw}
              onPaste={maskedPaste(setPw)}
              onKeyDown={(e) => { if (e.key === "Enter") primarySubmit(); }}
              validation={screen !== "login" && passwordStarted ? (passwordValid ? "valid" : "invalid") : undefined}
              validationMessage={screen !== "login" && passwordStarted
                ? passwordValid ? t("loginPwPolicyOk")
                  : screen === "resetComplete" ? t("loginResetPwShort") : t("loginErrPwShort")
                : undefined}
            />
          </div>
        )}
        {(screen === "create" || screen === "resetComplete") && (
          <div className="field" style={{ marginBottom: 10 }}>
            <label>{t("loginPasswordConfirm")}</label>
            <SecretInput
              key={`confirmation-${screen}`}
              value={pw2}
              onChange={setPw2}
              onPaste={maskedPaste(setPw2)}
              onKeyDown={(e) => { if (e.key === "Enter") primarySubmit(); }}
              validation={confirmationStarted ? (confirmationValid ? "valid" : "invalid") : undefined}
              validationMessage={confirmationStarted
                ? confirmationValid ? t("loginPwMatchOk") : t("loginErrPwMatch")
                : undefined}
            />
          </div>
        )}
        {notice && <div className="login-success" role="status">{notice}</div>}
        {err && <div className="key-warn" style={{ marginBottom: 8 }}>{err}</div>}
        <button className="login-primary" style={{ width: "100%" }} onClick={primarySubmit} disabled={busy !== ""}>
          {busy === "form" ? <><span className="spinner" /> {formBusyLabel}</> : screen === "login" ? t("loginBtn")
            : screen === "resetRequest" ? t("loginResetRequestBtn")
            : screen === "resetVerify" ? t("loginResetVerifyBtn")
            : screen === "resetComplete" ? t("loginResetCompleteBtn")
            : screen === "adminMfa" ? t("loginMfaVerifyBtn")
            : screen === "adminTotpEnroll" ? t("loginMfaConfirmBtn")
            : screen === "precad" ? t("loginFinish") : t("loginCreateBtn")}
        </button>
        {screen === "adminTotpEnroll" && pendingAdminUser && (
          <button
            className="secondary" style={{ width: "100%", marginTop: 8 }} disabled={busy !== ""}
            onClick={() => finishAdmin(pendingAdminUser, adminToken, adminTokenExpires || 28800)}
          >{t("loginMfaSkip")}</button>
        )}
        <div className="login-links">
          {screen === "login" ? (
            <>
              {target === "admin" && (
                <button className="link-btn" onClick={() => {
                  setErr(""); setNotice(""); setPw(""); setAdminPw(""); setScreen("resetRequest");
                }}>{t("loginForgot")}</button>
              )}
              {target !== "admin" && (
                <button className="link-btn" onClick={() => { setErr(""); setNotice(""); setScreen("create"); }}>{t("loginNoAccount")}</button>
              )}
            </>
          ) : screen === "adminMfa" ? (
            <>
              {adminFactor === "totp" && pendingAdminUser && (
                <button className="link-btn" onClick={() => beginAdminMfa(pendingAdminUser, true)}>
                  {t("loginMfaUseEmail")}
                </button>
              )}
              {adminFactor === "email" && pendingAdminUser && (
                <button className="link-btn" onClick={() => beginAdminMfa(pendingAdminUser, true)}>
                  {t("loginMfaResend")}
                </button>
              )}
              <button className="link-btn" onClick={() => {
                setErr(""); setNotice(""); setResetCode(""); setPendingAdminUser(null); setScreen("login");
              }}>{t("loginBack")}</button>
            </>
          ) : screen === "resetRequest" || screen === "resetVerify" || screen === "resetComplete" ? (
            <button className="link-btn" onClick={() => {
              setErr(""); setNotice(""); setPw(""); setPw2("");
              setResetCode(""); setResetToken(""); setScreen("login");
            }}>{t("loginBack")}</button>
          ) : screen !== "precad" ? (
            <button className="link-btn" onClick={() => { setErr(""); setNotice(""); setScreen("login"); }}>{t("loginHaveAccount")}</button>
          ) : null}
        </div>
      </div>
      )}
      {screen !== "welcome" && screen !== "adminMfa" && screen !== "adminTotpEnroll" && (
        <button
          className="link-btn login-admin"
          onClick={() => {
            setErr(""); setNotice(""); setAdminPw(""); setScreen("login");
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

// Perfil na sidebar: identidade resumida no rodapé e modal informativo completo.
// O avatar permanece derivado da inicial; a estrutura fica pronta para foto futura
// sem inventar upload antes de existir um contrato de armazenamento.
function SidebarProfile({ collapsed }: { collapsed: boolean }) {
  const { t, locale } = useLang();
  const [sess, setSess] = useState<Session | null>(() => getSession());
  const [openProfile, setOpenProfile] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [profileError, setProfileError] = useState("");

  useEffect(() => {
    if (!sess?.id) return;
    const currentSession = sess;
    let cancelled = false;
    setLoadingProfile(true);
    invoke<string>("account", {
      op: "profile",
      payload: JSON.stringify({ id: currentSession.id }),
      mode: currentSession.mode,
    }).then((raw) => {
      if (cancelled) return;
      const response = JSON.parse(raw);
      if (!response.ok || !response.user) {
        setProfileError(t("profileLoadError"));
        return;
      }
      const next = { ...currentSession, ...response.user } as Session;
      setSess(next);
      localStorage.setItem("upexnote-session", JSON.stringify(next));
      setProfileError("");
    }).catch(() => {
      if (!cancelled) setProfileError(t("profileLoadError"));
    }).finally(() => {
      if (!cancelled) setLoadingProfile(false);
    });
    return () => { cancelled = true; };
  }, [sess?.id, sess?.mode, t]);

  useEffect(() => {
    if (!openProfile) return;
    const close = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpenProfile(false);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [openProfile]);

  if (!sess) return null;
  const fullName = [sess.first_name, sess.last_name].filter(Boolean).join(" ").trim();
  const displayName = fullName || sess.user_id || sess.email || t("profileFallback");
  const initial = (displayName[0] || "?").toUpperCase();
  const username = sess.user_id ? `@${sess.user_id}` : sess.email;
  const roleLabel = sess.role === "admin" ? t("profileRoleAdmin") : t("profileRoleUser");
  const footerRoleLabel = sess.role === "admin" ? "Admin" : roleLabel;
  const provider = sess.auth_provider === "google" ? "Google"
    : sess.auth_provider === "github" ? "GitHub"
      : t("profileProviderEmail");
  const logoutSession = sess;
  async function logout() {
    if (logoutSession.profile === "admin" && logoutSession.admin_token) {
      try {
        await invoke("api_admin_factor", {
          op: "revoke",
          payload: JSON.stringify({ email: logoutSession.email, elevation_token: logoutSession.admin_token }),
        });
      } catch { /* revogação também ocorrerá por expiração no servidor */ }
    }
    localStorage.removeItem("upexnote-session");
    clearLibCaches();
    window.location.reload();
  }
  return (
    <>
      <div className={"side-profile" + (collapsed ? " collapsed" : "")}>
        <button
          className="profile-trigger"
          onClick={() => setOpenProfile(true)}
          title={collapsed ? t("profileOpen") : undefined}
          aria-label={t("profileOpen")}
        >
          <span className="avatar">{initial}</span>
          {!collapsed && (
            <span className="sp-main">
              <span className="sp-name">{displayName}</span>
              <span className="sp-sub">{username}</span>
              <span className="sp-role">{footerRoleLabel}</span>
            </span>
          )}
        </button>
        {!collapsed && (
          <button className="tb-btn" onClick={logout} title={t("stoLogout")} aria-label={t("stoLogout")}>
            <LogOut size={15} strokeWidth={1.75} />
          </button>
        )}
      </div>
      {openProfile && (
        <div className="modal-overlay" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setOpenProfile(false);
        }}>
          <section className="modal-card profile-modal" role="dialog" aria-modal="true" aria-labelledby="profile-modal-title">
            <div className="profile-modal-head">
              <span className="profile-avatar-large">{initial}</span>
              <div>
                <span className="eyebrow">{t("profileAccount")}</span>
                <h2 id="profile-modal-title">{displayName}</h2>
                <p>{username}</p>
              </div>
              <button className="tb-btn" onClick={() => setOpenProfile(false)} title={t("profileClose")} aria-label={t("profileClose")}>
                <X size={18} />
              </button>
            </div>
            {loadingProfile && <div className="status"><span className="spinner" />{t("profileLoading")}</div>}
            {profileError && <div className="key-warn">{profileError}</div>}
            <div className="profile-facts">
              <div><span>{t("profileFullName")}</span><strong>{fullName || "—"}</strong></div>
              <div><span>{t("profileUsername")}</span><strong>{username || "—"}</strong></div>
              <div><span>{t("profileEmail")}</span><strong>{sess.email || "—"}</strong></div>
              <div><span>{t("profileRole")}</span><strong><span className="sp-role">{roleLabel}</span></strong></div>
              <div><span>{t("profileProvider")}</span><strong>{provider}</strong></div>
              <div><span>{t("profileStorage")}</span><strong>{sess.mode === "vps" ? t("stoModeVps") : t("stoModeLocal")}</strong></div>
              <div><span>{t("profileCreated")}</span><strong>{fmtDate(sess.created_at || null, locale)}</strong></div>
              <div><span>{t("profileLastLogin")}</span><strong>{fmtDate(sess.last_login_at || null, locale)}</strong></div>
            </div>
            <div className="profile-avatar-note"><UserRound size={16} /><span>{t("profileAvatarFuture")}</span></div>
          </section>
        </div>
      )}
    </>
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

type DataStudioColumn = {
  column_name: string; data_type: string; nullable: boolean; column_default: string | null;
  primary_key: boolean; ordinal: number; protected: boolean;
};
type DataStudioRelation = {
  column_name: string; target_schema: string; target_table: string;
  target_column: string; constraint_name: string;
};
type DataStudioIndex = { index_name: string; definition: string };
type DataStudioObject = {
  object_name: string; object_type: string; estimated_rows: number;
  columns: DataStudioColumn[]; relations: DataStudioRelation[]; indexes: DataStudioIndex[];
};
type DataStudioSchema = { name: string; objects: DataStudioObject[] };
type DataStudioSelection = { schema: string; object: DataStudioObject };
type DataStudioTab = "builder" | "data" | "structure" | "relations" | "indexes";
type DsCondition = { source: number; column: string; operator: string; value: string; connector: "and" | "or" };
type DsJoin = { schema: string; table: string; type: string; left_source: number; left_column: string; right_column: string };
type DsValue = { column: string; value: string };
type DsField = { source: number; column: string };
type DsDdlColumn = { name: string; type: string; nullable: boolean; primary: boolean };
type SqlThemeId = "midnight" | "postgres" | "dbeaver" | "dracula" | "solarized" | "github" | "paper" | "contrast";
type SqlFormatStyle = "standard" | "compact" | "expanded";
type SavedQuery = {
  id: number; name: string; description: string; category: string; sql_text: string;
  operation: string; parameter_names: string[]; archived_at?: string | null;
  created_at: string; updated_at: string; last_run_at?: string | null; run_count: number;
};
type SavedQueryHistory = {
  succeeded: boolean; operation: string; row_count: number; duration_ms: number;
  parameter_names: string[]; error_code?: string | null; executed_at: string;
};

const SQL_THEME_PALETTES: Record<SqlThemeId, {
  label: string; dark: boolean; bg: string; gutter: string; text: string; caret: string;
  keyword: string; string: string; number: string; type: string; name: string; comment: string; operator: string; selection: string;
}> = {
  midnight: { label: "Midnight", dark: true, bg: "#11131c", gutter: "#0c0e16", text: "#d8dee9", caret: "#ffb4ac", keyword: "#c792ea", string: "#c3e88d", number: "#f78c6c", type: "#82aaff", name: "#f07178", comment: "#697386", operator: "#89ddff", selection: "#33415c" },
  postgres: { label: "PostgreSQL Blue", dark: true, bg: "#102232", gutter: "#0b1925", text: "#d7e9f7", caret: "#f6c85f", keyword: "#64b5f6", string: "#9ccc65", number: "#ffb74d", type: "#80cbc4", name: "#ef9a9a", comment: "#7293a8", operator: "#81d4fa", selection: "#244b67" },
  dbeaver: { label: "DBeaver Dark", dark: true, bg: "#24282e", gutter: "#1d2025", text: "#d5d8dc", caret: "#ffffff", keyword: "#cc7832", string: "#6a8759", number: "#6897bb", type: "#ffc66d", name: "#9876aa", comment: "#808080", operator: "#a9b7c6", selection: "#3d4b5c" },
  dracula: { label: "Dracula", dark: true, bg: "#282a36", gutter: "#21222c", text: "#f8f8f2", caret: "#f8f8f0", keyword: "#ff79c6", string: "#f1fa8c", number: "#bd93f9", type: "#8be9fd", name: "#50fa7b", comment: "#6272a4", operator: "#ff79c6", selection: "#44475a" },
  solarized: { label: "Solarized Dark", dark: true, bg: "#002b36", gutter: "#00242d", text: "#839496", caret: "#eee8d5", keyword: "#859900", string: "#2aa198", number: "#d33682", type: "#b58900", name: "#268bd2", comment: "#586e75", operator: "#cb4b16", selection: "#073642" },
  github: { label: "GitHub Light", dark: false, bg: "#ffffff", gutter: "#f6f8fa", text: "#24292f", caret: "#0969da", keyword: "#cf222e", string: "#0a3069", number: "#0550ae", type: "#953800", name: "#8250df", comment: "#6e7781", operator: "#cf222e", selection: "#b6d7ff" },
  paper: { label: "Warm Paper", dark: false, bg: "#fbf7ef", gutter: "#f2eadc", text: "#3d3929", caret: "#b3522c", keyword: "#9c36b5", string: "#2b8a3e", number: "#e8590c", type: "#1971c2", name: "#c2255c", comment: "#8a8175", operator: "#495057", selection: "#ead9b8" },
  contrast: { label: "High Contrast", dark: true, bg: "#000000", gutter: "#080808", text: "#ffffff", caret: "#ffff00", keyword: "#00ffff", string: "#7fff00", number: "#ffbf00", type: "#ff69b4", name: "#ffffff", comment: "#a8a8a8", operator: "#ffff00", selection: "#264f78" },
};

function makeSqlTheme(id: SqlThemeId): Extension {
  const palette = SQL_THEME_PALETTES[id];
  return [
    EditorView.theme({
      "&": { color: palette.text, backgroundColor: palette.bg },
      ".cm-content": { caretColor: palette.caret },
      ".cm-cursor, .cm-dropCursor": { borderLeftColor: palette.caret },
      "&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection": { backgroundColor: palette.selection },
      ".cm-gutters": { backgroundColor: palette.gutter, color: palette.comment, border: "none" },
      ".cm-activeLine": { backgroundColor: `${palette.selection}55` },
      ".cm-activeLineGutter": { backgroundColor: `${palette.selection}88` },
      ".cm-tooltip": { backgroundColor: palette.gutter, color: palette.text, borderColor: palette.selection },
      ".cm-tooltip-autocomplete > ul > li[aria-selected]": { backgroundColor: palette.selection, color: palette.text },
    }, { dark: palette.dark }),
    syntaxHighlighting(HighlightStyle.define([
      { tag: [tags.keyword, tags.controlKeyword, tags.definitionKeyword], color: palette.keyword, fontWeight: "650" },
      { tag: [tags.string, tags.special(tags.string)], color: palette.string },
      { tag: [tags.number, tags.bool, tags.null], color: palette.number },
      { tag: [tags.typeName, tags.className], color: palette.type },
      { tag: [tags.variableName, tags.propertyName, tags.attributeName], color: palette.name },
      { tag: [tags.comment, tags.lineComment, tags.blockComment], color: palette.comment, fontStyle: "italic" },
      { tag: [tags.operator, tags.punctuation], color: palette.operator },
    ])),
  ];
}

function DataStudioWorkspace() {
  const { t } = useLang();
  const sess = getSession();
  const [schemas, setSchemas] = useState<DataStudioSchema[]>([]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [expandedObjects, setExpandedObjects] = useState<string[]>([]);
  const [selection, setSelection] = useState<DataStudioSelection | null>(null);
  const [tab, setTab] = useState<DataStudioTab>("builder");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [explorerCollapsed, setExplorerCollapsed] = useState(false);
  const [resultExpanded, setResultExpanded] = useState(false);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [resultColumns, setResultColumns] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [filterColumn, setFilterColumn] = useState("");
  const [filterOperator, setFilterOperator] = useState("contains");
  const [filterValue, setFilterValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [builderOp, setBuilderOp] = useState("select");
  const [builderFields, setBuilderFields] = useState<DsField[]>([]);
  const [builderJoins, setBuilderJoins] = useState<DsJoin[]>([]);
  const [builderConditions, setBuilderConditions] = useState<DsCondition[]>([]);
  const [builderValues, setBuilderValues] = useState<DsValue[]>([]);
  const [sortColumn, setSortColumn] = useState("");
  const [sortDirection, setSortDirection] = useState("asc");
  const [ddlName, setDdlName] = useState("");
  const [ddlType, setDdlType] = useState("text");
  const [createTableName, setCreateTableName] = useState("");
  const [createColumns, setCreateColumns] = useState<DsDdlColumn[]>([]);
  const [alterAction, setAlterAction] = useState("add_column");
  const [newName, setNewName] = useState("");
  const [plan, setPlan] = useState<{ sql: string; plan_hash: string; mutation: boolean } | null>(null);
  const [builderResult, setBuilderResult] = useState<{ columns: string[]; rows: Record<string, unknown>[]; affected?: number } | null>(null);
  const [studioMode, setStudioMode] = useState<"visual" | "sql" | "saved" | "diagram">("visual");
  const [diagramScope, setDiagramScope] = useState<ErScope>({ kind: "schema", schema: "public" });
  const [sqlText, setSqlText] = useState("SELECT *\nFROM public.engines\nORDER BY id ASC;");
  const [sqlTheme, setSqlTheme] = useState<SqlThemeId>("midnight");
  const [sqlFont, setSqlFont] = useState("Cascadia Code");
  const [sqlFontSize, setSqlFontSize] = useState(14);
  const [sqlKeywordCase, setSqlKeywordCase] = useState<"upper" | "lower" | "preserve">("upper");
  const [sqlFormatStyle, setSqlFormatStyle] = useState<SqlFormatStyle>("standard");
  const [showSqlSettings, setShowSqlSettings] = useState(false);
  const [sqlPlan, setSqlPlan] = useState<{ sql: string; plan_hash: string; mutation: boolean; operation: string } | null>(null);
  const [sqlResult, setSqlResult] = useState<{ columns: string[]; rows: Record<string, unknown>[]; affected?: number; truncated?: boolean } | null>(null);
  const [savedQueries, setSavedQueries] = useState<SavedQuery[]>([]);
  const [savedSearch, setSavedSearch] = useState("");
  const [includeArchivedQueries, setIncludeArchivedQueries] = useState(false);
  const [selectedSavedId, setSelectedSavedId] = useState<number | null>(null);
  const [savedDraft, setSavedDraft] = useState({ name: "", description: "", category: "General", sql: "" });
  const [savedParameters, setSavedParameters] = useState<Record<string, string>>({});
  const [savedPlan, setSavedPlan] = useState<{ plan_hash: string; mutation: boolean; operation: string } | null>(null);
  const [savedResult, setSavedResult] = useState<{ columns: string[]; rows: Record<string, unknown>[]; affected?: number; truncated?: boolean } | null>(null);
  const [savedHistory, setSavedHistory] = useState<SavedQueryHistory[]>([]);

  async function call(op: "data-catalog" | "data-table" | "data-query" | "data-sql" | "data-saved-queries", payload: Record<string, unknown> = {}) {
    const raw = await invoke<string>("admin", {
      op, mode: sess?.mode ?? null,
      payload: JSON.stringify({
        actor: sess?.id ?? null,
        admin_email: sess?.email || "",
        admin_token: sess?.admin_token || "",
        ...payload,
      }),
    });
    return JSON.parse(raw);
  }

  async function loadCatalog() {
    setBusy(true); setErr("");
    try {
      const result = await call("data-catalog");
      if (!result.ok) {
        setErr(result.error || t("dsLoadError"));
        return;
      }
      const next = result.schemas || [];
      setSchemas(next);
      setExpanded((current) => current.length ? current : next.slice(0, 2).map((schema: DataStudioSchema) => schema.name));
      if (selection) {
        const schema = next.find((item: DataStudioSchema) => item.name === selection.schema);
        const object = schema?.objects.find((item: DataStudioObject) => item.object_name === selection.object.object_name);
        if (object) setSelection({ schema: schema.name, object });
      }
    } catch (error) {
      setErr(String(error));
    } finally {
      setBusy(false);
    }
  }

  async function loadTable(target = selection, targetPage = page) {
    if (!target) return;
    setBusy(true); setErr("");
    try {
      const filters = filterColumn && (filterOperator === "is_null" || filterValue.trim())
        ? [{ column: filterColumn, operator: filterOperator, value: filterValue }]
        : [];
      const result = await call("data-table", {
        schema: target.schema, table: target.object.object_name,
        page: targetPage, page_size: 50, filters,
      });
      if (!result.ok) {
        setErr(result.error || t("dsLoadError"));
        return;
      }
      setRows(result.rows || []);
      setResultColumns(result.columns || []);
      setPage(result.page || targetPage);
      setHasMore(Boolean(result.has_more));
    } catch (error) {
      setErr(String(error));
    } finally {
      setBusy(false);
    }
  }

  function selectObject(schema: string, object: DataStudioObject) {
    const target = { schema, object };
    setSelection(target);
    setTab("builder");
    setPage(1);
    setFilterColumn("");
    setFilterValue("");
    setRows([]);
    setBuilderFields([]);
    setBuilderJoins([]);
    setBuilderConditions([]);
    setBuilderValues([]);
    setPlan(null);
    setBuilderResult(null);
    void loadTable(target, 1);
  }

  function handleExplorerObject(schema: string, object: DataStudioObject) {
    if (studioMode === "diagram") {
      setDiagramScope({ kind: "table", schema, table: object.object_name });
      return;
    }
    if (studioMode !== "visual") {
      const key = `${schema}.${object.object_name}`;
      setExpandedObjects((current) => current.includes(key)
        ? current.filter((item) => item !== key) : [...current, key]);
      return;
    }
    selectObject(schema, object);
  }

  const builderSources = useMemo(() => {
    if (!selection) return [];
    const base = [{ schema: selection.schema, object: selection.object }];
    for (const join of builderJoins) {
      const object = schemas.find((schema) => schema.name === join.schema)?.objects.find((item) => item.object_name === join.table);
      if (object) base.push({ schema: join.schema, object });
    }
    return base;
  }, [selection, builderJoins, schemas]);

  function builderPayload() {
    if (!selection) return {};
    return {
      operation: builderOp, schema: selection.schema,
      table: builderOp === "create_table" ? createTableName : selection.object.object_name,
      fields: builderFields, joins: builderJoins, conditions: builderConditions, values: builderValues,
      sort: sortColumn ? { source: 0, column: sortColumn, direction: sortDirection } : {},
      columns: createColumns, alter_action: alterAction, column: ddlName, new_name: newName, data_type: ddlType, limit: 100,
    };
  }

  async function previewBuilder() {
    setBusy(true); setErr(""); setPlan(null); setBuilderResult(null);
    try {
      const result = await call("data-query", builderPayload());
      if (!result.ok) setErr(result.error || t("dsLoadError"));
      else if (result.mutation) setPlan(result);
      else {
        const executed = await call("data-query", { ...builderPayload(), execute: true, plan_hash: result.plan_hash });
        if (!executed.ok) setErr(executed.error || t("dsLoadError"));
        else setBuilderResult({ columns: executed.columns || [], rows: executed.rows || [] });
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function executeBuilder() {
    if (!plan) return;
    setBusy(true); setErr("");
    try {
      const result = await call("data-query", { ...builderPayload(), execute: true, plan_hash: plan.plan_hash });
      if (!result.ok) setErr(result.error || t("dsLoadError"));
      else {
        setBuilderResult({ columns: result.columns || [], rows: result.rows || [], affected: result.affected });
        if (plan.mutation) { setPlan(null); await loadCatalog(); }
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function runSqlEditor() {
    if (!sqlText.trim()) return;
    setBusy(true); setErr(""); setSqlPlan(null); setSqlResult(null);
    try {
      const preview = await call("data-sql", { sql: sqlText });
      if (!preview.ok) setErr(preview.error || t("dsSqlError"));
      else if (preview.mutation) setSqlPlan(preview);
      else {
        const result = await call("data-sql", { sql: sqlText, execute: true });
        if (!result.ok) setErr(result.error || t("dsSqlError"));
        else setSqlResult({ columns: result.columns || [], rows: result.rows || [], truncated: Boolean(result.truncated) });
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function confirmSqlEditor() {
    if (!sqlPlan) return;
    setBusy(true); setErr("");
    try {
      const result = await call("data-sql", { sql: sqlText, execute: true, plan_hash: sqlPlan.plan_hash });
      if (!result.ok) setErr(result.error || t("dsSqlError"));
      else {
        setSqlResult({ columns: result.columns || [], rows: result.rows || [], affected: result.affected });
        setSqlPlan(null);
        await loadCatalog();
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function loadSavedQueries() {
    setBusy(true); setErr("");
    try {
      const result = await call("data-saved-queries", {
        action: "list", search: savedSearch, include_archived: includeArchivedQueries,
      });
      if (!result.ok) setErr(result.error || t("dsSavedLoadError"));
      else setSavedQueries(result.queries || []);
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  function newSavedQuery(sql = "") {
    setSelectedSavedId(null);
    setSavedDraft({ name: "", description: "", category: "General", sql: sql || "SELECT *\nFROM public.engines\nORDER BY id ASC;" });
    setSavedParameters({}); setSavedPlan(null); setSavedResult(null); setSavedHistory([]);
  }

  function openSavedQuery(item: SavedQuery) {
    setSelectedSavedId(item.id);
    setSavedDraft({ name: item.name, description: item.description, category: item.category, sql: item.sql_text });
    setSavedParameters(Object.fromEntries((item.parameter_names || []).map((name) => [name, ""])));
    setSavedPlan(null); setSavedResult(null);
    void loadSavedHistory(item.id);
  }

  async function saveSavedQuery() {
    setBusy(true); setErr("");
    try {
      const result = await call("data-saved-queries", {
        action: "save", id: selectedSavedId, name: savedDraft.name,
        description: savedDraft.description, category: savedDraft.category, sql: savedDraft.sql,
      });
      if (!result.ok) setErr(result.error || t("dsSavedSaveError"));
      else {
        setSelectedSavedId(result.id);
        setSavedParameters(Object.fromEntries((result.parameter_names || []).map((name: string) => [name, savedParameters[name] || ""])));
        await loadSavedQueries();
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function loadSavedHistory(id: number) {
    try {
      const result = await call("data-saved-queries", { action: "history", id });
      if (result.ok) setSavedHistory(result.history || []);
    } catch { setSavedHistory([]); }
  }

  async function runSavedQuery(confirm = false) {
    if (!selectedSavedId) return;
    setBusy(true); setErr(""); setSavedResult(null);
    try {
      const payload: Record<string, unknown> = { action: "run", id: selectedSavedId, parameters: savedParameters };
      if (confirm && savedPlan) { payload.execute = true; payload.plan_hash = savedPlan.plan_hash; }
      const preview = await call("data-saved-queries", payload);
      if (!preview.ok) setErr(preview.error || t("dsSavedRunError"));
      else if (preview.mutation && !confirm) setSavedPlan(preview);
      else if (!confirm) {
        const result = await call("data-saved-queries", { ...payload, execute: true });
        if (!result.ok) setErr(result.error || t("dsSavedRunError"));
        else {
          setSavedResult({ columns: result.columns || [], rows: result.rows || [], affected: result.affected, truncated: result.truncated });
          await loadSavedHistory(selectedSavedId); await loadSavedQueries();
        }
      } else {
        setSavedResult({ columns: preview.columns || [], rows: preview.rows || [], affected: preview.affected, truncated: preview.truncated });
        setSavedPlan(null); await loadSavedHistory(selectedSavedId); await loadSavedQueries();
      }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  async function archiveSavedQuery(action: "archive" | "restore" | "delete") {
    if (!selectedSavedId) return;
    if (action === "delete" && !window.confirm(t("dsDeleteSavedConfirm"))) return;
    setBusy(true); setErr("");
    try {
      const result = await call("data-saved-queries", { action, id: selectedSavedId });
      if (!result.ok) setErr(result.error || t("dsSavedSaveError"));
      else { newSavedQuery(); await loadSavedQueries(); }
    } catch (error) { setErr(String(error)); } finally { setBusy(false); }
  }

  function applySqlFormat() {
    try {
      const preset = {
        compact: { tabWidth: 2, expressionWidth: 120, linesBetweenQueries: 1 },
        standard: { tabWidth: 2, expressionWidth: 60, linesBetweenQueries: 1 },
        expanded: { tabWidth: 4, expressionWidth: 32, linesBetweenQueries: 2 },
      }[sqlFormatStyle];
      setSqlText(formatSql(sqlText, {
        language: "postgresql",
        keywordCase: sqlKeywordCase,
        ...preset,
      }));
      setErr("");
    } catch (error) {
      setErr(String(error));
    }
  }

  useEffect(() => { void loadCatalog(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (studioMode === "saved") void loadSavedQueries();
  }, [studioMode, includeArchivedQueries]); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredSchemas = useMemo(() => {
    const query = catalogSearch.trim().toLowerCase();
    if (!query) return schemas;
    return schemas.map((schema) => ({
      ...schema,
      objects: schema.objects.filter((object) =>
        `${schema.name}.${object.object_name}`.toLowerCase().includes(query)),
    })).filter((schema) => schema.objects.length);
  }, [schemas, catalogSearch]);
  const filterableColumns = selection?.object.columns.filter((column) => !column.protected) || [];
  const sqlSchema = useMemo(() => Object.fromEntries(schemas.flatMap((schema) =>
    schema.objects.flatMap((object) => {
      const columns = object.columns.filter((column) => !column.protected).map((column) => column.column_name);
      return [[`${schema.name}.${object.object_name}`, columns], [object.object_name, columns]];
    }))), [schemas]);
  const sqlExtensions = useMemo(() => [sqlLanguage({
    dialect: PostgreSQL,
    schema: sqlSchema,
    upperCaseKeywords: sqlKeywordCase === "upper",
  })], [sqlSchema, sqlKeywordCase]);
  const sqlThemeExtension = useMemo(() => makeSqlTheme(sqlTheme), [sqlTheme]);
  const currentSavedQuery = savedQueries.find((item) => item.id === selectedSavedId) || null;
  const savedParameterNames = useMemo(() => {
    const names: string[] = [];
    const pattern = /(^|[^:]):([a-z][a-z0-9_]{0,62})/gi;
    for (const match of savedDraft.sql.matchAll(pattern)) if (!names.includes(match[2])) names.push(match[2]);
    return names;
  }, [savedDraft.sql]);

  return <section className="card admin-workspace data-studio">
    <header className="workspace-head">
      <div>
        <span className="eyebrow">{t("navAdmin")}</span>
        <h2>{t("dsTitle")}</h2>
        <p className="muted ds-lead">{t("dsLead")}</p>
      </div>
      <div className="row workspace-actions">
        <span className="ds-connection"><LockKeyhole size={14} />{t("dsCentral")}<b>{t("dsReadOnly")}</b></span>
        <button className="secondary icon-button" onClick={loadCatalog} disabled={busy}>
          {busy ? <span className="spinner" /> : <RefreshCw size={16} />}<span>{t("libRefresh")}</span>
        </button>
      </div>
    </header>
    <div className="ds-mode-switch" role="tablist" aria-label={t("dsWorkspaceMode")}>
      <button className={studioMode === "visual" ? "active" : ""} onClick={() => setStudioMode("visual")}>
        <Table2 size={15} />{t("dsVisualMode")}
      </button>
      <button className={studioMode === "sql" ? "active" : ""} onClick={() => setStudioMode("sql")}>
        <Code2 size={15} />{t("dsSqlEditor")}
      </button>
      <button className={studioMode === "saved" ? "active" : ""} onClick={() => {
        setStudioMode("saved");
        setExplorerCollapsed(true);
        if (!selectedSavedId && !savedDraft.sql) newSavedQuery(sqlText);
      }}>
        <FolderOpen size={15} />{t("dsSavedQueries")}
      </button>
      <button className={studioMode === "diagram" ? "active" : ""} onClick={() => {
        setStudioMode("diagram"); setExplorerCollapsed(true);
        if (selection) setDiagramScope({ kind: "table", schema: selection.schema, table: selection.object.object_name });
      }}>
        <Network size={15} />{t("dsErDiagram")}
      </button>
    </div>
    {err && <div className="key-warn">{err}</div>}
    <div className={`ds-layout${explorerCollapsed ? " explorer-collapsed" : ""}${resultExpanded ? " result-expanded" : ""}`}>
      <aside className="ds-explorer">
        <div className="ds-pane-title"><Database size={16} /><strong>{t("dsExplorer")}</strong>
          <button className="icon-action" onClick={() => setExplorerCollapsed((value) => !value)}
            title={explorerCollapsed ? t("dsExpandExplorer") : t("dsCollapseExplorer")}>
            {explorerCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
        </div>
        <label className="queue-search ds-search">
          <Search size={15} /><input value={catalogSearch} onChange={(event) => setCatalogSearch(event.currentTarget.value)} placeholder={t("dsSearch")} />
        </label>
        <div className="ds-tree">
          {!schemas.length && busy && <div className="status"><span className="spinner" />{t("dsLoading")}</div>}
          {filteredSchemas.map((schema) => {
            const isOpen = expanded.includes(schema.name) || Boolean(catalogSearch);
            return <div className="ds-schema" key={schema.name}>
              <button onClick={() => setExpanded((current) => current.includes(schema.name)
                ? current.filter((item) => item !== schema.name) : [...current, schema.name])}>
                {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <Database size={14} /><strong>{schema.name}</strong><span>{schema.objects.length}</span>
              </button>
              {isOpen && <div className="ds-objects">{schema.objects.map((object) => {
                const objectKey = `${schema.name}.${object.object_name}`;
                const objectOpen = studioMode !== "visual" && expandedObjects.includes(objectKey);
                const visibleColumns = object.columns.filter((column) => !column.protected);
                return <div className="ds-object-node" key={object.object_name}>
                  <button
                    className={selection?.schema === schema.name && selection.object.object_name === object.object_name ? "active" : ""}
                    onClick={() => handleExplorerObject(schema.name, object)}
                    aria-expanded={studioMode !== "visual" ? objectOpen : undefined}>
                    {studioMode !== "visual" && (objectOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />)}
                    <Table2 size={14} /><span>{object.object_name}</span>
                    <small>{object.object_type === "view" ? "view" : object.estimated_rows.toLocaleString()}</small>
                  </button>
                  {objectOpen && <div className="ds-object-columns">
                    {visibleColumns.map((column) => <div key={column.column_name} title={`${column.column_name} · ${column.data_type}`}>
                      <Columns3 size={12} /><span>{column.column_name}</span><small>{column.data_type}</small>
                    </div>)}
                    {!visibleColumns.length && <p>{t("dsNoVisibleColumns")}</p>}
                  </div>}
                </div>;
              })}</div>}
            </div>;
          })}
          {!filteredSchemas.length && !busy && <p className="empty-queue">{t("dsNoObjects")}</p>}
        </div>
      </aside>
      <div className="ds-workspace">
        {studioMode === "diagram" ? <div className="ds-er-workspace">
          <header className="ds-er-head">
            <div><span className="eyebrow">DATA STUDIO</span><h3>{t("dsErDiagram")}</h3>
              <p>{t("dsErLead")}</p></div>
            <div className="ds-er-scope">
              <label><span>{t("dsDiagramScope")}</span><select value={diagramScope.kind}
                onChange={(event) => {
                  const kind = event.currentTarget.value;
                  if (kind === "schema") setDiagramScope({ kind: "schema", schema: schemas[0]?.name || "public" });
                  else if (kind === "table") {
                    const first = schemas[0]?.objects[0];
                    if (first) setDiagramScope({ kind: "table", schema: schemas[0].name, table: first.object_name });
                  } else if (currentSavedQuery) setDiagramScope({ kind: "query", label: currentSavedQuery.name, sql: currentSavedQuery.sql_text });
                }}>
                <option value="schema">{t("dsDiagramSchema")}</option>
                <option value="table">{t("dsDiagramTable")}</option>
                <option value="query" disabled={!currentSavedQuery}>{t("dsDiagramQuery")}</option>
              </select></label>
              {diagramScope.kind === "schema" && <label><span>{t("dsSchema")}</span><select value={diagramScope.schema}
                onChange={(event) => setDiagramScope({ kind: "schema", schema: event.currentTarget.value })}>
                {schemas.map((schema) => <option key={schema.name}>{schema.name}</option>)}</select></label>}
              {diagramScope.kind === "table" && <label><span>{t("dsTable")}</span><select
                value={`${diagramScope.schema}.${diagramScope.table}`}
                onChange={(event) => {
                  const [schema, ...parts] = event.currentTarget.value.split(".");
                  setDiagramScope({ kind: "table", schema, table: parts.join(".") });
                }}>
                {schemas.flatMap((schema) => schema.objects.map((object) =>
                  <option key={`${schema.name}.${object.object_name}`} value={`${schema.name}.${object.object_name}`}>{schema.name}.{object.object_name}</option>
                ))}</select></label>}
              {diagramScope.kind === "query" && <span className="status-pill">{diagramScope.label}</span>}
            </div>
          </header>
          <ErDiagram schemas={schemas} scope={diagramScope} labels={{
            findTable: t("dsFindTable"), columns: t("dsColumns"), horizontal: t("dsHorizontal"),
            vertical: t("dsVertical"), fit: t("dsFitDiagram"), noTables: t("dsNoDiagramTables"),
            noTablesHelp: t("dsNoDiagramTablesHelp"), tables: t("dsTables"), relations: t("dsRelations"),
            table: t("dsTable"), view: t("dsView"), primaryKey: t("dsPrimaryKey"),
            foreignKey: t("dsForeignKey"), notNull: t("dsNotNull"),
          }} />
        </div> : studioMode === "saved" ? <div className="ds-saved-workspace">
          <aside className="ds-saved-list">
            <header><div><span className="eyebrow">DATA STUDIO</span><h3>{t("dsSavedQueries")}</h3></div>
              <button className="icon-action" onClick={() => newSavedQuery()} title={t("dsNewSavedQuery")}><Plus size={16} /></button>
            </header>
            <label className="queue-search"><Search size={14} /><input value={savedSearch}
              onChange={(event) => setSavedSearch(event.currentTarget.value)}
              onKeyDown={(event) => { if (event.key === "Enter") void loadSavedQueries(); }}
              placeholder={t("dsSearchSaved")} /></label>
            <label className="ds-saved-archived"><input type="checkbox" checked={includeArchivedQueries}
              onChange={(event) => setIncludeArchivedQueries(event.currentTarget.checked)} />{t("dsShowArchived")}</label>
            <div className="ds-saved-items">
              {savedQueries.map((item) => <button key={item.id} className={selectedSavedId === item.id ? "active" : ""}
                onClick={() => openSavedQuery(item)}>
                <span><strong>{item.name}</strong><small>{item.category} · {item.operation.toUpperCase()}</small></span>
                <span>{item.archived_at && <ArchiveRestore size={13} />}<small>{item.run_count}</small></span>
              </button>)}
              {!savedQueries.length && !busy && <div className="ds-saved-empty"><FolderOpen size={24} /><p>{t("dsNoSavedQueries")}</p></div>}
            </div>
          </aside>
          <section className="ds-saved-detail">
            <header className="ds-saved-detail-head">
              <div><span className="eyebrow">{selectedSavedId ? t("dsSavedQuery") : t("dsNewSavedQuery")}</span>
                <h3>{savedDraft.name || t("dsUntitledQuery")}</h3></div>
              <div>
                <button className="secondary" onClick={() => newSavedQuery()}><Plus size={15} />{t("dsNew")}</button>
                <button onClick={saveSavedQuery} disabled={busy || !savedDraft.name.trim() || !savedDraft.sql.trim()}><Save size={15} />{t("dsSave")}</button>
              </div>
            </header>
            <div className="ds-saved-meta">
              <label><span>{t("dsQueryName")}</span><input maxLength={100} value={savedDraft.name}
                onChange={(event) => setSavedDraft({ ...savedDraft, name: event.currentTarget.value })} placeholder={t("dsQueryNamePlaceholder")} /></label>
              <label><span>{t("dsCategory")}</span><input maxLength={60} value={savedDraft.category}
                onChange={(event) => setSavedDraft({ ...savedDraft, category: event.currentTarget.value })} /></label>
              <label className="wide"><span>{t("dsDescription")}</span><input maxLength={500} value={savedDraft.description}
                onChange={(event) => setSavedDraft({ ...savedDraft, description: event.currentTarget.value })} placeholder={t("dsDescriptionPlaceholder")} /></label>
            </div>
            <div className="ds-saved-code">
              <CodeMirror value={savedDraft.sql} height="100%" theme={sqlThemeExtension} extensions={sqlExtensions}
                onChange={(value) => { setSavedDraft({ ...savedDraft, sql: value }); setSavedPlan(null); setSavedResult(null); }}
                basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: true, bracketMatching: true, autocompletion: true, closeBrackets: true }} />
            </div>
            {!!(currentSavedQuery?.parameter_names || savedParameterNames).length && <section className="ds-saved-parameters">
              <header><div><strong>{t("dsParameters")}</strong><span>{t("dsParametersHelp")}</span></div>
                <span className="status-pill">{(currentSavedQuery?.parameter_names || savedParameterNames).length}</span></header>
              <div>{(currentSavedQuery?.parameter_names || savedParameterNames).map((name) => <label key={name}>
                <span>:{name}</span><input value={savedParameters[name] || ""} onChange={(event) =>
                  setSavedParameters({ ...savedParameters, [name]: event.currentTarget.value })} placeholder={t("dsParameterValue")} />
              </label>)}</div>
            </section>}
            <footer className="ds-saved-actions">
              <div>
                {selectedSavedId && <button className="secondary" onClick={() => {
                  setDiagramScope({ kind: "query", label: savedDraft.name, sql: savedDraft.sql });
                  setStudioMode("diagram"); setExplorerCollapsed(true);
                }}><Network size={15} />{t("dsViewDiagram")}</button>}
                {selectedSavedId && <button className="secondary" onClick={() => void archiveSavedQuery(currentSavedQuery?.archived_at ? "restore" : "archive")}>
                  <ArchiveRestore size={15} />{currentSavedQuery?.archived_at ? t("dsRestore") : t("dsArchive")}</button>}
                {selectedSavedId && <button className="icon-action danger" onClick={() => void archiveSavedQuery("delete")} title={t("dsDelete")}><Trash2 size={15} /></button>}
              </div>
              <button onClick={() => void runSavedQuery()} disabled={busy || !selectedSavedId ||
                (currentSavedQuery?.parameter_names || []).some((name) => savedParameters[name] === undefined)}>
                {busy ? <span className="spinner" /> : <Play size={15} />}{t("dsRunSavedQuery")}</button>
              {savedPlan?.mutation && <button className="danger-button" onClick={() => void runSavedQuery(true)}>
                <Play size={15} />{t("dsConfirmExecute")}</button>}
            </footer>
            {savedResult && <div className="ds-builder-result ds-sql-result">
              <header className="ds-result-head"><div><strong>{t("dsQueryResult")}</strong><span>{savedResult.rows.length} {t("dsRows")}</span></div>
                <button className="secondary" onClick={() => navigator.clipboard.writeText([
                  savedResult.columns.join("\t"),
                  ...savedResult.rows.map((row) => savedResult.columns.map((column) => String(row[column] ?? "")).join("\t")),
                ].join("\n"))}><Copy size={14} />{t("dsCopyResult")}</button></header>
              {savedResult.affected !== undefined && <div className="notice">{t("dsAffected", { n: savedResult.affected })}</div>}
              {!!savedResult.columns.length && <div className="ds-data-scroll"><table className="ds-data-table"><thead><tr>{savedResult.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                <tbody>{savedResult.rows.map((row, index) => <tr key={index}>{savedResult.columns.map((column) => <td key={column}>{row[column] === null ? <i>NULL</i> : typeof row[column] === "object" ? JSON.stringify(row[column]) : String(row[column])}</td>)}</tr>)}</tbody></table></div>}
            </div>}
            {!!savedHistory.length && <section className="ds-saved-history"><header><Clock3 size={15} /><strong>{t("dsRecentRuns")}</strong></header>
              <div>{savedHistory.slice(0, 5).map((run, index) => <article key={`${run.executed_at}-${index}`}>
                <span className={run.succeeded ? "ok" : "error"}>{run.succeeded ? t("dsSucceeded") : t("dsFailed")}</span>
                <strong>{run.operation.toUpperCase()}</strong><span>{run.row_count} {t("dsRows")}</span><span>{run.duration_ms} ms</span><time>{new Date(run.executed_at).toLocaleString()}</time>
              </article>)}</div></section>}
          </section>
        </div> : studioMode === "sql" ? <div className="ds-sql-editor">
          <header className="ds-sql-head">
            <div><span className="eyebrow">POSTGRESQL</span><h3>{t("dsSqlEditor")}</h3><p>{t("dsSqlLead")}</p></div>
            <div className="ds-sql-status"><span className="status-pill">{t("dsAutocomplete")}</span><span className="status-pill">{t("dsSingleStatement")}</span></div>
          </header>
          <div className="ds-editor-toolbar">
            <span>{SQL_THEME_PALETTES[sqlTheme].label} · {sqlFont} · {sqlFontSize}px</span>
            <div>
              <button className="secondary" onClick={() => {
                setDiagramScope({ kind: "query", label: t("dsCurrentSql"), sql: sqlText });
                setStudioMode("diagram"); setExplorerCollapsed(true);
              }}>
                <Network size={15} />{t("dsViewDiagram")}
              </button>
              <button className="secondary" onClick={() => { newSavedQuery(sqlText); setStudioMode("saved"); setExplorerCollapsed(true); }}>
                <Save size={15} />{t("dsSaveQuery")}
              </button>
              <button className={`secondary${showSqlSettings ? " active" : ""}`} onClick={() => setShowSqlSettings((value) => !value)}
                aria-expanded={showSqlSettings}><Settings size={15} />{t("dsEditorSettings")}</button>
              <button className="secondary" onClick={applySqlFormat}><Code2 size={15} />{t("dsFormatSql")}</button>
            </div>
          </div>
          {showSqlSettings && <section className="ds-sql-settings" aria-label={t("dsEditorSettings")}>
            <header><div><strong>{t("dsEditorSettings")}</strong><span>{t("dsSettingsHelp")}</span></div>
              <button className="icon-action" onClick={() => setShowSqlSettings(false)} title={t("dsCloseSettings")}><X size={15} /></button>
            </header>
            <div className="ds-settings-fields">
              <label><span>{t("dsFormatStyle")}</span><select value={sqlFormatStyle} onChange={(event) => setSqlFormatStyle(event.currentTarget.value as SqlFormatStyle)}>
                <option value="standard">{t("dsFormatStandard")}</option><option value="compact">{t("dsFormatCompact")}</option><option value="expanded">{t("dsFormatExpanded")}</option>
              </select></label>
              <label><span>{t("dsKeywordStyle")}</span><select value={sqlKeywordCase} onChange={(event) => setSqlKeywordCase(event.currentTarget.value as typeof sqlKeywordCase)}>
                <option value="upper">UPPERCASE</option><option value="lower">lowercase</option><option value="preserve">{t("dsPreserve")}</option>
              </select></label>
              <label><span>{t("dsEditorFont")}</span><select value={sqlFont} onChange={(event) => setSqlFont(event.currentTarget.value)}>
                <option>Cascadia Code</option><option>Consolas</option><option>IBM Plex Mono</option><option>Courier New</option>
              </select></label>
              <label><span>{t("dsFontSize")}</span><select value={sqlFontSize} onChange={(event) => setSqlFontSize(Number(event.currentTarget.value))}>
                {[12, 13, 14, 15, 16, 18].map((size) => <option key={size} value={size}>{size}px</option>)}
              </select></label>
            </div>
            <div className="ds-theme-picker"><span>{t("dsEditorTheme")}</span><div>
              {(Object.entries(SQL_THEME_PALETTES) as [SqlThemeId, typeof SQL_THEME_PALETTES[SqlThemeId]][]).map(([id, palette]) =>
                <button key={id} className={sqlTheme === id ? "active" : ""} onClick={() => setSqlTheme(id)}
                  aria-pressed={sqlTheme === id}>
                  <i style={{ background: `linear-gradient(135deg, ${palette.bg} 58%, ${palette.keyword} 59% 72%, ${palette.string} 73%)` }} />
                  <span>{palette.label}</span>
                </button>)}
            </div></div>
          </section>}
          <div className="ds-code-shell" style={{ "--sql-font": sqlFont, "--sql-size": `${sqlFontSize}px` } as CSSProperties}>
            <CodeMirror
              value={sqlText}
              height="100%"
              theme={sqlThemeExtension}
              extensions={sqlExtensions}
              onChange={(value) => { setSqlText(value); setSqlPlan(null); setSqlResult(null); }}
              basicSetup={{ lineNumbers: true, foldGutter: true, highlightActiveLine: true, bracketMatching: true, autocompletion: true, closeBrackets: true }}
            />
            <span className="ds-resize-hint">{t("dsResizeEditor")}</span>
          </div>
          <footer className="ds-sql-actions">
            <div><strong>{t("dsExecution")}</strong><span>{t("dsExecutionHelp")}</span></div>
            <button onClick={runSqlEditor} disabled={busy || !sqlText.trim()}>{busy ? <span className="spinner" /> : <Play size={15} />}{t("dsRunSql")}</button>
            {sqlPlan?.mutation && <button className="danger-button" onClick={confirmSqlEditor} disabled={busy}><Play size={15} />{t("dsConfirmExecute")}</button>}
          </footer>
          {sqlPlan?.mutation && <div className="ds-sql-confirm">
            <strong>{t("dsMutationPreview")}</strong><span>{sqlPlan.operation.toUpperCase()}</span><code>{sqlPlan.sql}</code>
          </div>}
          {sqlResult && <div className="ds-builder-result ds-sql-result">
            <header className="ds-result-head"><div><strong>{t("dsQueryResult")}</strong><span>{sqlResult.rows.length} {t("dsRows")}</span></div>
              {sqlResult.truncated && <span className="status-pill">{t("dsLimitedRows")}</span>}
            </header>
            {sqlResult.affected !== undefined && <div className="notice">{t("dsAffected", { n: sqlResult.affected })}</div>}
            {!!sqlResult.columns.length && <div className="ds-data-scroll"><table className="ds-data-table"><thead><tr>{sqlResult.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
              <tbody>{sqlResult.rows.map((row, index) => <tr key={index}>{sqlResult.columns.map((column) => <td key={column}>{row[column] === null ? <i>NULL</i> : typeof row[column] === "object" ? JSON.stringify(row[column]) : String(row[column])}</td>)}</tr>)}</tbody></table></div>}
          </div>}
        </div> : !selection ? <div className="ds-welcome">
          <Database size={34} />
          <h3>{t("dsWelcome")}</h3>
          <p>{t("dsWelcomeLead")}</p>
        </div> : <>
          <div className="ds-object-head">
            <div><span>{selection.schema}</span><h3>{selection.object.object_name}</h3></div>
            <span className="status-pill">{selection.object.object_type.replace(/_/g, " ")}</span>
          </div>
          <div className="ds-tabs" role="tablist">
            {([
              ["builder", <Code2 size={15} />, t("dsBuilder")],
              ["data", <Table2 size={15} />, t("dsData")],
              ["structure", <Columns3 size={15} />, t("dsStructure")],
              ["relations", <KeyRound size={15} />, t("dsRelations")],
              ["indexes", <FileText size={15} />, t("dsIndexes")],
            ] as const).map(([id, icon, label]) => <button key={id} role="tab" aria-selected={tab === id}
              className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{icon}{label}</button>)}
          </div>
          {tab === "builder" && <div className="ds-builder">
            <div className="ds-builder-toolbar">
              <label><span>{t("dsOperation")}</span><select value={builderOp} onChange={(event) => {
                setBuilderOp(event.currentTarget.value); setPlan(null); setBuilderResult(null);
              }}>
                <option value="select">SELECT</option><option value="insert">INSERT</option>
                <option value="update">UPDATE</option><option value="delete">DELETE</option>
                <option value="create_table">CREATE TABLE</option><option value="alter_table">ALTER TABLE</option>
              </select></label>
              <button className="secondary ds-describe" onClick={() => setTab("structure")}><Columns3 size={15} />{t("dsDescribe")}</button>
            </div>
            {builderOp === "select" && <section className="ds-builder-section ds-fields-section">
              <header><div><strong>1. {t("dsFields")}</strong><small>{t("dsFieldsHelp")}</small></div>
                <button className="secondary" onClick={() => {
                  const first = selection.object.columns.find((column) => !column.protected);
                  if (first) setBuilderFields([...builderFields, { source: 0, column: first.column_name }]);
                }}><Plus size={14} />{t("dsAddField")}</button></header>
              <div className="ds-builder-rows">{builderFields.map((field, index) => <div className="ds-builder-row" key={index}>
                <select value={field.source} onChange={(event) => {
                  const next = [...builderFields]; next[index] = { source: Number(event.currentTarget.value), column: "" }; setBuilderFields(next); setPlan(null);
                }}>{builderSources.map((source, sourceIndex) => <option value={sourceIndex} key={sourceIndex}>{source.schema}.{source.object.object_name}</option>)}</select>
                <select value={field.column} onChange={(event) => { const next = [...builderFields]; next[index] = { ...field, column: event.currentTarget.value }; setBuilderFields(next); setPlan(null); }}>
                  <option value="">{t("dsChooseField")}</option>{(builderSources[field.source]?.object.columns || []).filter((column) => !column.protected).map((column) => <option key={column.column_name}>{column.column_name}</option>)}
                </select><button className="icon-action danger" onClick={() => setBuilderFields(builderFields.filter((_, item) => item !== index))}><Trash2 size={14} /></button>
              </div>)}</div>
            </section>}
            {builderOp === "select" && <section className="ds-builder-section ds-joins-section">
              <header><div><strong>2. {t("dsJoins")}</strong><small>{t("dsJoinsHelp")}</small></div>
                <button className="secondary" onClick={() => {
                  const candidate = schemas.flatMap((schema) => schema.objects.map((object) => ({ schema: schema.name, object }))).find((item) => item.object.object_type.includes("table"));
                  if (candidate) setBuilderJoins([...builderJoins, { schema: candidate.schema, table: candidate.object.object_name, type: "left", left_source: 0, left_column: "", right_column: "" }]);
                }}><Plus size={14} />{t("dsAddJoin")}</button></header>
              <div className="ds-builder-rows">{builderJoins.map((join, index) => {
                const joined = schemas.find((schema) => schema.name === join.schema)?.objects.find((object) => object.object_name === join.table);
                return <div className="ds-join-row" key={index}>
                  <select value={join.type} onChange={(e) => { const next = [...builderJoins]; next[index] = { ...join, type: e.currentTarget.value }; setBuilderJoins(next); setPlan(null); }}>
                    <option value="inner">INNER JOIN</option><option value="left">LEFT JOIN</option><option value="right">RIGHT JOIN</option><option value="full">FULL JOIN</option>
                  </select>
                  <select value={`${join.schema}.${join.table}`} onChange={(e) => { const [schema, ...rest] = e.currentTarget.value.split("."); const next = [...builderJoins]; next[index] = { ...join, schema, table: rest.join("."), right_column: "" }; setBuilderJoins(next); setPlan(null); }}>
                    {schemas.flatMap((schema) => schema.objects.map((object) => <option key={`${schema.name}.${object.object_name}`} value={`${schema.name}.${object.object_name}`}>{schema.name}.{object.object_name}</option>))}
                  </select>
                  <select value={join.left_source} onChange={(e) => { const next = [...builderJoins]; next[index] = { ...join, left_source: Number(e.currentTarget.value), left_column: "" }; setBuilderJoins(next); }}>
                    {builderSources.slice(0, index + 1).map((source, i) => <option value={i} key={i}>{source.object.object_name}</option>)}
                  </select>
                  <select value={join.left_column} onChange={(e) => { const next = [...builderJoins]; next[index] = { ...join, left_column: e.currentTarget.value }; setBuilderJoins(next); }}>
                    <option value="">{t("dsLeftField")}</option>{(builderSources[join.left_source]?.object.columns || []).filter((c) => !c.protected).map((c) => <option key={c.column_name}>{c.column_name}</option>)}
                  </select><span>=</span>
                  <select value={join.right_column} onChange={(e) => { const next = [...builderJoins]; next[index] = { ...join, right_column: e.currentTarget.value }; setBuilderJoins(next); }}>
                    <option value="">{t("dsRightField")}</option>{(joined?.columns || []).filter((c) => !c.protected).map((c) => <option key={c.column_name}>{c.column_name}</option>)}
                  </select><button className="icon-action danger" onClick={() => setBuilderJoins(builderJoins.filter((_, item) => item !== index))}><Trash2 size={14} /></button>
                </div>;
              })}</div>
            </section>}
            {(builderOp === "select" || builderOp === "update" || builderOp === "delete") && <section className="ds-builder-section ds-conditions-section">
              <header><div><strong>{builderOp === "select" ? "1." : "1."} {t("dsConditions")}</strong><small>{builderOp !== "select" ? t("dsConditionsRequired") : t("dsConditionsHelp")}</small></div>
                <button className="secondary" onClick={() => {
                  const first = selection.object.columns.find((column) => !column.protected);
                  if (first) setBuilderConditions([...builderConditions, { source: 0, column: first.column_name, operator: "eq", value: "", connector: "and" }]);
                }}><Plus size={14} />{t("dsAddCondition")}</button></header>
              <div className="ds-builder-rows">{builderConditions.map((condition, index) => <div className="ds-condition-row" key={index}>
                {index > 0 ? <select value={condition.connector} onChange={(e) => { const next = [...builderConditions]; next[index] = { ...condition, connector: e.currentTarget.value as "and" | "or" }; setBuilderConditions(next); }}><option value="and">AND</option><option value="or">OR</option></select> : <span className="ds-where">WHERE</span>}
                <select value={condition.source} onChange={(e) => { const next = [...builderConditions]; next[index] = { ...condition, source: Number(e.currentTarget.value), column: "" }; setBuilderConditions(next); }}>
                  {(builderOp === "select" ? builderSources : builderSources.slice(0, 1)).map((source, i) => <option value={i} key={i}>{source.object.object_name}</option>)}
                </select>
                <select value={condition.column} onChange={(e) => { const next = [...builderConditions]; next[index] = { ...condition, column: e.currentTarget.value }; setBuilderConditions(next); }}>
                  {(builderSources[condition.source]?.object.columns || []).filter((c) => !c.protected).map((c) => <option key={c.column_name}>{c.column_name}</option>)}
                </select><select value={condition.operator} onChange={(e) => { const next = [...builderConditions]; next[index] = { ...condition, operator: e.currentTarget.value }; setBuilderConditions(next); }}>
                  <option value="eq">=</option><option value="ne">≠</option><option value="contains">{t("dsContains")}</option><option value="starts">{t("dsStarts")}</option>
                  <option value="gt">&gt;</option><option value="gte">≥</option><option value="lt">&lt;</option><option value="lte">≤</option><option value="is_null">NULL</option><option value="is_not_null">NOT NULL</option>
                </select><input value={condition.value} disabled={condition.operator.includes("null")} placeholder={t("dsFilterValue")} onChange={(e) => { const next = [...builderConditions]; next[index] = { ...condition, value: e.currentTarget.value }; setBuilderConditions(next); }} />
                <button className="icon-action danger" onClick={() => setBuilderConditions(builderConditions.filter((_, item) => item !== index))}><Trash2 size={14} /></button>
              </div>)}</div>
            </section>}
            {builderOp === "select" && <section className="ds-builder-section ds-sort-section">
              <header><div><strong>2. {t("dsOrderBy")}</strong><small>{t("dsOrderHelp")}</small></div></header>
              <div className="ds-sort-row"><select value={sortColumn} onChange={(event) => { setSortColumn(event.currentTarget.value); setPlan(null); }}>
                <option value="">{t("dsNoOrder")}</option>{selection.object.columns.filter((column) => !column.protected).map((column) => <option key={column.column_name}>{column.column_name}</option>)}
              </select><select value={sortDirection} disabled={!sortColumn} onChange={(event) => setSortDirection(event.currentTarget.value)}>
                <option value="asc">{t("dsAscending")}</option><option value="desc">{t("dsDescending")}</option>
              </select></div>
            </section>}
            {(builderOp === "insert" || builderOp === "update") && <section className="ds-builder-section">
              <header><div><strong>{builderOp === "update" ? "2." : "1."} {t("dsValues")}</strong><small>{t("dsValuesHelp")}</small></div>
                <button className="secondary" onClick={() => {
                  const used = new Set(builderValues.map((item) => item.column));
                  const first = selection.object.columns.find((column) => !column.protected && !used.has(column.column_name));
                  if (first) setBuilderValues([...builderValues, { column: first.column_name, value: "" }]);
                }}><Plus size={14} />{t("dsAddValue")}</button></header>
              <div className="ds-builder-rows">{builderValues.map((value, index) => <div className="ds-builder-row" key={index}>
                <select value={value.column} onChange={(e) => { const next = [...builderValues]; next[index] = { ...value, column: e.currentTarget.value }; setBuilderValues(next); }}>
                  {selection.object.columns.filter((c) => !c.protected).map((c) => <option key={c.column_name}>{c.column_name}</option>)}
                </select><input value={value.value} placeholder={t("dsFilterValue")} onChange={(e) => { const next = [...builderValues]; next[index] = { ...value, value: e.currentTarget.value }; setBuilderValues(next); }} />
                <button className="icon-action danger" onClick={() => setBuilderValues(builderValues.filter((_, item) => item !== index))}><Trash2 size={14} /></button>
              </div>)}</div>
            </section>}
            {builderOp === "create_table" && <section className="ds-builder-section">
              <header><div><strong>1. {t("dsCreateTable")}</strong><small>{t("dsCreateHelp")}</small></div>
                <button className="secondary" onClick={() => setCreateColumns([...createColumns, { name: "", type: "text", nullable: true, primary: false }])}><Plus size={14} />{t("dsAddColumn")}</button></header>
              <div className="ds-create-name"><label><span>{t("dsTableName")}</span><input value={createTableName} onChange={(e) => { setCreateTableName(e.currentTarget.value); setPlan(null); }} placeholder="new_table" /></label></div>
              <div className="ds-builder-rows">{createColumns.map((column, index) => <div className="ds-create-row" key={index}>
                <input value={column.name} onChange={(e) => { const next = [...createColumns]; next[index] = { ...column, name: e.currentTarget.value }; setCreateColumns(next); }} placeholder={t("dsColumnName")} />
                <select value={column.type} onChange={(e) => { const next = [...createColumns]; next[index] = { ...column, type: e.currentTarget.value }; setCreateColumns(next); }}>{["text", "varchar", "integer", "bigint", "numeric", "boolean", "date", "timestamptz", "jsonb", "uuid"].map((type) => <option key={type}>{type}</option>)}</select>
                <label className="ds-check"><input type="checkbox" checked={column.nullable} onChange={(e) => { const next = [...createColumns]; next[index] = { ...column, nullable: e.currentTarget.checked }; setCreateColumns(next); }} />NULL</label>
                <label className="ds-check"><input type="checkbox" checked={column.primary} onChange={(e) => { const next = [...createColumns]; next[index] = { ...column, primary: e.currentTarget.checked }; setCreateColumns(next); }} />PRIMARY KEY</label>
                <button className="icon-action danger" onClick={() => setCreateColumns(createColumns.filter((_, item) => item !== index))}><Trash2 size={14} /></button>
              </div>)}</div>
            </section>}
            {builderOp === "alter_table" && <section className="ds-builder-section">
              <header><div><strong>1. {t("dsAlterAction")}</strong><small>{t("dsAlterHelp")}</small></div></header>
              <div className="ds-ddl-row"><select value={alterAction} onChange={(e) => setAlterAction(e.currentTarget.value)}>
                <option value="add_column">{t("dsAddColumn")}</option><option value="rename_column">{t("dsRenameColumn")}</option><option value="drop_column">{t("dsDropColumn")}</option>
              </select>{alterAction === "add_column" ? <input value={ddlName} onChange={(e) => setDdlName(e.currentTarget.value)} placeholder={t("dsColumnName")} /> :
                <select value={ddlName} onChange={(e) => setDdlName(e.currentTarget.value)}><option value="">{t("dsChooseField")}</option>{selection.object.columns.filter((c) => !c.protected).map((c) => <option key={c.column_name}>{c.column_name}</option>)}</select>}
                {alterAction === "add_column" && <select value={ddlType} onChange={(e) => setDdlType(e.currentTarget.value)}>{["text", "varchar", "integer", "bigint", "numeric", "boolean", "date", "timestamptz", "jsonb", "uuid"].map((type) => <option key={type}>{type}</option>)}</select>}
                {alterAction === "rename_column" && <input value={newName} onChange={(e) => setNewName(e.currentTarget.value)} placeholder={t("dsNewName")} />}</div>
            </section>}
            <footer className="ds-builder-actions">
              <span>{builderOp === "select" ? t("dsResultBelow") : t("dsPreviewBeforeChange")}</span>
              <button className={builderOp === "select" ? "" : "secondary"} onClick={previewBuilder} disabled={busy}>
                {busy ? <span className="spinner" /> : builderOp === "select" ? <Play size={15} /> : <Code2 size={15} />}
                {builderOp === "select" ? t("dsRun") : t("dsPreview")}
              </button>
              {plan?.mutation && <button onClick={executeBuilder} disabled={busy} className="danger-button"><Play size={15} />{t("dsConfirmExecute")}</button>}
            </footer>
            {builderResult && <div className="ds-builder-result">
              <header className="ds-result-head"><div><strong>{t("dsQueryResult")}</strong><span>{builderResult.rows.length} {t("dsRows")}</span></div>
                <button className="secondary" onClick={() => setResultExpanded((value) => !value)}>
                  {resultExpanded ? <X size={15} /> : <Square size={14} />}{resultExpanded ? t("dsRestoreResult") : t("dsExpandResult")}
                </button></header>
              {builderResult.affected !== undefined && <div className="notice">{t("dsAffected", { n: builderResult.affected })}</div>}
              {!!builderResult.columns.length && <div className="ds-data-scroll"><table className="ds-data-table"><thead><tr>{builderResult.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                <tbody>{builderResult.rows.map((row, index) => <tr key={index}>{builderResult.columns.map((column) => <td key={column}>{row[column] === null ? <i>NULL</i> : typeof row[column] === "object" ? JSON.stringify(row[column]) : String(row[column])}</td>)}</tr>)}</tbody></table></div>}
            </div>}
            {plan && <details className="ds-sql-preview"><summary><strong>{t("dsTechnicalDetails")}</strong><span>{t("dsParameterized")}</span></summary><code>{plan.sql.replace(/"t\d+"\./g, "")}</code></details>}
          </div>}
          {tab === "data" && <>
            <div className="ds-filterbar">
              <Filter size={16} />
              <select value={filterColumn} onChange={(event) => setFilterColumn(event.currentTarget.value)}>
                <option value="">{t("dsFilterColumn")}</option>
                {filterableColumns.map((column) => <option key={column.column_name} value={column.column_name}>{column.column_name}</option>)}
              </select>
              <select value={filterOperator} onChange={(event) => setFilterOperator(event.currentTarget.value)}>
                <option value="contains">{t("dsContains")}</option><option value="eq">{t("dsEquals")}</option>
                <option value="starts">{t("dsStarts")}</option><option value="gt">&gt;</option>
                <option value="gte">≥</option><option value="lt">&lt;</option><option value="lte">≤</option>
                <option value="is_null">NULL</option>
              </select>
              <input value={filterValue} disabled={filterOperator === "is_null"} onChange={(event) => setFilterValue(event.currentTarget.value)} placeholder={t("dsFilterValue")} />
              <button className="secondary" onClick={() => { setPage(1); void loadTable(selection, 1); }} disabled={busy}>{t("dsApply")}</button>
            </div>
            <div className="ds-data-scroll">
              <table className="ds-data-table"><thead><tr>{resultColumns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                <tbody>{rows.map((row, index) => <tr key={index}>{resultColumns.map((column) =>
                  <td key={column} title={String(row[column] ?? "")}>{row[column] === null ? <i>NULL</i> : typeof row[column] === "object" ? JSON.stringify(row[column]) : String(row[column])}</td>)}</tr>)}</tbody>
              </table>
              {!rows.length && !busy && <p className="empty-queue">{t("dsNoRows")}</p>}
            </div>
            <footer className="ds-pager">
              <span>{t("dsPage", { n: page })} · {rows.length} {t("dsRows")}</span>
              <div><button className="icon-action" disabled={page <= 1 || busy} onClick={() => void loadTable(selection, page - 1)} title={t("dsPrevious")}><ChevronsLeft size={16} /></button>
                <button className="icon-action" disabled={!hasMore || busy} onClick={() => void loadTable(selection, page + 1)} title={t("dsNext")}><ChevronsRight size={16} /></button></div>
            </footer>
          </>}
          {tab === "structure" && <div className="ds-meta-list">{selection.object.columns.map((column) =>
            <div key={column.column_name}><span>{column.primary_key ? <KeyRound size={14} /> : <Columns3 size={14} />}</span>
              <strong>{column.column_name}</strong><code>{column.data_type}</code>
              <small>{column.protected ? t("dsProtected") : column.nullable ? "NULL" : "NOT NULL"}</small></div>)}</div>}
          {tab === "relations" && <div className="ds-meta-list">{selection.object.relations.map((relation) =>
            <div key={`${relation.constraint_name}-${relation.column_name}`}><KeyRound size={14} /><strong>{relation.column_name}</strong>
              <span>→</span><code>{relation.target_schema}.{relation.target_table}.{relation.target_column}</code></div>)}
            {!selection.object.relations.length && <p className="empty-queue">{t("dsNoRelations")}</p>}</div>}
          {tab === "indexes" && <div className="ds-indexes">{selection.object.indexes.map((index) =>
            <article key={index.index_name}><strong>{index.index_name}</strong><code>{index.definition}</code></article>)}
            {!selection.object.indexes.length && <p className="empty-queue">{t("dsNoIndexes")}</p>}</div>}
        </>}
      </div>
    </div>
  </section>;
}

function AdminView({ active, section }: { active: boolean; section: AdminSection }) {
  const { t, locale } = useLang();
  const sess = getSession();
  const [tab, setTab] = useState<AdminSection>(section);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [telemetryDays, setTelemetryDays] = useState(7);
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [supportTicket, setSupportTicket] = useState<SupportDetail | null>(null);
  const [supportReply, setSupportReply] = useState("");
  const [supportStatus, setSupportStatus] = useState("open");
  const [supportQuery, setSupportQuery] = useState("");
  const [supportFilter, setSupportFilter] = useState("all");
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
  const [activityEvent, setActivityEvent] = useState("");
  const [activityEmail, setActivityEmail] = useState("");
  const [activityDetail, setActivityDetail] = useState("");
  const [aTable, setATable] = useState("");
  const [aId, setAId] = useState("");
  const [openSnap, setOpenSnap] = useState<number | null>(null);

  async function call(op: string, payload: Record<string, unknown>) {
    const raw = await invoke<string>("admin", {
      op, mode: sess?.mode ?? null,
      payload: JSON.stringify({
        actor: sess?.id ?? null,
        admin_email: sess?.email || "",
        admin_token: sess?.admin_token || "",
        ...payload,
      }),
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
  async function loadTelemetry(days = telemetryDays) {
    setBusy(true); setErr("");
    try {
      const raw = await invoke<string>("telemetry_overview", { payload: JSON.stringify({ email: sess?.email || "", elevation_token: sess?.admin_token || "", days }) });
      const r = JSON.parse(raw);
      if (r.error) setErr(r.error); else setTelemetry(r);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }
  async function supportCall(op: string, payload: Record<string, unknown> = {}) {
    const raw = await invoke<string>("support", { op, payload: JSON.stringify({ email: sess?.email || "", elevation_token: sess?.admin_token || "", ...payload }) });
    return JSON.parse(raw);
  }
  async function loadSupportQueue() {
    setBusy(true); setErr("");
    try { const r = await supportCall("admin-list"); if (r.ok) setSupportTickets(r.tickets || []); else setErr(r.error || "mfa_required"); }
    catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }
  async function openSupportTicket(id: number) {
    setBusy(true); setErr("");
    try { const r = await supportCall("admin-detail", { ticket_id: id }); if (r.ok) { setSupportTicket(r.ticket); setSupportStatus(r.ticket.status); } else setErr(r.error || "ticket_not_found"); }
    catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }
  async function respondSupportTicket() {
    if (!supportTicket || !supportReply.trim()) return;
    setBusy(true); setErr("");
    try { const r = await supportCall("admin-comment", { ticket_id: supportTicket.id, body: supportReply.trim() }); if (r.ok) { setSupportReply(""); await openSupportTicket(supportTicket.id); await loadSupportQueue(); } else setErr(r.error || "service_unavailable"); }
    catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }
  async function changeSupportStatus() {
    if (!supportTicket) return;
    setBusy(true); setErr("");
    try { const r = await supportCall("admin-status", { ticket_id: supportTicket.id, status: supportStatus }); if (r.ok) { await openSupportTicket(supportTicket.id); await loadSupportQueue(); } else setErr(r.error || "service_unavailable"); }
    catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  useEffect(() => {
    setTab(section);
    setErr(""); setNotice("");
    if (section === "telemetry") void loadTelemetry();
    if (section === "support") void loadSupportQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section]);

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
  const activityOptions = useMemo(() => {
    const values = (pick: (event: typeof data.events[number]) => string | null | undefined) =>
      [...new Set(data.events.map(pick).filter((value): value is string => Boolean(value)))].sort((a, b) => a.localeCompare(b));
    return {
      events: values((event) => event.event),
      emails: values((event) => event.email),
      details: values((event) => event.detail),
    };
  }, [data.events]);
  const eventsFiltered = useMemo(() => {
    const eventQuery = activityEvent.trim().toLowerCase();
    const emailQuery = activityEmail.trim().toLowerCase();
    const detailQuery = activityDetail.trim().toLowerCase();
    return data.events.filter((ev) => (!sinceMs || (ev.occurred_at && Date.parse(ev.occurred_at) >= sinceMs)) &&
      (!eventQuery || ev.event.toLowerCase().includes(eventQuery)) &&
      (!emailQuery || (ev.email || "").toLowerCase().includes(emailQuery)) &&
      (!detailQuery || (ev.detail || "").toLowerCase().includes(detailQuery)));
  }, [data.events, sinceMs, activityEvent, activityEmail, activityDetail]);
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

  const supportFiltered = useMemo(() => {
    const q = supportQuery.trim().toLowerCase();
    return supportTickets.filter((ticket) =>
      (supportFilter === "all" || ticket.status === supportFilter) &&
      (!q || [ticket.ticket_number, ticket.subject, ticket.email, ticket.category]
        .filter(Boolean).some((value) => String(value).toLowerCase().includes(q))));
  }, [supportTickets, supportFilter, supportQuery]);
  const supportStats = useMemo(() => ({
    total: supportTickets.length,
    open: supportTickets.filter((x) => x.status === "open").length,
    progress: supportTickets.filter((x) => x.status === "in_progress").length,
    waiting: supportTickets.filter((x) => x.status === "pending_customer").length,
    resolved: supportTickets.filter((x) => x.status === "resolved" || x.status === "closed").length,
  }), [supportTickets]);

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
  const auditSnapshotEntries = (snapshot: Record<string, unknown> | null) => Object.entries(snapshot || {}).filter(([key]) => !["provider_scopes", "provider_id", "access_token", "refresh_token", "password_hash"].includes(key));

  if (tab === "data-studio") return <DataStudioWorkspace />;

  if (tab === "support") {
    return <section className="card admin-workspace">
      <header className="workspace-head">
        <div><span className="eyebrow">{t("navAdmin")}</span><h2>{t("admTabSupport")}</h2></div>
        <button className="secondary icon-button" onClick={loadSupportQueue} disabled={busy}>{busy ? <span className="spinner" /> : <RefreshCw size={16} />}<span>{t("libRefresh")}</span></button>
      </header>
      {err && <div className="key-warn">{err}</div>}
      <AdminSupportWorkspace
        tickets={supportFiltered} stats={supportStats} ticket={supportTicket} busy={busy}
        query={supportQuery} filter={supportFilter} reply={supportReply} status={supportStatus}
        onQuery={setSupportQuery} onFilter={setSupportFilter} onOpen={openSupportTicket}
        onBack={() => setSupportTicket(null)} onReply={setSupportReply} onRespond={respondSupportTicket}
        onStatus={setSupportStatus} onChangeStatus={changeSupportStatus}
      />
    </section>;
  }

  return (
    <section className="card admin-workspace">
      <header className="workspace-head">
        <div><span className="eyebrow">{t("navAdmin")}</span><h2>{tab === "telemetry" ? "Telemetry" : t(tab === "users" ? "admTabUsers" : tab === "activity" ? "admTabActivity" : "admTabAudit")}</h2></div>
        <div className="row workspace-actions">
          {cacheTs && <span className="muted" title={t("libCacheTitle")}>{t("libCacheUpdating", { ts: fmtDate(cacheTs, locale) })}</span>}
          <button className="secondary icon-button" onClick={() => { loadOverview(); if (tab === "telemetry") loadTelemetry(); }} disabled={busy}>
            {busy ? <span className="spinner" /> : <RefreshCw size={16} />}<span>{t("libRefresh")}</span>
          </button>
        </div>
      </header>
      {err && <div className="key-warn" style={{ marginBottom: 10 }}>{err}</div>}
      {notice && <div className="engine-info" style={{ marginBottom: 10 }}>{notice}</div>}

      {false && supportTicket && <div className="support-admin">
        <div className="support-layout">
          <div><h3>{t("admTabSupport")}</h3>{!supportTickets.length && <p className="muted">{t("supportNoTickets")}</p>}<div className="support-ticket-list">{supportTickets.map((item) => <button key={item.id} className={"support-ticket" + (supportTicket?.id === item.id ? " active" : "")} onClick={() => openSupportTicket(item.id)}><b>{item.ticket_number}</b><span>{item.subject}</span><small>{item.email} · {item.status}</small></button>)}</div></div>
          <div />
        </div>
      </div>}

      {tab === "telemetry" && (
        <div className="telemetry-dashboard">
          <div className="row wrap" style={{ marginBottom: 14 }}>
            <strong>Privacy-safe telemetry</strong><span className="muted">Only consented, anonymous technical events.</span><span style={{ flex: 1 }} />
            {[1, 7, 30, 90].map((days) => <button key={days} className={telemetryDays === days ? "" : "secondary"} onClick={() => { setTelemetryDays(days); loadTelemetry(days); }}>{days}d</button>)}
          </div>
          {!telemetry && busy && <div className="status"><span className="spinner" /> Loading telemetry…</div>}
          {telemetry && <>
            <div className="telemetry-kpis">
              <div><span>Consented installations</span><strong>{telemetry.installations}</strong></div><div><span>Events</span><strong>{telemetry.events}</strong></div><div><span>Completed</span><strong>{telemetry.completed}</strong></div><div><span>Failed</span><strong>{telemetry.failed}</strong></div>
            </div>
            <div className="telemetry-grid"><section><h3>Errors and outcomes</h3>{(telemetry.errors || []).map((x: any, i: number) => <div className="telemetry-row" key={i}><span>{x.error_code || x.event}</span><b>{x.count}</b></div>) || "No events yet"}</section><section><h3>Engines</h3>{(telemetry.engines || []).map((x: any) => <div className="telemetry-row" key={x.engine}><span>{x.engine} · {Math.round(x.avg_duration_seconds / 60)} min avg</span><b>{x.count}</b></div>) || "No engine activity yet"}</section></div>
          </>}
        </div>
      )}

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
                <SecretInput
                  value={cPw}
                  onChange={setCPw}
                  onPaste={(e) => {
                    e.preventDefault();
                    setCPw(e.clipboardData.getData("text"));
                  }}
                  validation={cPw.length > 0 ? (cPw.length >= 6 ? "valid" : "invalid") : undefined}
                />
              </div>
              <button onClick={createUser} disabled={busy}>{t("admCreateBtn")}</button>
            </div>
          )}
          <div className="table-scroll">
            <table className="eng-table admin-user-table">
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
                    <td title={u.user_id}>{u.user_id}</td>
                    <td title={u.email}>
                      {u.email}{u.deleted_at && <span className="badge" style={{ marginLeft: 6 }}>{t("admDeletedBadge")}</span>}
                    </td>
                    <td>{u.auth_provider}</td>
                    <td>{u.role}</td>
                    <td>{u.transcription_count}</td>
                    <td>{fmtDate(u.last_login_at, locale)}</td>
                    <td>
                      {!u.deleted_at ? (
                        <span className="table-actions">
                          <button className="icon-action" title={t("admEdit")} aria-label={t("admEdit")} onClick={() => {
                            setErr("");
                            setEditUser({
                              id: u.id, email: u.email, user_id: u.user_id,
                              first_name: u.first_name || "", last_name: u.last_name || "", role: u.role,
                            });
                          }}>
                            <Pencil size={15} />
                          </button>
                          <button className="icon-action" title={t("admDelete")} aria-label={t("admDelete")} onClick={() => setConfirmDel({ id: u.id, purge: false })}><Archive size={15} /></button>
                          <button className="icon-action danger" title={t("admPurge")} aria-label={t("admPurge")} onClick={() => setConfirmDel({ id: u.id, purge: true })}><Trash2 size={15} /></button>
                        </span>
                      ) : (
                        <button className="icon-action danger" title={t("admPurge")} aria-label={t("admPurge")} onClick={() => setConfirmDel({ id: u.id, purge: true })}><Trash2 size={15} /></button>
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
          <section className="admin-filterbar">
            <div className="field"><label>Period</label><select value={period} onChange={(e) => setPeriod(e.currentTarget.value as typeof period)}><option value="day">{t("admPeriodDay")}</option><option value="week">{t("admPeriodWeek")}</option><option value="month">{t("admPeriodMonth")}</option><option value="all">{t("admPeriodAll")}</option></select></div>
            <div className="field"><label>{t("admColEvent")}</label><select value={activityEvent} onChange={(e) => setActivityEvent(e.currentTarget.value)}><option value="">{t("admPeriodAll")}</option>{activityOptions.events.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
            <div className="field"><label>{t("loginEmail")}</label><select value={activityEmail} onChange={(e) => setActivityEmail(e.currentTarget.value)}><option value="">{t("admPeriodAll")}</option>{activityOptions.emails.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
            <div className="field"><label>{t("admColDetail")}</label><select value={activityDetail} onChange={(e) => setActivityDetail(e.currentTarget.value)}><option value="">{t("admPeriodAll")}</option>{activityOptions.details.map((value) => <option key={value} value={value}>{value}</option>)}</select></div>
          </section>
          <div className="activity-summary" style={{ marginBottom: 12 }}>
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
                          <dl className="audit-detail-grid">
                            {auditSnapshotEntries(a.snapshot).map(([key, value]) => <Fragment key={key}><dt>{key.split("_").join(" ")}</dt><dd>{value == null ? "—" : String(value)}</dd></Fragment>)}
                          </dl>
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
type AdminSupportProps = {
  tickets: SupportTicket[]; stats: { total: number; open: number; progress: number; waiting: number; resolved: number };
  ticket: SupportDetail | null; busy: boolean; query: string; filter: string; reply: string; status: string;
  onQuery: (value: string) => void; onFilter: (value: string) => void; onOpen: (id: number) => void; onBack: () => void;
  onReply: (value: string) => void; onRespond: () => void; onStatus: (value: string) => void; onChangeStatus: () => void;
};

function AdminSupportWorkspace(props: AdminSupportProps) {
  const { t, locale } = useLang();
  const label = (status: string) => t(status === "open" ? "supportOpen" : status === "in_progress" ? "supportProgress" : status === "pending_customer" ? "supportPending" : status === "resolved" ? "supportResolved" : "supportClosed");
  if (props.ticket) {
    const ticket = props.ticket;
    return <div className="case-detail">
      <button className="link-btn back-to-queue" onClick={props.onBack}><ArrowLeft size={16} /> {t("supportBackToQueue")}</button>
      <div className="case-title"><div><span className="eyebrow">{ticket.ticket_number}</span><h3>{ticket.subject}</h3></div><span className={`status-pill ${ticket.status}`}>{label(ticket.status)}</span></div>
      <div className="case-layout">
        <div className="case-main">
          <section className="case-card"><span className="eyebrow">{t("supportMessage")}</span><p className="support-description">{ticket.description}</p></section>
          <section className="case-card"><span className="eyebrow">{t("supportTimeline")}</span><h3>{t("supportConversation")}</h3><div className="support-comments">{ticket.comments.map((comment) => <article key={comment.id} className={comment.author_kind === "support" || comment.author_kind === "admin" ? "from-support" : ""}><strong>{comment.author_label || comment.author_kind}</strong><small>{fmtDate(comment.created_at, locale)}</small><p>{comment.body}</p></article>)}</div></section>
          <section className="case-card composer"><span className="eyebrow">{t("supportReplyAs")}</span><h3>{t("supportReply")}</h3><textarea rows={7} value={props.reply} placeholder={t("supportReplyPlaceholder")} onChange={(e) => props.onReply(e.currentTarget.value)} /><div className="composer-actions"><span className="muted">{t("supportReplyIdentity")}</span><button disabled={props.busy || !props.reply.trim()} onClick={props.onRespond}>{t("supportReplySend")}</button></div></section>
        </div>
        <aside className="case-sidebar">
          <section className="case-card"><span className="eyebrow">{t("supportCaseContext")}</span><div className="field"><label>{t("supportStatus")}</label><select value={props.status} onChange={(e) => props.onStatus(e.currentTarget.value)}><option value="open">{t("supportOpen")}</option><option value="in_progress">{t("supportProgress")}</option><option value="pending_customer">{t("supportPending")}</option><option value="resolved">{t("supportResolved")}</option><option value="closed">{t("supportClosed")}</option></select></div><button className="secondary full-width" disabled={props.busy} onClick={props.onChangeStatus}>{t("admSaved")}</button></section>
          <section className="case-card case-meta"><span>{t("supportRequester")}</span><strong>{ticket.email || "—"}</strong><span>{t("supportCategory")}</span><strong>{ticket.category}</strong><span>{t("supportCreatedAt")}</span><strong>{fmtDate((ticket as any).created_at || ticket.updated_at, locale)}</strong></section>
          <section className="case-card"><span className="eyebrow">{t("supportEvidenceCount", { n: ticket.attachments?.length || 0 })}</span>{ticket.attachments?.length ? ticket.attachments.map((attachment) => <div className="attachment-row" key={attachment.id}><FileText size={15} /><span>{attachment.original_filename}</span></div>) : <p className="muted">{t("supportNoEvidence")}</p>}</section>
        </aside>
      </div>
    </div>;
  }
  return <div className="support-workspace">
    <section className="support-dashboard"><div><span className="eyebrow">{t("supportOverview")}</span><h3>{t("supportDashboardTitle")}</h3><p className="muted">{t("supportDashboardLead")}</p></div><div className="support-kpis"><div><span>{t("supportKpiTotal")}</span><strong>{props.stats.total}</strong></div><div><span>{t("supportOpen")}</span><strong>{props.stats.open}</strong></div><div><span>{t("supportProgress")}</span><strong>{props.stats.progress}</strong></div><div><span>{t("supportPending")}</span><strong>{props.stats.waiting}</strong></div><div><span>{t("supportResolved")}</span><strong>{props.stats.resolved}</strong></div></div></section>
    <section className="support-queue"><div className="queue-head"><div><span className="eyebrow">{t("supportInbox")}</span><h3>{t("supportQueueTitle")}</h3></div><div className="queue-controls"><div className="queue-search"><Search size={16} /><input type="text" value={props.query} placeholder={t("supportQueueSearch")} onChange={(e) => props.onQuery(e.currentTarget.value)} /></div><select value={props.filter} onChange={(e) => props.onFilter(e.currentTarget.value)}><option value="all">{t("supportAll")}</option><option value="open">{t("supportOpen")}</option><option value="in_progress">{t("supportProgress")}</option><option value="pending_customer">{t("supportPending")}</option><option value="resolved">{t("supportResolved")}</option></select></div></div>{!props.tickets.length ? <p className="empty-queue">{t("supportNoTickets")}</p> : <div className="ticket-table-scroll"><div className="ticket-table" role="table"><div className="ticket-table-head" role="row"><span>{t("supportColId")}</span><span>{t("supportColSubject")}</span><span>{t("supportRequester")}</span><span>{t("supportCreatedAt")}</span><span>{t("supportStatus")}</span></div>{props.tickets.map((item) => <button className="ticket-table-row" role="row" key={item.id} onClick={() => props.onOpen(item.id)}><strong>{item.ticket_number}</strong><span className="ticket-subject">{item.subject}<small>{item.category}</small></span><span>{item.email || "—"}</span><span>{fmtDate((item as any).created_at || item.updated_at, locale)}</span><span><b className={`status-pill ${item.status}`}>{label(item.status)}</b></span></button>)}</div></div>}</section>
  </div>;
}

type SupportTicket = { id: number; ticket_number: string; subject: string; status: string; category: string; updated_at: string; created_at?: string; comments: number; attachments: number; email?: string };
type SupportDetail = SupportTicket & { description: string; comments: { id: number; author_kind: string; author_label: string | null; body: string; created_at: string }[]; attachments: { id: number; original_filename: string; archive_state: string; created_at: string }[] };

function SupportView({ active }: { active: boolean }) {
  const { t, locale } = useLang(); const sess = getSession();
  const [tickets, setTickets] = useState<SupportTicket[]>([]); const [selected, setSelected] = useState<SupportDetail | null>(null);
  const [subject, setSubject] = useState(""); const [category, setCategory] = useState("general"); const [body, setBody] = useState(""); const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false); const [notice, setNotice] = useState("");
  const identity = () => ({ email: sess?.email || "", username: sess?.user_id || (sess?.email || "guest").split("@")[0].replace(/[^a-zA-Z0-9._-]/g, ""), display_name: sess?.user_id || sess?.email || "UpexNote user" });
  async function call(op: string, payload: Record<string, unknown> = {}) { return JSON.parse(await invoke<string>("support", { op, payload: JSON.stringify({ ...identity(), ...payload }) })); }
  async function load() { if (!sess?.email) return; setBusy(true); try { const r = await call("list"); if (r.ok) setTickets(r.tickets || []); else setNotice(t("supportError")); } catch { setNotice(t("supportError")); } finally { setBusy(false); } }
  async function openTicket(ticketId: number) { setBusy(true); setNotice(""); try { const r = await call("detail", { ticket_id: ticketId }); if (r.ok) setSelected(r.ticket); else setNotice(t("supportError")); } catch { setNotice(t("supportError")); } finally { setBusy(false); } }
  async function create() { if (subject.trim().length < 4 || body.trim().length < 8) return; setBusy(true); setNotice(""); try { const r = await call("create", { subject: subject.trim(), body: body.trim(), category, priority: "normal", app_version: await getVersion(), platform: "desktop", locale }); if (r.ok) { setSubject(""); setBody(""); setNotice(t("supportCreated", { n: r.ticket.ticket_number })); await load(); await openTicket(r.ticket.id); } else setNotice(t("supportError")); } catch { setNotice(t("supportError")); } finally { setBusy(false); } }
  async function sendReply() { if (!selected || !reply.trim()) return; setBusy(true); setNotice(""); try { const r = await call("comment", { ticket_id: selected.id, body: reply.trim() }); if (r.ok) { setReply(""); await openTicket(selected.id); await load(); } else setNotice(t("supportError")); } catch { setNotice(t("supportError")); } finally { setBusy(false); } }
  async function addEvidence() { if (!selected) return; const path = await open({ multiple: false, directory: false, title: t("supportAddEvidence"), filters: [{ name: "Evidence", extensions: ["png", "jpg", "jpeg", "webp", "pdf"] }] }); if (typeof path !== "string") return; setBusy(true); setNotice(""); try { const r = await call("attachment", { ticket_id: selected.id, file_path: path }); if (r.ok) { await openTicket(selected.id); await load(); } else setNotice(t("supportError")); } catch { setNotice(t("supportError")); } finally { setBusy(false); } }
  useEffect(() => { if (active) void load(); }, [active]); // eslint-disable-line react-hooks/exhaustive-deps
  const statusLabel = (status: string) => t(status === "open" ? "supportOpen" : status === "in_progress" ? "supportProgress" : status === "pending_customer" ? "supportPending" : status === "resolved" ? "supportResolved" : "supportClosed");
  return <section className="card support-view"><h2>{t("supportTitle")}</h2><p className="engine-info">{t("supportLead")}</p>{notice && <div className="engine-info">{notice}</div>}<div className="support-layout"><div><h3>{t("supportNew")}</h3><div className="field"><label>{t("supportSubject")}</label><input value={subject} onChange={(e) => setSubject(e.currentTarget.value)} maxLength={240} /></div><div className="field"><label>{t("supportCategory")}</label><select value={category} onChange={(e) => setCategory(e.currentTarget.value)}><option value="general">General</option><option value="account">Account</option><option value="transcription">Transcription</option><option value="billing">Billing</option><option value="bug">Bug</option></select></div><div className="field"><label>{t("supportMessage")}</label><textarea rows={7} value={body} onChange={(e) => setBody(e.currentTarget.value)} /></div><p className="muted">{t("supportEvidence")}</p><button disabled={busy || subject.trim().length < 4 || body.trim().length < 8} onClick={create}>{busy ? t("supportSending") : t("supportSend")}</button></div><div><div className="row"><h3 style={{ flex: 1 }}>{t("supportMyTickets")}</h3><button className="secondary" disabled={busy} onClick={load}>{t("libRefresh")}</button></div>{!tickets.length && <p className="muted">{t("supportNoTickets")}</p>}<div className="support-ticket-list">{tickets.map((item) => <button key={item.id} className={"support-ticket" + (selected?.id === item.id ? " active" : "")} onClick={() => openTicket(item.id)}><b>{item.ticket_number}</b><span>{item.subject}</span><small>{statusLabel(item.status)} · {fmtDate(item.updated_at, locale)}</small></button>)}</div></div></div>{selected && <section className="support-detail"><div className="row"><h3 style={{ flex: 1 }}>{selected.ticket_number} · {selected.subject}</h3><span className="badge">{statusLabel(selected.status)}</span></div><p className="support-description">{selected.description}</p><div className="row"><strong>{selected.attachments?.length || 0} evidence</strong><button className="secondary" disabled={busy} onClick={addEvidence}>{busy ? t("supportEvidenceUploading") : t("supportAddEvidence")}</button></div>{(selected.attachments || []).map((a) => <p className="muted" key={a.id}>{a.original_filename} · {a.archive_state}</p>)}<div className="support-comments">{selected.comments.map((c) => <article key={c.id}><strong>{c.author_label || c.author_kind}</strong><small>{fmtDate(c.created_at, locale)}</small><p>{c.body}</p></article>)}</div><div className="field"><label>{t("supportReply")}</label><textarea rows={3} value={reply} onChange={(e) => setReply(e.currentTarget.value)} /></div><button disabled={busy || !reply.trim()} onClick={sendReply}>{t("supportReplySend")}</button></section>}</section>;
}

function App() {
  const { t } = useLang();
  const appearance = useAppearance();
  const font = useFontPrefs();
  // Sessão iniciada (user/admin) — null = mostrar o login
  const [session, setSession] = useState<string | null>(() => {
    const saved = getSession();
    if (saved) return saved.profile;
    localStorage.removeItem("upexnote-profile"); // chave da v0.12.0, obsoleta
    return null;
  });
  useEffect(() => {
    if (session !== "admin") return;
    const current = getSession();
    if (!current?.admin_expires_at) { setSession(null); return; }
    const remaining = Date.parse(current.admin_expires_at) - Date.now();
    if (remaining <= 0) { setSession(null); return; }
    const timer = window.setTimeout(() => {
      localStorage.removeItem("upexnote-session");
      clearLibCaches();
      setView("transcribe");
      setSession(null);
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [session]);
  // Telemetria de melhoria é opcional: perguntar uma única vez após o login,
  // sem caixas pré-marcadas e sem impedir o uso de quem recusar.
  const [telemetryPrompt, setTelemetryPrompt] = useState(false);
  const [telemetryPromptBusy, setTelemetryPromptBusy] = useState(false);
  useEffect(() => {
    if (!session) { setTelemetryPrompt(false); return; }
    let active = true;
    invoke<string>("get_settings")
      .then((raw) => {
        const settings = JSON.parse(raw) as StorageSettings;
        if (active) setTelemetryPrompt(!settings.telemetry_consent_set);
      })
      .catch(() => { if (active) setTelemetryPrompt(false); });
    return () => { active = false; };
  }, [session]);
  async function chooseTelemetry(consent: boolean) {
    setTelemetryPromptBusy(true);
    try {
      await invoke("set_settings", { telemetryConsent: consent });
      setTelemetryPrompt(false);
      if (consent) void telemetry("app_started");
    } finally {
      setTelemetryPromptBusy(false);
    }
  }
  type TelemetryFields = { engine?: string; durationSeconds?: number; estimatedCostMicros?: number; errorCode?: string };
  async function telemetry(event: "app_started" | "transcription_completed" | "transcription_failed", fields: TelemetryFields = {}) {
    try {
      const appVersion = await getVersion();
      await invoke("telemetry_event", { event, appVersion, ...fields });
    } catch {
      // Telemetria nunca altera o percurso da pessoa nem mostra falhas na UI.
    }
  }
  useEffect(() => {
    if (session) void telemetry("app_started");
    // Só reenvia ao abrir uma nova sessão; o worker ignora se não houver opt-in.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);
  const [view, setView] = useState<View>("transcribe");
  const [libraryOpenRequest, setLibraryOpenRequest] = useState<LibraryOpenRequest | null>(null);
  const [adminExpanded, setAdminExpanded] = useState(true);
  const [adminSection, setAdminSection] = useState<AdminSection>("users");
  // Histórico de vistas para as setas voltar/avançar da barra de título
  const [histBack, setHistBack] = useState<View[]>([]);
  const [histFwd, setHistFwd] = useState<View[]>([]);
  function navTo(v: View) {
    if (v === view) return;
    setHistBack((h) => [...h, view]);
    setHistFwd([]);
    setView(v);
  }
  function openAdmin(section?: AdminSection) {
    if (section) setAdminSection(section);
    if (view !== "admin") navTo("admin");
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
  // undefined = a persistência ainda está a terminar; null = indisponível;
  // number = transcript pronto para ser retomado diretamente pela Library.
  const [resultTranscriptionId, setResultTranscriptionId] = useState<number | null | undefined>(undefined);
  const [showPostTranscriptionEducation, setShowPostTranscriptionEducation] = useState(
    () => localStorage.getItem("upexnote-post-transcription-education-v1") !== "seen"
  );
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
        setResultTranscriptionId(undefined);
        setStatus(obj.ok ? t("trDone") : t("trDoneWarn"));
        const costMicros = Number.isFinite(Number(obj.cost)) ? Math.max(0, Math.round(Number(obj.cost) * 1_000_000)) : undefined;
        void telemetry(obj.ok ? "transcription_completed" : "transcription_failed", {
          engine: selected?.id,
          durationSeconds: Number.isFinite(Number(obj.duration_s)) ? Math.max(0, Math.round(Number(obj.duration_s))) : undefined,
          estimatedCostMicros: costMicros,
          errorCode: obj.ok ? undefined : "TRANSCRIPTION_VALIDATION_FAILED",
        });
      } else if (obj.type === "transcription_saved") {
        const transcriptionId = Number(obj.transcription_id);
        setResultTranscriptionId(obj.saved && Number.isFinite(transcriptionId) && transcriptionId > 0 ? transcriptionId : null);
      } else if (obj.type === "error") {
        setStatus(t("errPrefix") + obj.message);
        void telemetry("transcription_failed", { engine: selected?.id, errorCode: "TRANSCRIPTION_ERROR" });
      }
    });
    const unlistenDone = listen("worker://done", () => setRunning(false));
    return () => {
      unlistenEvent.then((f) => f());
      unlistenDone.then((f) => f());
    };
    // re-subscreve quando o idioma muda, para o t do closure não ficar velho
  }, [t, selected]);

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
    setResultTranscriptionId(undefined);
    setStatus("");
    setStage(0);
    setElapsed(0);
  }

  async function startTranscription() {
    if (!file || !selected || running) return;
    setRunning(true);
    setResult(null);
    setResultTranscriptionId(undefined);
    setStage(1);
    setStatus(t("trStarting"));
    try {
      await invoke("transcribe", { engine: selected.id, file, dest: dest.trim() || null, user: getSession()?.id ?? null });
    } catch (e) {
      setStatus(t("errPrefix") + String(e));
      setRunning(false);
      void telemetry("transcription_failed", { engine: selected.id, errorCode: "TRANSCRIPTION_START_FAILED" });
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

  function acknowledgePostTranscriptionEducation() {
    localStorage.setItem("upexnote-post-transcription-education-v1", "seen");
    setShowPostTranscriptionEducation(false);
  }

  function continueInLibrary(openPreviewComposer: boolean) {
    acknowledgePostTranscriptionEducation();
    if (typeof resultTranscriptionId === "number") {
      setLibraryOpenRequest({
        transcriptionId: resultTranscriptionId,
        openPreviewComposer,
        nonce: Date.now(),
      });
    }
    navTo("library");
  }

  const navItems: { id: View; icon: ReactNode; label: string }[] = [
    { id: "transcribe", icon: <Mic size={16} strokeWidth={1.75} />, label: t("navTranscribe") },
    { id: "library", icon: <LibraryBig size={16} strokeWidth={1.75} />, label: t("navLibrary") },
    { id: "notebooks", icon: <BookOpen size={16} strokeWidth={1.75} />, label: t("navNotebooks") },
    { id: "settings", icon: <Settings size={16} strokeWidth={1.75} />, label: t("navSettings") },
  ];
  // A aba de Administração só existe para sessões admin (o worker revalida na
  // base de qualquer forma — isto é apresentação, não segurança).
  if (getSession()?.role !== "admin") {
    navItems.splice(3, 0, { id: "support", icon: <MessageCircle size={16} strokeWidth={1.75} />, label: t("navSupport") });
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
      {telemetryPrompt && (
        <div className="modal-overlay" role="presentation">
          <section className="modal-card telemetry-consent" role="dialog" aria-modal="true" aria-labelledby="telemetry-consent-title">
            <BrandMark size={30} />
            <h2 id="telemetry-consent-title">{t("telemetryConsentTitle")}</h2>
            <p>{t("telemetryConsentLead")}</p>
            <p className="telemetry-consent-detail">{t("telemetryConsentData")}</p>
            <p className="telemetry-consent-control">{t("telemetryConsentControl")}</p>
            <div className="telemetry-consent-actions">
              <button onClick={() => chooseTelemetry(true)} disabled={telemetryPromptBusy}>
                {t("telemetryConsentAccept")}
              </button>
              <button className="secondary" onClick={() => chooseTelemetry(false)} disabled={telemetryPromptBusy}>
                {t("telemetryConsentEssential")}
              </button>
            </div>
            <button className="link-btn telemetry-customize" disabled={telemetryPromptBusy} onClick={() => { setTelemetryPrompt(false); navTo("settings"); }}>
              {telemetryPromptBusy ? t("telemetryConsentSaving") : t("telemetryConsentCustomize")}
            </button>
          </section>
        </div>
      )}
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
          {getSession()?.role === "admin" && <>
            <button className={"nav-item admin-parent" + (view === "admin" ? " active" : "")} onClick={() => { setAdminExpanded((expanded) => !expanded); openAdmin(); }} title={t("navAdmin")} aria-expanded={adminExpanded}>
              <span className="nav-ico"><ShieldCheck size={16} strokeWidth={1.75} /></span>
              {!collapsed && <><span>{t("navAdmin")}</span><span className="nav-expand">{adminExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span></>}
            </button>
            {!collapsed && adminExpanded && <div className="admin-subnav">
              {([
                ["users", <Users size={15} />, t("admTabUsers")],
                ["activity", <Activity size={15} />, t("admTabActivity")],
                ["audit", <FileText size={15} />, t("admTabAudit")],
                ["telemetry", <BarChart3 size={15} />, "Telemetry"],
                ["support", <LifeBuoy size={15} />, t("admTabSupport")],
                ["data-studio", <Database size={15} />, t("dsTitle")],
              ] as const).map(([section, icon, label]) => <button key={section} className={"admin-subnav-item" + (view === "admin" && adminSection === section ? " active" : "")} onClick={() => openAdmin(section)}><span>{icon}</span>{label}</button>)}
            </div>}
          </>}
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
                <section className="card post-transcription-panel">
                  <div className="post-transcription-head">
                    <div>
                      <span className="preview-kicker">{t("postTrKicker")}</span>
                      <h2>{result.ok ? t("postTrTitle") : t("postTrTitleWarn")}</h2>
                      <p>{result.ok ? t("postTrHelp") : t("postTrHelpWarn")}</p>
                    </div>
                    <span className={`badge ${result.ok ? "ok" : "warn"}`}>
                      {result.ok ? t("valOk") : t("valWarn")}
                    </span>
                  </div>
                  <div className="post-transcription-actions">
                    <button className="secondary" onClick={() => {
                      acknowledgePostTranscriptionEducation();
                      transcriptRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                    }}>
                      <Eye size={16} aria-hidden="true" /> {t("postTrViewTranscript")}
                    </button>
                    {result.ok && (
                      <button
                        onClick={() => continueInLibrary(true)}
                        disabled={typeof resultTranscriptionId !== "number"}
                      >
                        <FileText size={16} aria-hidden="true" /> {t("postTrCreatePreview")}
                      </button>
                    )}
                    <button className="secondary" onClick={() => continueInLibrary(false)}>
                      <LibraryBig size={16} aria-hidden="true" /> {t("postTrOpenLibrary")}
                    </button>
                  </div>
                  {result.ok && resultTranscriptionId === undefined && (
                    <div className="muted post-transcription-state"><span className="spinner" /> {t("postTrSaving")}</div>
                  )}
                  {result.ok && resultTranscriptionId === null && (
                    <div className="key-warn post-transcription-state">{t("postTrSaveUnavailable")}</div>
                  )}
                  {showPostTranscriptionEducation && (
                    <div className="post-transcription-note">
                      <strong>{t("postTrLayersTitle")}</strong>
                      <span>{t("postTrLayersHelp")}</span>
                    </div>
                  )}
                </section>
              )}

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
            <LibraryView
              active={view === "library"}
              openRequest={libraryOpenRequest}
              onOpenRequestHandled={() => setLibraryOpenRequest(null)}
            />
          </div>

          <div className={"view-pane" + (view === "notebooks" ? "" : " hidden")}>
            <NotebooksView active={view === "notebooks"} />
          </div>

          {getSession()?.role !== "admin" && <div className={"view-pane" + (view === "support" ? "" : " hidden")}>
            <SupportView active={view === "support"} />
          </div>}

          {getSession()?.role === "admin" && (
            <div className={"view-pane" + (view === "admin" ? "" : " hidden")}>
              <AdminView active={view === "admin"} section={adminSection} />
            </div>
          )}

          <div className={"view-pane" + (view === "settings" ? "" : " hidden")}>
            <AppearanceCard {...appearance} />
            <TypographyCard prefs={font.prefs} setPrefs={font.setPrefs} />
            <MfaSettingsCard />
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
