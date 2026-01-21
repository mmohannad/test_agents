# Adding Test Cases to Supabase

A repeatable guide for converting raw example data (from Claude conversations, docs, etc.) into SQL migrations for testing the Condenser and Legal Search agents.

---

## Quick Workflow

```
1. Gather raw data → 2. Identify tables → 3. Map fields → 4. Write SQL → 5. Add articles → 6. Verify
```

---

## Step 1: Gather Raw Data Sources

Typical sources you'll receive:

| Source | Contains |
|--------|----------|
| **Structured fields** | Party names, IDs, dates, capacities |
| **OCR text (Arabic)** | Full POA/document text |
| **Template extractions** | Checkbox/radio selections from forms |
| **Expected outcome** | What the agent should determine |

Example structure from a Claude conversation:
```
Extracted fields coming from structured data:
- Full Name of A: [name]
- ID type: QID/Passport
- ID Number: [number]
- Sifa of A: [capacity in Arabic]

Extracted Text from attachment (POA):
[Arabic OCR text]

Extraction from template:
☑ [selected items]
☐ [unselected items]
```

---

## Step 2: Identify Which Tables to Populate

### Core Tables (always needed)

| Table | Purpose | Rows |
|-------|---------|------|
| `applications` | Main record | 1 |
| `parties` | People involved | 2-4 |
| `capacity_proofs` | Authority documentation | 1 per grantor/agent with capacity |
| `documents` | Uploaded files | 1+ |
| `document_extractions` | OCR results | 1 per document |

### Optional Tables (based on case)

| Table | When Needed |
|-------|-------------|
| `poa_templates` | If template checkbox data provided |
| `articles` | If new legal concepts being tested |
| `extracted_fields` | If granular field-level data needed |

---

## Step 3: Field Mapping Reference

### Party Capacity Types (from "Sifa")

| Arabic Sifa | `capacity` enum value |
|-------------|----------------------|
| عن نفسه / بصفته الشخصية | `self` |
| وكيل بموجب وكالة / توكيل | `agent_under_poa` |
| مخول بالتوقيع في السجل التجاري | `authorized_signatory_cr` |
| شريك في شركة | `partner_in_company` |
| مالك | `owner` |
| الولي الطبيعي | `natural_guardian` |
| الوصي | `trustee` |
| القيم | `custodian_guardian` |

### ID Types

| Arabic/Input | `national_id_type` enum |
|--------------|------------------------|
| QID / الرقم الشخصي | `qatari_id` |
| Passport / جواز سفر | `passport` |
| GCC ID | `gcc_id` |
| Residence Permit | `residence_permit` |

### Transaction Types

| Code | Description |
|------|-------------|
| `POA_SPECIAL_VEHICLE` | Vehicle-specific POA |
| `POA_SPECIAL_COMPANY` | Company management POA |
| `POA_SPECIAL_PROPERTY` | Real estate POA |
| `POA_GENERAL` | General POA |
| `POA_GENERAL_CASES` | Litigation POA |
| `SALE_SHARES` | Share sale transaction |

---

## Step 4: Write SQL Migration

### Naming Convention
```
migrations/00X_[description]_test.sql
```
Examples:
- `004_vehicle_subdelegation_test.sql`
- `005_minor_grantor_test.sql`
- `006_expired_poa_test.sql`

### UUID Pattern
Use predictable UUIDs for test data:
```sql
-- Application
'a0000003-3333-4444-5555-666666666666'

-- Parties
'b0000005-3333-4444-5555-666666666666'  -- first party
'b0000006-3333-4444-5555-666666666666'  -- second party

-- Capacity Proofs
'c0000003-3333-4444-5555-666666666666'

-- Documents
'd0000004-3333-4444-5555-666666666666'

-- Extractions
'e0000004-3333-4444-5555-666666666666'
```

### Template Structure

```sql
-- ============================================================================
-- SAK AI Agent - Test Case: [DESCRIPTION]
-- ============================================================================
-- Case: [Brief description of scenario]
--
-- Key Test Elements:
--   1. [Element 1]
--   2. [Element 2]
--
-- Expected Result: [VALID/INVALID/REQUIRES_REVIEW] - [reason]
-- ============================================================================

-- STEP 1: APPLICATION
INSERT INTO applications (...) VALUES (...);

-- STEP 2: PARTIES
INSERT INTO parties (...) VALUES (...);  -- Grantor
INSERT INTO parties (...) VALUES (...);  -- Agent

-- STEP 3: CAPACITY PROOF (if capacity != 'self')
INSERT INTO capacity_proofs (...) VALUES (...);

-- STEP 4: DOCUMENTS
INSERT INTO documents (...) VALUES (...);

-- STEP 5: DOCUMENT EXTRACTIONS
INSERT INTO document_extractions (...) VALUES (...);

-- STEP 6: LEGAL ARTICLES (if testing new concepts)
INSERT INTO articles (...) VALUES (...);

-- STEP 7: VERIFICATION QUERY
SELECT ... FROM applications a
JOIN parties ...
WHERE a.id = '[your-test-uuid]';

-- SUMMARY COMMENT
```

---

## Step 5: Extract Data from Arabic OCR Text

### Common Arabic Fields to Look For

