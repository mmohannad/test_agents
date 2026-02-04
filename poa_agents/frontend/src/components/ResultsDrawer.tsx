"use client";

import { useState } from "react";
import { JsonViewer } from "./JsonViewer";

interface ResultsDrawerProps {
  result: Record<string, unknown> | string;
  onClose: () => void;
}

// --- Type helpers for the legal brief JSON ---

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

export function ResultsDrawer({ result, onClose }: ResultsDrawerProps) {
  const [activeTab, setActiveTab] = useState<"report" | "raw">("report");

  const isStructured = typeof result === "object";
  const brief: LegalBrief | null = isStructured ? (result as LegalBrief) : null;

  return (
    <div className="border-t border-gray-700 bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <h2 className="text-sm font-bold text-gray-100">Agent Results</h2>
          <div className="flex gap-1">
            <button
              onClick={() => setActiveTab("report")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === "report"
                  ? "bg-gray-700 text-gray-100"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Structured Report
            </button>
            <button
              onClick={() => setActiveTab("raw")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === "raw"
                  ? "bg-gray-700 text-gray-100"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              Raw JSON
            </button>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 transition-colors text-sm"
        >
          Close
        </button>
      </div>

      {/* Body */}
      <div className="max-h-[50vh] overflow-y-auto px-6 py-4">
        {activeTab === "report" && (
          <div className="space-y-4">
            {brief ? (
              <>
                <ReportHeader brief={brief} />
                {brief.case_summary && (
                  <CaseSummarySection data={brief.case_summary} />
                )}
                {brief.parties && brief.parties.length > 0 && (
                  <PartiesSection data={brief.parties} />
                )}
                {brief.entity_information && (
                  <EntitySection data={brief.entity_information} />
                )}
                {brief.poa_details && (
                  <POADetailsSection data={brief.poa_details} />
                )}
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
            ) : (
              <div className="bg-gray-800 rounded-lg p-4">
                <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono">
                  {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}

        {activeTab === "raw" && (
          <JsonViewer data={result} label="Full Agent Response" defaultOpen />
        )}
      </div>
    </div>
  );
}

// --- Section wrapper ---

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

// --- Header ---

function ReportHeader({ brief }: { brief: LegalBrief }) {
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
            <span className="text-gray-500 text-xs">Application</span>
            <p className="text-gray-200 font-mono text-xs">{brief.application_id}</p>
          </div>
        )}
        {brief.generated_at && (
          <div>
            <span className="text-gray-500 text-xs">Generated</span>
            <p className="text-gray-200 text-xs">
              {new Date(brief.generated_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>
      {confidence != null && (
        <div className="text-right">
          <span className="text-gray-500 text-xs">Extraction Confidence</span>
          <p className={`text-sm font-semibold ${confidenceColor}`}>
            {(confidence * 100).toFixed(0)}%
          </p>
        </div>
      )}
    </div>
  );
}

// --- Case Summary ---

function CaseSummarySection({ data }: { data: CaseSummary }) {
  return (
    <Section title="Case Summary">
      <div className="grid grid-cols-3 gap-4 text-sm">
        <KV label="Application #" value={data.application_number} />
        <KV label="Transaction Type" value={data.transaction_type} />
        <KV label="Description" value={data.transaction_description} span={3} />
      </div>
    </Section>
  );
}

// --- Parties ---

function PartiesSection({ data }: { data: Party[] }) {
  // Group by role
  const grouped = new Map<string, Party[]>();
  for (const p of data) {
    const role = p.role ?? "unknown";
    if (!grouped.has(role)) grouped.set(role, []);
    grouped.get(role)!.push(p);
  }

  return (
    <Section
      title="Parties"
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? "party" : "parties"}
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
                  <KV label="Name (AR)" value={p.name_ar} />
                  <KV label="Name (EN)" value={p.name_en} />
                  <KV label="QID" value={p.qid} mono />
                  <KV label="Nationality" value={p.nationality} />
                  <KV label="Capacity Claimed" value={p.capacity_claimed} />
                  <KV label="Capacity Evidence" value={p.capacity_evidence} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

// --- Entity Information ---

function EntitySection({ data }: { data: EntityInformation }) {
  const authorities = data.registered_authorities ?? [];

  return (
    <Section title="Entity Information">
      <div className="grid grid-cols-4 gap-4 text-sm">
        <KV label="Company (AR)" value={data.company_name_ar} />
        <KV label="Company (EN)" value={data.company_name_en} />
        <KV label="Reg. Number" value={data.registration_number} mono />
        <KV label="Entity Type" value={data.entity_type} />
      </div>
      {authorities.length > 0 && (
        <div className="mt-3">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            Registered Authorities ({authorities.length})
          </span>
          <table className="w-full mt-1 text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700/50">
                <th className="text-left py-1.5 pr-3 font-medium">Name</th>
                <th className="text-left py-1.5 pr-3 font-medium">Position</th>
                <th className="text-left py-1.5 pr-3 font-medium">Authority Scope</th>
                <th className="text-left py-1.5 font-medium">ID</th>
              </tr>
            </thead>
            <tbody>
              {authorities.map((a, i) => (
                <tr key={i} className="border-b border-gray-800/30 text-gray-300">
                  <td className="py-1.5 pr-3">{a.person_name ?? "—"}</td>
                  <td className="py-1.5 pr-3">{a.position ?? "—"}</td>
                  <td className="py-1.5 pr-3 max-w-xs truncate" title={a.authority_scope}>
                    {a.authority_scope ?? "—"}
                  </td>
                  <td className="py-1.5 font-mono">{a.id_number ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

// --- POA Details ---

function POADetailsSection({ data }: { data: POADetails }) {
  const powers = data.powers_granted ?? [];
  const subst =
    data.substitution_allowed === true
      ? "Yes"
      : data.substitution_allowed === false
        ? "No"
        : typeof data.substitution_allowed === "string"
          ? data.substitution_allowed
          : "—";

  return (
    <Section title="POA Details">
      <div className="grid grid-cols-3 gap-4 text-sm">
        <KV label="Type" value={data.poa_type} />
        <KV label="Duration" value={data.duration} />
        <KV label="Substitution Allowed" value={subst} />
      </div>
      {powers.length > 0 && (
        <div className="mt-3">
          <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
            Powers Granted ({powers.length})
          </span>
          <ul className="mt-1 space-y-1">
            {powers.map((p, i) => (
              <li
                key={i}
                className="text-xs text-gray-300 pl-3 border-l-2 border-gray-700"
              >
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.poa_text_en && (
        <CollapsibleText label="POA Text (EN)" text={data.poa_text_en} />
      )}
      {data.poa_text_ar && (
        <CollapsibleText label="POA Text (AR)" text={data.poa_text_ar} dir="rtl" />
      )}
    </Section>
  );
}

// --- Evidence Summary ---

function EvidenceSummarySection({ data }: { data: EvidenceItem[] }) {
  return (
    <Section
      title="Evidence Summary"
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? "document" : "documents"}
        </span>
      }
    >
      <div className="grid grid-cols-2 gap-3">
        {data.map((item, i) => (
          <div key={i} className="bg-gray-900/50 rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-200">
                {item.document_type ?? `Document ${i + 1}`}
              </span>
              {item.confidence != null && (
                <ConfidenceBadge value={item.confidence} />
              )}
            </div>
            {item.key_facts_extracted && item.key_facts_extracted.length > 0 && (
              <ul className="space-y-1">
                {item.key_facts_extracted.map((fact, j) => (
                  <li key={j} className="text-[11px] text-gray-400 flex gap-1.5">
                    <span className="text-gray-600 shrink-0">•</span>
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

// --- Fact Comparisons ---

function FactComparisonsSection({ data }: { data: FactComparison[] }) {
  return (
    <Section
      title="Fact Comparisons"
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? "comparison" : "comparisons"}
        </span>
      }
    >
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-500 border-b border-gray-700/50">
            <th className="text-left py-1.5 pr-3 font-medium">Fact</th>
            <th className="text-left py-1.5 pr-3 font-medium">Source 1</th>
            <th className="text-left py-1.5 pr-3 font-medium">Source 2</th>
            <th className="text-center py-1.5 pr-3 font-medium w-16">Match</th>
            <th className="text-left py-1.5 font-medium">Notes</th>
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
                  <span className="text-green-400 font-semibold">Yes</span>
                ) : fc.match === false ? (
                  <span className="text-red-400 font-semibold">No</span>
                ) : (
                  <span className="text-gray-600">—</span>
                )}
              </td>
              <td className="py-2 text-gray-400">{fc.notes ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

// --- Open Questions ---

function OpenQuestionsSection({ data }: { data: OpenQuestion[] }) {
  // Group by priority
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
      title="Open Questions"
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? "question" : "questions"}
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

// --- Missing Information ---

function MissingInfoSection({ data }: { data: string[] }) {
  return (
    <Section
      title="Missing Information"
      badge={
        <span className="text-[10px] text-gray-600 font-normal">
          {data.length} {data.length === 1 ? "item" : "items"}
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

// --- Shared UI primitives ---

function KV({
  label,
  value,
  mono,
  span,
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
  span?: number;
}) {
  return (
    <div style={span ? { gridColumn: `span ${span}` } : undefined}>
      <span className="text-[10px] text-gray-500">{label}</span>
      <p
        className={`text-xs text-gray-200 ${mono ? "font-mono" : ""} ${
          !value ? "text-gray-600 italic" : ""
        }`}
      >
        {value || "—"}
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
        {open ? "▾" : "▸"} {label}
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
