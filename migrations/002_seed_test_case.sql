-- ============================================================================
-- SAK AI Agent - Test Case Seed Data
-- ============================================================================
-- Case: Hamza Awad (Manager - Passports Authority ONLY) trying to grant
--       Hussein Motaz FULL management powers over company
-- Expected Result: Agent should determine INVALID (grantor exceeds authority)
-- ============================================================================

-- ============================================================================
-- STEP 0: ENABLE PGVECTOR EXTENSION
-- ============================================================================

-- Enable the vector extension for embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- STEP 1: SEED LEGAL ARTICLES FOR RAG
-- ============================================================================

-- Insert test articles with new schema
-- Using article_number 90001-90006 to clearly identify test/dummy articles
INSERT INTO articles (
    article_number,
    hierarchy_path,
    text_arabic,
    text_english,
    effective_date,
    is_active,
    added,
    updated
) VALUES
-- Article 90001: Lawyers-only activities
(
    90001,
    '{"chapter": {"ar": "المحاماة", "en": "Legal Practice"}, "section": {"ar": "أحكام عامة", "en": "General Provisions"}, "level": 1}',
    'لا يجوز لغير المحامين مزاولة مهنة المحاماة، ويعتبر من أعمال المحاماة ما يلي: ١- الحضور عن ذوي الشأن أمام المحاكم، والنيابة العامة، وهيئات التحكيم، والجهات الإدارية ذات الاختصاص القضائي، وجهات التحقيق التي يحددها القانون. ٢- الدفاع عن ذوي الشأن في الدعاوى التي ترفع منهم أو عليهم، والقيام بأعمال المرافعات والإجراءات القضائية المتصلة به',
    'Only licensed lawyers may practice law. The following are considered legal practice activities: 1- Appearing on behalf of parties before courts, public prosecution, arbitration bodies, administrative bodies with judicial jurisdiction, and investigation authorities specified by law. 2- Defending parties in lawsuits filed by or against them, and carrying out pleading and related judicial procedures.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
),
-- Article 90002: CRITICAL - Cannot grant more than you have
(
    90002,
    '{"chapter": {"ar": "القانون المدني", "en": "Civil Code"}, "section": {"ar": "الوكالة", "en": "Agency"}, "level": 2}',
    'لا يجوز للموكل أن يمنح الوكيل حقوقاً أو صلاحيات تزيد عما يملكه الموكل نفسه من حقوق قانونية أو أهلية أداء. إن الوكالة هي تفويض في ممارسة الحق، ولا يمكن تفويض ما هو غير مستحق أو غير مملوك.',
    'The principal may not grant the agent rights or authorities exceeding what the principal himself possesses in terms of legal rights or capacity. Agency is a delegation in the exercise of a right, and one cannot delegate what is not due or not owned.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
),
-- Article 90003: CRITICAL - Must have capacity for delegated acts
(
    90003,
    '{"chapter": {"ar": "القانون المدني", "en": "Civil Code"}, "section": {"ar": "الوكالة", "en": "Agency"}, "level": 2}',
    'يجب أن تتوافر في الموكل الأهلية الكاملة لمباشرة التصرف الذي يوكل فيه غيره. وبناءً عليه: إذا كان الموكل لا يملك حق البيع (لعدم ملكية العقار مثلاً)، فلا تنعقد الوكالة للوكيل بالبيع. إذا كان الموكل ناقص الأهلية أو ممنوعاً من التصرف قانوناً، فلا تنتقل للوكيل صلاحية هذا التصرف عبر الوكالة.',
    'The principal must have full capacity to carry out the act for which he appoints another as agent. Accordingly: If the principal does not have the right to sell (e.g., due to not owning the property), the agency for sale is not valid. If the principal lacks capacity or is legally prohibited from the act, such authority cannot be transferred to the agent through agency.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
),
-- Article 90004: Scope of special POA
(
    90004,
    '{"chapter": {"ar": "القانون المدني", "en": "Civil Code"}, "section": {"ar": "الوكالة", "en": "Agency"}, "level": 2}',
    'الوكالة الخاصة لا تخول الوكيل إلا سلطة إجراء الأمور المحددة فيها، وما تستتبعه هذه الأمور من توابع ضرورية وفقاً لطبيعة كل أمر والعرف الجاري.',
    'A special power of attorney authorizes the agent only to carry out the matters specified therein, and the necessary consequences of such matters according to the nature of each matter and prevailing custom.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
),
-- Article 90005: Company representation authority
(
    90005,
    '{"chapter": {"ar": "قانون الشركات", "en": "Commercial Companies Law"}, "section": {"ar": "الإدارة", "en": "Management"}, "level": 1}',
    'يحدد عقد تأسيس الشركة أو نظامها الأساسي صلاحيات المديرين والمفوضين بالتوقيع. ولا يجوز لأي مدير أو مفوض التصرف خارج نطاق الصلاحيات الممنوحة له في السجل التجاري.',
    'The company''s memorandum of association or articles of association shall specify the authorities of managers and authorized signatories. No manager or authorized signatory may act outside the scope of authorities granted to them in the commercial register.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
),
-- Article 90006: Agent exceeding limits
(
    90006,
    '{"chapter": {"ar": "القانون المدني", "en": "Civil Code"}, "section": {"ar": "الوكالة", "en": "Agency"}, "level": 2}',
    'لا يجوز للوكيل أن يتجاوز حدود الوكالة، فإذا فعل كان تصرفه موقوفاً على إجازة الموكل. والتصرف الذي يجريه الوكيل خارج حدود وكالته لا يلزم الموكل إلا إذا أجازه.',
    'The agent may not exceed the limits of the agency. If he does, his act is suspended pending the principal''s ratification. Acts performed by the agent outside the scope of his agency do not bind the principal unless ratified.',
    '2027-01-13',
    TRUE,
    '2026-01-13',
    '2026-01-13'
)
ON CONFLICT (article_number) DO UPDATE SET
    hierarchy_path = EXCLUDED.hierarchy_path,
    text_arabic = EXCLUDED.text_arabic,
    text_english = EXCLUDED.text_english,
    updated = CURRENT_DATE;

