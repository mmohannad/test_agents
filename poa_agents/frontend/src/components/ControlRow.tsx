"use client";

import { useState, type FormEvent } from "react";

interface ControlRowProps {
  onLoad: (applicationId: string) => void;
  onRunAgents?: () => void;
  status: "idle" | "loading" | "loaded" | "error";
  agentStatus: "idle" | "running" | "completed" | "error";
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
  error,
  agentError,
  loadedAt,
  partyCount,
  docCount,
}: ControlRowProps) {
  const [appId, setAppId] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = appId.trim();
    if (trimmed) onLoad(trimmed);
  };

  const statusBadge = {
    idle: { label: "Idle", color: "bg-gray-700 text-gray-300" },
    loading: { label: "Loading...", color: "bg-blue-900 text-blue-300" },
    loaded: { label: "Loaded", color: "bg-green-900 text-green-300" },
    error: { label: "Error", color: "bg-red-900 text-red-300" },
  }[status];

  return (
    <div className="border-b border-gray-800 bg-gray-900 px-6 py-4">
      <div className="flex items-center gap-4">
        {/* App ID input */}
        <form onSubmit={handleSubmit} className="flex items-center gap-3 flex-1">
          <label className="text-sm font-medium text-gray-400 whitespace-nowrap">
            Application ID
          </label>
          <input
            type="text"
            value={appId}
            onChange={(e) => setAppId(e.target.value)}
            placeholder="e.g. a0000001-1111-2222-3333-444444444444"
            className="flex-1 max-w-lg bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent font-mono"
          />
          <button
            type="submit"
            disabled={!appId.trim() || status === "loading"}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {status === "loading" ? "Loading..." : "Load Context"}
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
                {partyCount} parties, {docCount} docs
              </span>
              {loadedAt && (
                <span className="text-gray-600 text-xs">at {loadedAt}</span>
              )}
            </>
          )}

          {status === "error" && error && (
            <span className="text-red-400 text-xs max-w-xs truncate" title={error}>
              {error}
            </span>
          )}
        </div>

        {/* Agent status */}
        {agentStatus !== "idle" && (
          <>
            <span className="text-gray-500">|</span>
            {agentStatus === "running" && (
              <span className="flex items-center gap-2 text-xs text-blue-400">
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                Running condenser...
              </span>
            )}
            {agentStatus === "completed" && (
              <span className="text-xs text-green-400">Agent complete</span>
            )}
            {agentStatus === "error" && (
              <span className="text-xs text-red-400 max-w-xs truncate" title={agentError ?? ""}>
                Agent failed{agentError ? `: ${agentError}` : ""}
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
          {agentStatus === "running" ? "Running..." : "Run Agents"}
        </button>
      </div>
    </div>
  );
}
