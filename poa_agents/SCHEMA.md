# Supabase Database Schema

High-level overview of tables used by the POA validation system.

---

## Entity Relationship Diagram

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│ transaction_    │     │    applications      │     │ personal_       │
│ types           │────▶│    (11 rows)         │     │ parties         │
│ (10 types)      │     │                      │     │ (29 rows)       │
└─────────────────┘     └──────────┬───────────┘     └────────┬────────┘
        │                          │                          │
        ▼                          │                          │
┌─────────────────┐               │                          │
│ transaction_    │               │                          │
│ configs         │               ▼                          ▼
│ (10 configs)    │     ┌─────────────────────────────────────────┐
└─────────────────┘     │      application_party_roles            │
                        │      (29 rows)                          │
                        └─────────────────┬───────────────────────┘
                                          │
┌─────────────────┐     ┌─────────────────▼───────────────────────┐
│ document_types  │────▶│         attachments                     │
│ (10 types)      │     │         (43 rows)                       │
└─────────────────┘     └─────────────────┬───────────────────────┘
                                          │
                        ┌─────────────────▼───────────────────────┐
                        │       document_extractions              │
                        │       (32 rows)                         │
                        └─────────────────┬───────────────────────┘
                                          │
                        ┌─────────────────▼───────────────────────┐
                        │         poa_extractions                 │
                        │         (11 rows)                       │
                        └─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      VALIDATION PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   applications ──▶ validation_reports ──▶ legal_opinions        │
