-- ============================================================================
-- SAK AI Agent - Test Case: Vehicle POA - Exceeding Delegated Authority
-- ============================================================================
-- Case: A (Mohannad) received LIMITED vehicle POA from C (Youssef - owner).
--       A is now trying to grant B (Omar) BROADER powers than A received.
--
-- Key Test Elements:
--   1. A's capacity = agent_under_poa (not owner, not acting as self)
--   2. A's original POA (from C) is LIMITED: drive, ship, export ONLY
--   3. A is trying to grant B: drive, ship, export + SALE + borders
--   4. Original POA explicitly prohibits: sale, transfer, sub-delegation
--   5. Template shows sale rights selected (MISMATCH with OCR restrictions)
--
-- Expected Result: INVALID
--   - A cannot sub-delegate (prohibited)
--   - A cannot grant sale rights (never received from C)
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
    'a0000002-2222-3333-4444-555555555555',
    'SAK-2026-POA-TEST002',
    'POA_SPECIAL_VEHICLE',
    'first_party',
    '14723699',
    'qatari_id',
    'submitted',
    'tier1_validation',
    'توكيل خاص في المركبات - محاولة توكيل الغير',
    'Special Vehicle POA - Sub-delegation Attempt',
    'fixed',
    '2026-07-31',
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    status = 'submitted',
    processing_stage = 'tier1_validation';

-- ============================================================================
-- STEP 2: CREATE PARTIES
-- ============================================================================

-- Party 1: Mohannad Jaber (Grantor/First Party - acting under POA)
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
    'b0000003-2222-3333-4444-555555555555',
    'a0000002-2222-3333-4444-555555555555',
    'first_party',
    1,
    'grantor',
    TRUE,
    '14723699',
    'qatari_id',
    '2026-04-28',
    'مهند جابر',
    'Mohannad Jaber',
    'QAT',
    'male',
    'agent_under_poa'  -- KEY: Acting under POA, not personal capacity
) ON CONFLICT (id) DO UPDATE SET
    capacity = 'agent_under_poa';

-- Party 2: Omar Anas (Agent/Second Party - receiving the sub-delegation)
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
    'b0000004-2222-3333-4444-555555555555',
    'a0000002-2222-3333-4444-555555555555',
    'second_party',
    1,
    'agent',
    FALSE,
    'VQ32456',
    'passport',
    '2030-02-12',
    'عمر أنس',
    'Omar Anas',
    'EGY',
    'male',
    'self'
) ON CONFLICT (id) DO UPDATE SET
    party_role = 'agent';

