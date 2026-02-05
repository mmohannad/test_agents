"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";
import { EditableField } from "./EditableField";
import { JsonViewer } from "./JsonViewer";

interface UnstructuredPanelProps {
  data: {
    document_extractions: Record<string, unknown>[];
  };
  onUpdateExtraction: (extractionIndex: number, key: string, value: string) => void;
  onUpdateExtractedField: (extractionIndex: number, fieldKey: string, value: unknown) => void;
}

function ConfidenceBadge({ value, t }: { value: number; t: (key: string) => string }) {
  const pct = Math.round(value * 100);
  let color = "text-red-400 bg-red-950";
  if (pct >= 80) color = "text-green-400 bg-green-950";
  else if (pct >= 60) color = "text-yellow-400 bg-yellow-950";

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${color}`}>
      {pct}% {t("common.confidence")}
    </span>
  );
}

function getDocTypeLabel(code: string, t: (key: string) => string): string {
  const key = `docTypes.${code}`;
  const translated = t(key);
  // If no translation found (key returned as-is), fall back to formatting the code
  return translated !== key ? translated : code.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function UnstructuredPanel({ data, onUpdateExtraction, onUpdateExtractedField }: UnstructuredPanelProps) {
  const { t } = useLocale();
  const extractions = data.document_extractions;
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-bold text-gray-100">
          {t("unstructuredPanel.title")}
        </h2>
        <span className="text-xs text-gray-600">{t("common.clickToEdit")}</span>
      </div>

      {extractions.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 text-center">
          <p className="text-gray-500 text-sm">
            {t("unstructuredPanel.noExtractions")}
          </p>
        </div>
      ) : (
        <>
          {/* Tab bar */}
          <div className="flex gap-1 border-b border-gray-800 pb-0">
            {extractions.map((ext, i) => {
              const rawCode = String(
                ext.document_type_code || ext.file_name || `Doc ${i + 1}`
              );
              let docType = getDocTypeLabel(rawCode, t);
              // Disambiguate tabs by appending person name from extracted_fields
              const fields = ext.extracted_fields as Record<string, unknown> | null;
              if (fields) {
                const name = fields.first_name || fields.name_en || fields.company_name_en;
                if (name) docType += ` — ${String(name)}`;
              }
              return (
                <button
                  key={i}
                  onClick={() => setActiveTab(i)}
                  className={`px-3 py-2 text-xs font-medium rounded-t-md transition-colors ${
                    activeTab === i
                      ? "bg-gray-800 text-gray-100 border border-gray-700 border-b-gray-800"
                      : "text-gray-500 hover:text-gray-300 hover:bg-gray-900"
                  }`}
                >
                  {docType}
                </button>
              );
            })}
          </div>

          {/* Active document extraction */}
          {extractions.map((ext, i) => {
            if (i !== activeTab) return null;
            const rawAr = ext.raw_text_ar as string | null;
            const rawEn = ext.raw_text_en as string | null;
            const extractedFields = ext.extracted_fields as Record<
              string,
              unknown
            > | null;
            const confidence = ext.ocr_confidence as number | null;
            const update = (key: string, value: string) => onUpdateExtraction(i, key, value);

            return (
              <div key={i} className="space-y-4">
                {/* Metadata row */}
                <div className="flex items-center gap-3 text-xs text-gray-400">
                  <span>
                    Doc ID:{" "}
                    <span className="text-gray-300 font-mono">
                      {String(ext.document_id || ext.id || "?")}
                    </span>
                  </span>
                  {confidence !== null && confidence !== undefined && (
                    <ConfidenceBadge value={confidence} t={t} />
                  )}
                  {ext.extraction_model ? (
                    <span>Model: {String(ext.extraction_model)}</span>
                  ) : null}
                </div>

                {/* Arabic text — editable */}
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    {t("unstructuredPanel.rawTextAr")}
                  </h4>
                  <EditableField
                    label=""
                    value={rawAr}
                    fieldKey="raw_text_ar"
                    onChange={update}
                    multiline
                    dir="rtl"
                  />
                </div>

                {/* English text — editable */}
                <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                    {t("unstructuredPanel.rawTextEn")}
                  </h4>
                  <EditableField
                    label=""
                    value={rawEn}
                    fieldKey="raw_text_en"
                    onChange={update}
                    multiline
                  />
                </div>

                {!rawAr && !rawEn && (
                  <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-center">
                    <p className="text-gray-500 text-sm italic">
                      {t("unstructuredPanel.noRawText")}
                    </p>
                  </div>
                )}

                {/* Extracted Fields */}
                {extractedFields &&
                  Object.keys(extractedFields).length > 0 && (
                    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                        {t("unstructuredPanel.extractedFields")}
                      </h4>
                      <ExtractedFieldsView
                        fields={extractedFields}
                        onFieldChange={(key, value) => onUpdateExtractedField(i, key, value)}
                      />
                    </div>
                  )}

                {/* Raw JSON for this extraction */}
                <JsonViewer data={ext} label={t("common.rawJson")} />
              </div>
            );
          })}
        </>
      )}

      {/* Full payload raw JSON */}
      <JsonViewer data={data} label={t("unstructuredPanel.fullUnstructuredJson")} />
    </div>
  );
}

/* ---- Clean renderer for extracted_fields ---- */

function formatFieldLabel(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ExtractedFieldsView({
  fields,
  onFieldChange,
}: {
  fields: Record<string, unknown>;
  onFieldChange: (key: string, value: unknown) => void;
}) {
  const scalarFields: [string, unknown][] = [];
  const arrayFields: [string, unknown[]][] = [];
  const objectFields: [string, Record<string, unknown>][] = [];

  for (const [key, value] of Object.entries(fields)) {
    if (Array.isArray(value)) {
      arrayFields.push([key, value]);
    } else if (value !== null && typeof value === "object") {
      objectFields.push([key, value as Record<string, unknown>]);
    } else {
      scalarFields.push([key, value]);
    }
  }

  return (
    <div className="space-y-4">
      {/* Scalar fields — editable */}
      {scalarFields.length > 0 && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {scalarFields.map(([key]) => (
            <EditableField
              key={key}
              label={formatFieldLabel(key)}
              value={fields[key]}
              fieldKey={key}
              onChange={(k, v) => onFieldChange(k, v)}
            />
          ))}
        </div>
      )}

      {/* Object fields — each child editable */}
      {objectFields.map(([key, obj]) => (
        <div key={key}>
          <h5 className="text-xs font-semibold text-gray-400 mb-2">{formatFieldLabel(key)}</h5>
          <div className="bg-gray-800/50 rounded p-3 grid grid-cols-2 gap-x-4 gap-y-1">
            {Object.entries(obj).map(([k]) => (
              <EditableField
                key={k}
                label={formatFieldLabel(k)}
                value={obj[k]}
                fieldKey={k}
                onChange={(childKey, v) => {
                  onFieldChange(key, { ...obj, [childKey]: v });
                }}
              />
            ))}
          </div>
        </div>
      ))}

      {/* Array fields — each item's children editable */}
      {arrayFields.map(([key, arr]) => (
        <div key={key}>
          <h5 className="text-xs font-semibold text-gray-400 mb-2">
            {formatFieldLabel(key)}
            <span className="text-gray-600 font-normal ml-2">({arr.length})</span>
          </h5>
          <div className="space-y-2">
            {arr.map((item, idx) => {
              if (item !== null && typeof item === "object" && !Array.isArray(item)) {
                const obj = item as Record<string, unknown>;
                const title =
                  obj.name_en || obj.name_ar || obj.name || obj.type || obj.document_type;
                return (
                  <div key={idx} className="bg-gray-800/50 border border-gray-700/50 rounded p-3">
                    {title ? (
                      <div className="text-xs font-medium text-gray-200 mb-2">
                        {String(title)}
                      </div>
                    ) : null}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                      {Object.entries(obj).map(([k]) => (
                        <EditableField
                          key={k}
                          label={formatFieldLabel(k)}
                          value={obj[k]}
                          fieldKey={k}
                          onChange={(childKey, v) => {
                            const newArr = [...arr];
                            newArr[idx] = { ...obj, [childKey]: v };
                            onFieldChange(key, newArr);
                          }}
                        />
                      ))}
                    </div>
                  </div>
                );
              }
              // Primitive array items — editable
              return (
                <EditableField
                  key={idx}
                  label={`${formatFieldLabel(key)} ${idx + 1}`}
                  value={item}
                  fieldKey={String(idx)}
                  onChange={(_, v) => {
                    const newArr = [...arr];
                    newArr[idx] = v;
                    onFieldChange(key, newArr);
                  }}
                />
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
