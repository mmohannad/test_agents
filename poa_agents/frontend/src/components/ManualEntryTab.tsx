"use client";

import { useState, useCallback } from "react";
import { ApplicationForm } from "./manual/ApplicationForm";
import { AttachmentPanel } from "./manual/AttachmentPanel";
import { ValidationModal } from "./ValidationModal";
import {
  createEmptyParty,
  type ManualParty,
  type ManualAttachment,
} from "@/lib/manualDefaults";
import { runManualTier1Checks, type ValidationFinding } from "@/lib/validation";
import type { AgentPayload } from "@/lib/agentApi";

type AgentStepStatus = "idle" | "running" | "completed" | "error";

interface ManualEntryTabProps {
  onRunAgents: (payload: AgentPayload) => void;
  isRunning: boolean;
  condenserStatus: AgentStepStatus;
  legalSearchStatus: AgentStepStatus;
  condenserError: string | null;
  legalSearchError: string | null;
}

function buildPayload(
  applicationType: string,
  firstParty: ManualParty,
  secondParty: ManualParty,
  namadhij: string,
  attachments: ManualAttachment[]
): AgentPayload {
  // Map first party to the party shape the agents expect
  const party1: Record<string, unknown> = {
    party_type: "first_party",
    party_role: "grantor",
    full_name_en: firstParty.fullName,
    full_name_ar: "",
    capacity: firstParty.capacity,
    national_id_type: firstParty.idType,
    national_id: firstParty.idNumber,
    id_validity_date: firstParty.expirationDate,
    nationality_code: firstParty.citizenship,
    phone: firstParty.phone,
    email: firstParty.email,
  };

  const party2: Record<string, unknown> = {
    party_type: "second_party",
    party_role: "agent",
    full_name_en: secondParty.fullName,
    full_name_ar: "",
    capacity: secondParty.capacity,
    national_id_type: secondParty.idType,
    national_id: secondParty.idNumber,
    nationality_code: secondParty.citizenship,
  };

  // Build capacity proofs from namadhij
  const capacityProofs: Record<string, unknown>[] = [];
  if (firstParty.capacity || namadhij) {
    capacityProofs.push({
      capacity_type: firstParty.capacity,
      granted_powers: namadhij ? [namadhij] : [],
      granted_powers_en: namadhij ? [namadhij] : [],
      poa_full_text_en: namadhij,
      poa_full_text_ar: "",
    });
  }

  // Map attachments to document_extractions shape
  const documentExtractions: Record<string, unknown>[] = attachments.map((att) => {
    const fields: Record<string, unknown> = { ...att.extractedFields };
    // Merge signatories into extracted_fields for CR attachments
    if (att.documentTypeCode === "COMMERCIAL_REGISTRATION" && att.signatories.length > 0) {
      fields.authorized_signatories = att.signatories.map((s) => ({
        ...s,
        percentage: s.percentage ? Number(s.percentage) : 0,
      }));
    }
    return {
      id: att.id,
      document_type_code: att.documentTypeCode,
      raw_text_ar: att.rawTextAr,
      raw_text_en: att.rawTextEn,
      extracted_fields: fields,
    };
  });

  return {
    case_data: {
      application: {
        transaction_type_code: applicationType,
        status: "manual_entry",
        processing_stage: "manual_validation",
      },
      parties: [party1, party2],
      capacity_proofs: capacityProofs,
    },
    document_extractions: documentExtractions,
    additional_context: { source: "manual_entry" },
  };
}

