-- ============================================================================
-- SAK AI Agent - Data Model Migration v1.0 (Fresh Install)
-- ============================================================================
-- This migration creates all tables for a new Supabase project
-- Run this in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE ENUMS
-- ============================================================================

-- Application Enums
CREATE TYPE application_status AS ENUM (
    'draft',
    'submitted',
    'in_review',
    'pending_documents',
    'pending_sme',
    'approved',
    'rejected',
    'cancelled',
    'completed'
);

CREATE TYPE processing_stage AS ENUM (
    'intake',
    'document_processing',
    'tier1_validation',
    'tier2_analysis',
    'risk_scoring',
    'decision_pending',
    'completed'
);

CREATE TYPE duration_type AS ENUM (
    'fixed',
    'indefinite',
    'until_completion'
);

-- Party Enums
CREATE TYPE party_type AS ENUM (
    'first_party',
    'second_party'
);

CREATE TYPE party_role AS ENUM (
    'grantor',
    'agent',
    'seller',
    'buyer',
    'witness',
    'representative'
);

CREATE TYPE id_type AS ENUM (
    'qatari_id',
    'gcc_id',
    'passport',
    'residence_permit'
);

CREATE TYPE gender_type AS ENUM ('male', 'female');

-- Capacity Enums
CREATE TYPE capacity_type AS ENUM (
    'personal_capacity',
    'establishment_based',
    'commercial_registration',
    'foreign_entity',
    'agency_mandate',
    'legal_mandate'
);

CREATE TYPE party_capacity AS ENUM (
    'self',
    'natural_guardian',
    'company_representative',
    'authorized_signatory_establishment',
    'partner_in_company',
    'partner_in_factory',
    'owner',
    'authorized_signatory_cr',
    'partner_foreign_company',
    'agent_under_poa',
    'authorized_agent',
    'trustee',
    'custodian_guardian',
    'agent_for_absentee'
);

CREATE TYPE entry_method AS ENUM (
    'not_applicable',
    'manual_entry',
    'auto_retrieved_mec',
    'system_verification'
);

-- Principal Enums
CREATE TYPE principal_type AS ENUM (
    'natural_person',
    'legal_person'
);

CREATE TYPE legal_entity_capacity AS ENUM (
    'company',
    'establishment',
    'foreign_company'
);

-- Document Enums
CREATE TYPE ocr_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'skipped'
);

CREATE TYPE attachment_category AS ENUM (
    'identity',
    'corporate',
    'authorization',
    'government_approval',
    'legal',
    'other'
);

-- Duplicate Check Enums
CREATE TYPE duplicate_match_type AS ENUM (
    'same_id_same_capacity_same_proof',
    'same_id_same_capacity',
    'same_id_different_capacity'
);

CREATE TYPE duplicate_resolution AS ENUM (
    'merged',
    'kept_both',
    'removed_duplicate',
    'false_positive'
);

-- ML Pipeline Enums
CREATE TYPE case_build_status AS ENUM (
    'pending',
    'building',
    'completed',
    'failed'
);

CREATE TYPE brief_status AS ENUM (
    'draft',
    'ready',
    'in_analysis',
    'completed'
);

CREATE TYPE analysis_status AS ENUM (
    'pending',
    'decomposing',
    'retrieving',
    'synthesizing',
    'verifying',
    'completed',
    'failed'
);

CREATE TYPE issue_category AS ENUM (
    'grantor_capacity',
    'agent_capacity',
    'poa_scope',
    'substitution_rights',
    'formalities',
    'validity',
    'compliance',
    'business_rules'
);

CREATE TYPE research_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'blocked'
);

CREATE TYPE risk_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE routing_decision_type AS ENUM (
    'approve',
    'reject',
    'remediate',
    'escalate',
    'hold'
);

CREATE TYPE decision_bucket AS ENUM (
    'valid',
    'valid_with_remediations',
    'invalid',
    'needs_review'
);

CREATE TYPE routing_target AS ENUM (
    'auto_approve',
    'employee_review',
    'sme_review',
    'rejection_queue',
    'hold_queue'
);

-- ============================================================================
-- STEP 2: CREATE REFERENCE TABLES
-- ============================================================================

