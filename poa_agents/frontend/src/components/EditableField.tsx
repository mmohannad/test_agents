"use client";

import { useState, useRef, useEffect } from "react";
import { useLocale } from "@/lib/i18n";

interface EditableFieldProps {
  label: string;
  value: unknown;
  fieldKey: string;
  onChange: (key: string, value: string) => void;
  multiline?: boolean;
  dir?: "ltr" | "rtl";
}

export function EditableField({
  label,
  value,
  fieldKey,
  onChange,
  multiline = false,
  dir = "ltr",
}: EditableFieldProps) {
  const { t } = useLocale();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  const display =
    value === null || value === undefined || value === ""
      ? null
      : typeof value === "object"
        ? JSON.stringify(value)
        : String(value);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
    }
  }, [editing]);

  const startEdit = () => {
    setDraft(display ?? "");
    setEditing(true);
  };

  const commit = () => {
    setEditing(false);
    onChange(fieldKey, draft);
  };

  const cancel = () => {
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !multiline) {
      commit();
    } else if (e.key === "Enter" && multiline && e.metaKey) {
      commit();
    } else if (e.key === "Escape") {
      cancel();
    }
  };

  if (editing) {
    return (
      <div className="text-sm">
        <span className="text-gray-500 text-xs block mb-1">{label}:</span>
        {multiline ? (
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={handleKeyDown}
            dir={dir}
            rows={4}
            className="w-full bg-gray-800 border border-blue-600 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y font-mono"
          />
        ) : (
          <input
            ref={inputRef as React.RefObject<HTMLInputElement>}
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={handleKeyDown}
            dir={dir}
            className="w-full bg-gray-800 border border-blue-600 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
          />
        )}
      </div>
    );
  }

  // Read-only display — click to edit
  return (
    <div
      className="flex gap-2 text-sm group cursor-pointer hover:bg-gray-800/50 rounded px-1 -mx-1 py-0.5 transition-colors"
      onClick={startEdit}
    >
      <span className="text-gray-500 shrink-0">{label}:</span>
      {display ? (
        <span className="text-gray-200 break-all" dir={dir}>
          {display}
          <span className="text-gray-700 text-xs ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {t("common.edit")}
          </span>
        </span>
      ) : (
        <span className="text-gray-600 italic">
          {t("common.emptyClickToAdd")}
          <span className="text-gray-700 text-xs ml-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {t("common.edit")}
          </span>
        </span>
      )}
    </div>
  );
}
