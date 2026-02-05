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
 * Translation keys used in this file:
 *
 * Category names:
 * - validation.expiredDocument
 * - validation.missingData
 * - validation.crossValidation
 * - validation.crossValidationMismatch
 * - validation.missingAttachment
 * - validation.unsavedData
 *
 * Messages for runTier1Checks:
 * - validation.unknownParty, validation.idOf, validation.expiredOn, validation.partyNationalId
 * - validation.poaEndDatePast, validation.capacityProof, validation.poaExpiryPast, validation.crExpiryPast
 * - validation.extractedIdOf, validation.unknown, validation.docExtraction
 * - validation.noIdInStructured, validation.noIdExtractionFound, validation.idNumber
 * - validation.partyNoMatchingExtraction, validation.idExpiryMismatch, validation.structured, validation.extracted
 * - validation.nationalityMismatch, validation.nameMismatch, validation.idTypeMismatch
 * - validation.unmatchedExtraction, validation.applicationNumberEmpty, validation.partyHasNoName
 * - validation.partyIdLabel, validation.noPartiesFound
 *
 * Messages for runManualTier1Checks:
 * - validation.firstParty, validation.secondParty, validation.noAppTypeSelected
 * - validation.partyNoName, validation.partyNoId, validation.noAttachments
 * - validation.partiesButNoId, validation.addIdBeforeAgents, validation.unsavedAttachments
 * - validation.saveBeforeAgents, validation.noName, validation.idExpiredOn, validation.idAttachmentNum
 * - validation.attachment, validation.crOf, validation.crNum, validation.expiredOnDate
 * - validation.signatoryLabel, validation.signatoryIdNoMatch, validation.expectedOneOf
 * - validation.signatoryNameNoMatch, validation.partyNames, validation.signatoryNationalityMismatch
 * - validation.signatory, validation.party, validation.noIdAttachmentForParty
 * - validation.noMatchingIdExtraction, validation.formLabel
 */

/**
 * Run deterministic Tier-1 checks against the current (possibly edited)
 * context data. Returns an array of findings — empty means all clear.
 */