-- 2.1 transaction_types
CREATE TABLE transaction_types (
    code                    VARCHAR(50) PRIMARY KEY,
    name_ar                 VARCHAR(255) NOT NULL,
    name_en                 VARCHAR(255),
    category_code           VARCHAR(50) NOT NULL,
    parent_category         VARCHAR(50),
    requires_first_party    BOOLEAN DEFAULT TRUE,
    requires_second_party   BOOLEAN DEFAULT TRUE,
    min_first_parties       INTEGER DEFAULT 1,
    max_first_parties       INTEGER,
    min_second_parties      INTEGER DEFAULT 1,
    max_second_parties      INTEGER,
    requires_duration       BOOLEAN DEFAULT TRUE,
    has_mandatory_templates BOOLEAN DEFAULT TRUE,
    has_optional_templates  BOOLEAN DEFAULT TRUE,
    base_fee                DECIMAL(10,2),
    fee_currency            CHAR(3) DEFAULT 'QAR',
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed transaction types
INSERT INTO transaction_types (code, name_ar, name_en, category_code, parent_category) VALUES
('POA_GENERAL_CASES',      'توكيل عام في الدعاوى',                    'General Power of Attorney in Cases',                'documentation', 'powers_of_attorney'),
('POA_SPECIAL',            'توكيل خاص',                              'Special Power of Attorney',                          'documentation', 'powers_of_attorney'),
('POA_SPECIAL_VEHICLE',    'توكيل خاص في المركبات',                   'Special Power of Attorney for Vehicle',              'documentation', 'powers_of_attorney'),
('SALE_SHARES',            'بيع حصص في شركة / مؤسسة',                 'Sale of Shares in Company/Establishment',            'documentation', 'sale'),
('POA_SPECIAL_COMPANY',    'توكيل خاص لشركة',                         'Special Power of Attorney for Company',              'documentation', 'powers_of_attorney'),
('POA_SPECIAL_PROPERTY',   'توكيل خاص في عقار',                       'Special Power of Attorney for Property',             'documentation', 'powers_of_attorney'),
('POA_GENERAL',            'توكيل عام',                              'General Power of Attorney',                          'documentation', 'powers_of_attorney'),
('SALE_COMPANY',           'بيع شركة',                               'Sale of Company',                                    'documentation', 'sale'),
('POA_SPECIAL_GOVT',       'توكيل خاص لإنجاز المعاملات الحكومية',      'Special Power of Attorney for Government Transactions', 'documentation', 'powers_of_attorney'),
('POA_SPECIAL_INHERITANCE','توكيل رسمي خاص في الإرث',                 'Special Official Power of Attorney for Inheritance', 'documentation', 'powers_of_attorney');

CREATE INDEX idx_transaction_types_category ON transaction_types(category_code);
CREATE INDEX idx_transaction_types_parent ON transaction_types(parent_category);

-- 2.2 transaction_configs
CREATE TABLE transaction_configs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_type_code   VARCHAR(50) NOT NULL REFERENCES transaction_types(code),
    required_parties        JSONB,
    required_documents      JSONB,
    optional_documents      JSONB,
    tier1_checks            JSONB,
    notes                   TEXT,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(transaction_type_code)
);

CREATE INDEX idx_transaction_configs_type ON transaction_configs(transaction_type_code);

-- 2.3 capacity_configurations
CREATE TABLE capacity_configurations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capacity                party_capacity UNIQUE NOT NULL,
    name_ar                 VARCHAR(255) NOT NULL,
    name_en                 VARCHAR(255) NOT NULL,
    capacity_type           capacity_type NOT NULL,
    entry_method            entry_method NOT NULL,
    required_proof_fields   JSONB NOT NULL DEFAULT '[]',
    appears_in_instrument   BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Seed capacity configurations
INSERT INTO capacity_configurations (capacity, name_ar, name_en, capacity_type, entry_method, required_proof_fields, appears_in_instrument) VALUES
('self',                              'شخصي',                                    'Self (in personal capacity)',                    'personal_capacity',        'not_applicable',       '[]', TRUE),
('natural_guardian',                  'الولي الطبيعي',                           'Natural Guardian',                               'personal_capacity',        'not_applicable',       '[]', TRUE),
('company_representative',            'مندوب',                                   'Company Representative',                         'establishment_based',      'manual_entry',         '["establishment_number", "establishment_name", "po_box", "establishment_phone", "expiry_date"]', FALSE),
('authorized_signatory_establishment','مخول بالتوقيع في سجل المنشأة',            'Authorized Signatory in Establishment Record',  'establishment_based',      'manual_entry',         '["establishment_number", "establishment_name", "po_box", "establishment_phone", "expiry_date"]', TRUE),
('partner_in_company',                'شريك في شركة',                            'Partner in a Company',                           'commercial_registration',  'auto_retrieved_mec',   '["cr_number", "company_name", "po_box", "company_phone", "expiry_date"]', TRUE),
('partner_in_factory',                'شريك في مصنع',                            'Partner in a Factory',                           'commercial_registration',  'auto_retrieved_mec',   '["cr_number", "company_name", "po_box", "company_phone", "expiry_date"]', TRUE),
('owner',                             'مالك',                                    'Owner',                                          'commercial_registration',  'auto_retrieved_mec',   '["cr_number", "company_name", "po_box", "company_phone", "expiry_date"]', TRUE),
('authorized_signatory_cr',           'مخول بالتوقيع في السجل التجاري',           'Authorized Signatory in Commercial Register',   'commercial_registration',  'auto_retrieved_mec',   '["cr_number", "company_name", "po_box", "company_phone", "expiry_date"]', TRUE),
('partner_foreign_company',           'شريك في شركة أجنبية',                      'Partner in a Foreign Company',                   'foreign_entity',           'manual_entry',         '["cr_number", "company_name", "nationality", "company_phone", "expiry_date"]', TRUE),
('agent_under_poa',                   'وكيل بموجب توكيل',                         'Agent Under a Power of Attorney (POA)',          'agency_mandate',           'system_verification',  '["poa_authorization_number"]', TRUE),
('authorized_agent',                  'المفوض',                                  'Authorized Agent',                               'agency_mandate',           'system_verification',  '["poa_authorization_number"]', TRUE),
('trustee',                           'الوصي',                                   'Trustee',                                        'legal_mandate',            'manual_entry',         '["letter_number", "issuing_authority"]', TRUE),
('custodian_guardian',                'القيم',                                   'Custodian/Guardian',                             'legal_mandate',            'manual_entry',         '["letter_number", "issuing_authority"]', TRUE),
('agent_for_absentee',                'وكيل عن غائب',                            'Agent for an Absentee',                          'legal_mandate',            'manual_entry',         '["poa_details"]', TRUE);

CREATE INDEX idx_capacity_config_type ON capacity_configurations(capacity_type);
CREATE INDEX idx_capacity_config_entry ON capacity_configurations(entry_method);

