// Leitor de documento estruturado (ADF-01, passo 2 ponto 3) — SÓ LEITURA.
//
// Porquê só leitura: é o menor passo que já entrega valor e valida o contrato
// de blocos na prática, antes de investir no editor da ADF-02. O editor cresce
// por cima desta vista, não ao lado dela.
//
// Contrato de dados (worker: db.document_item):
//   hub + blocks[] ordenados por position + jargon[] + métricas.
// ARMADILHA REAL: `content` é guardado como TEXT no banco, portanto blocos
// cujo conteúdo é lista ou dicionário chegam aqui como STRING JSON. Sem o
// parse abaixo, a tela mostraria JSON cru em vez de uma lista de ações.
import {
  ArrowLeft, BookOpen, CircleHelp, Clock3, Copy, FileText, Hash,
  ListChecks, NotebookPen, Quote, ShieldCheck, Target, TriangleAlert,
} from "lucide-react";
import type { TFn } from "./i18n";

export type DocBlock = {
  block_key: string;
  block_type: string;
  heading: string | null;
  content: string | null;
  speaker: string | null;
  block_timestamp: string | null;
};
export type DocJargon = { term: string; meaning: string };

/** Referência leve devolvida por `library_item` — o suficiente para listar. */
export type DocRef = {
  id: number;
  profile: string | null;
  title: string | null;
  created_at: string | null;
  engine: string | null;
  // ADF-02 fatia 4: id da nota já criada a partir deste documento, se
  // existir — decide "Salvar no Caderno" vs "Abrir no Caderno" sem 2ª ida ao worker.
  notebook_note_id: number | null;
};

export type DocDetail = {
  id: number;
  created_at: string | null;
  edited_at: string | null;
  transcription_id: number | null;
  engine: string | null;
  profile: string | null;
  title: string | null;
  objective: string | null;
  raw_clean_check_ok: boolean | null;
  processing_s: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  blocks: DocBlock[];
  jargon: DocJargon[];
  notebook_note_id: number | null;
};

const TYPE_ICON: Record<string, typeof FileText> = {
  section: FileText,
  objective: Target,
  requirement: ListChecks,
  decision: ShieldCheck,
  action: ListChecks,
  risk: TriangleAlert,
  question: CircleHelp,
  topic: Hash,
  technical_context: BookOpen,
  excerpt: Quote,
};

const TYPE_LABEL: Record<string, string> = {
  section: "docTypeSection",
  objective: "docTypeObjective",
  requirement: "docTypeRequirement",
  decision: "docTypeDecision",
  action: "docTypeAction",
  risk: "docTypeRisk",
  question: "docTypeQuestion",
  topic: "docTypeTopic",
  technical_context: "docTypeTechnicalContext",
  excerpt: "docTypeExcerpt",
};

const PROFILE_LABEL: Record<string, string> = {
  detalhado: "docProfileDetalhado",
  resumo_tecnico: "docProfileResumo",
  estudo: "docProfileEstudo",
};

/** Tenta reconstruir a estrutura original; devolve a string se não for JSON. */
function parseContent(raw: string | null): unknown {
  if (raw == null) return null;
  const s = raw.trim();
  if (!s) return null;
  if (s.startsWith("[") || s.startsWith("{")) {
    try {
      return JSON.parse(s);
    } catch {
      return raw; // conteúdo legítimo que começa por [ ou { — mostra como texto
    }
  }
  return raw;
}

