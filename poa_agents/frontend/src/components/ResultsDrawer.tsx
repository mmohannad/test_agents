"use client";

import { useState } from "react";
import { JsonViewer } from "./JsonViewer";
import { useLocale } from "@/lib/i18n";

type AgentStepStatus = "idle" | "running" | "completed" | "error";

interface ResultsDrawerProps {
  condenserResult: Record<string, unknown> | string | null;
  legalSearchResult: Record<string, unknown> | string | null;
  legalSearchStatus: AgentStepStatus;
  legalSearchError: string | null;
  onClose: () => void;
}

// =====================================================================
// Type helpers — Legal Brief (condenser output)
// =====================================================================

interface CaseSummary {
  application_number?: string;
  transaction_type?: string;
  transaction_description?: string;
}

interface Party {
  role?: string;
  name_ar?: string;
  name_en?: string;
  qid?: string;
  nationality?: string;
  capacity_claimed?: string;
  capacity_evidence?: string;
  additional_attributes?: Record<string, unknown>;
}

interface RegisteredAuthority {
  person_name?: string;
  position?: string;
  authority_scope?: string;
  id_number?: string;
}

interface EntityInformation {
  company_name_ar?: string;
  company_name_en?: string;
  registration_number?: string;
  entity_type?: string;
  registered_authorities?: RegisteredAuthority[];
}

interface POADetails {
  poa_type?: string;
  poa_text_ar?: string;
  poa_text_en?: string;
  powers_granted?: string[];
  duration?: string;
  substitution_allowed?: boolean | string;
}

interface EvidenceItem {
  document_type?: string;
  key_facts_extracted?: string[];
  confidence?: number;
}

interface FactComparison {
  fact_type?: string;
  source_1?: { source?: string; value?: string };
  source_2?: { source?: string; value?: string };
  match?: boolean;
  notes?: string;
}

interface OpenQuestion {
  question_id?: string;
  category?: string;
  question?: string;
  relevant_facts?: string[];
  priority?: string;
}

interface LegalBrief {
  application_id?: string;
  generated_at?: string;
  extraction_confidence?: number;
  case_summary?: CaseSummary;
  parties?: Party[];
  entity_information?: EntityInformation;
  poa_details?: POADetails;
  evidence_summary?: EvidenceItem[];
  fact_comparisons?: FactComparison[];
  open_questions?: OpenQuestion[];
  missing_information?: string[];
}

// =====================================================================
// Type helpers — Legal Opinion (legal search output)
// =====================================================================

interface IssueAnalysis {
  issue_id?: string;
  issue_title?: string;
  category?: string;
  primary_question?: string;
  facts_considered?: string[];
  legal_analysis?: string;
  finding?: string;
  finding_status?: string;
  confidence?: number;
  reasoning?: string;
  reasoning_summary?: string;
  applicable_articles?: {
    article_number?: number;
    article_text?: string;
    text?: string;
    application_to_facts?: string;
    similarity_score?: number;
  }[];
  supporting_articles?: {
    article_number?: number;
    article_text?: string;
    text?: string;
    application_to_facts?: string;
    similarity_score?: number;
  }[];
  concerns?: string[];
}

interface Citation {
  citation_id?: string;
  article_number?: number;
  law_name?: string;
  chapter?: string;
  text_en?: string;
  text_ar?: string;
  text_arabic?: string;
  text_english?: string;
  quoted_text?: string;
  relevance?: string;
  similarity_score?: number;
}

interface RetrievalMetrics {
  total_iterations?: number;
  total_articles?: number;
  stop_reason?: string;
  coverage_score?: number;
  avg_similarity?: number;
  top_3_similarity?: number;
  total_llm_calls?: number;
  total_embedding_calls?: number;
  total_latency_ms?: number;
  estimated_cost_usd?: number;
}

interface LegalOpinion {
  application_id?: string;
  generated_at?: string;
  overall_finding?: string;
  decision_bucket?: string;
  confidence_score?: number;
  confidence_level?: string;
  opinion_summary_en?: string;
  opinion_summary_ar?: string;
  case_summary?: {
    application_type?: string;
    parties_involved?: string;
    core_question?: string;
    key_facts?: string[];
  };
  detailed_analysis?: {
    introduction?: string;
    issue_by_issue_analysis?: IssueAnalysis[];
    synthesis?: string;
    conclusion?: string;
  };
  findings?: IssueAnalysis[];
  issues_analyzed?: IssueAnalysis[];
  concerns?: string[];
  recommendations?: string[];
  conditions?: string[];
  citations?: Citation[];
  all_citations?: Citation[];
  grounding_score?: number;
  retrieval_coverage?: number;
  retrieval_metrics?: RetrievalMetrics;
}