-- 2.4 attachment_types
CREATE TABLE attachment_types (
    code                    VARCHAR(50) PRIMARY KEY,
    name_ar                 VARCHAR(255) NOT NULL,
    name_en                 VARCHAR(255),
    category                attachment_category NOT NULL,
    has_expiry              BOOLEAN DEFAULT FALSE,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO attachment_types (code, name_ar, name_en, category, has_expiry) VALUES
('PERSONAL_ID',           'الهوية الشخصية',                     'Personal ID',                        'identity', TRUE),
('COMMERCIAL_REGISTRATION','السجل التجاري',                     'Commercial Registration (CR)',       'corporate', TRUE),
('AUTHORIZATION',         'التفويض',                           'Authorization',                      'authorization', TRUE),
('POWER_OF_ATTORNEY',     'الوكالة',                           'Power of Attorney',                  'authorization', TRUE),
('PASSPORT',              'جواز السفر',                         'Passport',                           'identity', TRUE),
('TRADE_LICENSE',         'الرخصة التجارية',                    'Trade License',                      'corporate', TRUE),
('FOUNDATION_CONTRACT',   'نسخة من عقد التأسيس',                 'Copy of Foundation Contract',        'corporate', FALSE),
('ESTABLISHMENT_RECORD',  'سجل المنشأة',                        'Establishment Record',               'corporate', TRUE),
('MINORS_AFFAIRS_LETTER', 'خطاب من هيئة شؤون القاصرين',          'Letter from Minors Affairs Authority', 'legal', FALSE),
('GOVT_ENTITY_APPROVAL',  'موافقة جهة حكومية',                   'Government Entity Approval',         'government_approval', FALSE),
('SEMI_GOVT_APPROVAL',    'موافقة جهة شبه حكومية',               'Semi-Government Entity Approval',    'government_approval', FALSE),
('NON_GOVT_APPROVAL',     'موافقة جهة غير حكومية',               'Non-Government Entity Approval',     'government_approval', FALSE);

-- 2.5 template_definitions
CREATE TABLE template_definitions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_code           VARCHAR(50) UNIQUE NOT NULL,
    name_ar                 VARCHAR(255) NOT NULL,
    name_en                 VARCHAR(255),
    template_text_ar        TEXT NOT NULL,
    template_text_en        TEXT,
    is_mandatory            BOOLEAN DEFAULT FALSE,
    allows_custom_text      BOOLEAN DEFAULT TRUE,
    custom_text_label_ar    VARCHAR(255),
    custom_text_label_en    VARCHAR(255),
    transaction_types       VARCHAR(50)[] NOT NULL,
    display_order           INTEGER DEFAULT 0,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_template_definitions_types ON template_definitions USING GIN(transaction_types);

-- 2.6 articles (Legal Corpus for RAG)
CREATE TABLE articles (
    article_number          INTEGER PRIMARY KEY,
    law_name_ar             VARCHAR(255) NOT NULL,
    law_name_en             VARCHAR(255),
    article_text_ar         TEXT NOT NULL,
    article_text_en         TEXT,
    chapter                 VARCHAR(255),
    section                 VARCHAR(255),
    effective_date          DATE,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_articles_law ON articles(law_name_ar);

-- ============================================================================
-- STEP 3: CREATE CORE TABLES
-- ============================================================================

-- 3.1 applications
CREATE TABLE applications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    application_number      VARCHAR(50) UNIQUE NOT NULL,
    transaction_type_code   VARCHAR(50) NOT NULL REFERENCES transaction_types(code),

    -- Submitter Info
    submitter_party_type    party_type NOT NULL,
    submitter_national_id   VARCHAR(20) NOT NULL,
    submitter_id_type       id_type NOT NULL,

    -- Status
    status                  application_status NOT NULL DEFAULT 'draft',
    processing_stage        processing_stage NOT NULL DEFAULT 'intake',

    -- Transaction Details
    transaction_value       DECIMAL(18,2),
    transaction_subject_ar  TEXT,
    transaction_subject_en  TEXT,

    -- POA Duration
    poa_duration_type       duration_type,
    poa_start_date          DATE,
    poa_end_date            DATE,

    -- Lifecycle Dates
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at            TIMESTAMP WITH TIME ZONE,
    last_modified           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at            TIMESTAMP WITH TIME ZONE,

    -- Draft/Rejection Expiry
    draft_expires_at        TIMESTAMP WITH TIME ZONE,
    rejection_expires_at    TIMESTAMP WITH TIME ZONE,

    -- Resubmission Tracking
    is_resubmission         BOOLEAN DEFAULT FALSE,
    original_application_id UUID REFERENCES applications(id),
    rejection_reason        TEXT,
    rejected_at             TIMESTAMP WITH TIME ZONE,

    -- Assignment
    assigned_employee_id    VARCHAR(50),
    assigned_branch_id      VARCHAR(50),

    -- Source
    source_system           VARCHAR(50) DEFAULT 'SAK_PORTAL',

    -- Metadata
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_type ON applications(transaction_type_code);
CREATE INDEX idx_applications_submitter ON applications(submitter_national_id);
CREATE INDEX idx_applications_draft_expiry ON applications(draft_expires_at) WHERE status = 'draft';
CREATE INDEX idx_applications_rejection_expiry ON applications(rejection_expires_at) WHERE status = 'rejected';

-- Trigger for draft expiry
CREATE OR REPLACE FUNCTION set_draft_expiry()
RETURNS TRIGGER AS $$
BEGIN
    NEW.draft_expires_at := NEW.created_at + INTERVAL '7 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_draft_expiry
    BEFORE INSERT ON applications
    FOR EACH ROW
    EXECUTE FUNCTION set_draft_expiry();

-- Trigger for rejection expiry
CREATE OR REPLACE FUNCTION set_rejection_expiry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'rejected' AND (OLD.status IS NULL OR OLD.status != 'rejected') THEN
        NEW.rejection_expires_at := NOW() + INTERVAL '15 days';
        NEW.rejected_at := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_set_rejection_expiry
    BEFORE UPDATE ON applications
    FOR EACH ROW
    EXECUTE FUNCTION set_rejection_expiry();

-- 3.2 parties
CREATE TABLE parties (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,

    -- Party Position
    party_type              party_type NOT NULL,
    party_index             INTEGER NOT NULL DEFAULT 1,

    -- Party Role
    party_role              party_role NOT NULL,

    -- Submitter flags
    is_submitter            BOOLEAN DEFAULT FALSE,
    is_editable             BOOLEAN DEFAULT TRUE,

    -- Identity
    national_id             VARCHAR(20) NOT NULL,
    national_id_type        id_type NOT NULL,
    id_validity_date        DATE NOT NULL,

    -- Personal Info
    full_name_ar            VARCHAR(255) NOT NULL,
    full_name_en            VARCHAR(255),
    date_of_birth           DATE,
    nationality_code        CHAR(3),
    gender                  gender_type,

    -- Entity Flag
    is_entity               BOOLEAN DEFAULT FALSE,
    entity_type             VARCHAR(50),

    -- Capacity
    capacity                party_capacity NOT NULL,

    -- Contact
    phone                   VARCHAR(20),
    email                   VARCHAR(255),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(application_id, party_type, party_index)
);

CREATE INDEX idx_parties_application ON parties(application_id);
CREATE INDEX idx_parties_national_id ON parties(national_id);
CREATE INDEX idx_parties_submitter ON parties(application_id, is_submitter) WHERE is_submitter = TRUE;
CREATE INDEX idx_parties_type_role ON parties(party_type, party_role);

-- 3.3 capacity_proofs (merged from poa_extractions)
CREATE TABLE capacity_proofs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id                UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,

    -- Capacity Type
    capacity_type           capacity_type NOT NULL,

    -- Establishment-Based Fields
    establishment_number    VARCHAR(50),
    establishment_name      VARCHAR(255),
    establishment_po_box    VARCHAR(20),
    establishment_phone     VARCHAR(20),
    establishment_expiry    DATE,

    -- Commercial Registration Fields
    cr_number               VARCHAR(50),
    company_name            VARCHAR(255),
    company_po_box          VARCHAR(20),
    company_phone           VARCHAR(20),
    cr_expiry_date          DATE,
    mec_retrieved           BOOLEAN DEFAULT FALSE,
    mec_retrieved_at        TIMESTAMP WITH TIME ZONE,

    -- Foreign Entity Fields
    company_nationality     CHAR(3),

    -- Agency/Mandate Fields (from poa_extractions)
    poa_authorization_number VARCHAR(50),
    poa_date                DATE,
    poa_expiry              DATE,
    poa_issuing_authority   VARCHAR(255),
    poa_verified            BOOLEAN DEFAULT FALSE,
    poa_verified_at         TIMESTAMP WITH TIME ZONE,

    -- POA extracted data
    principal_name_ar       VARCHAR(255),
    principal_name_en       VARCHAR(255),
    principal_qid           VARCHAR(20),
    agent_name_ar           VARCHAR(255),
    agent_name_en           VARCHAR(255),
    agent_qid               VARCHAR(20),
    granted_powers          JSONB,
    granted_powers_en       JSONB,
    is_general_poa          BOOLEAN,
    is_special_poa          BOOLEAN,
    has_substitution_right  BOOLEAN,
    poa_full_text_ar        TEXT,
    poa_full_text_en        TEXT,

    -- Legal Mandate Fields - Letter
    letter_number           VARCHAR(50),
    issuing_authority       VARCHAR(255),

    -- Legal Mandate Fields - Absentee
    poa_details             TEXT,

    -- Sale Transaction Fields
    share_percentage        DECIMAL(5,2),
    share_value             DECIMAL(18,2),
    sale_price              DECIMAL(18,2),
    payment_method          VARCHAR(100),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(party_id)
);

CREATE INDEX idx_capacity_proofs_party ON capacity_proofs(party_id);
CREATE INDEX idx_capacity_proofs_type ON capacity_proofs(capacity_type);
CREATE INDEX idx_capacity_proofs_cr ON capacity_proofs(cr_number) WHERE cr_number IS NOT NULL;
CREATE INDEX idx_capacity_proofs_establishment ON capacity_proofs(establishment_number) WHERE establishment_number IS NOT NULL;
CREATE INDEX idx_capacity_proofs_poa ON capacity_proofs(poa_authorization_number) WHERE poa_authorization_number IS NOT NULL;

-- 3.4 capacity_principals
CREATE TABLE capacity_principals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capacity_proof_id       UUID NOT NULL REFERENCES capacity_proofs(id) ON DELETE CASCADE,

    -- Principal Type
    principal_type          principal_type NOT NULL,

    -- For Natural Person
    national_id             VARCHAR(20),
    national_id_type        id_type,
    full_name_ar            VARCHAR(255),
    full_name_en            VARCHAR(255),

    -- For Legal Person
    legal_entity_capacity   legal_entity_capacity,
    commercial_registration VARCHAR(50),
    entity_name_ar          VARCHAR(255),

    -- Selection
    selected_from_list      BOOLEAN DEFAULT FALSE,
    source_party_id         UUID REFERENCES parties(id),

    -- Order
    principal_index         INTEGER NOT NULL DEFAULT 1,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(capacity_proof_id, principal_index)
);

