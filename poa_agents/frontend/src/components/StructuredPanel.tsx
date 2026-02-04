"use client";

import { useState } from "react";
import { EditableField } from "./EditableField";
import { JsonViewer } from "./JsonViewer";

interface StructuredPanelProps {
  data: {
    application: Record<string, unknown>;
    parties: Record<string, unknown>[];
    capacity_proofs: Record<string, unknown>[];
  };
  onUpdateApplication: (key: string, value: string) => void;
  onUpdateParty: (partyIndex: number, key: string, value: string) => void;
  onUpdateCapacityProof: (proofIndex: number, key: string, value: unknown) => void;
}

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <h3 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
        {title}
      </h3>
      {count !== undefined && (
        <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
          {count}
        </span>
      )}
    </div>
  );
}

function partyTypeLabel(partyType: string) {
  switch (partyType) {
    case "first_party": return "First Party";
    case "second_party": return "Second Party";
    case "third_party": return "Third Party";
    default: return partyType;
  }
}

function roleBadgeColor(role: string) {
  switch (role?.toLowerCase()) {
    case "grantor": return "bg-purple-900/50 text-purple-300 border-purple-700";
    case "agent": return "bg-blue-900/50 text-blue-300 border-blue-700";
    case "seller": return "bg-orange-900/50 text-orange-300 border-orange-700";
    case "buyer": return "bg-green-900/50 text-green-300 border-green-700";
    default: return "bg-gray-800 text-gray-300 border-gray-700";
  }
}