-- ============================================================================
-- STEP 2: CREATE TEST APPLICATION
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
    created_at,
    submitted_at
) VALUES (
    'a0000001-1111-2222-3333-444444444444',
    'SAK-2026-POA-TEST001',
    'POA_SPECIAL_COMPANY',
    'first_party',
    '13572468',
    'qatari_id',
    'submitted',
    'tier1_validation',
    'توكيل خاص لإدارة الشركة',
    'Special POA for Company Management',
    'indefinite',
    NOW(),
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    status = 'submitted',
    processing_stage = 'tier1_validation';

-- ============================================================================
-- STEP 3: CREATE PARTIES
-- ============================================================================

-- Party 1: Hamza Awad (Grantor/First Party)
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
    'b0000001-1111-2222-3333-444444444444',
    'a0000001-1111-2222-3333-444444444444',
    'first_party',
    1,
    'grantor',
    TRUE,
    '13572468',
    'qatari_id',
    '2028-12-31',
    'حمزة عوض',
    'Hamza Awad',
    'CAN',
    'male',
    'authorized_signatory_cr'
) ON CONFLICT (id) DO UPDATE SET
    full_name_en = 'Hamza Awad';

-- Party 2: Hussein Motaz (Agent/Second Party)
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
    'b0000002-1111-2222-3333-444444444444',
    'a0000001-1111-2222-3333-444444444444',
    'second_party',
    1,
    'agent',
    FALSE,
    '14356543',
    'qatari_id',
    '2029-06-30',
    'حسين معتز',
    'Hussein Motaz',
    'QAT',
    'male',
    'self'
) ON CONFLICT (id) DO UPDATE SET
    party_role = 'agent';

-- ============================================================================
-- STEP 4: CREATE CAPACITY PROOF FOR GRANTOR
-- ============================================================================