│                          │                      │                │
│                          └──────┬───────────────┘                │
│                                 ▼                                │
│                           escalations                            │
│                                 │                                │
│                                 ▼                                │
│                         research_traces                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│    articles     │  Legal corpus for RAG (pgvector embeddings)
└─────────────────┘
```

---

## Core Tables

### `applications`
**Purpose:** Main application records for POA transactions.

| Key Fields | Description |
|------------|-------------|
| `id` | UUID primary key |
| `sak_case_number` | Human-readable case number (e.g., SAK-2024-POA-00001) |
| `status` | pending, processing, approved, rejected, error |
| `transaction_type_code` | FK to transaction_types |
| `transaction_value` | Monetary value (QAR) |
| `transaction_subject_ar/en` | Description of transaction |
| `processing_status` | Current stage in pipeline |

**Rows:** 11 test applications

---

### `personal_parties`
**Purpose:** Individuals or entities involved in applications.

| Key Fields | Description |
|------------|-------------|
| `id` | UUID primary key |
| `qid` | Qatar ID number (11 digits) |
| `name_ar` / `name_en` | Arabic and English names |
| `nationality` | Country code |
| `date_of_birth` | For age verification |
| `is_entity` | True for companies |
| `entity_type` | LLC, QSC, etc. if is_entity |

**Rows:** 29 parties

---

### `application_party_roles`
**Purpose:** Links parties to applications with their role.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `personal_party_id` | FK to personal_parties |
| `party_position` | grantor, agent, witness, etc. |
| `role_code` | FK to role_types |
| `capacity_fields` | JSON - special capacity info |
| `capacity_verified` | Boolean - has capacity been verified |

**Rows:** 29 role assignments

---

### `attachments`
**Purpose:** Uploaded documents for applications.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `file_name` / `file_url` | Document location |
| `document_type_code` | FK to document_types |
| `ocr_status` | pending, completed, failed |

**Rows:** 43 documents

---

### `document_extractions`
**Purpose:** OCR/VLM extraction results from documents.

| Key Fields | Description |
|------------|-------------|
| `attachment_id` | FK to attachments |
| `extraction_model` | Model used (Azure DI, GPT-4V) |
| `confidence_overall` | Extraction confidence 0-1 |
| `raw_text_ar/en` | Full extracted text |
| `extracted_fields` | JSON - structured field values |

**Rows:** 32 extractions

---

### `poa_extractions`
**Purpose:** POA-specific structured data extracted from documents.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `poa_number` / `poa_date` / `poa_expiry` | POA identification |
| `principal_qid` / `agent_qid` | Principal and agent QIDs |
| `granted_powers` | Array of powers granted |
| `is_general_poa` / `is_special_poa` | POA type flags |
| `has_substitution_right` | Can agent sub-delegate |

**Rows:** 11 POA extractions

---

## Reference Tables

### `transaction_types`
**Purpose:** Defines types of POA transactions.

| Key Fields | Description |
|------------|-------------|
| `code` | Unique identifier (e.g., GENERAL_POA) |
| `category` | POA, SALE, etc. |
| `requires_special_poa` | Boolean |
| `is_act_of_disposition` | High-risk transaction flag |

**Current Types:**
- GENERAL_POA, GENERAL_POA_CASES
- SPECIAL_POA_PROPERTY, SPECIAL_POA_GOVT, SPECIAL_POA_COMPANY
- SPECIAL_POA_INHERITANCE, SPECIAL_POA_BANKING

---

### `transaction_configs`
**Purpose:** Per-transaction-type validation requirements.

| Key Fields | Description |
|------------|-------------|
| `transaction_type_code` | FK to transaction_types |
| `required_parties` | JSON array of required party roles |
| `required_documents` | JSON array of required doc types |
| `tier1_checks` | JSON array of check function names |

---

### `role_types`
**Purpose:** Defines possible party roles.

| Examples | Description |
|----------|-------------|
| `INDIVIDUAL_SELF` | Acting in personal capacity |
| `POA_HOLDER` | Authorized attorney |
| `GUARDIAN_MINOR` | Guardian of minor child |
| `COMPANY_AUTHORIZED` | Company representative |

---

### `capacity_types`
**Purpose:** Legal capacity categories.

| Examples | Description |
|----------|-------------|
| `PERSONAL` | Individual acting for self |
| `REPRESENTATIVE` | Acting for another |
| `GUARDIAN` | Legal guardian |
| `CORPORATE` | Company representative |

---

### `document_types`
**Purpose:** Document classification taxonomy.

| Examples | Description |
|----------|-------------|
| `QID_GRANTOR` | Grantor's Qatar ID |
| `QID_AGENT` | Agent's Qatar ID |
| `POA_DOCUMENT` | Power of Attorney |
| `BOARD_RESOLUTION` | Company board resolution |

---

## Validation Pipeline Tables

### `validation_reports`
**Purpose:** Tier 1 deterministic validation results.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `tier` | "tier1" |
| `checks_run` | JSON array of check results |
| `blocking_failures` | Count of blocking issues |
| `can_proceed_to_tier2` | Boolean - passed Tier 1 |
| `legal_opinion_id` | FK to legal_opinions (if Tier 2 run) |

---

### `research_traces`
**Purpose:** Audit trail of Tier 2 deep research.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `decomposition` | JSON - sub-questions generated |
| `research_steps` | JSON array - all research actions |
| `sub_question_findings` | JSON array - findings per question |
| `verification` | JSON - reflection pass results |
| `max_depth_reached` | How deep the research went |

---

### `legal_opinions`
**Purpose:** Final Tier 2 legal opinions.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `finding` | VALID, INVALID, VALID_WITH_CONDITIONS, REQUIRES_REVIEW, INCONCLUSIVE |
| `confidence` | 0.0 - 1.0 |
| `confidence_level` | HIGH (≥0.8), MEDIUM (0.6-0.8), LOW (<0.6) |
| `analysis` | JSON - structured analysis by category |
| `concerns` / `recommendations` | JSON arrays |
| `opinion_text` | Full opinion in markdown |

---

### `escalations`
**Purpose:** Cases requiring human review.

| Key Fields | Description |
|------------|-------------|
| `application_id` | FK to applications |
| `tier_at_escalation` | tier1 or tier2 |
| `escalation_reason` | Why escalated |
| `confidence_at_escalation` | Confidence when escalated |
| `priority` | standard, urgent, critical |
| `sme_decision` | Human reviewer's decision |
| `resolved_at` | When resolved |

---

## Legal Corpus

### `articles`
**Purpose:** Legal articles for RAG-based research.

| Key Fields | Description |
|------------|-------------|
| `article_number` | Primary key |
| `text_arabic` / `text_english` | Article content |
| `hierarchy_path` | JSON - law/chapter/section |
| `embedding` | pgvector - for semantic search |

**Used by:** Legal Research Agent for retrieving relevant legal context.

---

## Deprecated Tables

### `rule_packs` ⚠️
### `validation_rules` ⚠️

These tables were part of the original rule-based approach. They are marked deprecated with `deprecated=true` flag. The new two-tier architecture uses:
- **Tier 1:** Code-based checks in `tier1_validation_agent`
- **Tier 2:** RAG + LLM reasoning in `legal_research_agent`

---

## Row Counts Summary

| Table | Rows | Notes |
|-------|------|-------|
| applications | 11 | Test scenarios |
| personal_parties | 29 | ~2-3 per application |
| application_party_roles | 29 | Role assignments |
| attachments | 43 | ~4 per application |
| document_extractions | 32 | OCR results |
| poa_extractions | 11 | One per application |
| transaction_types | 10 | Reference data |
| transaction_configs | 10 | Reference data |
| role_types | 14 | Reference data |
| capacity_types | 6 | Reference data |
| document_types | 10 | Reference data |
| validation_reports | 0 | Populated by agents |
| research_traces | 0 | Populated by agents |
| legal_opinions | 0 | Populated by agents |
| escalations | 0 | Populated by agents |
| articles | 0 | Legal corpus (to be seeded) |

