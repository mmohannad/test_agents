import type { ContextData } from "./supabase";

export type Severity = "error" | "warning";

export interface ValidationFinding {
  severity: Severity;
  category: string;
  message: string;
  details?: string;
}

/**
 * Run deterministic Tier-1 checks against the current (possibly edited)
 * context data. Returns an array of findings — empty means all clear.
 */
export function runTier1Checks(ctx: ContextData): ValidationFinding[] {
  const findings: ValidationFinding[] = [];
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD

  const app = ctx.structured.application;
  const parties = ctx.structured.parties;
  const proofs = ctx.structured.capacity_proofs;
  const extractions = ctx.unstructured.document_extractions;

  // ── Helper ─────────────────────────────────────────────────────
  function isExpired(dateStr: unknown): boolean {
    if (!dateStr || typeof dateStr !== "string") return false;
    // Accept YYYY-MM-DD or ISO strings
    const d = dateStr.slice(0, 10);
    return d < today;
  }

  function str(v: unknown): string {
    if (v === null || v === undefined) return "";
    return String(v).trim();
  }

  // Build a lookup of ID extractions keyed by id_number
  const idExtractionsByNumber = new Map<
    string,
    { index: number; fields: Record<string, unknown> }
  >();
  for (let i = 0; i < extractions.length; i++) {
    const ext = extractions[i];
    const fields = ext.extracted_fields as Record<string, unknown> | null;
    if (!fields) continue;
    const idNum = str(fields.id_number);
    if (idNum) {
      idExtractionsByNumber.set(idNum, { index: i, fields });
    }
  }

  // ── 1. Expiry date checks ─────────────────────────────────────

  // 1a. Party ID expiry
  for (const party of parties) {
    const expiry = str(party.id_validity_date);
    const name = str(party.full_name_en) || str(party.full_name_ar) || "Unknown party";
    if (expiry && isExpired(expiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `${name}'s ID expired on ${expiry}`,
        details: `Party national_id: ${str(party.national_id)}`,
      });
    }
  }

  // 1b. Application POA end date
  const poaEnd = str(app.poa_end_date);
  if (poaEnd && isExpired(poaEnd)) {
    findings.push({
      severity: "error",
      category: "Expired Document",
      message: `POA end date is in the past: ${poaEnd}`,
    });
  }

  // 1c. Capacity proof expiry dates
  for (let pi = 0; pi < proofs.length; pi++) {
    const proof = proofs[pi];
    const label = `Capacity Proof ${pi + 1}`;

    const poaExpiry = str(proof.poa_expiry);
    if (poaExpiry && isExpired(poaExpiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `${label}: POA expiry is in the past (${poaExpiry})`,
      });
    }

    const crExpiry = str(proof.cr_expiry_date);
    if (crExpiry && isExpired(crExpiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `${label}: CR expiry is in the past (${crExpiry})`,
      });
    }
  }

  // 1d. Extraction-level ID expiry
  for (let i = 0; i < extractions.length; i++) {
    const fields = extractions[i].extracted_fields as Record<string, unknown> | null;
    if (!fields) continue;
    const idExpiry = str(fields.id_expiry);
    const who = str(fields.first_name) + " " + str(fields.last_name);
    if (idExpiry && isExpired(idExpiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `Extracted ID for ${who.trim() || "unknown"} expired on ${idExpiry}`,
        details: `Document extraction #${i + 1}`,
      });
    }
  }

  // ── 2. Cross-validation: Structured party ↔ Unstructured ID ───

  const matchedExtractionIds = new Set<string>();

  for (const party of parties) {
    const partyId = str(party.national_id);
    const name = str(party.full_name_en) || str(party.full_name_ar) || "Unknown party";

    if (!partyId) {
      findings.push({
        severity: "warning",
        category: "Missing Data",
        message: `${name} has no national ID number in structured data`,
      });
      continue;
    }

    const match = idExtractionsByNumber.get(partyId);
    if (!match) {
      findings.push({
        severity: "warning",
        category: "Cross-Validation",
        message: `No ID document extraction found for ${name} (ID: ${partyId})`,
        details: "Structured party has no matching unstructured ID extraction",
      });
      continue;
    }

    matchedExtractionIds.add(partyId);
    const ef = match.fields;

    // 2a. ID expiry mismatch
    const partyExpiry = str(party.id_validity_date);
    const extExpiry = str(ef.id_expiry);
    if (partyExpiry && extExpiry && partyExpiry !== extExpiry) {
      findings.push({
        severity: "error",
        category: "Cross-Validation Mismatch",
        message: `${name}: ID expiry mismatch`,
        details: `Structured: ${partyExpiry}  |  Extracted: ${extExpiry}`,
      });
    }

    // 2b. Citizenship / nationality mismatch
    const partyNat = str(party.nationality_code).toUpperCase();
    const extNat = str(ef.citizenship).toUpperCase();
    if (partyNat && extNat && partyNat !== extNat) {
      findings.push({
        severity: "error",
        category: "Cross-Validation Mismatch",
        message: `${name}: citizenship mismatch`,
        details: `Structured: ${partyNat}  |  Extracted: ${extNat}`,
      });
    }

    // 2c. Name mismatch (fuzzy: compare lowercased full name)
    const partyName = str(party.full_name_en).toLowerCase();
    const extName = (str(ef.first_name) + " " + str(ef.last_name)).trim().toLowerCase();
    if (partyName && extName && partyName !== extName) {
      findings.push({
        severity: "warning",
        category: "Cross-Validation Mismatch",
        message: `${name}: name mismatch with extracted ID`,
        details: `Structured: "${str(party.full_name_en)}"  |  Extracted: "${str(ef.first_name)} ${str(ef.last_name)}"`,
      });
    }

    // 2d. ID type mismatch
    const partyIdType = str(party.national_id_type).toLowerCase().replace(/[_\s-]/g, "");
    const extIdType = str(ef.id_type).toLowerCase().replace(/[_\s-]/g, "");
    if (partyIdType && extIdType && partyIdType !== extIdType) {
      findings.push({
        severity: "warning",
        category: "Cross-Validation Mismatch",
        message: `${name}: ID type mismatch`,
        details: `Structured: ${str(party.national_id_type)}  |  Extracted: ${str(ef.id_type)}`,
      });
    }
  }

  // 2e. Unmatched ID extractions (extraction has id_number but no party uses it)
  for (const [idNum, { fields }] of idExtractionsByNumber) {
    if (!matchedExtractionIds.has(idNum)) {
      const who = (str(fields.first_name) + " " + str(fields.last_name)).trim();
      findings.push({
        severity: "warning",
        category: "Cross-Validation",
        message: `Extracted ID for ${who || "unknown"} (${idNum}) has no matching structured party`,
      });
    }
  }

  // ── 3. Missing required fields ────────────────────────────────

  if (!str(app.application_number)) {
    findings.push({
      severity: "warning",
      category: "Missing Data",
      message: "Application number is empty",
    });
  }

  for (const party of parties) {
    const name = str(party.full_name_en) || str(party.full_name_ar);
    if (!name) {
      findings.push({
        severity: "warning",
        category: "Missing Data",
        message: `A party (ID: ${str(party.national_id) || "?"}) has no name`,
      });
    }
  }

  if (parties.length === 0) {
    findings.push({
      severity: "error",
      category: "Missing Data",
      message: "No parties found in structured data",
    });
  }

  return findings;
}