export function runTier1Checks(ctx: ContextData, t: (key: string) => string): ValidationFinding[] {
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
    const name = str(party.full_name_en) || str(party.full_name_ar) || t("validation.unknownParty");
    if (expiry && isExpired(expiry)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${t("validation.idOf")} ${name} ${t("validation.expiredOn")} ${expiry}`,
        details: `${t("validation.partyNationalId")}: ${str(party.national_id)}`,
      });
    }
  }

  // 1b. Application POA end date
  const poaEnd = str(app.poa_end_date);
  if (poaEnd && isExpired(poaEnd)) {
    findings.push({
      severity: "error",
      category: t("validation.expiredDocument"),
      message: `${t("validation.poaEndDatePast")}: ${poaEnd}`,
    });
  }

  // 1c. Capacity proof expiry dates
  for (let pi = 0; pi < proofs.length; pi++) {
    const proof = proofs[pi];
    const label = `${t("validation.capacityProof")} ${pi + 1}`;

    const poaExpiry = str(proof.poa_expiry);
    if (poaExpiry && isExpired(poaExpiry)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${label}: ${t("validation.poaExpiryPast")} (${poaExpiry})`,
      });
    }

    const crExpiry = str(proof.cr_expiry_date);
    if (crExpiry && isExpired(crExpiry)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${label}: ${t("validation.crExpiryPast")} (${crExpiry})`,
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
        category: t("validation.expiredDocument"),
        message: `${t("validation.extractedIdOf")} ${who || t("validation.unknown")} ${t("validation.expiredOn")} ${idExpiry}`,
        details: `${t("validation.docExtraction")}${i + 1}`,
      });
    }
  }

  // ── 2. Cross-validation: Structured party ↔ Unstructured ID ───

  const matchedExtractionIds = new Set<string>();

  for (const party of parties) {
    const partyId = str(party.national_id);
    const name = str(party.full_name_en) || str(party.full_name_ar) || t("validation.unknownParty");

    if (!partyId) {
      findings.push({
        severity: "warning",
        category: t("validation.missingData"),
        message: `${name} ${t("validation.noIdInStructured")}`,
      });
      continue;
    }

    const match = idExtractionsByNumber.get(partyId);
    if (!match) {
      findings.push({
        severity: "warning",
        category: t("validation.crossValidation"),
        message: `${t("validation.noIdExtractionFound")} ${name} (${t("validation.idNumber")}: ${partyId})`,
        details: t("validation.partyNoMatchingExtraction"),
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
        category: t("validation.crossValidationMismatch"),
        message: `${name}: ${t("validation.idExpiryMismatch")}`,
        details: `${t("validation.structured")}: ${partyExpiry}  |  ${t("validation.extracted")}: ${extExpiry}`,
      });
    }

    // 2b. Citizenship / nationality mismatch
    const partyNat = str(party.nationality_code).toUpperCase();
    const extNat = str(ef.citizenship).toUpperCase();
    if (partyNat && extNat && partyNat !== extNat) {
      findings.push({
        severity: "error",
        category: t("validation.crossValidationMismatch"),
        message: `${name}: ${t("validation.nationalityMismatch")}`,
        details: `${t("validation.structured")}: ${partyNat}  |  ${t("validation.extracted")}: ${extNat}`,
      });
    }

    // 2c. Name mismatch (fuzzy: compare lowercased full name)
    const partyName = str(party.full_name_en).toLowerCase();
    const extName = (str(ef.name_en) || (str(ef.first_name) + " " + str(ef.last_name)).trim()).toLowerCase();
    if (partyName && extName && partyName !== extName) {
      findings.push({
        severity: "warning",
        category: t("validation.crossValidationMismatch"),
        message: `${name}: ${t("validation.nameMismatch")}`,
        details: `${t("validation.structured")}: "${str(party.full_name_en)}"  |  ${t("validation.extracted")}: "${str(ef.name_en) || (str(ef.first_name) + " " + str(ef.last_name)).trim()}"`,
      });
    }

    // 2d. ID type mismatch
    const partyIdType = str(party.national_id_type).toLowerCase().replace(/[_\s-]/g, "");
    const extIdType = str(ef.id_type).toLowerCase().replace(/[_\s-]/g, "");
    if (partyIdType && extIdType && partyIdType !== extIdType) {
      findings.push({
        severity: "warning",
        category: t("validation.crossValidationMismatch"),
        message: `${name}: ${t("validation.idTypeMismatch")}`,
        details: `${t("validation.structured")}: ${str(party.national_id_type)}  |  ${t("validation.extracted")}: ${str(ef.id_type)}`,
      });
    }
  }

  // 2e. Unmatched ID extractions (extraction has id_number but no party uses it)
  for (const [idNum, { fields }] of idExtractionsByNumber) {
    if (!matchedExtractionIds.has(idNum)) {
      const who = str(fields.name_en) || (str(fields.first_name) + " " + str(fields.last_name)).trim();
      findings.push({
        severity: "warning",
        category: t("validation.crossValidation"),
        message: `${t("validation.extractedIdOf")} ${who || t("validation.unknown")} (${idNum}) ${t("validation.unmatchedExtraction")}`,
      });
    }
  }

  // ── 3. Missing required fields ────────────────────────────────

  if (!str(app.application_number)) {
    findings.push({
      severity: "warning",
      category: t("validation.missingData"),
      message: t("validation.applicationNumberEmpty"),
    });
  }

  for (const party of parties) {
    const name = str(party.full_name_en) || str(party.full_name_ar);
    if (!name) {
      findings.push({
        severity: "warning",
        category: t("validation.missingData"),
        message: `${t("validation.party")} (${t("validation.partyIdLabel")}: ${str(party.national_id) || "?"}) ${t("validation.partyHasNoName")}`,
      });
    }
  }

  if (parties.length === 0) {
    findings.push({
      severity: "error",
      category: t("validation.missingData"),
      message: t("validation.noPartiesFound"),
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
  attachments: ManualAttachment[],
  t: (key: string) => string
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
    { label: t("validation.firstParty"), role: "grantor", party: firstParty },
    { label: t("validation.secondParty"), role: "agent", party: secondParty },
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
      category: t("validation.missingData"),
      message: t("validation.noAppTypeSelected"),
    });
  }

  for (const { label, party } of parties) {
    if (!party.fullName) {
      findings.push({
        severity: "warning",
        category: t("validation.missingData"),
        message: `${label} ${t("validation.partyNoName")}`,
      });
    }
    if (!party.idNumber) {
      findings.push({
        severity: "warning",
        category: t("validation.missingData"),
        message: `${label} ${t("validation.partyNoId")}`,
      });
    }
  }

  if (attachments.length === 0) {
    findings.push({
      severity: "warning",
      category: t("validation.missingData"),
      message: t("validation.noAttachments"),
    });
  }

  // Parties exist but no Personal ID attachments
  const hasParties = firstParty.fullName || secondParty.fullName || firstParty.idNumber || secondParty.idNumber;
  if (hasParties && idAttachments.length === 0) {
    findings.push({
      severity: "error",
      category: t("validation.missingAttachment"),
      message: t("validation.partiesButNoId"),
      details: t("validation.addIdBeforeAgents"),
    });
  }

  const unsaved = attachments.filter((a) => !a.saved);
  if (unsaved.length > 0) {
    findings.push({
      severity: "warning",
      category: t("validation.unsavedData"),
      message: `${unsaved.length} ${t("validation.unsavedAttachments")}`,
      details: t("validation.saveBeforeAgents"),
    });
  }

  // ── 2. Party ID expiry checks ───────────────────────────────────

  for (const { label, party } of parties) {
    if (party.expirationDate && isExpired(party.expirationDate)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${label} (${party.fullName || t("validation.noName")}): ${t("validation.idExpiredOn")} ${party.expirationDate}`,
      });
    }
  }

  // ── 3. Attachment expiry checks ─────────────────────────────────

  for (let i = 0; i < idAttachments.length; i++) {
    const att = idAttachments[i];
    const ef = att.extractedFields;
    const expiry = ef.id_expiry || "";
    const name = ef.name_en || `${t("validation.idAttachmentNum")} ${i + 1}`;
    if (expiry && isExpired(expiry)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${t("validation.extractedIdOf")} ${name} ${t("validation.expiredOn")} ${expiry}`,
        details: `${t("validation.attachment")}: ${att.documentTypeCode}`,
      });
    }
  }

  for (let i = 0; i < crAttachments.length; i++) {
    const att = crAttachments[i];
    const ef = att.extractedFields;
    const crName = ef.company_name || `${t("validation.crNum")} ${i + 1}`;

    // 3a. CR expiry date
    const crExpiry = (ef.cr_expiry_date ?? "").trim();
    if (crExpiry && isExpired(crExpiry)) {
      findings.push({
        severity: "error",
        category: t("validation.expiredDocument"),
        message: `${t("validation.crOf")} "${crName}" ${t("validation.expiredOnDate")} ${crExpiry}`,
      });
    }

    // 3b. Cross-validate CR signatories against parties
    const allPartyIds = new Set(
      parties.map(({ party }) => party.idNumber.trim()).filter(Boolean)
    );
    const allPartyNames = new Map(
      parties.map(({ label, party }) => [norm(party.fullName), label] as const)
    );

    for (let si = 0; si < att.signatories.length; si++) {
      const sig = att.signatories[si];
      const sigLabel = sig.name_en || `${t("validation.signatoryLabel")} ${si + 1}`;
      const sigId = sig.identification_number.trim();

      // Signatory ID number should match one of the parties
      if (sigId && !allPartyIds.has(sigId)) {
        findings.push({
          severity: "error",
          category: t("validation.crossValidationMismatch"),
          message: `${t("validation.signatory")} "${sigLabel}": ${t("validation.signatoryIdNoMatch")} (${sigId})`,
          details: `${t("validation.expectedOneOf")}: ${[...allPartyIds].join("، ")}`,
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
            category: t("validation.crossValidationMismatch"),
            message: `${t("validation.signatory")} "${sig.name_en}" ${t("validation.signatoryNameNoMatch")}`,
            details: `${t("validation.partyNames")}: ${parties.map(({ party }) => party.fullName).filter(Boolean).join("، ")}`,
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
              category: t("validation.crossValidationMismatch"),
              message: `${t("validation.signatory")} "${sigLabel}": ${t("validation.signatoryNationalityMismatch")} ${matchingParty.label}`,
              details: `${t("validation.signatory")}: "${sig.nationality_en}"  |  ${t("validation.party")}: "${matchingParty.party.citizenship}"`,
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
          category: t("validation.crossValidation"),
          message: `${t("validation.noIdAttachmentForParty")} ${label} (${partyId})`,
          details: `${partyName || t("validation.noName")} — ${t("validation.noMatchingIdExtraction")}`,
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
        category: t("validation.crossValidationMismatch"),
        message: `${label}: ${t("validation.nameMismatch")}`,
        details: `${t("validation.formLabel")}: "${partyName}"  |  ${t("validation.extracted")}: "${ef.name_en}"`,
      });
    }

    // 4b. Citizenship mismatch
    const partyCit = norm(party.citizenship);
    const extCit = norm(ef.citizenship || "");
    if (partyCit && extCit && partyCit !== extCit) {
      findings.push({
        severity: "error",
        category: t("validation.crossValidationMismatch"),
        message: `${label}: ${t("validation.nationalityMismatch")}`,
        details: `${t("validation.formLabel")}: "${party.citizenship}"  |  ${t("validation.extracted")}: "${ef.citizenship}"`,
      });
    }

    // 4c. ID expiry mismatch
    const partyExpiry = party.expirationDate.trim();
    const extExpiry = (ef.id_expiry || "").trim();
    if (partyExpiry && extExpiry && partyExpiry !== extExpiry) {
      findings.push({
        severity: "error",
        category: t("validation.crossValidationMismatch"),
        message: `${label}: ${t("validation.idExpiryMismatch")}`,
        details: `${t("validation.formLabel")}: ${partyExpiry}  |  ${t("validation.extracted")}: ${extExpiry}`,
      });
    }
  }

  return findings;
}