-- ============================================================================
-- STEP 3: CREATE CAPACITY PROOF FOR GRANTOR (Mohannad's authority from Youssef)
-- ============================================================================

INSERT INTO capacity_proofs (
    id,
    party_id,
    capacity_type,

    -- POA Details (the original POA from Youssef to Mohannad)
    poa_authorization_number,
    poa_date,
    poa_expiry,
    poa_issuing_authority,
    poa_verified,

    -- Principal (original grantor: Youssef Mansour)
    principal_name_ar,
    principal_name_en,
    principal_qid,

    -- Agent (Mohannad - who is now trying to sub-delegate)
    agent_name_ar,
    agent_name_en,
    agent_qid,

    -- Powers granted in original POA
    granted_powers,
    granted_powers_en,
    is_general_poa,
    is_special_poa,
    has_substitution_right,  -- CRITICAL: FALSE = cannot sub-delegate

    -- Full POA text for context
    poa_full_text_ar,
    poa_full_text_en
) VALUES (
    'c0000002-2222-3333-4444-555555555555',
    'b0000003-2222-3333-4444-555555555555',  -- FK to Mohannad's party record
    'agency_mandate',

    -- POA Details
    '1111',
    '2026-01-13',
    '2026-07-31',
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

    -- Powers - note: limited to driving, shipping, export
    '["قيادة المركبة", "شحن المركبة", "تصدير المركبة", "مراجعة الحدود والجمارك"]',
    '["Drive vehicle", "Ship vehicle", "Export vehicle", "Border and customs clearance"]',
    FALSE,  -- Not general
    TRUE,   -- Is special (vehicle-specific)
    FALSE,  -- CRITICAL: NO substitution right

    -- Full Arabic text (includes explicit prohibition)
    'إنه في يوم : الثلاثاء الموافق : 2026-01-13 الساعة : 3:21 تقدم لنا نحن : كاتب العدل بإدارة التوثيق . أنا الموقع أدناه : الإسم / : يوسف منصور ، الجنسية : قطري ،
 جواز سفر رقم : 33453  ،
 جوال رقم : 4345322
، بصفته : عن نفسه - بصفته الشخصية
وكلت السيد : الإسم / : مهند جابر ، الجنسية : قطري ، الرقم الشخصي : 14723699 ، بصفته : عن نفسه - بصفته الشخصية
وذلك في القيام مقامي ونيابة عني بصفتي المشار إليها في : إتخاذ كافة الإجراءات اللازمة بشأن المركبة المذكورة أدناه، والقيام بالآتي: قيادة وشحن وتصدير المركبة، وله الحق في مراجعة جميع الحدود والمنافذ والموانئ والجمارك، والتوقيع على كافة المستندات والطلبات اللازمة لإنهاء إجراءات التصدير والشحن.
بيانات المركبة:
نوع المركبة: تويوتا (Toyota)
رقم اللوحة: 123A34
نوع اللوحة: نقل خاص
التصرفات والقيود : تقتصر هذه الوكالة على القيادة والشحن والتصدير والمراجعة فقط، ولا يحق للوكيل البيع أو نقل الملكية أو الرهن أو توكيل الغير، وتعتبر هذه الوكالة سارية المفعول حتى تاريخ 2026-07-31 ما لم يتم إلغاؤها قبل ذلك',

    -- English translation
    'On Tuesday, 2026-01-13 at 3:21, before us the Notary of the Documentation Department. I the undersigned: Name: Youssef Mansour, Nationality: Qatari, Passport No: 33453, Mobile: 4345322, acting in personal capacity, have appointed Mr: Name: Mohannad Jaber, Nationality: Qatari, QID: 14723699, in personal capacity, to act on my behalf regarding the vehicle described below: driving, shipping, and exporting the vehicle, with the right to appear before all borders, ports, and customs, and to sign all documents and applications necessary to complete export and shipping procedures.
Vehicle Details: Type: Toyota, Plate Number: 123A34, Plate Type: Private Transport.
RESTRICTIONS: This POA is LIMITED to driving, shipping, export, and clearance ONLY. The agent has NO right to sell, transfer ownership, mortgage, or SUB-DELEGATE TO OTHERS. This POA is valid until 2026-07-31 unless cancelled earlier.'
) ON CONFLICT (id) DO UPDATE SET
    has_substitution_right = FALSE;

-- ============================================================================
-- STEP 4: CREATE POA DOCUMENTS (2 attachments from OCR)
-- ============================================================================

-- Document 1: Main POA with restrictions
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
    'd0000002-2222-3333-4444-555555555555',
    'a0000002-2222-3333-4444-555555555555',
    'poa_youssef_to_mohannad_v1.pdf',
    '/uploads/a0000002/poa_youssef_to_mohannad_v1.pdf',
    'POWER_OF_ATTORNEY',
    'POWER_OF_ATTORNEY',
    0.94,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- Document 2: Second POA version (without explicit restrictions section)
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
    'd0000003-2222-3333-4444-555555555555',
    'a0000002-2222-3333-4444-555555555555',
    'poa_youssef_to_mohannad_v2.pdf',
    '/uploads/a0000002/poa_youssef_to_mohannad_v2.pdf',
    'POWER_OF_ATTORNEY',
    'POWER_OF_ATTORNEY',
    0.91,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- ============================================================================
-- STEP 5: CREATE DOCUMENT EXTRACTIONS (OCR RESULTS)
-- ============================================================================

-- Extraction 1: Full POA with restrictions visible
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
    'e0000002-2222-3333-4444-555555555555',
    'd0000002-2222-3333-4444-555555555555',
    'azure-document-intelligence',
    'إنه في يوم : الثلاثاء الموافق : 2026-01-13 الساعة : 3:21 تقدم لنا نحن : كاتب العدل بإدارة التوثيق . أنا الموقع أدناه : الإسم / : يوسف منصور ، الجنسية : قطري ،
 جواز سفر رقم : 33453  ،
 جوال رقم : 4345322
، بصفته : عن نفسه - بصفته الشخصية
وكلت السيد : الإسم / : مهند جابر ، الجنسية : قطري ، الرقم الشخصي : 14723699 ، بصفته : عن نفسه - بصفته الشخصية
وذلك في القيام مقامي ونيابة عني بصفتي المشار إليها في : إتخاذ كافة الإجراءات اللازمة بشأن المركبة المذكورة أدناه، والقيام بالآتي: قيادة وشحن وتصدير المركبة، وله الحق في مراجعة جميع الحدود والمنافذ والموانئ والجمارك، والتوقيع على كافة المستندات والطلبات اللازمة لإنهاء إجراءات التصدير والشحن.
بيانات المركبة:
نوع المركبة: تويوتا (Toyota)
رقم اللوحة: 123A34
نوع اللوحة: نقل خاص
التصرفات والقيود : تقتصر هذه الوكالة على القيادة والشحن والتصدير والمراجعة فقط، ولا يحق للوكيل البيع أو نقل الملكية أو الرهن أو توكيل الغير، وتعتبر هذه الوكالة سارية المفعول حتى تاريخ 2026-07-31 ما لم يتم إلغاؤها قبل ذلك',
    'On Tuesday, 2026-01-13 at 3:21... [see capacity_proofs.poa_full_text_en for full translation]',
    0.93,
    '{
        "document_type": "power_of_attorney",
        "poa_date": "2026-01-13",
        "poa_expiry": "2026-07-31",
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
        "vehicle": {
            "type_ar": "تويوتا",
            "type_en": "Toyota",
            "plate_number": "123A34",
            "plate_type_ar": "نقل خاص",
            "plate_type_en": "Private Transport"
        },
        "powers_granted": [
            "قيادة المركبة",
            "شحن المركبة",
            "تصدير المركبة",
            "مراجعة الحدود والمنافذ والموانئ والجمارك",
            "التوقيع على المستندات"
        ],
        "restrictions": {
            "scope_limited": true,
            "limited_to": ["قيادة", "شحن", "تصدير", "مراجعة"],
            "prohibited_acts": ["البيع", "نقل الملكية", "الرهن", "توكيل الغير"],
            "can_sell": false,
            "can_transfer_ownership": false,
            "can_mortgage": false,
            "can_subdelegate": false
        }
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- Extraction 2: Second version (without restrictions section)
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
    'e0000003-2222-3333-4444-555555555555',
    'd0000003-2222-3333-4444-555555555555',
    'azure-document-intelligence',
    'إنه في يوم : الثلاثاء الموافق : 2026-01-13 الساعة : 3:21 تقدم لنا نحن : كاتب العدل بإدارة التوثيق . أنا الموقع أدناه : الإسم / : يوسف منصور ، الجنسية : قطري ،
 جواز سفر رقم : 33453  ،
 جوال رقم : 4345322
، بصفته : عن نفسه - بصفته الشخصية
وكلت السيد : الإسم / : مهند جابر ، الجنسية : قطري ، الرقم الشخصي : 14723699 ، بصفته : عن نفسه - بصفته الشخصية
وذلك في القيام مقامي ونيابة عني بصفتي المشار إليها في : إتخاذ كافة الإجراءات اللازمة بشأن المركبة المذكورة أدناه، والقيام بالآتي: قيادة وشحن وتصدير المركبة، وله الحق في مراجعة جميع الحدود والمنافذ والموانئ والجمارك، والتوقيع على كافة المستندات والطلبات اللازمة لإنهاء إجراءات التصدير والشحن.
بيانات المركبة:
نوع المركبة: تويوتا (Toyota)
رقم اللوحة: 123A34
نوع اللوحة: نقل خاص
وتعتبر هذه الوكالة سارية المفعول حتى تاريخ 2026-07-31 ما لم يتم إلغاؤها قبل ذلك',
    'Version 2 - without explicit restrictions section',
    0.89,
    '{
        "document_type": "power_of_attorney",
        "poa_date": "2026-01-13",
        "poa_expiry": "2026-07-31",
        "principal": {
            "name_ar": "يوسف منصور",
            "qid": "33453"
        },
        "agent": {
            "name_ar": "مهند جابر",
            "qid": "14723699"
        },
        "vehicle": {
            "type_ar": "تويوتا",
            "plate_number": "123A34",
            "plate_type_ar": "نقل خاص"
        },
        "powers_granted": [
            "قيادة المركبة",
            "شحن المركبة",
            "تصدير المركبة"
        ],
        "restrictions": {
            "note": "No explicit restrictions section in this version"
        }
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

SELECT
    'Vehicle Sub-delegation Test Case Seeded' as status,
    a.application_number,
    a.transaction_type_code,
    p1.full_name_en as grantor,
    p1.capacity as grantor_capacity,
    p2.full_name_en as agent,
    cp.has_substitution_right,
    (SELECT COUNT(*) FROM documents WHERE application_id = a.id) as document_count
FROM applications a
JOIN parties p1 ON p1.application_id = a.id AND p1.party_role = 'grantor'
JOIN parties p2 ON p2.application_id = a.id AND p2.party_role = 'agent'
LEFT JOIN capacity_proofs cp ON cp.party_id = p1.id
WHERE a.id = 'a0000002-2222-3333-4444-555555555555';

-- ============================================================================
-- SUMMARY
-- ============================================================================
--
-- Chain of Authority (agent must discover this):
--
--   C (Youssef Mansour - vehicle owner)
--       ↓ POA #1111 (LIMITED: drive, ship, export ONLY - NO sale, NO sub-delegation)
--   A (Mohannad Jaber - agent under POA)
--       ↓ THIS APPLICATION (trying to grant BROADER powers)
--   B (Omar Anas - proposed new agent)
--
-- Seeded:
--   - 1 application (SAK-2026-POA-TEST002) - Vehicle POA sub-delegation attempt
--   - 2 parties:
--       * Mohannad Jaber (grantor, capacity: agent_under_poa)
--       * Omar Anas (agent, capacity: self)
--   - 1 capacity_proof documenting Mohannad's authority from Youssef (C)
--   - 2 documents (POA attachments with OCR)
--   - 2 document_extractions (structured OCR results)
--
-- What A (Mohannad) RECEIVED from C (Youssef):
--   - Drive, ship, export vehicle
--   - NO sale rights
--   - NO sub-delegation rights
--
-- What A is TRYING TO GRANT to B (Omar):
--   - Drive, ship, export (OK - has these)
--   - Borders/customs representation (OK - has this)
--   - SALE AND TRANSFER (INVALID - never received this)
--   - Sub-delegation itself (INVALID - prohibited)
--
-- Key Facts for Agent to Discover:
--   1. A's capacity = agent_under_poa (not acting as self)
--   2. Look at capacity_proofs → see POA from C with restrictions
--   3. OCR text says: "لا يحق للوكيل البيع أو نقل الملكية... توكيل الغير"
--   4. has_substitution_right = FALSE
--   5. Template shows sale selected (MISMATCH with OCR restrictions)
--
-- Agent should determine: INVALID
--   - Reason 1: A cannot sub-delegate (explicitly prohibited)
--   - Reason 2: A cannot grant sale rights (never received from C)
--   - Legal principle: "nemo dat quod non habet" (can't give what you don't have)
--
-- ============================================================================
