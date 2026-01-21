-- ============================================================================
-- SAK AI Agent - Test Case: POA Scope Mismatch
-- ============================================================================
-- Case: A (Mohannad) has POA from C (Youssef) for UTILITY companies (Kahramaa/Ooredoo).
--       A is trying to grant B (Hamza) powers for MINISTRY OF EDUCATION.
--       These are completely different scopes!
--
-- Key Test Elements:
--   1. A's capacity = agent_under_poa (acting under POA #1234)
--   2. Original POA #1234 scope: Kahramaa and Ooredoo (utilities)
--   3. New POA attempting to grant: Ministry of Education representation
--   4. POA number discrepancy: Application says 12345, attachment says 1234
--   5. Sub-delegation with scope expansion (invalid)
--
-- Expected Result: INVALID
--   - A cannot grant powers for Ministry of Education (never received)
--   - Scope mismatch between original POA and new delegation
--   - POA number inconsistency
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE TEST APPLICATION
-- ============================================================================

INSERT INTO applications (
    id,
    application_number,
    transaction_type_code,
    submitter_party_type,
    submitter_national_id,
    submitter_id_type,
    status,
    processing_stage,
    transaction_subject_ar,
    transaction_subject_en,
    poa_duration_type,
    poa_end_date,
    created_at,
    submitted_at
) VALUES (
    'a0000003-3333-4444-5555-666666666666',
    'SAK-2026-POA-TEST003',
    'POA_SPECIAL_GOVT',
    'first_party',
    '14723699',
    'qatari_id',
    'submitted',
    'tier1_validation',
    'توكيل خاص لإنجاز المعاملات الحكومية - وزارة التربية والتعليم',
    'Special POA for Government Transactions - Ministry of Education',
    'fixed',
    '2026-12-25',
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    status = 'submitted',
    processing_stage = 'tier1_validation';

-- ============================================================================
-- STEP 2: CREATE PARTIES
-- ============================================================================

-- Party A: Mohannad Jaber (Grantor - acting under POA)
INSERT INTO parties (
    id,
    application_id,
    party_type,
    party_index,
    party_role,
    is_submitter,
    national_id,
    national_id_type,
    id_validity_date,
    full_name_ar,
    full_name_en,
    nationality_code,
    gender,
    capacity
) VALUES (
    'b0000005-3333-4444-5555-666666666666',
    'a0000003-3333-4444-5555-666666666666',
    'first_party',
    1,
    'grantor',
    TRUE,
    '14723699',
    'qatari_id',
    '2027-06-15',
    'مهند جابر',
    'Mohannad Jaber',
    'QAT',
    'male',
    'agent_under_poa'  -- Acting under POA, not personal capacity
) ON CONFLICT (id) DO UPDATE SET
    capacity = 'agent_under_poa';

-- Party B: Hamza Awad (Agent - receiving delegation)
INSERT INTO parties (
    id,
    application_id,
    party_type,
    party_index,
    party_role,
    is_submitter,
    national_id,
    national_id_type,
    id_validity_date,
    full_name_ar,
    full_name_en,
    nationality_code,
    gender,
    capacity
) VALUES (
    'b0000006-3333-4444-5555-666666666666',
    'a0000003-3333-4444-5555-666666666666',
    'second_party',
    1,
    'agent',
    FALSE,
    '13572468',
    'qatari_id',
    '2028-12-31',
    'حمزة عوض',
    'Hamza Awad',
    'CAN',
    'male',
    'self'  -- Acting in personal capacity
) ON CONFLICT (id) DO UPDATE SET
    party_role = 'agent';

-- ============================================================================
-- STEP 3: CREATE CAPACITY PROOF FOR A (Mohannad's POA from Youssef)
-- Note: POA number is 1234, but application references 12345 (discrepancy!)
-- ============================================================================

INSERT INTO capacity_proofs (
    id,
    party_id,
    capacity_type,

    -- POA Details
    poa_authorization_number,  -- The ACTUAL POA number from the document
    poa_date,
    poa_expiry,
    poa_issuing_authority,
    poa_verified,

    -- Principal (C: Youssef Mansour - the original grantor)
    principal_name_ar,
    principal_name_en,
    principal_qid,

    -- Agent (A: Mohannad)
    agent_name_ar,
    agent_name_en,
    agent_qid,

    -- Powers granted - CRITICAL: Only for Kahramaa and Ooredoo!
    granted_powers,
    granted_powers_en,
    is_general_poa,
    is_special_poa,
    has_substitution_right,

    -- Full POA text
    poa_full_text_ar,
    poa_full_text_en
) VALUES (
    'c0000003-3333-4444-5555-666666666666',
    'b0000005-3333-4444-5555-666666666666',
    'agency_mandate',

    -- POA Details - note: number is 1234, NOT 12345
    '1234',
    '2025-11-13',
    '2026-11-13',
    'كاتب العدل بإدارة التوثيق',
    TRUE,

    -- Principal
    'يوسف منصور',
    'Youssef Mansour',
    '33453',

    -- Agent
    'مهند جابر',
    'Mohannad Jaber',
    '14723699',

    -- Powers - ONLY for utilities (Kahramaa and Ooredoo)
    '["تمثيل أمام كهرماء", "تمثيل أمام أريد"]',
    '["Represent before Kahramaa", "Represent before Ooredoo"]',
    FALSE,
    TRUE,
    FALSE,  -- No sub-delegation right specified

    -- Full Arabic text
    'إنه في يوم : الثلاثاء الموافق : 2025-11-13 الساعة : 3:21 تقدم لنا نحن : كاتب العدل بإدارة التوثيق . أنا الموقع أدناه : الإسم / : يوسف منصور ، الجنسية : قطري ،
 جواز سفر رقم : 33453  ،
 جوال رقم : 4345322
، بصفته : عن نفسه - بصفته الشخصية
وكلت السيد : الإسم / : مهند جابر ، الجنسية : قطري ، الرقم الشخصي : 14723699 ، بصفته : عن نفسه - بصفته الشخصية
وذلك في القيام مقامي ونيابة عني بصفتي المشار إليها في:
 تمثيلي أمام كهرماء وأريد',

    'On Tuesday, 2025-11-13 at 3:21, before the Notary of the Documentation Department. I the undersigned: Name: Youssef Mansour, Nationality: Qatari, Passport No: 33453, Mobile: 4345322, acting in personal capacity, have appointed Mr: Name: Mohannad Jaber, Nationality: Qatari, QID: 14723699, in personal capacity, to act on my behalf in: Representing me before Kahramaa and Ooredoo.'
) ON CONFLICT (id) DO UPDATE SET
    granted_powers = EXCLUDED.granted_powers;

-- ============================================================================
-- STEP 4: CREATE DOCUMENTS
-- ============================================================================

-- Document 1: ID documents for A and B
INSERT INTO documents (
    id,
    application_id,
    file_name,
    file_path,
    attachment_type_code,
    ml_document_type_code,
    ml_confidence,
    classification_matches,
    ocr_status,
    ocr_completed_at,
    is_verified
) VALUES (
    'd0000004-3333-4444-5555-666666666666',
    'a0000003-3333-4444-5555-666666666666',
    'id_documents_a_b.pdf',
    '/uploads/a0000003/id_documents_a_b.pdf',
    'PERSONAL_ID',
    'PERSONAL_ID',
    0.96,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- Document 2: Original POA #1234 (from Youssef to Mohannad)
INSERT INTO documents (
    id,
    application_id,
    file_name,
    file_path,
    attachment_type_code,
    ml_document_type_code,
    ml_confidence,
    classification_matches,
    ocr_status,
    ocr_completed_at,
    is_verified
) VALUES (
    'd0000005-3333-4444-5555-666666666666',
    'a0000003-3333-4444-5555-666666666666',
    'poa_1234_youssef_to_mohannad.pdf',
    '/uploads/a0000003/poa_1234_youssef_to_mohannad.pdf',
    'POWER_OF_ATTORNEY',
    'POWER_OF_ATTORNEY',
    0.93,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- ============================================================================
-- STEP 5: CREATE DOCUMENT EXTRACTIONS
-- ============================================================================

-- Extraction for ID documents
INSERT INTO document_extractions (
    id,
    document_id,
    extraction_model,
    raw_text_ar,
    raw_text_en,
    ocr_confidence,
    extracted_fields,
    extraction_completed_at
) VALUES (
    'e0000004-3333-4444-5555-666666666666',
    'd0000004-3333-4444-5555-666666666666',
    'azure-document-intelligence',
    'بطاقة الهوية الشخصية
مهند جابر
الرقم الشخصي: 14723699
الجنسية: قطري

بطاقة الهوية الشخصية
حمزة عوض
الرقم الشخصي: 13572468
الجنسية: كندي',
    'Personal ID Card - Mohannad Jaber, QID: 14723699, Qatari
Personal ID Card - Hamza Awad, QID: 13572468, Canadian',
    0.95,
    '{
        "documents": [
            {
                "type": "qatari_id",
                "name_ar": "مهند جابر",
                "name_en": "Mohannad Jaber",
                "qid": "14723699",
                "nationality": "قطري"
            },
            {
                "type": "qatari_id",
                "name_ar": "حمزة عوض",
                "name_en": "Hamza Awad",
                "qid": "13572468",
                "nationality": "كندي"
            }
        ]
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- Extraction for POA #1234 - CRITICAL: Shows scope is Kahramaa/Ooredoo only
INSERT INTO document_extractions (
    id,
    document_id,
    extraction_model,
    raw_text_ar,
    raw_text_en,
    ocr_confidence,
    extracted_fields,
    extraction_completed_at
) VALUES (
    'e0000005-3333-4444-5555-666666666666',
    'd0000005-3333-4444-5555-666666666666',
    'azure-document-intelligence',
    'إنه في يوم : الثلاثاء الموافق : 2025-11-13 الساعة : 3:21 تقدم لنا نحن : كاتب العدل بإدارة التوثيق . أنا الموقع أدناه : الإسم / : يوسف منصور ، الجنسية : قطري ،
 جواز سفر رقم : 33453  ،
 جوال رقم : 4345322
، بصفته : عن نفسه - بصفته الشخصية
وكلت السيد : الإسم / : مهند جابر ، الجنسية : قطري ، الرقم الشخصي : 14723699 ، بصفته : عن نفسه - بصفته الشخصية
وذلك في القيام مقامي ونيابة عني بصفتي المشار إليها في:
 تمثيلي أمام كهرماء وأريد',
    'POA #1234: Youssef Mansour grants Mohannad Jaber power to represent before Kahramaa and Ooredoo only.',
    0.92,
    '{
        "document_type": "power_of_attorney",
        "poa_number": "1234",
        "poa_date": "2025-11-13",
        "notary": "كاتب العدل بإدارة التوثيق",
        "principal": {
            "name_ar": "يوسف منصور",
            "name_en": "Youssef Mansour",
            "nationality": "قطري",
            "passport_number": "33453",
            "mobile": "4345322",
            "capacity": "عن نفسه - بصفته الشخصية"
        },
        "agent": {
            "name_ar": "مهند جابر",
            "name_en": "Mohannad Jaber",
            "nationality": "قطري",
            "qid": "14723699",
            "capacity": "عن نفسه - بصفته الشخصية"
        },
        "scope": {
            "entities": ["كهرماء", "أريد"],
            "entities_en": ["Kahramaa", "Ooredoo"],
            "scope_type": "utility_companies",
            "note": "LIMITED to Kahramaa and Ooredoo only - NO Ministry of Education"
        },
        "powers_granted": [
            "تمثيلي أمام كهرماء",
            "تمثيلي أمام أريد"
        ]
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- ============================================================================
-- STEP 6: STORE TEMPLATE TEXT (what the application is trying to grant)
-- This goes in a separate extraction or could be in poa_templates
-- ============================================================================

-- Create a document for the template/application form
INSERT INTO documents (
    id,
    application_id,
    file_name,
    file_path,
    attachment_type_code,
    ml_document_type_code,
    ml_confidence,
    classification_matches,
    ocr_status,
    ocr_completed_at,
    is_verified
) VALUES (
    'd0000006-3333-4444-5555-666666666666',
    'a0000003-3333-4444-5555-666666666666',
    'application_template.pdf',
    '/uploads/a0000003/application_template.pdf',
    'POWER_OF_ATTORNEY',
    'POWER_OF_ATTORNEY',
    0.91,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- Template extraction - shows what A is TRYING to grant (Ministry of Education)
INSERT INTO document_extractions (
    id,
    document_id,
    extraction_model,
    raw_text_ar,
    raw_text_en,
    ocr_confidence,
    extracted_fields,
    extraction_completed_at
) VALUES (
    'e0000006-3333-4444-5555-666666666666',
    'd0000006-3333-4444-5555-666666666666',
    'template-extraction',
    'وذلك في القيام مقامي ونيابةً عني بصفتي المشار إليها، في تمثيلي أمام وزارة التربية والتعليم والتعليم العالي وإنجاز جميع المعاملات والإجراءات ذات الصلة، والمراجعة لدى الجهات المختصة دون استثناء، واتخاذ ما يلزم من إجراءات لتحقيق الغرض من هذه الوكالة
بما أنني الوكيل بموجب الوكالة رقم 1234، فإنني أوكل السيد/ حمزة عوض في القيام بكافة الأعمال الواردة في تلك الوكالة، وله في سبيل تنفيذ أعمال هذه الوكالة الحق في مراجعة جميع الجهات المختصة بما ذكر أعلاه وتوكيل الغير في تنفيذ أعمال وكالة سابقة رقمها: 1234
وتستخدم هذه الوكالة داخل دولة قطر وتسري هذه الوكالة حتى تاريخ: 2026/12/25',
    'Template text: Acting on my behalf before the Ministry of Education and Higher Education... As I am the agent under POA #1234, I delegate Mr. Hamza Awad to perform all tasks in that POA...',
    0.94,
    '{
        "document_type": "poa_application_template",
        "claimed_poa_number": "1234",
        "grantor": {
            "name_ar": "مهند جابر",
            "acting_under_poa": true,
            "original_poa_number": "1234"
        },
        "agent": {
            "name_ar": "حمزة عوض"
        },
        "scope_being_granted": {
            "entities": ["وزارة التربية والتعليم والتعليم العالي"],
            "entities_en": ["Ministry of Education and Higher Education"],
            "scope_type": "government_ministry",
            "includes_subdelegation": true
        },
        "validity": {
            "geographic": "داخل دولة قطر",
            "expiry_date": "2026-12-25"
        },
        "flags": {
            "references_previous_poa": true,
            "previous_poa_number": "1234",
            "grants_subdelegation_right": true
        }
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

SELECT
    'Scope Mismatch Test Case Seeded' as status,
    a.application_number,
    a.transaction_type_code,
    p1.full_name_en as grantor,
    p1.capacity as grantor_capacity,
    p2.full_name_en as agent,
    cp.poa_authorization_number as original_poa_number,
    cp.granted_powers as original_scope,
    (SELECT COUNT(*) FROM documents WHERE application_id = a.id) as document_count
FROM applications a
JOIN parties p1 ON p1.application_id = a.id AND p1.party_role = 'grantor'
JOIN parties p2 ON p2.application_id = a.id AND p2.party_role = 'agent'
LEFT JOIN capacity_proofs cp ON cp.party_id = p1.id
WHERE a.id = 'a0000003-3333-4444-5555-666666666666';

-- ============================================================================
-- SUMMARY
-- ============================================================================
--
-- Chain of Authority:
--
--   C (Youssef Mansour)
--       ↓ POA #1234 (scope: Kahramaa + Ooredoo ONLY)
--   A (Mohannad Jaber)
--       ↓ THIS APPLICATION (trying to grant: Ministry of Education!)
--   B (Hamza Awad)
--
-- Seeded:
--   - 1 application (SAK-2026-POA-TEST003)
--   - 2 parties: Mohannad (agent_under_poa), Hamza (self)
--   - 1 capacity_proof (POA #1234 from Youssef, scope: utilities)
--   - 3 documents (IDs, original POA, template)
--   - 3 document_extractions
--
-- CRITICAL ISSUES FOR AGENT TO DETECT:
--
--   1. SCOPE MISMATCH:
--      - Original POA #1234: "تمثيلي أمام كهرماء وأريد" (Kahramaa + Ooredoo)
--      - New application: "وزارة التربية والتعليم" (Ministry of Education)
--      - These are COMPLETELY DIFFERENT entities!
--
--   2. POA NUMBER DISCREPANCY:
--      - Application metadata may reference: 12345
--      - Actual attached POA number: 1234
--      - capacity_proofs shows: 1234
--
--   3. SUB-DELEGATION:
--      - Original POA has no sub-delegation clause
--      - A is attempting to sub-delegate anyway
--
-- Expected Verdict: INVALID
--   - A cannot grant powers for Ministry of Education (not in original scope)
--   - Original POA was for utility companies only
--   - Legal principle: agent cannot exceed scope of authority
--
-- ============================================================================