// =====================================================================
// Main component
// =====================================================================

export function ResultsDrawer({
  condenserResult,
  legalSearchResult,
  legalSearchStatus,
  legalSearchError,
  onClose,
}: ResultsDrawerProps) {
  const { t } = useLocale();
  const [activeTab, setActiveTab] = useState<"brief" | "opinion" | "raw">("brief");

  const briefIsStructured = typeof condenserResult === "object" && condenserResult !== null;
  const brief: LegalBrief | null = briefIsStructured ? (condenserResult as LegalBrief) : null;

  const opinionIsStructured = typeof legalSearchResult === "object" && legalSearchResult !== null;
  const opinion: LegalOpinion | null = opinionIsStructured ? (legalSearchResult as LegalOpinion) : null;

  const tabs: { key: "brief" | "opinion" | "raw"; label: string }[] = [
    { key: "brief", label: t("resultsDrawer.legalBrief") },
    { key: "opinion", label: t("resultsDrawer.legalOpinion") },
    { key: "raw", label: t("resultsDrawer.rawJson") },
  ];

  return (
    <div className="border-t border-gray-700 bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-sm font-bold text-gray-100">{t("resultsDrawer.title")}</h2>
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  activeTab === tab.key
                    ? "bg-gray-700 text-gray-100"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {tab.label}
                {tab.key === "opinion" && legalSearchStatus === "running" && (
                  <span className="ml-1.5 inline-block h-2 w-2 animate-spin rounded-full border border-blue-400 border-t-transparent" />
                )}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 transition-colors text-sm"
        >
          {t("resultsDrawer.close")}
        </button>
      </div>

      {/* Body */}
      <div className="max-h-[50vh] overflow-y-auto px-6 py-4">
        {/* Legal Brief tab */}
        {activeTab === "brief" && (
          <div className="space-y-4">
            {brief ? (
              <>
                <ReportHeader brief={brief} />
                {brief.case_summary && <CaseSummarySection data={brief.case_summary} />}
                {brief.parties && brief.parties.length > 0 && <PartiesSection data={brief.parties} />}
                {brief.entity_information && <EntitySection data={brief.entity_information} />}
                {brief.poa_details && <POADetailsSection data={brief.poa_details} />}
                {brief.evidence_summary && brief.evidence_summary.length > 0 && (
                  <EvidenceSummarySection data={brief.evidence_summary} />
                )}
                {brief.fact_comparisons && brief.fact_comparisons.length > 0 && (
                  <FactComparisonsSection data={brief.fact_comparisons} />
                )}
                {brief.open_questions && brief.open_questions.length > 0 && (
                  <OpenQuestionsSection data={brief.open_questions} />
                )}
                {brief.missing_information && brief.missing_information.length > 0 && (
                  <MissingInfoSection data={brief.missing_information} />
                )}
              </>
            ) : condenserResult ? (
              <div className="bg-gray-800 rounded-lg p-4">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                  {typeof condenserResult === "string"
                    ? condenserResult
                    : JSON.stringify(condenserResult, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">{t("resultsDrawer.noCondenserResults")}</p>
            )}
          </div>
        )}

        {/* Legal Opinion tab */}
        {activeTab === "opinion" && (
          <div className="space-y-4">
            {legalSearchStatus === "running" && (
              <div className="flex items-center gap-3 bg-blue-950/30 border border-blue-900/50 rounded-lg px-4 py-3">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                <span className="text-sm text-blue-300">
                  {t("resultsDrawer.legalSearchRunning")}
                </span>
              </div>
            )}
            {legalSearchStatus === "error" && (
              <div className="bg-red-950/30 border border-red-800/50 rounded-lg px-4 py-3">
                <p className="text-sm text-red-400">{t("resultsDrawer.legalSearchFailed")}</p>
                {legalSearchError && (
                  <p className="text-xs text-red-300 mt-1">{legalSearchError}</p>
                )}
              </div>
            )}
            {legalSearchStatus === "idle" && !legalSearchResult && (
              <p className="text-gray-500 text-sm">
                {t("resultsDrawer.legalSearchPending")}
              </p>
            )}
            {opinion ? (
              <>
                <DecisionBanner opinion={opinion} />
                <OpinionSummarySection opinion={opinion} />
                <IssuesAnalyzedSection opinion={opinion} />
                {opinion.concerns && opinion.concerns.length > 0 && (
                  <StringListSection title={t("resultsDrawer.concerns")} items={opinion.concerns} color="yellow" />
                )}
                {opinion.recommendations && opinion.recommendations.length > 0 && (
                  <StringListSection title={t("resultsDrawer.recommendations")} items={opinion.recommendations} color="blue" />
                )}
                {opinion.conditions && opinion.conditions.length > 0 && (
                  <StringListSection title={t("resultsDrawer.conditions")} items={opinion.conditions} color="orange" />
                )}
                <CitationsSection opinion={opinion} />
                {opinion.retrieval_metrics && (
                  <RetrievalMetricsSection metrics={opinion.retrieval_metrics} grounding={opinion.grounding_score} coverage={opinion.retrieval_coverage} />
                )}
              </>
            ) : legalSearchResult && typeof legalSearchResult === "string" ? (
              <div className="bg-gray-800 rounded-lg p-4">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                  {legalSearchResult}
                </pre>
              </div>
            ) : null}
          </div>
        )}

        {/* Raw JSON tab */}
        {activeTab === "raw" && (
          <div className="space-y-4">
            {condenserResult && (
              <JsonViewer data={condenserResult} label={t("resultsDrawer.condenserLabel")} defaultOpen />
            )}
            {legalSearchResult && (
              <JsonViewer data={legalSearchResult} label={t("resultsDrawer.legalSearchLabel")} defaultOpen />
            )}
            {!condenserResult && !legalSearchResult && (
              <p className="text-gray-500 text-sm">{t("resultsDrawer.noResults")}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// =====================================================================
// Shared UI primitives
// =====================================================================

function Section({
  title,
  badge,
  children,
}: {
  title: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-700/30">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          {title}
        </h3>
        {badge}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function KV({
  label,
  value,
  mono,
  span,
  dir,
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
  span?: number;
  dir?: "ltr" | "rtl";
}) {
  return (
    <div style={span ? { gridColumn: `span ${span}` } : undefined}>
      <span className="text-[10px] text-gray-500">{label}</span>
      <p
        className={`text-xs text-gray-200 ${mono ? "font-mono" : ""} ${
          !value ? "text-gray-600 italic" : ""
        }`}
        dir={dir}
      >
        {value || "\u2014"}
      </p>
    </div>
  );
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = (value * 100).toFixed(0);
  const color =
    value >= 0.8
      ? "bg-green-900/50 text-green-400"
      : value >= 0.5
        ? "bg-yellow-900/50 text-yellow-400"
        : "bg-red-900/50 text-red-400";

  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${color}`}>
      {pct}%
    </span>
  );
}

function CollapsibleText({
  label,
  text,
  dir,
}: {
  label: string;
  text: string;
  dir?: "rtl" | "ltr";
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen(!open)}
        className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-400 transition-colors"
      >
        {open ? "\u25BE" : "\u25B8"} {label}
      </button>
      {open && (
        <pre
          dir={dir}
          className="mt-1 text-xs text-gray-400 whitespace-pre-wrap bg-gray-900/50 rounded p-3 max-h-48 overflow-y-auto"
        >
          {text}
        </pre>
      )}
    </div>
  );
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// =====================================================================
// Legal Brief sections (condenser output)
// =====================================================================

function ReportHeader({ brief }: { brief: LegalBrief }) {
  const { t } = useLocale();
  const confidence = brief.extraction_confidence;
  const confidenceColor =
    confidence != null
      ? confidence >= 0.8
        ? "text-green-400"
        : confidence >= 0.5
          ? "text-yellow-400"
          : "text-red-400"
      : null;

  return (
    <div className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
      <div className="flex items-center gap-6 text-sm">
        {brief.application_id && (
          <div>
            <span className="text-gray-500 text-xs">{t("resultsDrawer.application")}</span>
            <p className="text-gray-200 font-mono text-xs">{brief.application_id}</p>
          </div>
        )}
        {brief.generated_at && (
          <div>
            <span className="text-gray-500 text-xs">{t("resultsDrawer.generatedAt")}</span>
            <p className="text-gray-200 text-xs">
              {new Date(brief.generated_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>
      {confidence != null && (
        <div className="text-right">
          <span className="text-gray-500 text-xs">{t("resultsDrawer.extractionConfidence")}</span>
          <p className={`text-sm font-semibold ${confidenceColor}`}>
            {(confidence * 100).toFixed(0)}%
          </p>
        </div>
      )}
    </div>
  );
}

function CaseSummarySection({ data }: { data: CaseSummary }) {
  const { t } = useLocale();
  return (
    <Section title={t("resultsDrawer.caseSummary")}>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <KV label={t("resultsDrawer.applicationNumber")} value={data.application_number} />
        <KV label={t("resultsDrawer.transactionType")} value={data.transaction_type} />
        <KV label={t("resultsDrawer.description")} value={data.transaction_description} span={3} />
      </div>
    </Section>
  );
}

function PartiesSection({ data }: { data: Party[] }) {
  const { t } = useLocale();
  const grouped = new Map<string, Party[]>();
  for (const p of data) {
    const role = p.role ?? "unknown";
    if (!grouped.has(role)) grouped.set(role, []);
    grouped.get(role)!.push(p);
  }

  return (
    <Section
      title={t("resultsDrawer.parties")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? t("resultsDrawer.party") : t("resultsDrawer.partiesPlural")}
        </span>
      }
    >
      <div className="space-y-3">
        {Array.from(grouped.entries()).map(([role, parties]) => (
          <div key={role}>
            <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider">
              {role}
            </span>
            <div className="mt-1 space-y-2">
              {parties.map((p, i) => (
                <div
                  key={i}
                  className="bg-gray-900/50 rounded p-3 grid grid-cols-3 gap-x-4 gap-y-2 text-sm"
                >
                  <KV label={t("resultsDrawer.nameAr")} value={p.name_ar} dir="rtl" />
                  <KV label={t("resultsDrawer.nameEn")} value={p.name_en} />
                  <KV label={t("resultsDrawer.idNumber")} value={p.qid} mono />
                  <KV label={t("resultsDrawer.nationality")} value={p.nationality} />
                  <KV label={t("resultsDrawer.claimedCapacity")} value={p.capacity_claimed} />
                  <KV label={t("resultsDrawer.capacityEvidence")} value={p.capacity_evidence} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

function EntitySection({ data }: { data: EntityInformation }) {
  const { t } = useLocale();
  const authorities = data.registered_authorities ?? [];

  return (
    <Section title={t("resultsDrawer.entityInfo")}>
      <div className="grid grid-cols-4 gap-4 text-sm">
        <KV label={t("resultsDrawer.companyAr")} value={data.company_name_ar} dir="rtl" />
        <KV label={t("resultsDrawer.companyEn")} value={data.company_name_en} />
        <KV label={t("resultsDrawer.registrationNumber")} value={data.registration_number} mono />
        <KV label={t("resultsDrawer.entityType")} value={data.entity_type} />
      </div>
      {authorities.length > 0 && (
        <div className="mt-3">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            {t("resultsDrawer.registeredAuthorities")} ({authorities.length})
          </span>
          <table className="w-full mt-1 text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700/50">
                <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.name")}</th>
                <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.position")}</th>
                <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.authorityScope")}</th>
                <th className="text-right py-1.5 font-medium">{t("resultsDrawer.id")}</th>
              </tr>
            </thead>
            <tbody>
              {authorities.map((a, i) => (
                <tr key={i} className="border-b border-gray-800/30 text-gray-300">
                  <td className="py-1.5 pr-3">{a.person_name ?? "\u2014"}</td>
                  <td className="py-1.5 pr-3">{a.position ?? "\u2014"}</td>
                  <td className="py-1.5 pr-3 max-w-xs truncate" title={a.authority_scope}>
                    {a.authority_scope ?? "\u2014"}
                  </td>
                  <td className="py-1.5 font-mono">{a.id_number ?? "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

function POADetailsSection({ data }: { data: POADetails }) {
  const { t } = useLocale();
  const powers = data.powers_granted ?? [];
  const subst =
    data.substitution_allowed === true
      ? t("common.yes")
      : data.substitution_allowed === false
        ? t("common.no")
        : typeof data.substitution_allowed === "string"
          ? data.substitution_allowed
          : "\u2014";

  return (
    <Section title={t("resultsDrawer.poaDetails")}>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <KV label={t("resultsDrawer.type")} value={data.poa_type} />
        <KV label={t("resultsDrawer.duration")} value={data.duration} />
        <KV label={t("resultsDrawer.substitutionRight")} value={subst} />
      </div>
      {powers.length > 0 && (
        <div className="mt-3">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            {t("resultsDrawer.grantedPowers")} ({powers.length})
          </span>
          <ul className="mt-1 space-y-1">
            {powers.map((p, i) => (
              <li
                key={i}
                className="text-xs text-gray-300 pr-3 border-r-2 border-gray-700"
              >
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.poa_text_en && (
        <CollapsibleText label={t("resultsDrawer.poaTextEn")} text={data.poa_text_en} />
      )}
      {data.poa_text_ar && (
        <CollapsibleText label={t("resultsDrawer.poaTextAr")} text={data.poa_text_ar} dir="rtl" />
      )}
    </Section>
  );
}

function EvidenceSummarySection({ data }: { data: EvidenceItem[] }) {
  const { t } = useLocale();
  return (
    <Section
      title={t("resultsDrawer.evidenceSummary")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? t("resultsDrawer.document") : t("resultsDrawer.documentsPlural")}
        </span>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        {data.map((item, i) => (
          <div key={i} className="bg-gray-900/50 rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-200">
                {item.document_type ?? `${t("resultsDrawer.document")} ${i + 1}`}
              </span>
              {item.confidence != null && (
                <ConfidenceBadge value={item.confidence} />
              )}
            </div>
            {item.key_facts_extracted && item.key_facts_extracted.length > 0 && (
              <ul className="space-y-1">
                {item.key_facts_extracted.map((fact, j) => (
                  <li key={j} className="text-[11px] text-gray-400 flex gap-1.5">
                    <span className="text-gray-600 shrink-0">&bull;</span>
                    {fact}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}

function FactComparisonsSection({ data }: { data: FactComparison[] }) {
  const { t } = useLocale();
  return (
    <Section
      title={t("resultsDrawer.factComparisons")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? t("resultsDrawer.comparison") : t("resultsDrawer.comparisons")}
        </span>
      }
    >
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-700/50">
            <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.factType")}</th>
            <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.source1")}</th>
            <th className="text-right py-1.5 pr-3 font-medium">{t("resultsDrawer.source2")}</th>
            <th className="text-center py-1.5 pr-3 font-medium w-16">{t("resultsDrawer.match")}</th>
            <th className="text-right py-1.5 font-medium">{t("resultsDrawer.notes")}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((fc, i) => (
            <tr key={i} className="border-b border-gray-800/30 text-gray-300 align-top">
              <td className="py-2 pr-3 font-medium text-gray-200">
                {formatLabel(fc.fact_type ?? "")}
              </td>
              <td className="py-2 pr-3">
                {fc.source_1 && (
                  <>
                    <span className="text-gray-500">{fc.source_1.source}: </span>
                    {fc.source_1.value}
                  </>
                )}
              </td>
              <td className="py-2 pr-3">
                {fc.source_2 && (
                  <>
                    <span className="text-gray-500">{fc.source_2.source}: </span>
                    {fc.source_2.value}
                  </>
                )}
              </td>
              <td className="py-2 pr-3 text-center">
                {fc.match === true ? (
                  <span className="text-green-400 font-semibold">{t("common.yes")}</span>
                ) : fc.match === false ? (
                  <span className="text-red-400 font-semibold">{t("common.no")}</span>
                ) : (
                  <span className="text-gray-600">\u2014</span>
                )}
              </td>
              <td className="py-2 text-gray-400">{fc.notes ?? "\u2014"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function OpenQuestionsSection({ data }: { data: OpenQuestion[] }) {
  const { t } = useLocale();
  const priorities = ["critical", "important", "supplementary"];
  const grouped = new Map<string, OpenQuestion[]>();
  for (const q of data) {
    const prio = q.priority ?? "supplementary";
    if (!grouped.has(prio)) grouped.set(prio, []);
    grouped.get(prio)!.push(q);
  }

  const prioColor: Record<string, string> = {
    critical: "border-red-500 bg-red-950/30",
    important: "border-yellow-500 bg-yellow-950/20",
    supplementary: "border-gray-600 bg-gray-900/50",
  };

  const prioLabel: Record<string, string> = {
    critical: "text-red-400",
    important: "text-yellow-400",
    supplementary: "text-gray-500",
  };

  return (
    <Section
      title={t("resultsDrawer.openQuestions")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? t("resultsDrawer.question") : t("resultsDrawer.questions")}
        </span>
      }
    >
      <div className="space-y-4">
        {priorities.map((prio) => {
          const questions = grouped.get(prio);
          if (!questions || questions.length === 0) return null;
          return (
            <div key={prio}>
              <span
                className={`text-[10px] font-semibold uppercase tracking-wider ${prioLabel[prio] ?? "text-gray-500"}`}
              >
                {prio} ({questions.length})
              </span>
              <div className="mt-1 space-y-2">
                {questions.map((q, i) => (
                  <div
                    key={i}
                    className={`border-l-2 rounded-r p-3 ${prioColor[prio] ?? prioColor.supplementary}`}
                  >
                    <div className="flex items-start gap-2">
                      {q.question_id && (
                        <span className="text-[10px] font-mono text-gray-600 shrink-0 mt-0.5">
                          {q.question_id}
                        </span>
                      )}
                      <div className="flex-1">
                        <p className="text-xs text-gray-200">{q.question}</p>
                        {q.category && (
                          <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">
                            {q.category}
                          </span>
                        )}
                        {q.relevant_facts && q.relevant_facts.length > 0 && (
                          <div className="mt-1.5 space-y-0.5">
                            {q.relevant_facts.map((f, j) => (
                              <p key={j} className="text-[10px] text-gray-500 pl-2 border-l border-gray-700">
                                {f}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function MissingInfoSection({ data }: { data: string[] }) {
  const { t } = useLocale();
  return (
    <Section
      title={t("resultsDrawer.missingInfo")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? t("resultsDrawer.item") : t("resultsDrawer.items")}
        </span>
      }
    >
      <ul className="space-y-1.5">
        {data.map((item, i) => (
          <li key={i} className="text-xs text-gray-300 flex gap-2">
            <span className="text-yellow-600 shrink-0">!</span>
            {item}
          </li>
        ))}
      </ul>
    </Section>
  );
}

// =====================================================================
// Legal Opinion sections (legal search output)
// =====================================================================

function DecisionBanner({ opinion }: { opinion: LegalOpinion }) {
  const { t } = useLocale();
  const finding = opinion.overall_finding ?? "UNKNOWN";
  const bucket = opinion.decision_bucket ?? "unknown";
  const confidence = opinion.confidence_score;
  const level = opinion.confidence_level;

  const findingColors: Record<string, string> = {
    VALID: "bg-green-900/40 border-green-700 text-green-300",
    VALID_WITH_CONDITIONS: "bg-yellow-900/40 border-yellow-700 text-yellow-300",
    INVALID: "bg-red-900/40 border-red-700 text-red-300",
    REQUIRES_REVIEW: "bg-orange-900/40 border-orange-700 text-orange-300",
    INCONCLUSIVE: "bg-gray-800 border-gray-600 text-gray-300",
  };

  const findingLabels: Record<string, string> = {
    VALID: t("resultsDrawer.valid"),
    VALID_WITH_CONDITIONS: t("resultsDrawer.validWithConditions"),
    INVALID: t("resultsDrawer.invalid"),
    REQUIRES_REVIEW: t("resultsDrawer.requiresReview"),
    INCONCLUSIVE: t("resultsDrawer.inconclusive"),
  };

  const bucketLabels: Record<string, string> = {
    valid: t("resultsDrawer.validBucket"),
    valid_with_remediations: t("resultsDrawer.validWithRemediations"),
    invalid: t("resultsDrawer.invalidBucket"),
    needs_review: t("resultsDrawer.needsReview"),
  };

  const bannerClass = findingColors[finding] ?? findingColors.INCONCLUSIVE;

  return (
    <div className={`border rounded-lg px-5 py-4 ${bannerClass}`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold">{findingLabels[finding] ?? finding.replace(/_/g, " ")}</span>
            <span className="text-xs px-2 py-0.5 rounded bg-black/20">
              {bucketLabels[bucket] ?? bucket}
            </span>
          </div>
          {opinion.generated_at && (
            <p className="text-[10px] mt-1 opacity-70">
              {t("resultsDrawer.generatedAt")} {new Date(opinion.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        {confidence != null && (
          <div className="text-right">
            <p className="text-2xl font-bold">{(confidence * 100).toFixed(0)}%</p>
            {level && <p className="text-[10px] uppercase tracking-wider opacity-70">{t("resultsDrawer.confidenceLevel")} {level}</p>}
          </div>
        )}
      </div>
    </div>
  );
}

function OpinionSummarySection({ opinion }: { opinion: LegalOpinion }) {
  const { t } = useLocale();
  const en = opinion.opinion_summary_en;
  const ar = opinion.opinion_summary_ar;
  if (!en && !ar) return null;

  return (
    <Section title={t("resultsDrawer.opinionSummary")}>
      {ar && (
        <p dir="rtl" className="text-sm text-gray-300 leading-relaxed">
          {ar}
        </p>
      )}
      {en && (
        <div className={ar ? "mt-3" : ""}>
          {ar && <span className="text-[10px] text-gray-500 uppercase tracking-wider">{t("resultsDrawer.englishSummary")}</span>}
          <p className={`text-sm text-gray-300 leading-relaxed ${ar ? "mt-1" : ""}`}>
            {en}
          </p>
        </div>
      )}
    </Section>
  );
}

function IssuesAnalyzedSection({ opinion }: { opinion: LegalOpinion }) {
  const { t } = useLocale();
  // Issues can be in different places depending on the output structure
  const issues =
    opinion.detailed_analysis?.issue_by_issue_analysis ??
    opinion.issues_analyzed ??
    opinion.findings ??
    [];

  if (issues.length === 0) return null;

  const findingColor: Record<string, string> = {
    SUPPORTED: "text-green-400",
    NOT_SUPPORTED: "text-red-400",
    PARTIALLY_SUPPORTED: "text-yellow-400",
    UNCLEAR: "text-orange-400",
  };

  return (
    <Section
      title={t("resultsDrawer.issuesAnalyzed")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {issues.length} {issues.length === 1 ? t("resultsDrawer.issue") : t("resultsDrawer.issues")}
        </span>
      }
    >
      <div className="space-y-3">
        {issues.map((issue, i) => {
          const finding = issue.finding ?? issue.finding_status ?? "UNKNOWN";
          const conf = issue.confidence;
          const articles = issue.applicable_articles ?? issue.supporting_articles ?? [];

          return (
            <div key={i} className="bg-gray-900/50 rounded-lg p-4 space-y-2">
              {/* Header row */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {issue.issue_id && (
                      <span className="text-[10px] font-mono text-gray-600">
                        {issue.issue_id}
                      </span>
                    )}
                    <span className="text-xs font-medium text-gray-200">
                      {issue.issue_title ?? issue.category ?? `${t("resultsDrawer.issue")} ${i + 1}`}
                    </span>
                  </div>
                  {issue.category && issue.issue_title && (
                    <span className="inline-block mt-0.5 text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500">
                      {issue.category}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-xs font-semibold ${findingColor[finding] ?? "text-gray-400"}`}>
                    {finding.replace(/_/g, " ")}
                  </span>
                  {conf != null && <ConfidenceBadge value={conf} />}
                </div>
              </div>

              {/* Question */}
              {issue.primary_question && (
                <p className="text-[11px] text-gray-400 italic">{issue.primary_question}</p>
              )}

              {/* Analysis/Reasoning */}
              {(issue.legal_analysis || issue.reasoning || issue.reasoning_summary) && (
                <p className="text-xs text-gray-300">
                  {issue.legal_analysis || issue.reasoning || issue.reasoning_summary}
                </p>
              )}

              {/* Supporting articles */}
              {articles.length > 0 && (
                <div className="mt-1">
                  <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">
                    {t("resultsDrawer.supportingArticles")} ({articles.length})
                  </span>
                  <div className="mt-1 space-y-1">
                    {articles.map((art, j) => (
                      <div key={j} className="text-[11px] text-gray-400 pl-2 border-l border-gray-700">
                        <span className="font-medium text-gray-300">
                          {t("resultsDrawer.article")} {art.article_number}
                        </span>
                        {" \u2014 "}
                        {(art.article_text || art.application_to_facts || art.text || "").slice(0, 200)}
                        {((art.article_text || art.application_to_facts || art.text || "").length > 200 ? "..." : "")}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Per-issue concerns */}
              {issue.concerns && issue.concerns.length > 0 && (
                <div className="mt-1">
                  <span className="text-[10px] text-yellow-500 font-semibold uppercase tracking-wider">
                    {t("resultsDrawer.concerns")}
                  </span>
                  <ul className="mt-0.5 space-y-0.5">
                    {issue.concerns.map((c, j) => (
                      <li key={j} className="text-[11px] text-yellow-400/70 pl-2 border-l border-yellow-800/50">
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function StringListSection({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: "yellow" | "blue" | "orange";
}) {
  const colors = {
    yellow: { border: "border-yellow-700/50", text: "text-yellow-400/80", icon: "text-yellow-600" },
    blue: { border: "border-blue-700/50", text: "text-blue-400/80", icon: "text-blue-600" },
    orange: { border: "border-orange-700/50", text: "text-orange-400/80", icon: "text-orange-600" },
  }[color];

  return (
    <Section title={title} badge={<span className="text-[10px] text-gray-600 font-normal">{items.length}</span>}>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className={`text-xs ${colors.text} flex gap-2 pl-2 border-l ${colors.border}`}>
            {item}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function CitationsSection({ opinion }: { opinion: LegalOpinion }) {
  const { t } = useLocale();
  const citations = opinion.all_citations ?? opinion.citations ?? [];
  if (citations.length === 0) return null;

  return (
    <Section
      title={t("resultsDrawer.citations")}
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {citations.length} {citations.length === 1 ? t("resultsDrawer.article") : t("resultsDrawer.articlesCount")}
        </span>
      }
    >
      <div className="space-y-2">
        {citations.map((c, i) => (
          <div key={i} className="bg-gray-900/50 rounded p-3">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-gray-200">
                  {t("resultsDrawer.article")} {c.article_number}
                </span>
                {c.law_name && (
                  <span className="text-[10px] text-gray-500 italic">{c.law_name}</span>
                )}
              </div>
              {c.similarity_score != null && (
                <span className="text-[10px] text-gray-500">
                  {t("resultsDrawer.similarity")}: {(c.similarity_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {(c.quoted_text || c.text_ar || c.text_arabic || c.text_en || c.text_english) && (() => {
              const displayText = c.quoted_text || c.text_ar || c.text_arabic || c.text_en || c.text_english || "";
              // Arabic text if any Arabic field is used
              const isArabic = !!(c.text_ar || c.text_arabic || (!c.text_en && !c.text_english && c.quoted_text));
              return (
                <p className="text-[11px] text-gray-400 leading-relaxed" dir={isArabic ? "rtl" : "ltr"}>
                  {displayText.slice(0, 300)}
                  {displayText.length > 300 ? "..." : ""}
                </p>
              );
            })()}
            {c.relevance && (
              <p className="text-[10px] text-gray-500 mt-1 italic">{c.relevance}</p>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}

function RetrievalMetricsSection({
  metrics,
  grounding,
  coverage,
}: {
  metrics: RetrievalMetrics;
  grounding?: number;
  coverage?: number;
}) {
  const { t } = useLocale();
  return (
    <Section title={t("resultsDrawer.verificationMetrics")}>
      <div className="grid grid-cols-2 gap-4">
        {/* Scores */}
        <div className="space-y-2">
          {grounding != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">{t("resultsDrawer.groundingScore")}</span>
              <ConfidenceBadge value={grounding} />
            </div>
          )}
          {coverage != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">{t("resultsDrawer.retrievalCoverage")}</span>
              <ConfidenceBadge value={coverage} />
            </div>
          )}
          {metrics.coverage_score != null && coverage == null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">{t("resultsDrawer.coverageScore")}</span>
              <ConfidenceBadge value={metrics.coverage_score} />
            </div>
          )}
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
          {metrics.total_iterations != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.iterations")}</span>
              <span className="text-gray-300 font-mono">{metrics.total_iterations}</span>
            </div>
          )}
          {metrics.total_articles != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.articles")}</span>
              <span className="text-gray-300 font-mono">{metrics.total_articles}</span>
            </div>
          )}
          {metrics.stop_reason && (
            <div className="flex justify-between col-span-2">
              <span className="text-gray-500">{t("resultsDrawer.stopReason")}</span>
              <span className="text-gray-300">{metrics.stop_reason}</span>
            </div>
          )}
          {metrics.avg_similarity != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.avgSimilarity")}</span>
              <span className="text-gray-300 font-mono">{(metrics.avg_similarity * 100).toFixed(0)}%</span>
            </div>
          )}
          {metrics.top_3_similarity != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.top3Similarity")}</span>
              <span className="text-gray-300 font-mono">{(metrics.top_3_similarity * 100).toFixed(0)}%</span>
            </div>
          )}
          {metrics.total_latency_ms != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.responseTime")}</span>
              <span className="text-gray-300 font-mono">{(metrics.total_latency_ms / 1000).toFixed(1)}s</span>
            </div>
          )}
          {metrics.estimated_cost_usd != null && (
            <div className="flex justify-between">
              <span className="text-gray-500">{t("resultsDrawer.estimatedCost")}</span>
              <span className="text-gray-300 font-mono">${metrics.estimated_cost_usd.toFixed(4)}</span>
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}