export function StructuredPanel({
  data,
  onUpdateApplication,
  onUpdateParty,
  onUpdateCapacityProof,
}: StructuredPanelProps) {
  const app = data.application;
  const parties = data.parties;
  const proofs = data.capacity_proofs;

  // Collect granted powers with their proof index for editing
  const powerEntries: { proofIndex: number; powerIndex: number; ar: string; en: string }[] = [];
  for (let pi = 0; pi < proofs.length; pi++) {
    const proof = proofs[pi];
    const powersAr = Array.isArray(proof.granted_powers) ? proof.granted_powers : [];
    const powersEn = Array.isArray(proof.granted_powers_en) ? proof.granted_powers_en : [];
    const len = Math.max(powersAr.length, powersEn.length);
    for (let i = 0; i < len; i++) {
      powerEntries.push({
        proofIndex: pi,
        powerIndex: i,
        ar: String(powersAr[i] ?? ""),
        en: String(powersEn[i] ?? ""),
      });
    }
  }

  return (
    <div className="p-5 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-bold text-gray-100">Structured Context</h2>
        <span className="text-xs text-gray-600">click any field to edit</span>
      </div>

      {/* Application */}
      <section className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-1">
        <SectionHeader title="Application" />
        <EditableField label="Application Number" value={app.application_number} fieldKey="application_number" onChange={onUpdateApplication} />
        <EditableField label="Status" value={app.status} fieldKey="status" onChange={onUpdateApplication} />
        <EditableField label="Processing Stage" value={app.processing_stage} fieldKey="processing_stage" onChange={onUpdateApplication} />
        <EditableField label="Transaction Type" value={app.transaction_type_code} fieldKey="transaction_type_code" onChange={onUpdateApplication} />
        <EditableField label="Transaction Value" value={app.transaction_value} fieldKey="transaction_value" onChange={onUpdateApplication} />
        <EditableField label="Subject (EN)" value={app.transaction_subject_en} fieldKey="transaction_subject_en" onChange={onUpdateApplication} />
        <EditableField label="Subject (AR)" value={app.transaction_subject_ar} fieldKey="transaction_subject_ar" onChange={onUpdateApplication} dir="rtl" />
        <EditableField label="POA Duration Type" value={app.poa_duration_type} fieldKey="poa_duration_type" onChange={onUpdateApplication} />
        <EditableField label="POA Start Date" value={app.poa_start_date} fieldKey="poa_start_date" onChange={onUpdateApplication} />
        <EditableField label="POA End Date" value={app.poa_end_date} fieldKey="poa_end_date" onChange={onUpdateApplication} />
        <EditableField label="Submitted" value={app.submitted_at} fieldKey="submitted_at" onChange={onUpdateApplication} />
      </section>

      {/* Parties */}
      <section className="space-y-3">
        <SectionHeader title="Parties" count={parties.length} />
        {parties.length === 0 && (
          <p className="text-gray-600 text-sm italic">No parties found</p>
        )}
        {parties.map((party, i) => {
          const role = String(party.party_role || "unknown");
          const pType = String(party.party_type || "");
          const update = (key: string, value: string) => onUpdateParty(i, key, value);
          return (
            <div
              key={String(party.id) || i}
              className={`border rounded-lg p-4 space-y-1 ${roleBadgeColor(role)}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider">
                  {role}
                </span>
                <span className="text-xs opacity-60">
                  ({partyTypeLabel(pType)})
                </span>
              </div>

              <EditableField label="Full Name (EN)" value={party.full_name_en} fieldKey="full_name_en" onChange={update} />
              <EditableField label="Full Name (AR)" value={party.full_name_ar} fieldKey="full_name_ar" onChange={update} dir="rtl" />
              <EditableField label="Capacity" value={party.capacity} fieldKey="capacity" onChange={update} />
              <EditableField label="ID Type" value={party.national_id_type} fieldKey="national_id_type" onChange={update} />
              <EditableField label="ID Number" value={party.national_id} fieldKey="national_id" onChange={update} />
              <EditableField label="ID Expiry" value={party.id_validity_date} fieldKey="id_validity_date" onChange={update} />
              <EditableField label="Citizenship" value={party.nationality_code} fieldKey="nationality_code" onChange={update} />
              <EditableField label="Gender" value={party.gender} fieldKey="gender" onChange={update} />
              <EditableField label="Phone" value={party.phone} fieldKey="phone" onChange={update} />
              <EditableField label="Email" value={party.email} fieldKey="email" onChange={update} />
            </div>
          );
        })}
      </section>

      {/* Permissions / Powers to be Granted */}
      <section className="space-y-3">
        <SectionHeader title="Permissions to be Granted" count={powerEntries.length} />
        {powerEntries.length === 0 ? (
          <p className="text-gray-600 text-sm italic">No permissions/powers found</p>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <EditablePowersList
              entries={powerEntries}
              proofs={proofs}
              onUpdateProof={onUpdateCapacityProof}
            />
          </div>
        )}
      </section>

      {/* POA Full Text (from capacity proofs) */}
      {proofs.map((proof, pi) => {
        const textAr = proof.poa_full_text_ar as string | null;
        const textEn = proof.poa_full_text_en as string | null;
        if (!textAr && !textEn) return null;
        return (
          <section key={pi} className="space-y-3">
            <SectionHeader title={`POA Full Text (Proof ${pi + 1})`} />
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
              {/* Capacity proof metadata */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-3">
                <EditableField label="Capacity Type" value={proof.capacity_type} fieldKey="capacity_type" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="CR Number" value={proof.cr_number} fieldKey="cr_number" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="Company Name" value={proof.company_name} fieldKey="company_name" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="CR Expiry" value={proof.cr_expiry_date} fieldKey="cr_expiry_date" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="POA Date" value={proof.poa_date} fieldKey="poa_date" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="POA Expiry" value={proof.poa_expiry} fieldKey="poa_expiry" onChange={(k, v) => onUpdateCapacityProof(pi, k, v)} />
                <EditableField label="General POA" value={proof.is_general_poa ? "Yes" : "No"} fieldKey="is_general_poa" onChange={(k, v) => onUpdateCapacityProof(pi, k, v === "Yes" || v === "yes" || v === "true")} />
                <EditableField label="Special POA" value={proof.is_special_poa ? "Yes" : "No"} fieldKey="is_special_poa" onChange={(k, v) => onUpdateCapacityProof(pi, k, v === "Yes" || v === "yes" || v === "true")} />
                <EditableField label="Substitution Right" value={proof.has_substitution_right ? "Yes" : "No"} fieldKey="has_substitution_right" onChange={(k, v) => onUpdateCapacityProof(pi, k, v === "Yes" || v === "yes" || v === "true")} />
              </div>

              {textEn && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">English</h4>
                  <EditableField
                    label=""
                    value={textEn}
                    fieldKey="poa_full_text_en"
                    onChange={(k, v) => onUpdateCapacityProof(pi, k, v)}
                    multiline
                  />
                </div>
              )}
              {textAr && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Arabic</h4>
                  <EditableField
                    label=""
                    value={textAr}
                    fieldKey="poa_full_text_ar"
                    onChange={(k, v) => onUpdateCapacityProof(pi, k, v)}
                    multiline
                    dir="rtl"
                  />
                </div>
              )}
            </div>
          </section>
        );
      })}

      {/* Raw JSON */}
      <JsonViewer data={data} label="Full Structured Payload (Raw JSON)" />
    </div>
  );
}

/* ---- Editable Powers List ---- */

function EditablePowersList({
  entries,
  proofs,
  onUpdateProof,
}: {
  entries: { proofIndex: number; powerIndex: number; ar: string; en: string }[];
  proofs: Record<string, unknown>[];
  onUpdateProof: (proofIndex: number, key: string, value: unknown) => void;
}) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [draftEn, setDraftEn] = useState("");
  const [draftAr, setDraftAr] = useState("");

  const startEdit = (idx: number) => {
    setEditingIdx(idx);
    setDraftEn(entries[idx].en);
    setDraftAr(entries[idx].ar);
  };

  const commit = () => {
    if (editingIdx === null) return;
    const entry = entries[editingIdx];
    const proof = proofs[entry.proofIndex];

    const powersEn = Array.isArray(proof.granted_powers_en) ? [...proof.granted_powers_en] : [];
    const powersAr = Array.isArray(proof.granted_powers) ? [...proof.granted_powers] : [];
    powersEn[entry.powerIndex] = draftEn;
    powersAr[entry.powerIndex] = draftAr;

    onUpdateProof(entry.proofIndex, "granted_powers_en", powersEn);
    onUpdateProof(entry.proofIndex, "granted_powers", powersAr);
    setEditingIdx(null);
  };

  return (
    <ul className="space-y-2">
      {entries.map((power, j) => {
        if (editingIdx === j) {
          return (
            <li key={j} className="space-y-1 bg-gray-800 rounded p-2">
              <input
                autoFocus
                type="text"
                value={draftEn}
                onChange={(e) => setDraftEn(e.target.value)}
                placeholder="English"
                className="w-full bg-gray-900 border border-blue-600 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none"
                onKeyDown={(e) => { if (e.key === "Escape") setEditingIdx(null); }}
              />
              <input
                type="text"
                value={draftAr}
                onChange={(e) => setDraftAr(e.target.value)}
                placeholder="Arabic"
                dir="rtl"
                className="w-full bg-gray-900 border border-blue-600 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none"
                onKeyDown={(e) => {
                  if (e.key === "Enter") commit();
                  if (e.key === "Escape") setEditingIdx(null);
                }}
              />
              <div className="flex gap-2 mt-1">
                <button onClick={commit} className="text-xs text-blue-400 hover:text-blue-300">Save</button>
                <button onClick={() => setEditingIdx(null)} className="text-xs text-gray-500 hover:text-gray-400">Cancel</button>
              </div>
            </li>
          );
        }
        return (
          <li
            key={j}
            className="flex items-start gap-3 text-sm group cursor-pointer hover:bg-gray-800/50 rounded px-1 -mx-1 py-1 transition-colors"
            onClick={() => startEdit(j)}
          >
            <span className="text-emerald-500 mt-0.5 shrink-0">&#x2713;</span>
            <div className="flex-1">
              <span className="text-gray-200">{power.en || power.ar}</span>
              {power.en && power.ar && (
                <span className="text-gray-500 text-xs block" dir="rtl">{power.ar}</span>
              )}
            </div>
            <span className="text-gray-700 text-xs opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
              edit
            </span>
          </li>
        );
      })}
    </ul>
  );
}
