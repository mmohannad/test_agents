"use client";

import { useState, useCallback } from "react";
import { loadContext, type ContextData } from "@/lib/supabase";
import { runTier1Checks, type ValidationFinding } from "@/lib/validation";
import {
  runCondenserAgent,
  runLegalSearchAgent,
  parseAgentContent,
  type AgentPayload,
} from "@/lib/agentApi";
import { useLocale } from "@/lib/i18n";
import { ControlRow } from "@/components/ControlRow";
import { StructuredPanel } from "@/components/StructuredPanel";
import { UnstructuredPanel } from "@/components/UnstructuredPanel";
import { ValidationModal } from "@/components/ValidationModal";
import { ResultsDrawer } from "@/components/ResultsDrawer";
import { ManualEntryTab } from "@/components/ManualEntryTab";

type AgentStepStatus = "idle" | "running" | "completed" | "error";

export default function Home() {
  const { locale, setLocale, t } = useLocale();
  const [activeMode, setActiveMode] = useState<"db" | "manual">("db");

  const [context, setContext] = useState<ContextData | null>(null);
  const [status, setStatus] = useState<
    "idle" | "loading" | "loaded" | "error"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState<string | null>(null);
  const [validationFindings, setValidationFindings] = useState<ValidationFinding[] | null>(null);

  // Per-agent state
  const [condenserStatus, setCondenserStatus] = useState<AgentStepStatus>("idle");
  const [condenserResult, setCondenserResult] = useState<
    Record<string, unknown> | string | null
  >(null);
  const [condenserError, setCondenserError] = useState<string | null>(null);

  const [legalSearchStatus, setLegalSearchStatus] = useState<AgentStepStatus>("idle");
  const [legalSearchResult, setLegalSearchResult] = useState<
    Record<string, unknown> | string | null
  >(null);
  const [legalSearchError, setLegalSearchError] = useState<string | null>(null);

  const handleLoad = useCallback(async (applicationId: string) => {
    setStatus("loading");
    setError(null);
    setContext(null);

    try {
      const data = await loadContext(applicationId);
      setContext(data);
      setStatus("loaded");
      setLoadedAt(new Date().toLocaleTimeString());
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setStatus("error");
    }
  }, []);

  // --- Mutation helpers (structured) ---

  const updateApplication = useCallback(
    (key: string, value: string) => {
      setContext((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          structured: {
            ...prev.structured,
            application: { ...prev.structured.application, [key]: value },
          },
        };
      });
    },
    []
  );

  const updateParty = useCallback(
    (partyIndex: number, key: string, value: string) => {
      setContext((prev) => {
        if (!prev) return prev;
        const parties = [...prev.structured.parties];
        parties[partyIndex] = { ...parties[partyIndex], [key]: value };
        return {
          ...prev,
          structured: { ...prev.structured, parties },
        };
      });
    },
    []
  );

  const updateCapacityProof = useCallback(
    (proofIndex: number, key: string, value: unknown) => {
      setContext((prev) => {
        if (!prev) return prev;
        const proofs = [...prev.structured.capacity_proofs];
        proofs[proofIndex] = { ...proofs[proofIndex], [key]: value };
        return {
          ...prev,
          structured: { ...prev.structured, capacity_proofs: proofs },
        };
      });
    },
    []
  );

  // --- Mutation helpers (unstructured) ---

  const updateExtraction = useCallback(
    (extractionIndex: number, key: string, value: string) => {
      setContext((prev) => {
        if (!prev) return prev;
        const extractions = [...prev.unstructured.document_extractions];
        extractions[extractionIndex] = {
          ...extractions[extractionIndex],
          [key]: value,
        };
        return {
          ...prev,
          unstructured: { ...prev.unstructured, document_extractions: extractions },
        };
      });
    },
    []
  );

  const updateExtractedField = useCallback(
    (extractionIndex: number, fieldKey: string, value: unknown) => {
      setContext((prev) => {
        if (!prev) return prev;
        const extractions = [...prev.unstructured.document_extractions];
        const ext = { ...extractions[extractionIndex] };
        ext.extracted_fields = {
          ...(ext.extracted_fields as Record<string, unknown>),
          [fieldKey]: value,
        };
        extractions[extractionIndex] = ext;
        return {
          ...prev,
          unstructured: { ...prev.unstructured, document_extractions: extractions },
        };
      });
    },
    []
  );

  // --- Assemble payload for agent ---

  const getAgentPayload = useCallback(() => {
    if (!context) return null;
    return {
      case_data: {
        application: context.structured.application,
        parties: context.structured.parties,
        capacity_proofs: context.structured.capacity_proofs,
      },
      document_extractions: context.unstructured.document_extractions,
      additional_context: {},
    };
  }, [context]);

  // Core agent runner — accepts an explicit payload (used by both DB View and Manual Entry)
  const runAgentsWithPayload = useCallback(async (payload: AgentPayload) => {
    setValidationFindings(null);

    // Reset all agent state
    setCondenserStatus("running");
    setCondenserResult(null);
    setCondenserError(null);
    setLegalSearchStatus("idle");
    setLegalSearchResult(null);
    setLegalSearchError(null);

    // Step 1: Condenser agent
    let condenserParsed: Record<string, unknown> | string;
    try {
      console.log("[RunAgents] Step 1/2: Sending payload to condenser agent...");
      const condenserRaw = await runCondenserAgent(payload, locale);
      condenserParsed = parseAgentContent(condenserRaw);
      console.log("[RunAgents] Condenser result:", condenserParsed);
      setCondenserResult(condenserParsed);
      setCondenserStatus("completed");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[RunAgents] Condenser failed:", msg);
      setCondenserError(msg);
      setCondenserStatus("error");
      return; // Don't chain to legal search if condenser failed
    }

    // Step 2: Legal search agent (auto-chain)
    if (typeof condenserParsed !== "object") {
      // Condenser returned raw text, can't chain — show what we have
      console.warn("[RunAgents] Condenser returned non-JSON, skipping legal search");
      return;
    }

    setLegalSearchStatus("running");
    try {
      console.log("[RunAgents] Step 2/2: Sending legal brief to legal search agent...");
      const legalRaw = await runLegalSearchAgent(condenserParsed, locale);
      const legalParsed = parseAgentContent(legalRaw);
      console.log("[RunAgents] Legal search result:", legalParsed);
      setLegalSearchResult(legalParsed);
      setLegalSearchStatus("completed");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[RunAgents] Legal search failed:", msg);
      setLegalSearchError(msg);
      setLegalSearchStatus("error");
    }
  }, [locale]);

  // DB View: builds payload from context, runs validation first
  const proceedWithAgents = useCallback(async () => {
    const payload = getAgentPayload();
    if (!payload) return;
    await runAgentsWithPayload(payload as AgentPayload);
  }, [getAgentPayload, runAgentsWithPayload]);

  const handleRunAgents = useCallback(() => {
    if (!context) return;
    const findings = runTier1Checks(context, t);
    if (findings.length > 0) {
      setValidationFindings(findings);
    } else {
      proceedWithAgents();
    }
  }, [context, t, proceedWithAgents]);

  // Compute overall agent status for ControlRow
  const overallAgentStatus: AgentStepStatus =
    condenserStatus === "idle" && legalSearchStatus === "idle"
      ? "idle"
      : condenserStatus === "running" || legalSearchStatus === "running"
        ? "running"
        : condenserStatus === "error"
          ? "error"
          : legalSearchStatus === "error"
            ? "error"
            : legalSearchStatus === "completed"
              ? "completed"
              : condenserStatus === "completed"
                ? "running" // condenser done, legal search pending
                : "idle";

  const isAgentsRunning = overallAgentStatus === "running";

  const showResults =
    condenserResult !== null || legalSearchResult !== null;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Mode Tab Bar */}
      <div className="border-b border-gray-800 bg-gray-950 px-4 flex items-center gap-0">
        <button
          onClick={() => setActiveMode("db")}
          className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${
            activeMode === "db"
              ? "text-blue-400 border-blue-500"
              : "text-gray-400 border-transparent hover:text-gray-200"
          }`}
        >
          {t("page.dbView")}
        </button>
        <button
          onClick={() => setActiveMode("manual")}
          className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${
            activeMode === "manual"
              ? "text-blue-400 border-blue-500"
              : "text-gray-400 border-transparent hover:text-gray-200"
          }`}
        >
          {t("page.manualEntry")}
        </button>

        {/* Language toggle */}
        <div className="ml-auto flex items-center">
          <button
            onClick={() => setLocale(locale === "ar" ? "en" : "ar")}
            className="px-3 py-1.5 text-xs font-medium rounded-md border border-gray-700 text-gray-300 hover:bg-gray-800 hover:text-gray-100 transition-colors"
          >
            {locale === "ar" ? "EN" : "AR"}
          </button>
        </div>
      </div>

      {/* DB View (existing functionality, unchanged) */}
      {activeMode === "db" && (
        <>
          <ControlRow
            onLoad={handleLoad}
            status={status}
            agentStatus={overallAgentStatus}
            condenserStatus={condenserStatus}
            legalSearchStatus={legalSearchStatus}
            error={error}
            agentError={condenserError || legalSearchError}
            loadedAt={loadedAt}
            partyCount={context?.structured.parties.length ?? 0}
            docCount={context?.unstructured.document_extractions.length ?? 0}
            onRunAgents={handleRunAgents}
          />

          {status === "idle" && (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-lg">{t("page.idlePrompt")}</p>
                <p className="text-sm mt-2 text-gray-600">
                  {t("page.idleDescription")}
                </p>
              </div>
            </div>
          )}

          {status === "loading" && (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-600 border-t-blue-500 mb-4" />
                <p>{t("page.loadingContext")}</p>
              </div>
            </div>
          )}

          {status === "error" && (
            <div className="flex-1 flex items-center justify-center">
              <div className="bg-red-950/50 border border-red-800 rounded-lg p-6 max-w-lg">
                <p className="text-red-400 font-medium">{t("page.loadFailed")}</p>
                <p className="text-red-300 text-sm mt-2">{error}</p>
              </div>
            </div>
          )}

          {status === "loaded" && context && (
            <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
              <div className="border-l border-gray-800 overflow-y-auto">
                <StructuredPanel
                  data={context.structured}
                  onUpdateApplication={updateApplication}
                  onUpdateParty={updateParty}
                  onUpdateCapacityProof={updateCapacityProof}
                />
              </div>
              <div className="overflow-y-auto">
                <UnstructuredPanel
                  data={context.unstructured}
                  onUpdateExtraction={updateExtraction}
                  onUpdateExtractedField={updateExtractedField}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* Manual Entry */}
      {activeMode === "manual" && (
        <ManualEntryTab
          onRunAgents={runAgentsWithPayload}
          isRunning={isAgentsRunning}
          condenserStatus={condenserStatus}
          legalSearchStatus={legalSearchStatus}
          condenserError={condenserError}
          legalSearchError={legalSearchError}
        />
      )}

      {/* Results Drawer */}
      {showResults && (
        <ResultsDrawer
          condenserResult={condenserResult}
          legalSearchResult={legalSearchResult}
          legalSearchStatus={legalSearchStatus}
          legalSearchError={legalSearchError}
          onClose={() => {
            setCondenserResult(null);
            setCondenserStatus("idle");
            setCondenserError(null);
            setLegalSearchResult(null);
            setLegalSearchStatus("idle");
            setLegalSearchError(null);
          }}
        />
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
