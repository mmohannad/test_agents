"use client";

import { useState } from "react";
import { useLocale } from "@/lib/i18n";

interface JsonViewerProps {
  data: unknown;
  label?: string;
  defaultOpen?: boolean;
}

export function JsonViewer({ data, label, defaultOpen = false }: JsonViewerProps) {
  const { t } = useLocale();
  const displayLabel = label ?? t("common.rawJson");
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-800 rounded-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-800/50 hover:bg-gray-800 transition-colors text-sm"
      >
        <span className="text-gray-400 font-medium">{displayLabel}</span>
        <span className="text-gray-600 text-xs">{open ? t("common.collapse") : t("common.expand")}</span>
      </button>
      {open && (
        <pre className="p-3 text-xs text-gray-300 overflow-x-auto max-h-96 overflow-y-auto bg-gray-950 font-mono leading-relaxed">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