function AgentProgressBar({
  condenserStatus,
  legalSearchStatus,
  condenserError,
  legalSearchError,
}: {
  condenserStatus: AgentStepStatus;
  legalSearchStatus: AgentStepStatus;
  condenserError: string | null;
  legalSearchError: string | null;
}) {
  const isIdle = condenserStatus === "idle" && legalSearchStatus === "idle";
  if (isIdle) return null;

  const stepLabel = (() => {
    if (condenserStatus === "running") return "Step 1/2: Running condenser agent...";
    if (condenserStatus === "completed" && legalSearchStatus === "idle") return "Step 1/2 complete, starting legal search...";
    if (legalSearchStatus === "running") return "Step 2/2: Running legal search agent...";
    if (condenserStatus === "completed" && legalSearchStatus === "completed") return "Both agents complete";
    if (condenserStatus === "error") return "Condenser agent failed";
    if (legalSearchStatus === "error") return "Legal search agent failed";
    return null;
  })();

  const isRunning = condenserStatus === "running" || legalSearchStatus === "running";
  const isError = condenserStatus === "error" || legalSearchStatus === "error";
  const isComplete = condenserStatus === "completed" && legalSearchStatus === "completed";

  // Progress percentage for the bar
  const progress = (() => {
    if (condenserStatus === "running") return 25;
    if (condenserStatus === "completed" && legalSearchStatus === "idle") return 50;
    if (legalSearchStatus === "running") return 75;
    if (isComplete) return 100;
    if (condenserStatus === "error") return 50;
    if (legalSearchStatus === "error") return 100;
    return 0;
  })();

  return (
    <div className={`border rounded-lg p-3 space-y-2 ${
      isError ? "border-red-800 bg-red-950/30" :
      isComplete ? "border-green-800 bg-green-950/30" :
      "border-blue-800 bg-blue-950/30"
    }`}>
      {/* Step label with spinner */}
      <div className="flex items-center gap-2">
        {isRunning && (
          <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
        )}
        {isComplete && (
          <span className="text-green-400 text-sm">&#10003;</span>
        )}
        {isError && (
          <span className="text-red-400 text-sm">&#10007;</span>
        )}
        <span className={`text-sm font-medium ${
          isError ? "text-red-400" :
          isComplete ? "text-green-400" :
          "text-blue-400"
        }`}>
          {stepLabel}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            isError ? "bg-red-500" :
            isComplete ? "bg-green-500" :
            "bg-blue-500"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-4 text-xs">
        <StepDot label="Condenser" status={condenserStatus} error={condenserError} />
        <div className="flex-1 border-t border-gray-700" />
        <StepDot label="Legal Search" status={legalSearchStatus} error={legalSearchError} />
      </div>

      {/* Error details */}
      {condenserError && condenserStatus === "error" && (
        <p className="text-xs text-red-400 mt-1 truncate" title={condenserError}>{condenserError}</p>
      )}
      {legalSearchError && legalSearchStatus === "error" && (
        <p className="text-xs text-red-400 mt-1 truncate" title={legalSearchError}>{legalSearchError}</p>
      )}
    </div>
  );
}

function StepDot({ label, status, error }: { label: string; status: AgentStepStatus; error: string | null }) {
  return (
    <div className="flex items-center gap-1.5" title={error ?? undefined}>
      <span className={`w-2 h-2 rounded-full ${
        status === "completed" ? "bg-green-400" :
        status === "running" ? "bg-blue-400 animate-pulse" :
        status === "error" ? "bg-red-400" :
        "bg-gray-600"
      }`} />
      <span className={`${
        status === "completed" ? "text-green-400" :
        status === "running" ? "text-blue-400" :
        status === "error" ? "text-red-400" :
        "text-gray-500"
      }`}>
        {label}
      </span>
    </div>
  );
}

