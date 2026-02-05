"use client";

import { LocaleProvider } from "@/lib/i18n";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return <LocaleProvider>{children}</LocaleProvider>;
}