CREATE INDEX idx_capacity_principals_proof ON capacity_principals(capacity_proof_id);
CREATE INDEX idx_capacity_principals_source ON capacity_principals(source_party_id) WHERE source_party_id IS NOT NULL;

-- 3.5 documents (renamed from attachments)
CREATE TABLE documents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,

    -- File Information
    file_name               VARCHAR(255) NOT NULL,
    file_path               VARCHAR(500) NOT NULL,
    file_size_bytes         BIGINT,
    mime_type               VARCHAR(100),
    file_hash               VARCHAR(64),

    -- User-selected Attachment Type
    attachment_type_code    VARCHAR(50) NOT NULL REFERENCES attachment_types(code),

    -- ML Classification Result
    ml_document_type_code   VARCHAR(50),
    ml_confidence           DECIMAL(3,2),
    classification_matches  BOOLEAN,

    -- OCR Status
    ocr_status              ocr_status DEFAULT 'pending',
    ocr_started_at          TIMESTAMP WITH TIME ZONE,
    ocr_completed_at        TIMESTAMP WITH TIME ZONE,
    ocr_engine              VARCHAR(50),

    -- Page Information
    page_count              INTEGER,

    -- Verification
    is_verified             BOOLEAN DEFAULT FALSE,
    verified_by             VARCHAR(50),
    verified_at             TIMESTAMP WITH TIME ZONE,

    -- Upload Info
    uploaded_by             VARCHAR(50),
    uploaded_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_application ON documents(application_id);