export function ManualEntryTab({
  onRunAgents,
  isRunning,
  condenserStatus,
  legalSearchStatus,
  condenserError,
  legalSearchError,
}: ManualEntryTabProps) {
  const [applicationType, setApplicationType] = useState("");
  const [firstParty, setFirstParty] = useState<ManualParty>(createEmptyParty());
  const [secondParty, setSecondParty] = useState<ManualParty>(createEmptyParty());
  const [namadhij, setNamadhij] = useState("");
  const [attachments, setAttachments] = useState<ManualAttachment[]>([]);
  const [validationFindings, setValidationFindings] = useState<ValidationFinding[] | null>(null);

  const proceedWithAgents = useCallback(() => {
    setValidationFindings(null);
    const payload = buildPayload(
      applicationType,
      firstParty,
      secondParty,
      namadhij,
      attachments
    );
    onRunAgents(payload);
  }, [applicationType, firstParty, secondParty, namadhij, attachments, onRunAgents]);

  const handleRunAgents = useCallback(() => {
    const findings = runManualTier1Checks(applicationType, firstParty, secondParty, attachments);
    if (findings.length > 0) {
      setValidationFindings(findings);
    } else {
      proceedWithAgents();
    }
  }, [applicationType, firstParty, secondParty, attachments, proceedWithAgents]);

  const hasMinimumData = applicationType !== "" || firstParty.fullName !== "" || attachments.length > 0;

  // Derive overall status for the pill (mirrors DB View's ControlRow logic)
  const overallStatus: "idle" | "running" | "completed" | "error" = (() => {
    if (condenserStatus === "idle" && legalSearchStatus === "idle") return "idle";
    if (condenserStatus === "running" || legalSearchStatus === "running") return "running";
    if (condenserStatus === "error" || legalSearchStatus === "error") return "error";
    if (condenserStatus === "completed" && legalSearchStatus === "completed") return "completed";
    if (condenserStatus === "completed" && legalSearchStatus === "idle") return "running";
    return "idle";
  })();

  const statusPill = {
    idle: { label: "Idle", color: "bg-gray-700 text-gray-300" },
    running: { label: "Running...", color: "bg-blue-900 text-blue-300" },
    completed: { label: "Completed", color: "bg-green-900 text-green-300" },
    error: { label: "Failed", color: "bg-red-900 text-red-300" },
  }[overallStatus];

  // Agent progress label (same as ControlRow)
  const agentProgressLabel = (() => {
    if (condenserStatus === "running") return "Step 1/2: Running condenser...";
    if (condenserStatus === "completed" && legalSearchStatus === "idle") return "Step 1/2 complete, starting legal search...";
    if (legalSearchStatus === "running") return "Step 2/2: Running legal search...";
    if (condenserStatus === "completed" && legalSearchStatus === "completed") return "Both agents complete";
    if (condenserStatus === "error") return "Condenser failed";
    if (legalSearchStatus === "error") return "Legal search failed";
    return null;
  })();

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header bar — mirrors ControlRow layout */}
      <div className="border-b border-gray-800 bg-gray-900 px-6 py-4">
        <div className="flex items-center gap-4">
          {/* Left: label + metadata */}
          <div className="flex items-center gap-3 flex-1">
            <span className="text-sm font-medium text-gray-400 whitespace-nowrap">
              Manual Entry
            </span>
            <span className="text-gray-600">|</span>
            <span className="text-xs text-gray-400">
              {attachments.length} attachment{attachments.length !== 1 ? "s" : ""}
              {attachments.length > 0 && (
                <span className="ml-1 text-gray-500">
                  ({attachments.filter(a => a.saved).length} saved)
                </span>
              )}
            </span>
          </div>

          {/* Right: status pill + agent progress + Run Agents button */}
          <div className="flex items-center gap-4 text-sm">
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusPill.color}`}
            >
              {statusPill.label}
            </span>
          </div>

          {/* Agent progress inline */}
          {overallStatus !== "idle" && (
            <>
              <span className="text-gray-500">|</span>
              {overallStatus === "running" && (
                <span className="flex items-center gap-2 text-xs text-blue-400">
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                  {agentProgressLabel}
                </span>
              )}
              {overallStatus === "completed" && (
                <span className="text-xs text-green-400">{agentProgressLabel}</span>
              )}
              {overallStatus === "error" && (
                <span className="text-xs text-red-400 max-w-xs truncate" title={condenserError || legalSearchError || ""}>
                  {agentProgressLabel}{(condenserError || legalSearchError) ? `: ${condenserError || legalSearchError}` : ""}
                </span>
              )}
            </>
          )}

          {/* Run Agents button */}
          <button
            disabled={!hasMinimumData || isRunning}
            onClick={handleRunAgents}
            className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {isRunning ? "Running..." : "Run Agents"}
          </button>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
        <div className="border-r border-gray-800 overflow-y-auto">
          <ApplicationForm
            applicationType={applicationType}
            onApplicationTypeChange={setApplicationType}
            firstParty={firstParty}
            onFirstPartyChange={setFirstParty}
            secondParty={secondParty}
            onSecondPartyChange={setSecondParty}
            namadhij={namadhij}
            onNamadhijChange={setNamadhij}
          />
        </div>
        <div className="overflow-y-auto">
          <AttachmentPanel
            attachments={attachments}
            onAttachmentsChange={setAttachments}
          />
        </div>
      </div>

      {/* Bottom detail bar — progress breakdown (only visible when agents have run) */}
      {overallStatus !== "idle" && (
        <div className="border-t border-gray-800 px-5 py-3 bg-gray-950">
          <AgentProgressBar
            condenserStatus={condenserStatus}
            legalSearchStatus={legalSearchStatus}
            condenserError={condenserError}
            legalSearchError={legalSearchError}
          />
        </div>
      )}

      {/* Validation Modal */}
      {validationFindings && (
        <ValidationModal
          findings={validationFindings}
          onClose={() => setValidationFindings(null)}
          onProceedAnyway={proceedWithAgents}
        />
      )}
    </div>
  );
}