function humanKey(k: string): string {
  return k.replace(/[_-]+/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function isScalar(v: unknown): v is string | number | boolean {
  return typeof v === "string" || typeof v === "number" || typeof v === "boolean";
}

function FieldList({ obj }: { obj: Record<string, unknown> }) {
  const entries = Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (entries.length === 0) return null;
  return (
    <dl className="doc-fields">
      {entries.map(([k, v]) => (
        <div className="doc-field" key={k}>
          <dt>{humanKey(k)}</dt>
          <dd>{isScalar(v) ? String(v) : JSON.stringify(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

function BlockContent({ value }: { value: unknown }) {
  if (value === null || value === undefined) return null;

  if (typeof value === "string") {
    const paras = value.split(/\n{2,}/).filter((p) => p.trim());
    return (
      <>
        {paras.map((p, i) => (
          <p className="doc-para" key={i}>{p}</p>
        ))}
      </>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return null;
    if (value.every(isScalar)) {
      return (
        <ul className="doc-list">
          {value.map((v, i) => <li key={i}>{String(v)}</li>)}
        </ul>
      );
    }
    return (
      <div className="doc-cards">
        {value.map((v, i) =>
          v && typeof v === "object" && !Array.isArray(v)
            ? <FieldList key={i} obj={v as Record<string, unknown>} />
            : <p className="doc-para" key={i}>{String(v)}</p>
        )}
      </div>
    );
  }

  if (typeof value === "object") return <FieldList obj={value as Record<string, unknown>} />;
  return <p className="doc-para">{String(value)}</p>;
}

function Block({ block, t }: { block: DocBlock; t: TFn }) {
  const Icon = TYPE_ICON[block.block_type] ?? FileText;
  const labelKey = TYPE_LABEL[block.block_type];
  const typeLabel = labelKey ? t(labelKey as never) : block.block_type;
  const value = parseContent(block.content);
  const empty = value === null;

  return (
    <article className={`doc-block doc-block-${block.block_type}`} id={`block-${block.block_key}`}>
      <header className="doc-block-head">
        <Icon size={15} aria-hidden="true" />
        <h3>{block.heading || typeLabel}</h3>
        <span className="doc-type-tag" title={typeLabel}>{typeLabel}</span>
      </header>
      {(block.speaker || block.block_timestamp) && (
        <div className="doc-block-meta">
          {block.speaker && <span>{t("docSpeaker", { name: block.speaker })}</span>}
          {block.block_timestamp && (
            <span><Clock3 size={12} aria-hidden="true" /> {block.block_timestamp}</span>
          )}
        </div>
      )}
      {empty ? <p className="muted doc-para">{t("docBlockEmpty")}</p> : <BlockContent value={value} />}
    </article>
  );
}

export default function DocumentReader({
  doc, t, locale, onBack, engineLabel, fmtDate,
  onSaveToNotebook, onOpenInNotebook, savingToNotebook,
}: {
  doc: DocDetail;
  t: TFn;
  locale: string;
  onBack: () => void;
  engineLabel: (id: string) => string;
  fmtDate: (iso: string | null, locale: string) => string;
  // ADF-02 fatia 4 ("Salvar no Caderno") — ambos opcionais: quem só quer o
  // leitor (ex.: uso futuro fora da Library) continua a funcionar sem eles.
  onSaveToNotebook?: () => void;
  onOpenInNotebook?: (noteId: number) => void;
  savingToNotebook?: boolean;
}) {
  const profileKey = doc.profile ? PROFILE_LABEL[doc.profile] : undefined;
  const profileLabel = profileKey ? t(profileKey as never) : (doc.profile || "—");

  /** Texto portável do documento — o princípio de portabilidade da ADF-05. */
  function plainText(): string {
    const parts: string[] = [];
    if (doc.title) parts.push(doc.title);
    if (doc.objective) parts.push(`${t("docObjective")}: ${doc.objective}`);
    for (const b of doc.blocks) {
      const v = parseContent(b.content);
      const head = b.heading || (TYPE_LABEL[b.block_type] ? t(TYPE_LABEL[b.block_type] as never) : b.block_type);
      const body = typeof v === "string" ? v : v == null ? "" : JSON.stringify(v, null, 2);
      parts.push(`\n## ${head}\n${body}`.trimEnd());
    }
    if (doc.jargon.length) {
      parts.push(`\n## ${t("docGlossary")}`);
      for (const j of doc.jargon) parts.push(`- ${j.term}: ${j.meaning}`);
    }
    return parts.join("\n");
  }

  return (
    <section className="card doc-reader">
      <div className="detail-head">
        <button className="secondary" onClick={onBack}>
          <ArrowLeft size={14} aria-hidden="true" /> {t("docBackToTranscript")}
        </button>
        <h2 className="doc-title" title={doc.title || undefined}>
          {doc.title || t("docTitleFallback", { id: doc.id })}
        </h2>
        <button className="secondary" onClick={() => navigator.clipboard.writeText(plainText())}>
          <Copy size={14} aria-hidden="true" /> {t("copy")}
        </button>
        {onSaveToNotebook && onOpenInNotebook && (
          doc.notebook_note_id != null ? (
            <button className="secondary" onClick={() => onOpenInNotebook(doc.notebook_note_id!)}>
              <NotebookPen size={14} aria-hidden="true" /> {t("nbOpenInNotebook")}
            </button>
          ) : (
            <button className="secondary" onClick={onSaveToNotebook} disabled={savingToNotebook}>
              <NotebookPen size={14} aria-hidden="true" /> {savingToNotebook ? t("nbSavingToNotebook") : t("nbSaveToNotebook")}
            </button>
          )
        )}
      </div>

      <div className="result-head">
        <span
          className="badge badge-id"
          title={t("idTooltip")}
          onClick={() => navigator.clipboard.writeText(String(doc.id))}
        >
          #{doc.id}
        </span>
        <span className="badge">{engineLabel(doc.engine ?? "")}</span>
        <span className="badge">{profileLabel}</span>
        {doc.raw_clean_check_ok === true && <span className="badge ok">{t("docCheckOk")}</span>}
        {doc.raw_clean_check_ok === false && <span className="badge warn-badge">{t("docCheckWarn")}</span>}
        <span className="badge">{fmtDate(doc.created_at, locale)}</span>
        {doc.processing_s != null && (
          <span className="badge">{t("docProcessing", { s: doc.processing_s.toFixed(1) })}</span>
        )}
        {(doc.input_tokens != null || doc.output_tokens != null) && (
          <span className="badge">
            {t("docTokens", { inp: doc.input_tokens ?? 0, out: doc.output_tokens ?? 0 })}
          </span>
        )}
      </div>

      {doc.objective && (
        <div className="doc-objective">
          <Target size={15} aria-hidden="true" />
          <div>
            <div className="doc-objective-label">{t("docObjective")}</div>
            <p className="doc-para">{doc.objective}</p>
          </div>
        </div>
      )}

      <div className="doc-body">
        {doc.blocks.length === 0 ? (
          <div className="muted doc-empty">{t("docNoBlocks")}</div>
        ) : (
          doc.blocks.map((b) => <Block key={b.block_key} block={b} t={t} />)
        )}
      </div>

      {doc.jargon.length > 0 && (
        <div className="doc-glossary">
          <h3><BookOpen size={15} aria-hidden="true" /> {t("docGlossary")}</h3>
          <dl className="doc-fields">
            {doc.jargon.map((j, i) => (
              <div className="doc-field" key={i}>
                <dt>{j.term}</dt>
                <dd>{j.meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="muted doc-foot">{t("docDerivedNote")}</div>
    </section>
  );
}