CREATE INDEX idx_documents_type ON documents(attachment_type_code);
CREATE INDEX idx_documents_ocr_status ON documents(ocr_status);

-- 3.6 document_extractions
CREATE TABLE document_extractions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Extraction Model
    extraction_model        VARCHAR(100),
    model_version           VARCHAR(50),

    -- OCR Output
    raw_text_ar             TEXT,
    raw_text_en             TEXT,
    ocr_confidence          DECIMAL(3,2),

    -- Structured Field Extraction
    extracted_fields        JSONB NOT NULL,
    field_confidences       JSONB,

    -- Position Info
    bounding_boxes          JSONB,

    -- Page-level data
    page_extractions        JSONB,

    -- Timestamps
    extraction_started_at   TIMESTAMP WITH TIME ZONE,
    extraction_completed_at TIMESTAMP WITH TIME ZONE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_document_extractions_document ON document_extractions(document_id);

-- 3.7 poa_templates
CREATE TABLE poa_templates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    template_id             UUID NOT NULL REFERENCES template_definitions(id),
    template_code           VARCHAR(50) NOT NULL,
    is_mandatory            BOOLEAN NOT NULL,
    is_selected             BOOLEAN DEFAULT FALSE,
    custom_text             TEXT,
    selection_order         INTEGER NOT NULL DEFAULT 1,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_poa_templates_application ON poa_templates(application_id);

-- 3.8 duplicate_checks
CREATE TABLE duplicate_checks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    party_id                UUID NOT NULL REFERENCES parties(id),
    duplicate_party_id      UUID REFERENCES parties(id),
    match_type              duplicate_match_type NOT NULL,
    match_fields            JSONB NOT NULL,
    is_resolved             BOOLEAN DEFAULT FALSE,
    resolution              duplicate_resolution,
    resolved_by             VARCHAR(50),
    resolved_at             TIMESTAMP WITH TIME ZONE,
    resolution_notes        TEXT,
    detected_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_duplicate_checks_application ON duplicate_checks(application_id);
CREATE INDEX idx_duplicate_checks_party ON duplicate_checks(party_id);
CREATE INDEX idx_duplicate_checks_unresolved ON duplicate_checks(is_resolved) WHERE is_resolved = FALSE;

-- ============================================================================
-- STEP 4: CREATE ML PIPELINE TABLES
-- ============================================================================

-- 4.1 document_classifications
CREATE TABLE document_classifications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Classification Result
    document_type_code      VARCHAR(50) NOT NULL,
    confidence              DECIMAL(3,2) NOT NULL,

    -- Alternative Classifications
    alternatives            JSONB,

    -- Model Info
    model_name              VARCHAR(100),
    model_version           VARCHAR(50),

    -- Comparison with user selection
    user_selected_type      VARCHAR(50),
    matches_user_selection  BOOLEAN,

    -- Metadata
    classified_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_doc_classifications_document ON document_classifications(document_id);
CREATE INDEX idx_doc_classifications_type ON document_classifications(document_type_code);
CREATE INDEX idx_doc_classifications_mismatch ON document_classifications(matches_user_selection) WHERE matches_user_selection = FALSE;

