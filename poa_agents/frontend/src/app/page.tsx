"use client";

import { useState, useCallback } from "react";
import { loadContext, type ContextData } from "@/lib/supabase";
import { runTier1Checks, type ValidationFinding } from "@/lib/validation";
import {
  runCondenserAgent,
  parseCondenserContent,
  type AgentPayload,
} from "@/lib/agentApi";
import { ControlRow } from "@/components/ControlRow";
import { StructuredPanel } from "@/components/StructuredPanel";
import { UnstructuredPanel } from "@/components/UnstructuredPanel";
import { ValidationModal } from "@/components/ValidationModal";
import { ResultsDrawer } from "@/components/ResultsDrawer";

export default function Home() {
  const [context, setContext] = useState<ContextData | null>(null);
  const [status, setStatus] = useState<
    "idle" | "loading" | "loaded" | "error"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [loadedAt, setLoadedAt] = useState<string | null>(null);
  const [validationFindings, setValidationFindings] = useState<ValidationFinding[] | null>(null);
  const [agentStatus, setAgentStatus] = useState<
    "idle" | "running" | "completed" | "error"
  >("idle");
  const [agentResult, setAgentResult] = useState<
    Record<string, unknown> | string | null
  >(null);
  const [agentError, setAgentError] = useState<string | null>(null);

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

  const proceedWithAgents = useCallback(async () => {
    const payload = getAgentPayload();
    if (!payload) return;

    setValidationFindings(null);
    setAgentStatus("running");
    setAgentError(null);
    setAgentResult(null);

    try {
      console.log("[RunAgents] Sending payload to condenser agent...");
      const content = await runCondenserAgent(payload as AgentPayload);
      const parsed = parseCondenserContent(content);
      console.log("[RunAgents] Condenser result:", parsed);
      setAgentResult(parsed);
      setAgentStatus("completed");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("[RunAgents] Agent call failed:", msg);
      setAgentError(msg);
      setAgentStatus("error");
    }
  }, [getAgentPayload]);

  const handleRunAgents = useCallback(() => {
    if (!context) return;
    const findings = runTier1Checks(context);
    if (findings.length > 0) {
      setValidationFindings(findings);
    } else {
      proceedWithAgents();
    }
  }, [context, proceedWithAgents]);

  return (
    <div className="min-h-screen flex flex-col">
      <ControlRow
        onLoad={handleLoad}
        status={status}
        agentStatus={agentStatus}
        error={error}
        agentError={agentError}
        loadedAt={loadedAt}
        partyCount={context?.structured.parties.length ?? 0}
        docCount={context?.unstructured.document_extractions.length ?? 0}
        onRunAgents={handleRunAgents}
      />

      {status === "idle" && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <p className="text-lg">Enter an Application ID to load case context</p>
            <p className="text-sm mt-2 text-gray-600">
              This loads the same data the condenser agent receives from Supabase
            </p>
          </div>
        </div>
      )}

      {status === "loading" && (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-gray-600 border-t-blue-500 mb-4" />
            <p>Loading application context from Supabase...</p>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="flex-1 flex items-center justify-center">
          <div className="bg-red-950/50 border border-red-800 rounded-lg p-6 max-w-lg">
            <p className="text-red-400 font-medium">Failed to load context</p>
            <p className="text-red-300 text-sm mt-2">{error}</p>
          </div>
        </div>
      )}

      {status === "loaded" && context && (
        <div className="flex-1 grid grid-cols-2 gap-0 min-h-0">
          <div className="border-r border-gray-800 overflow-y-auto">
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

      {/* Results Drawer */}
      {agentResult !== null && (
        <ResultsDrawer
          result={agentResult}
          onClose={() => {
            setAgentResult(null);
            setAgentStatus("idle");
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