INSERT INTO capacity_proofs (
    id,
    party_id,
    capacity_type,
    cr_number,
    company_name,
    cr_expiry_date,
    mec_retrieved,
    mec_retrieved_at,
    poa_full_text_ar,
    poa_full_text_en,
    granted_powers,
    granted_powers_en,
    is_general_poa,
    is_special_poa,
    has_substitution_right
) VALUES (
    'c0000001-1111-2222-3333-444444444444',
    'b0000001-1111-2222-3333-444444444444',
    'commercial_registration',
    '3333',
    'صولا للخدمات',
    '2027-12-31',
    TRUE,
    NOW(),
    'أنا الموقع أدناه: الاسم: حمزة عوض الجنسية: كندا رقم البطاقة الشخصية القطرية: 13572468
بصفتي شريك مدير / صاحب الصلاحية في شركة: صولا للخدمات رقم السجل التجاري: 3333
قد وكلت السيد: الاسم: حسين معتز الجنسية: قطرية رقم البطاقة الشخصية القطرية: 14356543

وذلك في القيام بالمهام التالية وتمثيلي أمام كافة الجهات الرسمية في دولة قطر، وهي:
الإدارة والتوقيع: إدارة الشركة وتسيير أعمالها اليومية والتوقيع على العقود والاتفاقيات والمراسلات باسم الشركة.
الجهات الحكومية: تمثيل الشركة أمام وزارة التجارة والصناعة، ووزارة العمل، ووزارة الداخلية (الجوازات)، والبلدية، وكافة الهيئات والمؤسسات الحكومية وشبه الحكومية.
السجل التجاري: القيام بكافة الإجراءات المتعلقة بالسجل التجاري من تجديد أو استخراج مستخرجات رسمية.',
    'I, the undersigned: Name: Hamza Awad, Nationality: Canadian, QID: 13572468
In my capacity as Partner Manager / Authority Holder in company: Sola Services, CR Number: 3333
Have appointed Mr.: Name: Hussein Motaz, Nationality: Qatari, QID: 14356543

To carry out the following tasks and represent me before all official authorities in the State of Qatar:
Management and Signing: Managing the company, running its daily operations, and signing contracts, agreements, and correspondence on behalf of the company.
Government Entities: Representing the company before the Ministry of Commerce and Industry, Ministry of Labor, Ministry of Interior (Passports), Municipality, and all government and semi-government bodies.
Commercial Registry: Carrying out all procedures related to the commercial registry including renewal and obtaining official extracts.',
    '["إدارة الشركة", "التوقيع على العقود", "تمثيل الشركة أمام الجهات الحكومية", "إجراءات السجل التجاري"]',
    '["Company Management", "Contract Signing", "Government Representation", "Commercial Registry Procedures"]',
    FALSE,
    TRUE,
    FALSE
) ON CONFLICT (id) DO UPDATE SET
    poa_full_text_ar = EXCLUDED.poa_full_text_ar;

-- ============================================================================
-- STEP 5: CREATE CR DOCUMENT (OCR completed)
-- ============================================================================

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
    'd0000001-1111-2222-3333-444444444444',
    'a0000001-1111-2222-3333-444444444444',
    'commercial_registry_extract.pdf',
    '/uploads/a0000001/commercial_registry_extract.pdf',
    'COMMERCIAL_REGISTRATION',
    'COMMERCIAL_REGISTRATION',
    0.95,
    TRUE,
    'completed',
    NOW(),
    TRUE
) ON CONFLICT (id) DO UPDATE SET
    ocr_status = 'completed';

-- ============================================================================
-- STEP 6: CREATE DOCUMENT EXTRACTION (OCR RESULT FROM CR)
-- This is the RAW extraction - shows what OCR found
-- ============================================================================

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
    'e0000001-1111-2222-3333-444444444444',
    'd0000001-1111-2222-3333-444444444444',
    'azure-document-intelligence',
    'السجل التجاري
رقم السجل: 3333
اسم الشركة: صولا للخدمات

المدراء:
ياسر أنس - مدير (صلاحيات كاملة ومطلقة) - لبنان - 12345678
محمد إلياس - مدير (الصلاحيات المالية) - سوريا - 87654321
حمزة عوض - مدير (الجوازات) - كندا - 13572468',
    'Commercial Registry
CR Number: 3333
Company Name: Sola Services

