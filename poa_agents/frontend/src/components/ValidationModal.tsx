"use client";

import { useLocale } from "@/lib/i18n";
import type { ValidationFinding } from "@/lib/validation";

interface ValidationModalProps {
  findings: ValidationFinding[];
  onClose: () => void;
  onProceedAnyway: () => void;
}

export function ValidationModal({
  findings,
  onClose,
  onProceedAnyway,
}: ValidationModalProps) {
  const { t } = useLocale();
  const errors = findings.filter((f) => f.severity === "error");
  const warnings = findings.filter((f) => f.severity === "warning");
  const hasErrors = errors.length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-800">
          <div className={`h-3 w-3 rounded-full ${hasErrors ? "bg-red-500" : "bg-yellow-500"}`} />
          <h2 className="text-lg font-bold text-gray-100">
            {hasErrors ? t("validation.tier1Failed") : t("validation.tier1Warnings")}
          </h2>
          <span className="ml-auto text-xs text-gray-500">
            {errors.length} {t("validation.errorCount")}، {warnings.length} {t("validation.warningCount")}
          </span>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Errors */}
          {errors.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider mb-2">
                {t("validation.errors")}
              </h3>
              <div className="space-y-2">
                {errors.map((f, i) => (
                  <FindingCard key={`err-${i}`} finding={f} />
                ))}
              </div>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-2">
                {t("validation.warnings")}
              </h3>
              <div className="space-y-2">
                {warnings.map((f, i) => (
                  <FindingCard key={`warn-${i}`} finding={f} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-800">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-gray-100 transition-colors"
          >
            {t("validation.goBackAndFix")}
          </button>
          {!hasErrors && (
            <button
              onClick={onProceedAnyway}
              className="px-4 py-2 bg-yellow-600 text-white text-sm font-medium rounded-md hover:bg-yellow-500 transition-colors"
            >
              {t("validation.proceedWithWarnings")}
            </button>
          )}
          {hasErrors && (
            <span className="text-xs text-red-400 italic">
              {t("validation.fixErrors")}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function FindingCard({ finding }: { finding: ValidationFinding }) {
  const isError = finding.severity === "error";
  const borderColor = isError ? "border-red-800" : "border-yellow-800";
  const bgColor = isError ? "bg-red-950/40" : "bg-yellow-950/40";
  const badgeColor = isError
    ? "bg-red-900 text-red-300"
    : "bg-yellow-900 text-yellow-300";

  return (
    <div className={`${bgColor} border ${borderColor} rounded-lg px-4 py-3`}>
      <div className="flex items-start gap-3">
        <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${badgeColor} shrink-0 mt-0.5`}>
          {finding.category}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-200">{finding.message}</p>
          {finding.details ? (
            <p className="text-xs text-gray-400 mt-1 font-mono">{finding.details}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
