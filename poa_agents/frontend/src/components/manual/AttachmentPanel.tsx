"use client";

import { useState } from "react";
import {
  ATTACHMENT_TYPES,
  ATTACHMENT_FIELD_SCHEMAS,
  type AttachmentTypeCode,
  type ManualAttachment,
  type Signatory,
  createEmptyAttachment,
  createEmptySignatory,
} from "@/lib/manualDefaults";

interface AttachmentPanelProps {
  attachments: ManualAttachment[];
  onAttachmentsChange: (attachments: ManualAttachment[]) => void;
}

const typeEntries = Object.entries(ATTACHMENT_TYPES) as [AttachmentTypeCode, string][];

const SIGNATORY_POSITIONS = ["director", "partner", "manager", "authorized signatory", "CEO", "chairman"];

function SignatoryCard({
  signatory,
  index,
  onChange,
  onRemove,
}: {
  signatory: Signatory;
  index: number;
  onChange: (s: Signatory) => void;
  onRemove: () => void;
}) {
  const update = (key: keyof Signatory, value: string) =>
    onChange({ ...signatory, [key]: value });

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded p-3 space-y-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-300">Signatory #{index + 1}</span>
        <button
          onClick={onRemove}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors"
        >
          Remove
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-gray-400 mb-0.5">Name</label>
          <input
            type="text"
            value={signatory.name_en}
            onChange={(e) => update("name_en", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-0.5">QID</label>
          <input
            type="text"
            value={signatory.identification_number}
            onChange={(e) => update("identification_number", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-0.5">Nationality</label>
          <input
            type="text"
            value={signatory.nationality_en}
            onChange={(e) => update("nationality_en", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-0.5">Percentage</label>
          <input
            type="text"
            value={signatory.percentage}
            onChange={(e) => update("percentage", e.target.value)}
            placeholder="e.g. 100"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="col-span-2">
          <label className="block text-xs text-gray-400 mb-0.5">Position</label>
          <select
            value={signatory.position}
            onChange={(e) => update("position", e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          >
            <option value="">— Select —</option>
            {SIGNATORY_POSITIONS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

export function AttachmentPanel({ attachments, onAttachmentsChange }: AttachmentPanelProps) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [showTypeSelector, setShowTypeSelector] = useState(false);

  const active = attachments[activeIdx] ?? null;

  const updateAttachment = (idx: number, patch: Partial<ManualAttachment>) => {
    const updated = [...attachments];
    updated[idx] = { ...updated[idx], ...patch, saved: false };
    onAttachmentsChange(updated);
  };

  const addAttachment = (typeCode: AttachmentTypeCode) => {
    const newAtt = createEmptyAttachment(typeCode);
    const updated = [...attachments, newAtt];
    onAttachmentsChange(updated);
    setActiveIdx(updated.length - 1);
    setShowTypeSelector(false);
  };

  const removeAttachment = (idx: number) => {
    const updated = attachments.filter((_, i) => i !== idx);
    onAttachmentsChange(updated);
    if (activeIdx >= updated.length) {
      setActiveIdx(Math.max(0, updated.length - 1));
    }
  };

  const saveAttachment = () => {
    if (!active) return;
    const updated = [...attachments];
    updated[activeIdx] = { ...active, saved: true };
    onAttachmentsChange(updated);
  };

  const updateField = (fieldKey: string, value: string) => {
    if (!active) return;
    updateAttachment(activeIdx, {
      extractedFields: { ...active.extractedFields, [fieldKey]: value },
    });
  };

  const updateRawText = (key: "rawTextAr" | "rawTextEn", value: string) => {
    if (!active) return;
    updateAttachment(activeIdx, { [key]: value });
  };

  // Signatory helpers
  const addSignatory = () => {
    if (!active) return;
    updateAttachment(activeIdx, {
      signatories: [...active.signatories, createEmptySignatory()],
    });
  };

  const updateSignatory = (sigIdx: number, s: Signatory) => {
    if (!active) return;
    const sigs = [...active.signatories];
    sigs[sigIdx] = s;
    updateAttachment(activeIdx, { signatories: sigs });
  };

  const removeSignatory = (sigIdx: number) => {
    if (!active) return;
    updateAttachment(activeIdx, {
      signatories: active.signatories.filter((_, i) => i !== sigIdx),
    });
  };

  const isCR = active?.documentTypeCode === "COMMERCIAL_REGISTRATION";

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-bold text-gray-100">
          SAK Attachment Extraction (OCR)
        </h2>
        <span className="text-xs text-gray-500">Manual Entry</span>
      </div>

      {/* Attachment instance tabs */}
      <div className="flex items-center gap-1 border-b border-gray-700 pb-0 overflow-x-auto">
        {attachments.map((att, idx) => {
          const label = ATTACHMENT_TYPES[att.documentTypeCode] ?? att.documentTypeCode;
          const isActive = idx === activeIdx;
          return (
            <button
              key={att.id}
              onClick={() => setActiveIdx(idx)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-t transition-colors whitespace-nowrap ${
                isActive
                  ? "bg-gray-800 text-blue-400 border-b-2 border-blue-500"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <span>#{idx + 1} {label}</span>
              {att.saved && (
                <span className="text-green-400 text-[10px]" title="Saved">&#10003;</span>
              )}
              {!att.saved && Object.values(att.extractedFields).some(v => v !== "") && (
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" title="Unsaved changes" />
              )}
              <span
                onClick={(e) => {
                  e.stopPropagation();
                  removeAttachment(idx);
                }}
                className="text-gray-600 hover:text-red-400 ml-1 cursor-pointer"
                title="Remove attachment"
              >
                x
              </span>
            </button>
          );
        })}

        <button
          onClick={() => setShowTypeSelector(!showTypeSelector)}
          className="px-3 py-1.5 text-xs text-green-400 hover:text-green-300 hover:bg-gray-800/50 rounded-t transition-colors whitespace-nowrap"
        >
          + Add Attachment
        </button>
      </div>

      {/* Type selector dropdown */}
      {showTypeSelector && (
        <div className="bg-gray-800 border border-gray-700 rounded p-2 space-y-1">
          <p className="text-xs text-gray-400 mb-1">Select attachment type:</p>
          <div className="grid grid-cols-2 gap-1">
            {typeEntries.map(([code, label]) => (
              <button
                key={code}
                onClick={() => addAttachment(code)}
                className="text-left px-2 py-1.5 text-xs text-gray-200 hover:bg-gray-700 rounded transition-colors"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Active attachment form */}
      {active ? (
        <div className="space-y-4">
          {/* Extracted fields */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider border-b border-gray-700 pb-1 mb-3">
              Extracted Fields
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {ATTACHMENT_FIELD_SCHEMAS[active.documentTypeCode].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs text-gray-400 mb-1">{field.label}</label>
                  <input
                    type={field.type ?? "text"}
                    value={active.extractedFields[field.key] ?? ""}
                    onChange={(e) => updateField(field.key, e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* CR: Authorized Signatories */}
          {isCR && (
            <div>
              <div className="flex items-center justify-between border-b border-gray-700 pb-1 mb-3">
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                  Authorized Signatories
                </h3>
                <button
                  onClick={addSignatory}
                  className="text-xs text-green-400 hover:text-green-300 transition-colors"
                >
                  + Add Signatory
                </button>
              </div>
              {active.signatories.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No signatories added yet</p>
              ) : (
                <div className="space-y-3">
                  {active.signatories.map((sig, sigIdx) => (
                    <SignatoryCard
                      key={sigIdx}
                      signatory={sig}
                      index={sigIdx}
                      onChange={(s) => updateSignatory(sigIdx, s)}
                      onRemove={() => removeSignatory(sigIdx)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Raw text fields */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider border-b border-gray-700 pb-1 mb-3">
              Raw Text
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Raw Text (Arabic)</label>
                <textarea
                  value={active.rawTextAr}
                  onChange={(e) => updateRawText("rawTextAr", e.target.value)}
                  dir="rtl"
                  rows={3}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 resize-y"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Raw Text (English)</label>
                <textarea
                  value={active.rawTextEn}
                  onChange={(e) => updateRawText("rawTextEn", e.target.value)}
                  rows={3}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 resize-y"
                />
              </div>
            </div>
          </div>

          {/* Save button */}
          <div className="flex items-center gap-3 pt-2 border-t border-gray-700">
            <button
              onClick={saveAttachment}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                active.saved
                  ? "bg-gray-700 text-gray-400 cursor-default"
                  : "bg-blue-600 text-white hover:bg-blue-500"
              }`}
            >
              {active.saved ? "Saved" : "Save Attachment"}
            </button>
            {active.saved && (
              <span className="text-xs text-green-400">Attachment details saved</span>
            )}
            {!active.saved && Object.values(active.extractedFields).some(v => v !== "") && (
              <span className="text-xs text-yellow-400">Unsaved changes</span>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-40 text-gray-500 text-sm">
          Click &quot;+ Add Attachment&quot; to create an attachment entry
        </div>
      )}
    </div>
  );
}