Directors:
Yasser Anas - Manager (Full and Absolute Authority) - Lebanon - 12345678
Mohamad Elyas - Manager (Financial Authority) - Syria - 87654321
Hamza Awad - Manager (Passports) - Canada - 13572468',
    0.92,
    '{
        "cr_number": "3333",
        "company_name_ar": "صولا للخدمات",
        "company_name_en": "Sola Services",
        "directors": [
            {
                "name_ar": "ياسر أنس",
                "name_en": "Yasser Anas",
                "position_ar": "مدير",
                "authority_ar": "صلاحيات كاملة ومطلقة",
                "authority_en": "Full and Absolute Authority",
                "nationality": "Lebanon",
                "id_number": "12345678"
            },
            {
                "name_ar": "محمد إلياس",
                "name_en": "Mohamad Elyas",
                "position_ar": "مدير",
                "authority_ar": "الصلاحيات المالية",
                "authority_en": "Financial Authority",
                "nationality": "Syria",
                "id_number": "87654321"
            },
            {
                "name_ar": "حمزة عوض",
                "name_en": "Hamza Awad",
                "position_ar": "مدير",
                "authority_ar": "الجوازات",
                "authority_en": "Passports",
                "nationality": "Canada",
                "id_number": "13572468"
            }
        ]
    }',
    NOW()
) ON CONFLICT (id) DO UPDATE SET
    extracted_fields = EXCLUDED.extracted_fields;

-- ============================================================================
-- STEP 7: MATCH_ARTICLES FUNCTION FOR RAG
-- Uses dynamic SQL with EXECUTE format() to handle embedding column selection
-- (Same approach as search_agent)
-- ============================================================================

CREATE OR REPLACE FUNCTION match_articles(
    query_embedding vector(1536),
    match_threshold float,
    match_count int,
    language text DEFAULT 'english'
)
RETURNS TABLE (
    article_number integer,
    hierarchy_path jsonb,
    text_arabic text,
    text_english text,
    similarity float
)
LANGUAGE plpgsql
AS $$
DECLARE
    embedding_col text;
BEGIN
    -- Determine which embedding column to use based on language
    IF language = 'arabic' THEN
        embedding_col := 'arabic_embedding';
    ELSE
        embedding_col := 'embedding';
    END IF;

    -- Perform vector similarity search using cosine distance
    -- The <=> operator returns cosine distance (0 = identical, 2 = opposite)
    -- We convert to similarity: 1 - distance (higher = more similar)
    RETURN QUERY
    EXECUTE format('
        SELECT
            a.article_number,
            a.hierarchy_path,
            a.text_arabic,
            a.text_english,
            1 - (a.%I <=> $1) as similarity
        FROM articles a
        WHERE a.is_active = TRUE
          AND a.%I IS NOT NULL
          AND 1 - (a.%I <=> $1) > $2
        ORDER BY a.%I <=> $1
        LIMIT $3
    ', embedding_col, embedding_col, embedding_col, embedding_col)
    USING query_embedding, match_threshold, match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_articles(vector(1536), float, int, text) TO anon, authenticated;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================

SELECT
    'Test Case Seeded' as status,
    a.application_number,
    a.transaction_type_code,
    p1.full_name_en as grantor,
    p2.full_name_en as agent,
    (SELECT COUNT(*) FROM articles WHERE is_active = TRUE) as article_count
FROM applications a
JOIN parties p1 ON p1.application_id = a.id AND p1.party_role = 'grantor'
JOIN parties p2 ON p2.application_id = a.id AND p2.party_role = 'agent'
WHERE a.id = 'a0000001-1111-2222-3333-444444444444';

-- ============================================================================
-- SUMMARY
-- ============================================================================
--
-- Seeded:
--   - 6 legal articles (agency law, company law)
--   - 1 application (SAK-2026-POA-TEST001)
--   - 2 parties (Hamza Awad as grantor, Hussein Motaz as agent)
--   - 1 capacity proof with POA text
--   - 1 document (CR extract)
--   - 1 document extraction (OCR result showing directors & authorities)
--
-- Key Facts for Agent to Discover:
--   - Hamza Awad is listed as "Manager (Passports)" in the CR
--   - Hamza is trying to grant: full management, contracts, govt representation
--   - Articles 2 & 3 clearly state: cannot delegate more than you have
--
-- Agent should independently determine: INVALID
--
-- ============================================================================
