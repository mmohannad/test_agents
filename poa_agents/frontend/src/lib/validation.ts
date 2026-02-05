import type { ContextData } from "./supabase";
import type { ManualParty, ManualAttachment } from "./manualDefaults";

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
    const who = str(fields.name_en) || (str(fields.first_name) + " " + str(fields.last_name)).trim();
    if (idExpiry && isExpired(idExpiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `Extracted ID for ${who || "unknown"} expired on ${idExpiry}`,
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
    const extName = (str(ef.name_en) || (str(ef.first_name) + " " + str(ef.last_name)).trim()).toLowerCase();
    if (partyName && extName && partyName !== extName) {
      findings.push({
        severity: "warning",
        category: "Cross-Validation Mismatch",
        message: `${name}: name mismatch with extracted ID`,
        details: `Structured: "${str(party.full_name_en)}"  |  Extracted: "${str(ef.name_en) || (str(ef.first_name) + " " + str(ef.last_name)).trim()}"`,
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
      const who = str(fields.name_en) || (str(fields.first_name) + " " + str(fields.last_name)).trim();
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

/**
 * Run Tier-1 checks for Manual Entry mode.
 * Cross-validates party form data against attachment extracted fields,
 * checks expiry dates, and flags missing data.
 */
export function runManualTier1Checks(
  applicationType: string,
  firstParty: ManualParty,
  secondParty: ManualParty,
  attachments: ManualAttachment[]
): ValidationFinding[] {
  const findings: ValidationFinding[] = [];
  const today = new Date().toISOString().slice(0, 10);

  function isExpired(dateStr: string): boolean {
    if (!dateStr) return false;
    const d = dateStr.slice(0, 10);
    return d < today;
  }

  function norm(v: string): string {
    return v.trim().toLowerCase();
  }

  const parties = [
    { label: "First Party", role: "grantor", party: firstParty },
    { label: "Second Party", role: "agent", party: secondParty },
  ];

  // Separate attachments by type
  const idAttachments = attachments.filter(
    (a) => a.documentTypeCode === "PERSONAL_ID" || a.documentTypeCode === "PASSPORT"
  );
  const crAttachments = attachments.filter(
    (a) => a.documentTypeCode === "COMMERCIAL_REGISTRATION"
  );

  // ── 1. Missing data ─────────────────────────────────────────────

  if (!applicationType) {
    findings.push({
      severity: "warning",
      category: "Missing Data",
      message: "Application type is not selected",
    });
  }

  for (const { label, party } of parties) {
    if (!party.fullName) {
      findings.push({
        severity: "warning",
        category: "Missing Data",
        message: `${label} has no name`,
      });
    }
    if (!party.idNumber) {
      findings.push({
        severity: "warning",
        category: "Missing Data",
        message: `${label} has no ID number`,
      });
    }
  }

  if (attachments.length === 0) {
    findings.push({
      severity: "warning",
      category: "Missing Data",
      message: "No attachments added",
    });
  }

  // Parties exist but no Personal ID attachments
  const hasParties = firstParty.fullName || secondParty.fullName || firstParty.idNumber || secondParty.idNumber;
  if (hasParties && idAttachments.length === 0) {
    findings.push({
      severity: "error",
      category: "Missing Attachment",
      message: "Parties exist but no Personal ID attachments submitted",
      details: "Add a Personal ID attachment for each party before running agents",
    });
  }

  const unsaved = attachments.filter((a) => !a.saved);
  if (unsaved.length > 0) {
    findings.push({
      severity: "warning",
      category: "Unsaved Data",
      message: `${unsaved.length} attachment(s) have unsaved changes`,
      details: "Save each attachment before running agents to ensure data is included",
    });
  }

  // ── 2. Party ID expiry checks ───────────────────────────────────

  for (const { label, party } of parties) {
    if (party.expirationDate && isExpired(party.expirationDate)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `${label} (${party.fullName || "unnamed"}): ID expired on ${party.expirationDate}`,
      });
    }
  }

  // ── 3. Attachment expiry checks ─────────────────────────────────

  for (let i = 0; i < idAttachments.length; i++) {
    const att = idAttachments[i];
    const ef = att.extractedFields;
    const expiry = ef.id_expiry || "";
    const name = ef.name_en || `ID Attachment #${i + 1}`;
    if (expiry && isExpired(expiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `Extracted ID for ${name} expired on ${expiry}`,
        details: `Attachment: ${att.documentTypeCode}`,
      });
    }
  }

  for (let i = 0; i < crAttachments.length; i++) {
    const att = crAttachments[i];
    const ef = att.extractedFields;
    const crName = ef.company_name || `CR #${i + 1}`;

    // 3a. CR expiry date
    const crExpiry = (ef.cr_expiry_date ?? "").trim();
    if (crExpiry && isExpired(crExpiry)) {
      findings.push({
        severity: "error",
        category: "Expired Document",
        message: `CR for "${crName}" expired on ${crExpiry}`,
      });
    }

    // 3b. CR status check
    const crStatus = (ef.cr_status ?? "").trim().toLowerCase();
    if (crStatus && crStatus !== "active" && crStatus !== "نشط") {
      findings.push({
        severity: "error",
        category: "Invalid Status",
        message: `CR for "${crName}" has status "${ef.cr_status}" (expected Active)`,
      });
    }

    // 3c. Cross-validate CR signatories against parties
    const allPartyIds = new Set(
      parties.map(({ party }) => party.idNumber.trim()).filter(Boolean)
    );
    const allPartyNames = new Map(
      parties.map(({ label, party }) => [norm(party.fullName), label] as const)
    );

    for (let si = 0; si < att.signatories.length; si++) {
      const sig = att.signatories[si];
      const sigLabel = sig.name_en || `Signatory #${si + 1}`;
      const sigId = sig.identification_number.trim();

      // Signatory ID number should match one of the parties
      if (sigId && !allPartyIds.has(sigId)) {
        findings.push({
          severity: "error",
          category: "Cross-Validation Mismatch",
          message: `CR signatory "${sigLabel}": ID (${sigId}) does not match any party`,
          details: `Expected one of: ${[...allPartyIds].join(", ")}`,
        });
      }

      // Signatory name should match one of the parties
      const sigNameNorm = norm(sig.name_en);
      if (sigNameNorm && !allPartyNames.has(sigNameNorm)) {
        // Try partial match (signatory name contained in a party name or vice versa)
        const partialMatch = [...allPartyNames.keys()].some(
          (pn) => pn.includes(sigNameNorm) || sigNameNorm.includes(pn)
        );
        if (!partialMatch) {
          findings.push({
            severity: "warning",
            category: "Cross-Validation Mismatch",
            message: `CR signatory "${sig.name_en}" name does not match any party name`,
            details: `Party names: ${parties.map(({ party }) => party.fullName).filter(Boolean).join(", ")}`,
          });
        }
      }

      // Signatory nationality vs party citizenship (if sigId matches a party)
      if (sigId) {
        const matchingParty = parties.find(({ party }) => party.idNumber.trim() === sigId);
        if (matchingParty) {
          const sigNat = norm(sig.nationality_en);
          const partyCit = norm(matchingParty.party.citizenship);
          if (sigNat && partyCit && sigNat !== partyCit) {
            findings.push({
              severity: "warning",
              category: "Cross-Validation Mismatch",
              message: `CR signatory "${sigLabel}": nationality mismatch with ${matchingParty.label}`,
              details: `Signatory: "${sig.nationality_en}"  |  Party: "${matchingParty.party.citizenship}"`,
            });
          }
        }
      }
    }
  }

  // ── 4. Cross-validation: party ↔ Personal ID attachments ───────

  // Build lookup of ID attachments by id_number
  const idAttByNumber = new Map<string, ManualAttachment>();
  for (const att of idAttachments) {
    const idNum = att.extractedFields.id_number?.trim();
    if (idNum) {
      idAttByNumber.set(idNum, att);
    }
  }

  for (const { label, party } of parties) {
    const partyId = party.idNumber.trim();
    const partyName = party.fullName.trim();
    if (!partyId) continue;

    const match = idAttByNumber.get(partyId);
    if (!match) {
      // Only warn if there are ID attachments at all (user might not have added one yet)
      if (idAttachments.length > 0) {
        findings.push({
          severity: "warning",
          category: "Cross-Validation",
          message: `No ID attachment found matching ${label}'s ID number (${partyId})`,
          details: `${partyName || "unnamed"} — no extracted ID with matching id_number`,
        });
      }
      continue;
    }

    const ef = match.extractedFields;

    // 4a. Name mismatch
    const extName = norm(ef.name_en || "");
    if (partyName && extName && norm(partyName) !== extName) {
      findings.push({
        severity: "warning",
        category: "Cross-Validation Mismatch",
        message: `${label}: name mismatch with extracted ID`,
        details: `Form: "${partyName}"  |  Extracted: "${ef.name_en}"`,
      });
    }

    // 4b. Citizenship mismatch
    const partyCit = norm(party.citizenship);
    const extCit = norm(ef.citizenship || "");
    if (partyCit && extCit && partyCit !== extCit) {
      findings.push({
        severity: "error",
        category: "Cross-Validation Mismatch",
        message: `${label}: citizenship mismatch`,
        details: `Form: "${party.citizenship}"  |  Extracted: "${ef.citizenship}"`,
      });
    }

    // 4c. ID expiry mismatch
    const partyExpiry = party.expirationDate.trim();
    const extExpiry = (ef.id_expiry || "").trim();
    if (partyExpiry && extExpiry && partyExpiry !== extExpiry) {
      findings.push({
        severity: "error",
        category: "Cross-Validation Mismatch",
        message: `${label}: ID expiry date mismatch`,
        details: `Form: ${partyExpiry}  |  Extracted: ${extExpiry}`,
      });
    }
  }

  return findings;
}
