# Supabase Data Model Architecture

> SAK AI Agent - POA & Sale Transaction Validation System

---

## Table of Contents

1. [Overview](#overview)
2. [ML Architecture Pipeline](#ml-architecture-pipeline)
3. [Entity Relationship Diagram](#entity-relationship-diagram)
4. [Core Tables](#core-tables)
5. [Reference Tables](#reference-tables)
6. [ML Pipeline Tables](#ml-pipeline-tables)
7. [Enums Reference](#enums-reference)
8. [Agent-to-Table Mapping](#agent-to-table-mapping)
9. [Data Flow](#data-flow)
10. [Migration Notes](#migration-notes)

---

## Overview

The SAK AI Agent uses a **two-tier validation pipeline** to process Power of Attorney and Sale applications:

- **Tier 1**: Deterministic validation (completeness, format, reconciliation)
- **Tier 2**: Agentic legal reasoning with RAG-based statute retrieval

### Key Technologies
- **PostgreSQL**: Primary relational database
- **pgvector**: Vector embeddings for semantic search (articles table)
- **Supabase**: Hosted PostgreSQL with REST API
- **Temporal**: Workflow orchestration for agentic agents

### Key Design Decisions
1. `poa_extractions` merged into `capacity_proofs` (supports POA + Sale transactions)
2. `tier1_checks` kept as JSON in `transaction_configs`
3. Dual party terminology: `party_type` (positional) + `party_role` (functional)
4. `is_entity` flag retained on parties
5. No separate users table - submitter is a party reference

---

## ML Architecture Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Document   │───►│   Virtual   │───►│   Tier 1    │───►│   Tier 2    │───►│   Routing   │
│  Processing │    │ Case Object │    │ Validation  │    │   Legal     │    │  Decision   │
│             │    │             │    │             │    │  Reasoning  │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     Vision             Builder        Deterministic        Agentic          Risk-Based
     Agents                            Rules Engine         RAG + LLM        Gate
```

### Pipeline Tables Mapping

| Stage | Tables |
|-------|--------|
| **Document Processing** | `documents`, `document_extractions`, `document_classifications`, `extracted_fields` |
| **Virtual Case Object** | `case_objects` |
| **Tier 1 Validation** | `validation_reports`, `fact_sheets` |
| **Tier 2 Legal Reasoning** | `legal_briefs`, `legal_analysis_sessions`, `issue_decompositions`, `retrieved_evidence`, `legal_opinions`, `citations` |
| **Routing Decision** | `risk_scores`, `routing_decisions`, `escalations` |

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LANDING ZONE                                  │
│                    (from SAK → Supabase)                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATIONS                                      │
│  - application_number, transaction_type_code                                  │
│  - submitter_party_type, submitter_national_id (the party who submitted)     │
│  - status (draft → submitted → ... → completed)                              │
│  - draft_expires_at (7 days), rejection_expires_at (15 days)                 │
│  - poa_duration_type, poa_start_date, poa_end_date                           │
└───────────────────────────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────────────────┐
        │ 1:N       │ 1:N       │ 1:N                   │ 1:N
        ▼           ▼           ▼                       ▼
┌─────────────┐ ┌─────────┐ ┌─────────────┐    ┌────────────────┐
│   PARTIES   │ │DOCUMENTS│ │POA_TEMPLATES│    │DUPLICATE_CHECKS│
│             │ │         │ │             │    │                │
│ party_type  │ │file_name│ │template_id  │    │match_type      │
│ party_role  │ │ocr_status│ │is_selected │    │is_resolved     │
│ capacity    │ │         │ │custom_text  │    │                │
│ is_entity   │ └────┬────┘ └─────────────┘    └────────────────┘
│ is_submitter│      │
└──────┬──────┘      │ 1:N
       │             ▼
       │ 1:1    ┌───────────────────┐
       ▼        │DOCUMENT_EXTRACTIONS│
┌──────────────┐│                   │
│CAPACITY_PROOFS│ (OCR results)     │
│              ││                   │
│ capacity_type│└───────────────────┘
│ cr_number    │
│ poa_number   │
│ letter_number│
│ (merged POA  │
│  extractions)│
└──────┬───────┘
       │
       │ 1:N
       ▼
┌──────────────────┐
│CAPACITY_PRINCIPALS│
│                  │
│ principal_type   │
│ national_id      │
│ entity_name      │
└──────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                        REFERENCE / CONFIG TABLES                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌───────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│ TRANSACTION_TYPES │     │ TRANSACTION_CONFIGS │     │CAPACITY_CONFIGURATIONS│
│                   │     │                    │     │                     │
│ code (PK)         │◄────│ transaction_type   │     │ capacity (PK)       │
│ name_ar/en        │     │ required_parties   │     │ capacity_type       │
│ category          │     │ required_documents │     │ entry_method        │
└───────────────────┘     │ tier1_checks (JSON)│     │ required_proof_fields│
                          └────────────────────┘     └─────────────────────┘

┌───────────────────┐     ┌────────────────────┐
│ ATTACHMENT_TYPES  │     │TEMPLATE_DEFINITIONS│
│                   │     │                    │
│ code (PK)         │     │ template_code (PK) │
│ name_ar/en        │     │ template_text_ar   │
│ category          │     │ transaction_types[]│
└───────────────────┘     └────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML PIPELINE TABLES                                   │
│                  (Document Processing → Tier 1 → Tier 2 → Routing)          │
└─────────────────────────────────────────────────────────────────────────────┘

DOCUMENTS
    │
    ├─────────────────────┐
    │ 1:N                 │ 1:N
    ▼                     ▼
┌────────────────┐  ┌────────────────────┐
│ DOC_CLASSIF-   │  │DOCUMENT_EXTRACTIONS│
│ ICATIONS       │  │                    │
│                │  │ extracted_fields   │
│ ml_type        │  │ raw_text_ar        │
│ confidence     │  │ bounding_boxes     │
│ alternatives   │  │                    │
└────────────────┘  └─────────┬──────────┘
                              │ 1:N (optional)
                              ▼
                    ┌────────────────────┐
                    │  EXTRACTED_FIELDS  │
                    │  (normalized)      │
                    │                    │
                    │ field_type         │
                    │ value, confidence  │
                    └────────────────────┘

applications
     │
     │ 1:N
     ▼
┌────────────────────┐
│   CASE_OBJECTS     │◄───── Virtual Case Object (unified JSON)
│                    │
│ case_data (JSONB)  │       Combines: SQL data + extracted evidence
│ completeness_score │
│ confidence_score   │
│ field_mappings     │
└─────────┬──────────┘
          │
          │ 1:1
          ▼
┌────────────────────┐     ┌────────────────────┐
│ VALIDATION_REPORTS │────►│    FACT_SHEETS     │
│                    │     │                    │
│ tier1 verdict      │     │ facts (JSONB)      │
│ checks_run         │     │ blockers           │
│ can_proceed_tier2  │     │ open_questions     │
└────────────────────┘     └─────────┬──────────┘
                                     │
                                     │ 1:1
                                     ▼
                           ┌────────────────────┐
                           │   LEGAL_BRIEFS     │◄───── Condenser Output
                           │                    │
                           │ brief_content      │
                           │ issues_to_analyze  │
                           └─────────┬──────────┘
                                     │
                                     │ 1:N
                                     ▼
                           ┌────────────────────┐
                           │LEGAL_ANALYSIS_     │◄───── Tier 2 Processing
                           │SESSIONS            │
                           │                    │
                           │ status (enum)      │
                           │ llm_model          │
                           └─────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │ 1:N            │ 1:N            │
                    ▼                ▼                │
          ┌─────────────────┐ ┌─────────────────┐    │
          │ISSUE_DECOMPOS-  │ │RESEARCH_TRACES  │    │
          │ITIONS           │ │                 │    │
          │                 │ │ phase           │    │
          │ question        │ │ trace_data      │    │
          │ category        │ │                 │    │
          │ finding         │ └─────────────────┘    │
          └────────┬────────┘                        │
                   │                                 │
                   │ 1:N                             │
                   ▼                                 │
          ┌─────────────────┐                        │
          │RETRIEVED_       │                        │
          │EVIDENCE         │                        │
          │                 │                        │
          │ article_number ─┼────────────────────────┼───► ARTICLES
          │ similarity_score│                        │
          │ chunk_text      │                        │
          └─────────────────┘                        │
                                                     │
                                     ┌───────────────┘
                                     │ 1:1
                                     ▼
                           ┌────────────────────┐
                           │  LEGAL_OPINIONS    │◄───── Final Tier 2 Output
                           │                    │
                           │ finding            │
                           │ confidence_score   │
                           │ full_analysis      │
                           │ needs_escalation   │
                           └─────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │ 1:N            │                │
                    ▼                │                │
          ┌─────────────────┐        │                │
          │   CITATIONS     │        │                │
          │                 │        │                │
          │ claim_text      │        │                │
          │ article_number ─┼────────┼───► ARTICLES   │
          └─────────────────┘        │                │
                                     │                │
                                     │ 1:1            │
                                     ▼                │
                           ┌────────────────────┐     │
                           │   RISK_SCORES      │     │
                           │                    │     │
                           │ composite_score    │     │
                           │ risk_level         │     │
                           │ reason_codes       │     │
                           └─────────┬──────────┘     │
                                     │                │
                                     │ 1:1            │
                                     ▼                │
                           ┌────────────────────┐     │
                           │ROUTING_DECISIONS   │     │
                           │                    │     │
                           │ decision_bucket    │     │
                           │ routed_to          │     │
                           │ remediations       │     │
                           └─────────┬──────────┘     │
                                     │                │
                                     │                │
                    ┌────────────────┴────────────────┘
                    │ (if escalation needed)
                    ▼
          ┌─────────────────┐
          │  ESCALATIONS    │
          │                 │
          │ tier, reason    │
          │ status          │
          │ sme_decision    │
          └─────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                      LEGAL CORPUS (RAG)                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│       ARTICLES          │
│                         │
│ article_number (PK)     │
│ text_arabic             │
│ text_english            │
│ hierarchy_path          │
│ embedding (pgvector)    │◄──── Vector similarity search for RAG
└─────────────────────────┘
```

---

## Core Tables

### applications

Main POA/Sale application records. Data landing zone from SAK system.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_number` | VARCHAR(50) | Unique case number (e.g., "SAK-2024-POA-00001") |
| `transaction_type_code` | VARCHAR(20) | FK to `transaction_types` |
| `submitter_party_type` | party_type | `first_party` or `second_party` |
| `submitter_national_id` | VARCHAR(20) | National ID of submitter |
| `submitter_id_type` | id_type | Type of ID used |
| `status` | application_status | Current status (draft → completed) |
| `processing_stage` | processing_stage | Pipeline stage |
| `transaction_value` | DECIMAL(18,2) | Monetary value in QAR |
| `transaction_subject_ar` | TEXT | Arabic description |
| `transaction_subject_en` | TEXT | English description |
| `poa_duration_type` | duration_type | fixed, indefinite, until_completion |
| `poa_start_date` | DATE | POA start date |
| `poa_end_date` | DATE | POA end date |
| `draft_expires_at` | TIMESTAMP | Auto-set to 7 days from creation |
| `rejection_expires_at` | TIMESTAMP | Auto-set to 15 days from rejection |
| `is_resubmission` | BOOLEAN | Is this a resubmission? |
| `original_application_id` | UUID | FK to original application |
| `assigned_employee_id` | VARCHAR(50) | Employee processing this |
| `assigned_branch_id` | VARCHAR(50) | Branch handling this |

**Auto-expiry triggers**:
- Draft applications expire after 7 days
- Rejected applications can be resubmitted within 15 days

---

### parties

Individuals or entities involved in applications. Direct link to application (no junction table).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `party_type` | party_type | Positional: `first_party` or `second_party` |
| `party_index` | INTEGER | For multiple parties of same type |
| `party_role` | party_role | Functional: grantor, agent, seller, buyer, witness |
| `is_submitter` | BOOLEAN | Is this the person who submitted? |
| `is_editable` | BOOLEAN | Can ID fields be edited? (FALSE for submitter) |
| `national_id` | VARCHAR(20) | Qatar ID or other ID |
| `national_id_type` | id_type | Type of ID |
| `id_validity_date` | DATE | ID expiry date |
| `full_name_ar` | VARCHAR(255) | Arabic full name |
| `full_name_en` | VARCHAR(255) | English full name |
| `date_of_birth` | DATE | For age verification |
| `nationality_code` | CHAR(3) | ISO 3166-1 alpha-3 |
| `gender` | gender_type | male/female |
| `is_entity` | BOOLEAN | True if company/organization |
| `entity_type` | VARCHAR(50) | LLC, QSC, etc. |
| `capacity` | party_capacity | One of 14 capacity types |
| `phone` | VARCHAR(20) | Contact number |
| `email` | VARCHAR(255) | Contact email |

**Dual Terminology**:
- `party_type` (positional): WHO in the transaction flow
- `party_role` (functional): WHAT ROLE they play

---

### capacity_proofs

Stores proof of capacity for each party. Merged from old `poa_extractions` - supports POA + Sale transactions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `party_id` | UUID | FK to `parties` (1:1 relationship) |
| `capacity_type` | capacity_type | Category of capacity |

**Establishment-Based Fields** (manual entry):
| Column | Type | Description |
|--------|------|-------------|
| `establishment_number` | VARCHAR(50) | Establishment registration number |
| `establishment_name` | VARCHAR(255) | Name of establishment |
| `establishment_po_box` | VARCHAR(20) | PO Box |
| `establishment_phone` | VARCHAR(20) | Phone |
| `establishment_expiry` | DATE | Registration expiry |

**Commercial Registration Fields** (auto-retrieved from MEC):
| Column | Type | Description |
|--------|------|-------------|
| `cr_number` | VARCHAR(50) | Commercial registration number |
| `company_name` | VARCHAR(255) | Company name |
| `company_po_box` | VARCHAR(20) | PO Box |
| `company_phone` | VARCHAR(20) | Phone |
| `cr_expiry_date` | DATE | CR expiry |
| `mec_retrieved` | BOOLEAN | Was data retrieved from MEC? |
| `mec_retrieved_at` | TIMESTAMP | When retrieved |

**Foreign Entity Fields** (manual entry):
| Column | Type | Description |
|--------|------|-------------|
| `company_nationality` | CHAR(3) | ISO country code |

**Agency/Mandate Fields** (from old poa_extractions):
| Column | Type | Description |
|--------|------|-------------|
| `poa_authorization_number` | VARCHAR(50) | POA document number |
| `poa_date` | DATE | When POA was issued |
| `poa_expiry` | DATE | When POA expires |
| `poa_issuing_authority` | VARCHAR(255) | Issuing authority |
| `poa_verified` | BOOLEAN | Has POA been verified? |
| `principal_name_ar` | VARCHAR(255) | Principal Arabic name |
| `principal_name_en` | VARCHAR(255) | Principal English name |
| `principal_qid` | VARCHAR(20) | Principal's QID |
| `agent_name_ar` | VARCHAR(255) | Agent Arabic name |
| `agent_name_en` | VARCHAR(255) | Agent English name |
| `agent_qid` | VARCHAR(20) | Agent's QID |
| `granted_powers` | JSONB | Array of powers in Arabic |
| `granted_powers_en` | JSONB | Powers in English |
| `is_general_poa` | BOOLEAN | Is this a general POA? |
| `is_special_poa` | BOOLEAN | Is this a special POA? |
| `has_substitution_right` | BOOLEAN | Can agent sub-delegate? |
| `poa_full_text_ar` | TEXT | Full POA text Arabic |
| `poa_full_text_en` | TEXT | Full POA text English |

**Legal Mandate Fields** (manual entry):
| Column | Type | Description |
|--------|------|-------------|
| `letter_number` | VARCHAR(50) | Letter/order number |
| `issuing_authority` | VARCHAR(255) | Authority that issued it |
| `poa_details` | TEXT | POA details for absentee agent |

**Sale Transaction Fields**:
| Column | Type | Description |
|--------|------|-------------|
| `share_percentage` | DECIMAL(5,2) | Percentage of shares |
| `share_value` | DECIMAL(18,2) | Value of shares |
| `sale_price` | DECIMAL(18,2) | Sale price |
| `payment_method` | VARCHAR(100) | Payment method |

---

### capacity_principals

For capacities that require linking to principals/wards (agent, guardian, trustee).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `capacity_proof_id` | UUID | FK to `capacity_proofs` |
| `principal_type` | principal_type | natural_person or legal_person |
| `national_id` | VARCHAR(20) | For natural person |
| `national_id_type` | id_type | Type of ID |
| `full_name_ar` | VARCHAR(255) | Arabic name |
| `full_name_en` | VARCHAR(255) | English name |
| `legal_entity_capacity` | legal_entity_capacity | For legal person |
| `commercial_registration` | VARCHAR(50) | CR number |
| `entity_name_ar` | VARCHAR(255) | Entity name |
| `selected_from_list` | BOOLEAN | Selected from first parties? |
| `source_party_id` | UUID | FK to source party |
| `principal_index` | INTEGER | Order of principals |

---

### documents

Uploaded documents (renamed from `attachments`).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `file_name` | VARCHAR(255) | Original filename |
| `file_path` | VARCHAR(500) | Storage location (S3/Filenet) |
| `file_size_bytes` | BIGINT | File size |
| `mime_type` | VARCHAR(100) | MIME type |
| `file_hash` | VARCHAR(64) | SHA-256 for integrity |
| `attachment_type_code` | VARCHAR(50) | User-selected type (FK to `attachment_types`) |
| `ml_document_type_code` | VARCHAR(50) | ML classified type |
| `ml_confidence` | DECIMAL(3,2) | ML confidence (0.00-1.00) |
| `classification_matches` | BOOLEAN | Does ML match user selection? |
| `ocr_status` | ocr_status | pending, processing, completed, failed, skipped |
| `ocr_started_at` | TIMESTAMP | When OCR started |
| `ocr_completed_at` | TIMESTAMP | When OCR completed |
| `ocr_engine` | VARCHAR(50) | Azure Document Intelligence, etc. |
| `page_count` | INTEGER | Number of pages |
| `is_verified` | BOOLEAN | Manually verified? |
| `verified_by` | VARCHAR(50) | Employee ID |
| `uploaded_by` | VARCHAR(50) | Who uploaded |
| `uploaded_at` | TIMESTAMP | When uploaded |

---

### document_extractions

OCR and field extraction results from documents.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `document_id` | UUID | FK to `documents` |
| `extraction_model` | VARCHAR(100) | Model used (Azure, GPT-4V) |
| `model_version` | VARCHAR(50) | Model version |
| `raw_text_ar` | TEXT | Full Arabic text |
| `raw_text_en` | TEXT | Full English text |
| `ocr_confidence` | DECIMAL(3,2) | Overall OCR confidence |
| `extracted_fields` | JSONB | Structured field values |
| `field_confidences` | JSONB | Per-field confidence |
| `bounding_boxes` | JSONB | Field positions |
| `page_extractions` | JSONB | Per-page data |

**extracted_fields example**:
```json
{
  "name_ar": "أحمد المنصوري",
  "name_en": "Ahmed Al-Mansouri",
  "qid": "12345678901",
  "date_of_birth": "1990-01-15",
  "expiry_date": "2026-12-31",
  "signature_present": true,
  "stamp_present": true
}
```

---

## Reference Tables

### transaction_types

10 transaction types for POA and Sale.

| Column | Type | Description |
|--------|------|-------------|
| `code` | VARCHAR(20) | Primary key |
| `name_ar` | VARCHAR(255) | Arabic name |
| `name_en` | VARCHAR(255) | English name |
| `category_code` | VARCHAR(20) | documentation, sale |
| `parent_category` | VARCHAR(20) | powers_of_attorney, sale |
| `requires_first_party` | BOOLEAN | Requires first party? |
| `requires_second_party` | BOOLEAN | Requires second party? |
| `min_first_parties` | INTEGER | Minimum first parties |
| `max_first_parties` | INTEGER | Maximum first parties |
| `min_second_parties` | INTEGER | Minimum second parties |
| `max_second_parties` | INTEGER | Maximum second parties |
| `requires_duration` | BOOLEAN | POA duration required? |
| `has_mandatory_templates` | BOOLEAN | Has mandatory templates? |
| `base_fee` | DECIMAL(10,2) | Base transaction fee |

**Available Types**:
| Code | Arabic | English |
|------|--------|---------|
| `POA_GENERAL` | توكيل عام | General Power of Attorney |
| `POA_GENERAL_CASES` | توكيل عام في الدعاوى | General POA in Cases |
| `POA_SPECIAL` | توكيل خاص | Special Power of Attorney |
| `POA_SPECIAL_VEHICLE` | توكيل خاص في المركبات | Special POA for Vehicle |
| `POA_SPECIAL_COMPANY` | توكيل خاص لشركة | Special POA for Company |
| `POA_SPECIAL_PROPERTY` | توكيل خاص في عقار | Special POA for Property |
| `POA_SPECIAL_GOVT` | توكيل خاص لإنجاز المعاملات الحكومية | Special POA for Government |
| `POA_SPECIAL_INHERITANCE` | توكيل رسمي خاص في الإرث | Special POA for Inheritance |
| `SALE_SHARES` | بيع حصص في شركة / مؤسسة | Sale of Shares |
| `SALE_COMPANY` | بيع شركة | Sale of Company |

---

### capacity_configurations

14 capacity types with their requirements.

| Capacity | Arabic | Type | Entry Method |
|----------|--------|------|--------------|
| `self` | شخصي | personal_capacity | not_applicable |
| `natural_guardian` | الولي الطبيعي | personal_capacity | not_applicable |
| `company_representative` | مندوب | establishment_based | manual_entry |
| `authorized_signatory_establishment` | مخول بالتوقيع في سجل المنشأة | establishment_based | manual_entry |
| `partner_in_company` | شريك في شركة | commercial_registration | auto_retrieved_mec |
| `partner_in_factory` | شريك في مصنع | commercial_registration | auto_retrieved_mec |
| `owner` | مالك | commercial_registration | auto_retrieved_mec |
| `authorized_signatory_cr` | مخول بالتوقيع في السجل التجاري | commercial_registration | auto_retrieved_mec |
| `partner_foreign_company` | شريك في شركة أجنبية | foreign_entity | manual_entry |
| `agent_under_poa` | وكيل بموجب توكيل | agency_mandate | system_verification |
| `authorized_agent` | المفوض | agency_mandate | system_verification |
| `trustee` | الوصي | legal_mandate | manual_entry |
| `custodian_guardian` | القيم | legal_mandate | manual_entry |
| `agent_for_absentee` | وكيل عن غائب | legal_mandate | manual_entry |

---

### attachment_types

12 document types.

| Code | Arabic | English | Category |
|------|--------|---------|----------|
| `PERSONAL_ID` | الهوية الشخصية | Personal ID | identity |
| `COMMERCIAL_REGISTRATION` | السجل التجاري | Commercial Registration | corporate |
| `AUTHORIZATION` | التفويض | Authorization | authorization |
| `POWER_OF_ATTORNEY` | الوكالة | Power of Attorney | authorization |
| `PASSPORT` | جواز السفر | Passport | identity |
| `TRADE_LICENSE` | الرخصة التجارية | Trade License | corporate |
| `FOUNDATION_CONTRACT` | نسخة من عقد التأسيس | Foundation Contract | corporate |
| `ESTABLISHMENT_RECORD` | سجل المنشأة | Establishment Record | corporate |
| `MINORS_AFFAIRS_LETTER` | خطاب من هيئة شؤون القاصرين | Minors Affairs Letter | legal |
| `GOVT_ENTITY_APPROVAL` | موافقة جهة حكومية | Government Approval | government_approval |
| `SEMI_GOVT_APPROVAL` | موافقة جهة شبه حكومية | Semi-Government Approval | government_approval |
| `NON_GOVT_APPROVAL` | موافقة جهة غير حكومية | Non-Government Approval | government_approval |

---

## ML Pipeline Tables

### case_objects

Virtual Case Object - unified JSON representation combining SQL data + extracted evidence.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `version` | INTEGER | Version number |
| `is_current` | BOOLEAN | Is this the current version? |
| `case_data` | JSONB | The unified case object |
| `build_status` | case_build_status | pending, building, completed, failed |
| `completeness_score` | INTEGER | 0-100 |
| `confidence_score` | INTEGER | 0-100 |
| `uncertainties` | JSONB | [{field, reason, impact}, ...] |
| `field_mappings_count` | INTEGER | Total field mappings |
| `exact_matches` | INTEGER | Exact matches count |
| `mismatches` | INTEGER | Mismatch count |
| `missing_evidence` | INTEGER | Missing evidence count |

**case_data JSON structure**:
```json
{
  "caseId": "uuid",
  "applicationNumber": "SAK-2024-POA-00001",
  "transactionType": {"code": "POA_GENERAL", "nameAr": "..."},
  "version": 1,
  "builtAt": "2024-01-15T10:30:00Z",
  "parties": [
    {
      "partyType": "first_party",
      "partyRole": "grantor",
      "capacity": "self",
      "sqlData": {"nationalId": "12345678901", "fullNameAr": "..."},
      "evidenceData": {"nationalId": {"value": "12345678901", "confidence": 0.98, "source": {...}}},
      "mismatches": []
    }
  ],
  "template": {...},
  "documents": [...],
  "fieldMappings": [...],
  "quality": {"completeness": 95, "confidence": 92, "uncertainties": [...]}
}
```

---

### validation_reports

Tier 1 deterministic validation results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `case_object_id` | UUID | FK to `case_objects` |
| `tier` | VARCHAR(10) | "tier1" |
| `verdict` | VARCHAR(20) | PASS, FAIL, WARNINGS |
| `rules_passed` | INTEGER | Count passed |
| `rules_failed` | INTEGER | Count failed |
| `rules_warned` | INTEGER | Count warned |
| `blocking_failures` | INTEGER | Blocking failures |
| `warnings_count` | INTEGER | Warnings |
| `can_proceed_to_tier2` | BOOLEAN | Can proceed? |
| `checks_run` | JSONB | Array of check results |
| `processing_time_ms` | INTEGER | Execution time |
| `agent_name` | VARCHAR(100) | Agent name |

---

### fact_sheets

Tier 1 output - structured facts for Tier 2.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `case_object_id` | UUID | FK to `case_objects` |
| `validation_report_id` | UUID | FK to `validation_reports` |
| `application_id` | UUID | FK to `applications` |
| `facts` | JSONB | Structured facts |
| `total_checks` | INTEGER | Total checks run |
| `passed_checks` | INTEGER | Passed |
| `failed_checks` | INTEGER | Failed |
| `warning_checks` | INTEGER | Warnings |
| `has_blockers` | BOOLEAN | Has blocking issues? |
| `blocker_count` | INTEGER | Number of blockers |
| `blocker_summary` | TEXT | Summary of blockers |
| `open_questions` | JSONB | Questions for Tier 2 |

---

### legal_briefs

Condenser Agent output - high-density artifact for Tier 2.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `case_object_id` | UUID | FK to `case_objects` |
| `fact_sheet_id` | UUID | FK to `fact_sheets` |
| `application_id` | UUID | FK to `applications` |
| `brief_content` | JSONB | The legal brief |
| `status` | brief_status | draft, ready, in_analysis, completed |
| `completeness_score` | DECIMAL(3,2) | Completeness |
| `fact_count` | INTEGER | Number of facts |
| `uncertainty_count` | INTEGER | Number of uncertainties |
| `issues_to_analyze` | JSONB | Issues for research |

---

### legal_analysis_sessions

Tracks individual Tier 2 analysis runs.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `legal_brief_id` | UUID | FK to `legal_briefs` |
| `application_id` | UUID | FK to `applications` |
| `session_number` | INTEGER | Session number |
| `status` | analysis_status | Status of analysis |
| `started_at` | TIMESTAMP | When started |
| `completed_at` | TIMESTAMP | When completed |
| `llm_model` | VARCHAR(100) | Model used |
| `llm_version` | VARCHAR(50) | Model version |
| `total_tokens` | INTEGER | Tokens used |
| `total_cost` | DECIMAL(10,4) | Cost |
| `workflow_id` | VARCHAR(100) | Temporal workflow ID |

---

### issue_decompositions

Sub-questions generated by Decomposer.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `analysis_session_id` | UUID | FK to `legal_analysis_sessions` |
| `issue_id` | VARCHAR(50) | Issue identifier (q1, q2) |
| `issue_category` | issue_category | Category of issue |
| `question` | TEXT | The question |
| `sub_questions` | JSONB | Sub-questions |
| `priority` | INTEGER | Priority order |
| `research_status` | research_status | pending, in_progress, completed |
| `finding` | VARCHAR(30) | SUPPORTED, NOT_SUPPORTED, UNCLEAR |
| `confidence` | DECIMAL(3,2) | Confidence |
| `analysis_text` | TEXT | Analysis text |

---

### retrieved_evidence

RAG results - evidence from legal corpus.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `issue_decomposition_id` | UUID | FK to `issue_decompositions` |
| `article_number` | INTEGER | FK to `articles` |
| `query_text` | TEXT | Search query |
| `similarity_score` | DECIMAL(4,3) | Vector similarity |
| `retrieval_rank` | INTEGER | Rank (1st, 2nd, etc.) |
| `chunk_text` | TEXT | Retrieved chunk |
| `is_relevant` | BOOLEAN | Is relevant? |
| `relevance_score` | DECIMAL(3,2) | Relevance score |
| `used_in_analysis` | BOOLEAN | Used in analysis? |
| `cited_in_opinion` | BOOLEAN | Cited in opinion? |

---

### legal_opinions

Final Tier 2 legal research opinions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `legal_brief_id` | UUID | FK to `legal_briefs` |
| `analysis_session_id` | UUID | FK to `legal_analysis_sessions` |
| `finding` | VARCHAR(30) | VALID, INVALID, VALID_WITH_CONDITIONS, etc. |
| `confidence_score` | DECIMAL(3,2) | 0.00-1.00 |
| `confidence_level` | VARCHAR(10) | HIGH, MEDIUM, LOW |
| `summary_ar` | TEXT | Arabic summary |
| `summary_en` | TEXT | English summary |
| `full_analysis` | JSONB | Full analysis by category |
| `concerns` | JSONB | Array of concerns |
| `recommendations` | JSONB | Array of recommendations |
| `legal_citations` | JSONB | Citations |
| `grounding_score` | DECIMAL(3,2) | Claims with citations |
| `retrieval_coverage` | DECIMAL(3,2) | Issues with evidence |
| `stability_score` | DECIMAL(3,2) | Multi-run consistency |
| `has_contradictions` | BOOLEAN | Has contradictions? |
| `needs_escalation` | BOOLEAN | Needs escalation? |
| `escalation_reason` | TEXT | Why escalation needed |

---

### risk_scores

Composite risk calculation for routing.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `extraction_completeness` | INTEGER | 0-100, weight 15% |
| `tier1_score` | INTEGER | 0-100, weight 25% |
| `brief_integrity` | INTEGER | 0-100, weight 10% |
| `grounding_score` | INTEGER | 0-100, weight 20% |
| `stability_score` | INTEGER | 0-100, weight 15% |
| `retrieval_success` | INTEGER | 0-100, weight 15% |
| `composite_score` | INTEGER | Final weighted score |
| `risk_level` | risk_level | low, medium, high, critical |
| `reason_codes` | VARCHAR(50)[] | Reason codes |

**Routing Thresholds**:
| Composite Score | Risk Level | Routing |
|-----------------|------------|---------|
| ≥ 85 | low | Auto-approve |
| 70-84 | medium | Employee review |
| 50-69 | high | SME review |
| < 50 | critical | Rejection queue |

---

### routing_decisions

Final routing based on risk scores.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `risk_score_id` | UUID | FK to `risk_scores` |
| `decision` | routing_decision | approve, reject, remediate, escalate, hold |
| `decision_bucket` | decision_bucket | valid, valid_with_remediations, invalid, needs_review |
| `routed_to` | routing_target | auto_approve, employee_review, sme_review, etc. |
| `routed_to_employee_id` | VARCHAR(50) | Employee ID |
| `routed_to_queue` | VARCHAR(100) | Queue name |
| `conditions_to_meet` | JSONB | Conditions |
| `remediations_required` | JSONB | Remediation steps |
| `requires_sme` | BOOLEAN | Needs SME? |
| `sme_reason` | TEXT | Why SME needed |

---

### escalations

Cases requiring human review.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `application_id` | UUID | FK to `applications` |
| `tier` | VARCHAR(20) | tier1, tier2, routing |
| `reason` | TEXT | Escalation reason |
| `validation_report_id` | UUID | FK (if tier1) |
| `legal_opinion_id` | UUID | FK (if tier2) |
| `routing_decision_id` | UUID | FK (if routing) |
| `confidence_at_escalation` | DECIMAL(3,2) | Confidence when escalated |
| `risk_level_at_escalation` | risk_level | Risk level when escalated |
| `status` | VARCHAR(20) | pending, assigned, reviewed, resolved |
| `priority` | VARCHAR(20) | standard, urgent, critical |
| `assigned_to` | VARCHAR(50) | Employee ID |
| `sme_decision` | TEXT | SME's decision |
| `sme_notes` | TEXT | SME's notes |
| `resolved_by` | VARCHAR(50) | Who resolved |
| `resolved_at` | TIMESTAMP | When resolved |

---

## Enums Reference

### Application Enums

```sql
-- application_status
'draft', 'submitted', 'in_review', 'pending_documents', 'pending_sme',
'approved', 'rejected', 'cancelled', 'completed'

-- processing_stage
'intake', 'document_processing', 'tier1_validation', 'tier2_analysis',
'risk_scoring', 'decision_pending', 'completed'

-- duration_type
'fixed', 'indefinite', 'until_completion'
```

### Party Enums

```sql
-- party_type (positional)
'first_party', 'second_party'

-- party_role (functional)
'grantor', 'agent', 'seller', 'buyer', 'witness', 'representative'

-- id_type
'qatari_id', 'gcc_id', 'passport', 'residence_permit'

-- gender_type
'male', 'female'
```

### Capacity Enums

```sql
-- capacity_type
'personal_capacity', 'establishment_based', 'commercial_registration',
'foreign_entity', 'agency_mandate', 'legal_mandate'

-- party_capacity (14 values)
'self', 'natural_guardian', 'company_representative',
'authorized_signatory_establishment', 'partner_in_company', 'partner_in_factory',
'owner', 'authorized_signatory_cr', 'partner_foreign_company',
'agent_under_poa', 'authorized_agent', 'trustee', 'custodian_guardian',
'agent_for_absentee'

-- entry_method
'not_applicable', 'manual_entry', 'auto_retrieved_mec', 'system_verification'
```

### ML Pipeline Enums

```sql
-- issue_category
'grantor_capacity', 'agent_capacity', 'poa_scope', 'substitution_rights',
'formalities', 'validity', 'compliance', 'business_rules'

-- risk_level
'low', 'medium', 'high', 'critical'

-- routing_decision
'approve', 'reject', 'remediate', 'escalate', 'hold'

-- decision_bucket
'valid', 'valid_with_remediations', 'invalid', 'needs_review'
```

---

## Agent-to-Table Mapping

| Agent | Reads | Writes | Updates |
|-------|-------|--------|---------|
| **Document Processing** | `documents` | `document_extractions`, `document_classifications`, `extracted_fields` | `documents` (ocr_status) |
| **Case Builder** | `applications`, `parties`, `capacity_proofs`, `documents`, `document_extractions` | `case_objects` | - |
| **Tier 1 Validation** | `case_objects`, `transaction_configs` | `validation_reports`, `fact_sheets` | `applications` (processing_stage) |
| **Condenser** | `case_objects`, `fact_sheets` | `legal_briefs` | - |
| **Tier 2 Legal Research** | `legal_briefs`, `articles` | `legal_analysis_sessions`, `issue_decompositions`, `retrieved_evidence`, `legal_opinions`, `citations`, `research_traces` | - |
| **Risk Scoring** | `validation_reports`, `legal_opinions` | `risk_scores` | - |
| **Router** | `risk_scores` | `routing_decisions`, `escalations` | `applications` (status) |
| **Orchestrator** | All tables | `escalations` | `applications` (status, processing_stage) |

---

## Data Flow

### Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTAKE                                          │
│  SAK Portal → applications, parties, capacity_proofs, documents             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT PROCESSING                                  │
│  OCR → document_extractions, document_classifications                       │
│  Field Extraction → extracted_fields                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VIRTUAL CASE OBJECT                                   │
│  SQL Data + Evidence → case_objects (unified JSON)                          │
│  Quality: completeness_score, confidence_score, mismatches                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TIER 1 VALIDATION                                    │
│  Deterministic Checks → validation_reports                                  │
│  Structured Output → fact_sheets (blockers, open_questions)                 │
│                                                                              │
│  Decision: can_proceed_to_tier2?                                            │
│  - YES → Continue to Tier 2                                                 │
│  - NO → Reject or Request Documents                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CONDENSER                                         │
│  Fact Sheet → legal_briefs (high-density brief)                             │
│  Issues to Analyze: [{issueId, category, question}, ...]                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TIER 2 LEGAL REASONING                                 │
│                                                                              │
│  1. Decomposer → issue_decompositions (sub-questions)                       │
│  2. Retriever (RAG) → retrieved_evidence (from articles)                    │
│  3. Synthesizer → draft opinion                                             │
│  4. Verifier → legal_opinions (grounded, verified)                          │
│                                                                              │
│  Metrics: grounding_score, stability_score, retrieval_coverage              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RISK SCORING                                        │
│                                                                              │
│  Components (weighted):                                                      │
│  - extraction_completeness (15%)                                            │
│  - tier1_score (25%)                                                        │
│  - brief_integrity (10%)                                                    │
│  - grounding_score (20%)                                                    │
│  - stability_score (15%)                                                    │
│  - retrieval_success (15%)                                                  │
│                                                                              │
│  → risk_scores (composite_score, risk_level)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ROUTING DECISION                                      │
│                                                                              │
│  Score ≥ 85 (low risk) → Auto-approve                                       │
│  Score 70-84 (medium) → Employee review                                     │
│  Score 50-69 (high) → SME review                                            │
│  Score < 50 (critical) → Rejection queue                                    │
│                                                                              │
│  → routing_decisions, escalations (if needed)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Migration Notes

### Deprecated Tables

Old tables have been renamed with `_deprecated` suffix:
- `applications_deprecated`
- `personal_parties_deprecated`
- `application_party_roles_deprecated`
- `attachments_deprecated`
- `document_extractions_deprecated`
- `poa_extractions_deprecated`
- `transaction_types_deprecated`
- `transaction_configs_deprecated`
- `role_types_deprecated`
- `document_types_deprecated`
- `capacity_types_deprecated`
- `validation_reports_deprecated`
- `legal_opinions_deprecated`
- `research_traces_deprecated`
- `escalations_deprecated`

### Key Changes

1. **`poa_extractions` → `capacity_proofs`**: Merged and expanded to support both POA and Sale transactions
2. **`attachments` → `documents`**: Renamed with added ML classification fields
3. **`personal_parties` + `application_party_roles` → `parties`**: Flattened to direct relationship
4. **New ML Pipeline tables**: `case_objects`, `fact_sheets`, `legal_briefs`, `legal_analysis_sessions`, `issue_decompositions`, `retrieved_evidence`, `citations`, `risk_scores`, `routing_decisions`
5. **New reference tables**: `capacity_configurations`, `attachment_types`, `template_definitions`

### Migration File

See `migrations/001_new_data_model.sql` for the complete SQL migration.

---

## Quick Reference

### Supabase Connection
```python
from supabase import create_client

SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
```

### Common Queries

**Load application with parties and documents**:
```python
result = supabase.table("applications").select(
    "*, parties(*, capacity_proofs(*)), documents(*, document_extractions(*))"
).eq("id", application_id).single().execute()
```

**Load current case object**:
```python
result = supabase.table("case_objects").select("*").eq(
    "application_id", application_id
).eq("is_current", True).single().execute()
```

**Get risk score and routing**:
```python
result = supabase.table("risk_scores").select(
    "*, routing_decisions(*)"
).eq("application_id", application_id).single().execute()
```

**Vector similarity search (articles)**:
```python
result = supabase.rpc("match_articles", {
    "query_embedding": embedding_vector,
    "match_threshold": 0.7,
    "match_count": 5
}).execute()
```
