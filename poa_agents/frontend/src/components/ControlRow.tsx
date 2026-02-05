"use client";

import { useState, type FormEvent } from "react";
import { useLocale } from "@/lib/i18n";

type AgentStepStatus = "idle" | "running" | "completed" | "error";

interface ControlRowProps {
  onLoad: (applicationId: string) => void;
  onRunAgents?: () => void;
  status: "idle" | "loading" | "loaded" | "error";
  agentStatus: AgentStepStatus;
  condenserStatus: AgentStepStatus;
  legalSearchStatus: AgentStepStatus;
  error: string | null;
  agentError: string | null;
  loadedAt: string | null;
  partyCount: number;
  docCount: number;
}

export function ControlRow({
  onLoad,
  onRunAgents,
  status,
  agentStatus,
  condenserStatus,
  legalSearchStatus,
  error,
  agentError,
  loadedAt,
  partyCount,
  docCount,
}: ControlRowProps) {
  const { t } = useLocale();
  const [appId, setAppId] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = appId.trim();
    if (trimmed) onLoad(trimmed);
  };

  const statusBadge = {
    idle: { label: t("controlRow.idle"), color: "bg-gray-700 text-gray-300" },
    loading: { label: t("controlRow.loadingStatus"), color: "bg-blue-900 text-blue-300" },
    loaded: { label: t("controlRow.loaded"), color: "bg-green-900 text-green-300" },
    error: { label: t("controlRow.errorStatus"), color: "bg-red-900 text-red-300" },
  }[status];

  // Determine step label for agent progress
  const agentProgressLabel = (() => {
    if (condenserStatus === "running") return t("controlRow.step1Running");
    if (condenserStatus === "completed" && legalSearchStatus === "idle") return t("controlRow.step1Done");
    if (legalSearchStatus === "running") return t("controlRow.step2Running");
    if (condenserStatus === "completed" && legalSearchStatus === "completed") return t("controlRow.agentsComplete");
    if (condenserStatus === "error") return t("controlRow.condenserFailed");
    if (legalSearchStatus === "error") return t("controlRow.legalSearchFailed");
    return null;
  })();

  return (
    <div className="border-b border-gray-800 bg-gray-900 px-6 py-4">
      <div className="flex items-center gap-4">
        {/* App ID input */}
        <form onSubmit={handleSubmit} className="flex items-center gap-3 flex-1">
          <label className="text-sm font-medium text-gray-400 whitespace-nowrap">
            {t("controlRow.applicationId")}
          </label>
          <input
            type="text"
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            placeholder={t("controlRow.placeholder")}
            dir="ltr"
            className="flex-1 max-w-lg bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent font-mono"
          />
          <button
            type="submit"
            disabled={!appId.trim() || status === "loading"}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {status === "loading" ? t("controlRow.loadingStatus") : t("controlRow.loadContext")}
          </button>
        </form>

        {/* Status + metadata */}
        <div className="flex items-center gap-4 text-sm">
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusBadge.color}`}
          >
            {statusBadge.label}
          </span>

          {status === "loaded" && (
            <>
              <span className="text-gray-500">|</span>
              <span className="text-gray-400">
                {partyCount} {t("controlRow.parties")}، {docCount} {t("controlRow.documents")}
              </span>
              {loadedAt && (
                <span className="text-gray-600 text-xs">{t("controlRow.at")} {loadedAt}</span>
              )}
            </>
          )}

          {status === "error" && error && (
            <span className="text-red-400 text-xs max-w-xs truncate" title={error}>
              {error}
            </span>
          )}
        </div>

        {/* Agent progress */}
        {agentStatus !== "idle" && (
          <>
            <span className="text-gray-500">|</span>
            {agentStatus === "running" && (
              <span className="flex items-center gap-2 text-xs text-blue-400">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                {agentProgressLabel}
              </span>
            )}
            {agentStatus === "completed" && (
              <span className="text-xs text-green-400">{agentProgressLabel}</span>
            )}
            {agentStatus === "error" && (
              <span className="text-xs text-red-400 max-w-xs truncate" title={agentError ?? ""}>
                {agentProgressLabel}{agentError ? `: ${agentError}` : ""}
              </span>
            )}
          </>
        )}

        {/* Run agents button */}
        <button
          disabled={status !== "loaded" || agentStatus === "running"}
          onClick={onRunAgents}
          className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-md hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          {agentStatus === "running" ? t("controlRow.running") : t("controlRow.runAgents")}
        </button>
      </div>
    </div>
  );
}