-- 4.2 extracted_fields (normalized)
CREATE TABLE extracted_fields (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_extraction_id  UUID NOT NULL REFERENCES document_extractions(id) ON DELETE CASCADE,
    document_id             UUID NOT NULL REFERENCES documents(id),

    -- Field Identity
    field_type              VARCHAR(50) NOT NULL,
    field_name              VARCHAR(100) NOT NULL,

    -- Extracted Value (polymorphic)
    value_text              TEXT,
    value_date              DATE,
    value_number            DECIMAL(18,4),
    value_boolean           BOOLEAN,
    value_json              JSONB,

    -- Confidence & Source
    confidence              DECIMAL(3,2) NOT NULL,
    extraction_method       VARCHAR(50),

    -- Position
    page_number             INTEGER,
    bounding_box            JSONB,

    -- Validation
    is_validated            BOOLEAN DEFAULT FALSE,
    validated_value         TEXT,
    validated_by            VARCHAR(50),
    validated_at            TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_extracted_fields_extraction ON extracted_fields(document_extraction_id);
CREATE INDEX idx_extracted_fields_type ON extracted_fields(field_type);
CREATE INDEX idx_extracted_fields_document ON extracted_fields(document_id);

-- 4.3 case_objects (Virtual Case Object)
CREATE TABLE case_objects (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,

    -- Version Control
    version                 INTEGER NOT NULL DEFAULT 1,
    is_current              BOOLEAN DEFAULT TRUE,

    -- The unified case object (JSON)
    case_data               JSONB NOT NULL,

    -- Processing Status
    build_status            case_build_status DEFAULT 'pending',
    build_started_at        TIMESTAMP WITH TIME ZONE,
    built_at                TIMESTAMP WITH TIME ZONE,
    build_error             TEXT,

    -- Data Quality Metrics
    completeness_score      INTEGER,
    confidence_score        INTEGER,
    uncertainties           JSONB,

    -- Field Reconciliation Summary
    field_mappings_count    INTEGER,
    exact_matches           INTEGER,
    mismatches              INTEGER,
    missing_evidence        INTEGER,

    -- Schema Info
    schema_version          VARCHAR(20),
    validation_errors       JSONB,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(application_id, version)
);

CREATE INDEX idx_case_objects_application ON case_objects(application_id);
CREATE INDEX idx_case_objects_current ON case_objects(application_id, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_case_objects_status ON case_objects(build_status);

-- 4.4 validation_reports
CREATE TABLE validation_reports (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),
    case_object_id          UUID REFERENCES case_objects(id),

    -- Tier
    tier                    VARCHAR(10) DEFAULT 'tier1',

    -- Result
    verdict                 VARCHAR(20) NOT NULL,
    rules_passed            INTEGER DEFAULT 0,
    rules_failed            INTEGER DEFAULT 0,
    rules_warned            INTEGER DEFAULT 0,
    blocking_failures       INTEGER DEFAULT 0,
    warnings_count          INTEGER DEFAULT 0,
    can_proceed_to_tier2    BOOLEAN DEFAULT FALSE,

    -- Check Details
    checks_run              JSONB,

    -- Performance
    processing_time_ms      INTEGER,

    -- Agent Info
    agent_name              VARCHAR(100),
    agent_version           VARCHAR(50),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_validation_reports_application ON validation_reports(application_id);
CREATE INDEX idx_validation_reports_verdict ON validation_reports(verdict);
CREATE INDEX idx_validation_reports_proceed ON validation_reports(can_proceed_to_tier2);

-- 4.5 fact_sheets (Tier 1 Output)
CREATE TABLE fact_sheets (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_object_id          UUID NOT NULL REFERENCES case_objects(id) ON DELETE CASCADE,
    validation_report_id    UUID NOT NULL REFERENCES validation_reports(id),
    application_id          UUID NOT NULL REFERENCES applications(id),

    -- Structured Facts
    facts                   JSONB NOT NULL,

    -- Summary Counts
    total_checks            INTEGER NOT NULL,
    passed_checks           INTEGER NOT NULL,
    failed_checks           INTEGER NOT NULL,
    warning_checks          INTEGER NOT NULL,

    -- Blockers
    has_blockers            BOOLEAN DEFAULT FALSE,
    blocker_count           INTEGER DEFAULT 0,
    blocker_summary         TEXT,

    -- Categories breakdown
    requirements_status     JSONB,
    reconciliation_status   JSONB,
    validity_status         JSONB,

    -- Open questions for Tier 2
    open_questions          JSONB,

    -- Metadata
    generated_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_fact_sheets_case ON fact_sheets(case_object_id);
CREATE INDEX idx_fact_sheets_application ON fact_sheets(application_id);
CREATE INDEX idx_fact_sheets_blockers ON fact_sheets(has_blockers) WHERE has_blockers = TRUE;

-- 4.6 legal_briefs (Condenser Agent Output)
CREATE TABLE legal_briefs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_object_id          UUID NOT NULL REFERENCES case_objects(id),
    fact_sheet_id           UUID NOT NULL REFERENCES fact_sheets(id),
    application_id          UUID NOT NULL REFERENCES applications(id),

    -- Brief Content
    brief_content           JSONB NOT NULL,

    -- Processing Status
    status                  brief_status DEFAULT 'draft',

    -- Quality Metrics
    completeness_score      DECIMAL(3,2),
    fact_count              INTEGER,
    uncertainty_count       INTEGER,

    -- Issues identified for research
    issues_to_analyze       JSONB,

    -- Metadata
    generated_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by             VARCHAR(50),
    reviewed_at             TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_legal_briefs_case ON legal_briefs(case_object_id);
CREATE INDEX idx_legal_briefs_application ON legal_briefs(application_id);
CREATE INDEX idx_legal_briefs_status ON legal_briefs(status);

-- 4.7 legal_analysis_sessions (Tier 2 Processing)
CREATE TABLE legal_analysis_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_brief_id          UUID NOT NULL REFERENCES legal_briefs(id),
    application_id          UUID NOT NULL REFERENCES applications(id),

    -- Session Info
    session_number          INTEGER NOT NULL DEFAULT 1,
    status                  analysis_status DEFAULT 'pending',

    -- Timing
    started_at              TIMESTAMP WITH TIME ZONE,
    completed_at            TIMESTAMP WITH TIME ZONE,

    -- LLM Info
    llm_model               VARCHAR(100),
    llm_version             VARCHAR(50),
    total_tokens            INTEGER,
    total_cost              DECIMAL(10,4),

    -- Workflow
    workflow_id             VARCHAR(100),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_analysis_sessions_brief ON legal_analysis_sessions(legal_brief_id);
CREATE INDEX idx_analysis_sessions_application ON legal_analysis_sessions(application_id);
CREATE INDEX idx_analysis_sessions_status ON legal_analysis_sessions(status);

-- 4.8 issue_decompositions (Tier 2 Sub-questions)
CREATE TABLE issue_decompositions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_session_id     UUID NOT NULL REFERENCES legal_analysis_sessions(id) ON DELETE CASCADE,

    -- Issue Identity
    issue_id                VARCHAR(50) NOT NULL,
    issue_category          issue_category NOT NULL,

    -- Question
    question                TEXT NOT NULL,
    sub_questions           JSONB,

    -- Priority
    priority                INTEGER DEFAULT 1,

    -- Status
    research_status         research_status DEFAULT 'pending',

    -- Research Results
    finding                 VARCHAR(30),
    confidence              DECIMAL(3,2),
    analysis_text           TEXT,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at            TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_issue_decompositions_session ON issue_decompositions(analysis_session_id);
CREATE INDEX idx_issue_decompositions_category ON issue_decompositions(issue_category);

-- 4.9 retrieved_evidence (RAG Results)
CREATE TABLE retrieved_evidence (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_decomposition_id  UUID NOT NULL REFERENCES issue_decompositions(id) ON DELETE CASCADE,

    -- Source Article
    article_number          INTEGER NOT NULL REFERENCES articles(article_number),

    -- Retrieval Info
    query_text              TEXT NOT NULL,
    similarity_score        DECIMAL(4,3) NOT NULL,
    retrieval_rank          INTEGER NOT NULL,

    -- Extracted Chunk
    chunk_text              TEXT NOT NULL,
    chunk_start             INTEGER,
    chunk_end               INTEGER,

    -- Relevance Assessment
    is_relevant             BOOLEAN,
    relevance_score         DECIMAL(3,2),
    relevance_reason        TEXT,

    -- Usage
    used_in_analysis        BOOLEAN DEFAULT FALSE,
    cited_in_opinion        BOOLEAN DEFAULT FALSE,

    -- Metadata
    retrieved_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_retrieved_evidence_issue ON retrieved_evidence(issue_decomposition_id);
CREATE INDEX idx_retrieved_evidence_article ON retrieved_evidence(article_number);
CREATE INDEX idx_retrieved_evidence_relevant ON retrieved_evidence(is_relevant) WHERE is_relevant = TRUE;

-- 4.10 research_traces
CREATE TABLE research_traces (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),
    analysis_session_id     UUID REFERENCES legal_analysis_sessions(id),

    -- Phase
    phase                   VARCHAR(50),

    -- Agent Info
    agent_name              VARCHAR(100),
    workflow_id             VARCHAR(100),

    -- Trace Data
    trace_data              JSONB,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_research_traces_application ON research_traces(application_id);
CREATE INDEX idx_research_traces_session ON research_traces(analysis_session_id);

-- 4.11 legal_opinions
CREATE TABLE legal_opinions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),
    legal_brief_id          UUID REFERENCES legal_briefs(id),
    analysis_session_id     UUID REFERENCES legal_analysis_sessions(id),

    -- Finding
    finding                 VARCHAR(30) NOT NULL,
    confidence_score        DECIMAL(3,2),
    confidence_level        VARCHAR(10),

    -- Content
    summary_ar              TEXT,
    summary_en              TEXT,
    full_analysis           JSONB,

    -- Issues
    concerns                JSONB,
    recommendations         JSONB,

    -- Citations (denormalized)
    legal_citations         JSONB,

    -- Verification Metrics
    grounding_score         DECIMAL(3,2),
    retrieval_coverage      DECIMAL(3,2),
    stability_score         DECIMAL(3,2),

    -- Flags
    has_contradictions      BOOLEAN DEFAULT FALSE,
    needs_escalation        BOOLEAN DEFAULT FALSE,
    escalation_reason       TEXT,

    -- Agent Info
    agent_name              VARCHAR(100),
    research_trace_id       UUID REFERENCES research_traces(id),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_legal_opinions_application ON legal_opinions(application_id);
CREATE INDEX idx_legal_opinions_finding ON legal_opinions(finding);
CREATE INDEX idx_legal_opinions_escalation ON legal_opinions(needs_escalation) WHERE needs_escalation = TRUE;

-- 4.12 citations
CREATE TABLE citations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_opinion_id        UUID NOT NULL REFERENCES legal_opinions(id) ON DELETE CASCADE,

    -- Citation Target
    article_number          INTEGER NOT NULL REFERENCES articles(article_number),

    -- Citation Details
    claim_text              TEXT NOT NULL,
    article_text            TEXT NOT NULL,
    article_span_start      INTEGER,
    article_span_end        INTEGER,

    -- Context
    issue_category          issue_category,
    retrieved_evidence_id   UUID REFERENCES retrieved_evidence(id),

    -- Verification
    is_verified             BOOLEAN DEFAULT FALSE,
    verification_method     VARCHAR(50),
    verification_score      DECIMAL(3,2),

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_citations_opinion ON citations(legal_opinion_id);
CREATE INDEX idx_citations_article ON citations(article_number);
CREATE INDEX idx_citations_verified ON citations(is_verified);

-- 4.13 risk_scores
CREATE TABLE risk_scores (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),
    case_object_id          UUID REFERENCES case_objects(id),

    -- Input References
    validation_report_id    UUID REFERENCES validation_reports(id),
    legal_opinion_id        UUID REFERENCES legal_opinions(id),

    -- Component Scores (0-100)
    extraction_completeness INTEGER NOT NULL,
    tier1_score             INTEGER NOT NULL,
    brief_integrity         INTEGER,
    grounding_score         INTEGER,
    stability_score         INTEGER,
    retrieval_success       INTEGER,

    -- Composite Score
    composite_score         INTEGER NOT NULL,

    -- Risk Level
    risk_level              risk_level NOT NULL,

    -- Reason Codes
    reason_codes            VARCHAR(50)[] NOT NULL,

    -- Metadata
    calculated_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_risk_scores_application ON risk_scores(application_id);
CREATE INDEX idx_risk_scores_level ON risk_scores(risk_level);

-- 4.14 routing_decisions
CREATE TABLE routing_decisions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),
    risk_score_id           UUID NOT NULL REFERENCES risk_scores(id),

    -- Decision
    decision                routing_decision_type NOT NULL,
    decision_bucket         decision_bucket NOT NULL,

    -- Routing Target
    routed_to               routing_target NOT NULL,
    routed_to_employee_id   VARCHAR(50),
    routed_to_queue         VARCHAR(100),

    -- Conditions
    conditions_to_meet      JSONB,
    remediations_required   JSONB,

    -- Flags
    requires_sme            BOOLEAN DEFAULT FALSE,
    sme_reason              TEXT,

    -- Metadata
    decided_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decided_by              VARCHAR(50) DEFAULT 'system'
);

CREATE INDEX idx_routing_decisions_application ON routing_decisions(application_id);
CREATE INDEX idx_routing_decisions_decision ON routing_decisions(decision);
CREATE INDEX idx_routing_decisions_target ON routing_decisions(routed_to);

-- 4.15 escalations
CREATE TABLE escalations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id          UUID NOT NULL REFERENCES applications(id),

    -- Source
    tier                    VARCHAR(20),
    reason                  TEXT NOT NULL,

    -- References
    validation_report_id    UUID REFERENCES validation_reports(id),
    legal_opinion_id        UUID REFERENCES legal_opinions(id),
    routing_decision_id     UUID REFERENCES routing_decisions(id),

    -- Context
    confidence_at_escalation DECIMAL(3,2),
    risk_level_at_escalation risk_level,

    -- Status
    status                  VARCHAR(20) DEFAULT 'pending',
    priority                VARCHAR(20) DEFAULT 'standard',

    -- Assignment
    assigned_to             VARCHAR(50),
    assigned_at             TIMESTAMP WITH TIME ZONE,

    -- Resolution
    sme_decision            TEXT,
    sme_notes               TEXT,
    resolved_by             VARCHAR(50),
    resolved_at             TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_escalations_application ON escalations(application_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_priority ON escalations(priority);
CREATE INDEX idx_escalations_assigned ON escalations(assigned_to) WHERE assigned_to IS NOT NULL;

-- ============================================================================
-- STEP 5: COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE applications IS 'Main POA/Sale application records. Data landing zone from SAK system.';
COMMENT ON TABLE parties IS 'Parties involved in applications. Direct link (no junction table). Supports dual terminology: party_type (positional) + party_role (functional).';
COMMENT ON TABLE capacity_proofs IS 'Proof of capacity for each party. Merged from old poa_extractions - now supports POA + Sale transactions.';
COMMENT ON TABLE capacity_principals IS 'Principals/wards linked to capacity proofs (for agents, guardians, trustees).';
COMMENT ON TABLE documents IS 'Uploaded documents (renamed from attachments). Supports user-selected type + ML classification.';
COMMENT ON TABLE document_extractions IS 'OCR and field extraction results from documents.';
COMMENT ON TABLE case_objects IS 'Virtual Case Object - unified JSON representation combining SQL data + extracted evidence.';
COMMENT ON TABLE fact_sheets IS 'Tier 1 output - structured facts with blockers and open questions for Tier 2.';
COMMENT ON TABLE legal_briefs IS 'Condenser Agent output - high-density artifact for Tier 2 legal reasoning.';
COMMENT ON TABLE legal_analysis_sessions IS 'Tracks individual Tier 2 analysis runs with LLM info and timing.';
COMMENT ON TABLE issue_decompositions IS 'Sub-questions generated by Decomposer for legal research.';
COMMENT ON TABLE retrieved_evidence IS 'RAG results - evidence retrieved from legal corpus for each issue.';
COMMENT ON TABLE legal_opinions IS 'Final Tier 2 legal research opinions with verification metrics.';
COMMENT ON TABLE citations IS 'Links claims in legal opinions to article evidence.';
COMMENT ON TABLE risk_scores IS 'Composite risk calculation for routing decisions.';
COMMENT ON TABLE routing_decisions IS 'Final routing based on risk scores.';
COMMENT ON TABLE escalations IS 'Cases requiring human review.';
COMMENT ON TABLE articles IS 'Legal corpus articles for RAG-based retrieval. Used by retrieved_evidence and citations.';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
--
-- TABLES CREATED:
--
--   Reference (5):
--     - transaction_types (10 rows seeded)
--     - transaction_configs
--     - capacity_configurations (14 rows seeded)
--     - attachment_types (12 rows seeded)
--     - template_definitions
--     - articles (legal corpus - empty, populate separately)
--
--   Core (8):
--     - applications
--     - parties
--     - capacity_proofs
--     - capacity_principals
--     - documents
--     - document_extractions
--     - poa_templates
--     - duplicate_checks
--
--   ML Pipeline (13):
--     - document_classifications
--     - extracted_fields
--     - case_objects
--     - validation_reports
--     - fact_sheets
--     - legal_briefs
--     - legal_analysis_sessions
--     - issue_decompositions
--     - retrieved_evidence
--     - research_traces
--     - legal_opinions
--     - citations
--     - risk_scores
--     - routing_decisions
--     - escalations
--
-- TOTAL: 27 tables + 24 enums
-- ============================================================================