| Arabic Text Pattern | Field |
|---------------------|-------|
| `الإسم / :` or `الاسم:` | Name |
| `الجنسية :` | Nationality |
| `الرقم الشخصي :` | QID |
| `جواز سفر رقم :` | Passport number |
| `بصفته :` | Capacity/Sifa |
| `وكلت السيد :` | Agent being appointed |
| `سارية المفعول حتى تاريخ` | Expiry date |
| `رقم اللوحة:` | Plate number |
| `نوع المركبة:` | Vehicle type |
| `لا يحق للوكيل` | Agent restrictions |
| `توكيل الغير` | Sub-delegation |
| `البيع` | Sale rights |
| `نقل الملكية` | Transfer ownership |

### Structuring `extracted_fields` JSON

```json
{
    "document_type": "power_of_attorney",
    "poa_date": "YYYY-MM-DD",
    "poa_expiry": "YYYY-MM-DD",
    "principal": {
        "name_ar": "",
        "name_en": "",
        "nationality": "",
        "qid": "",
        "passport_number": ""
    },
    "agent": {
        "name_ar": "",
        "name_en": "",
        "qid": ""
    },
    "powers_granted": [],
    "restrictions": {
        "can_sell": true/false,
        "can_transfer_ownership": true/false,
        "can_subdelegate": true/false
    }
}
```

---

## Step 6: Add Supporting Legal Articles

If your test case involves legal concepts not already in the corpus:

```sql
INSERT INTO articles (
    article_number,      -- Use 900XX range for test articles
    hierarchy_path,      -- JSON with chapter/section
    text_arabic,         -- Arabic text
    text_english,        -- English translation
    effective_date,
    is_active
) VALUES (
    90009,
    '{"chapter": {"ar": "القانون المدني", "en": "Civil Code"}, "section": {"ar": "الوكالة", "en": "Agency"}, "level": 2}',
    '[Arabic article text]',
    '[English translation]',
    '2027-01-13',
    TRUE
);
```

After adding articles, regenerate embeddings:
```bash
python migrations/003_generate_embeddings.py
```

---

## Step 7: Define Expected Agent Behavior

Document what the agents should find:

| Agent | Should Detect |
|-------|---------------|
| **Condenser** | Key facts, discrepancies, research questions |
| **Legal Search** | Applicable articles, verdict, confidence |

Example:
```
Condenser should detect:
- Grantor capacity = agent_under_poa (not self)
- has_substitution_right = FALSE in original POA
- MISMATCH: Template shows sale rights, OCR shows prohibited

Legal Search should:
- Find Article 90007/90008 on sub-delegation
- Determine: INVALID
- Reason: Sub-delegation explicitly prohibited
```

---

## Common Test Case Patterns

### 1. Sub-delegation Prohibited
- Grantor acting under POA
- Original POA says "لا يحق للوكيل توكيل الغير"
- Expected: INVALID

### 2. Grantor Exceeds Authority
- CR shows limited authority (e.g., "Passports only")
- POA grants broader powers (e.g., "full management")
- Expected: INVALID

### 3. Expired Documents
- QID/Passport expired before POA date
- Expected: TIER 1 FAIL

### 4. Template vs OCR Mismatch
- Template checkbox says X is allowed
- OCR text says X is prohibited
- Expected: REQUIRES_REVIEW (or INVALID if clear)

### 5. Minor/Incapacitated Grantor
- Date of birth shows grantor is minor
- Expected: INVALID (needs guardian)

---

## Checklist Before Running Migration

- [ ] Application has unique `application_number`
- [ ] UUIDs don't conflict with existing test data
- [ ] All FK references exist (application_id, party_id)
- [ ] `capacity_proofs` exists if capacity != 'self'
- [ ] `extracted_fields` JSON is valid
- [ ] Arabic text is properly escaped (use `$$` if needed)
- [ ] Verification query returns expected row
- [ ] New articles (if any) have unique `article_number`

---

## Example: Quick Conversion

**Input (from Claude conversation):**
```
Full Name of A: Mohannad Jaber
ID type: QID
ID Number: 14723699
Sifa of A: وكيل بموجب وكالة

Full Name of B: Omar Anas
ID type: Passport
ID Number: VQ32456
```

**Output (SQL snippet):**
```sql
-- Party A (acting as grantor under POA)
INSERT INTO parties (
    id, application_id, party_type, party_index, party_role,
    national_id, national_id_type, full_name_en, capacity
) VALUES (
    'b0000003-...', 'a0000002-...',
    'first_party', 1, 'grantor',
    '14723699', 'qatari_id', 'Mohannad Jaber', 'agent_under_poa'
);

-- Party B (receiving POA)
INSERT INTO parties (
    id, application_id, party_type, party_index, party_role,
    national_id, national_id_type, full_name_en, capacity
) VALUES (
    'b0000004-...', 'a0000002-...',
    'second_party', 1, 'agent',
    'VQ32456', 'passport', 'Omar Anas', 'self'
);
```

---

## Questions?

If mapping is unclear:
1. Check `001_new_data_model.sql` for enum values
2. Check `002_seed_test_case.sql` for working examples
3. Ask Claude to analyze the Arabic text for field extraction
