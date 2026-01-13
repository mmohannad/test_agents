"""
Shared Pydantic models for POA validation agents.

This module contains:
- Enums for status/category types
- Data models for database entities
- Tier 1 validation models
- Tier 2 legal research models (Condenser + Legal Search)
- Case Bundle for orchestration
"""

from datetime import date, datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class PartyPosition(str, Enum):
    GRANTOR = "grantor"
    AGENT = "agent"
    GRANTOR_REPRESENTATIVE = "grantor_representative"
    BENEFICIARY = "beneficiary"
    WITNESS = "witness"
    ORIGINAL_PRINCIPAL = "original_principal"
    BUYER = "buyer"
    BUYER_REPRESENTATIVE = "buyer_representative"
    SELLER = "seller"


class Tier1CheckCategory(str, Enum):
    FIELD_COMPLETENESS = "field_completeness"
    FORMAT_VALIDATION = "format_validation"
    CROSS_FIELD_LOGIC = "cross_field_logic"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DOCUMENT_MATCHING = "document_matching"
    BUSINESS_RULES = "business_rules"


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class Severity(str, Enum):
    BLOCKING = "BLOCKING"
    NON_BLOCKING = "NON_BLOCKING"


class LegalFinding(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    VALID_WITH_CONDITIONS = "VALID_WITH_CONDITIONS"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    INCONCLUSIVE = "INCONCLUSIVE"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================================
# Data Models - Database Entities
# ============================================================================

class PersonalParty(BaseModel):
    """A party (individual or entity) in an application."""
    id: str
    qid: Optional[str] = None
    name_ar: Optional[str] = None
    name_en: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_entity: bool = False
    entity_type: Optional[str] = None


class ApplicationPartyRole(BaseModel):
    """A party's role in an application."""
    id: str
    application_id: str
    personal_party_id: str
    party_position: str
    party_order: int = 1
    role_code: Optional[str] = None
    capacity_fields: dict = Field(default_factory=dict)
    capacity_verified: bool = False
    capacity_verification_notes: Optional[str] = None
    # Joined data
    personal_party: Optional[PersonalParty] = None


class Attachment(BaseModel):
    """An uploaded document."""
    id: str
    application_id: str
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    document_type_code: Optional[str] = None
    document_type_confidence: Optional[float] = None
    uploaded_by_party_role_id: Optional[str] = None
    ocr_status: str = "pending"
    ocr_processed_at: Optional[datetime] = None
    # Joined data
    document_extractions: list["DocumentExtraction"] = Field(default_factory=list)


class DocumentExtraction(BaseModel):
    """OCR extraction results for a document."""
    id: str
    attachment_id: str
    extraction_model: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None
    confidence_overall: Optional[float] = None
    raw_text_ar: Optional[str] = None
    raw_text_en: Optional[str] = None
    extracted_fields: dict = Field(default_factory=dict)
    field_confidences: dict = Field(default_factory=dict)
    bounding_boxes: dict = Field(default_factory=dict)


class POAExtraction(BaseModel):
    """Structured extraction of POA-specific fields."""
    id: str
    attachment_id: Optional[str] = None
    application_id: Optional[str] = None
    poa_number: Optional[str] = None
    poa_date: Optional[date] = None
    poa_expiry: Optional[date] = None
    issuing_authority: Optional[str] = None
    principal_name_ar: Optional[str] = None
    principal_name_en: Optional[str] = None
    principal_qid: Optional[str] = None
    agent_name_ar: Optional[str] = None
    agent_name_en: Optional[str] = None
    agent_qid: Optional[str] = None
    granted_powers: list[str] = Field(default_factory=list)
    granted_powers_en: list[str] = Field(default_factory=list)
    is_general_poa: bool = False
    is_special_poa: bool = False
    has_substitution_right: bool = False
    full_text_ar: Optional[str] = None
    full_text_en: Optional[str] = None


class Application(BaseModel):
    """A POA application with all related data."""
    id: str
    sak_case_number: Optional[str] = None
    status: str = "pending"
    transaction_type_code: Optional[str] = None
    transaction_value: Optional[float] = None
    transaction_subject_ar: Optional[str] = None
    transaction_subject_en: Optional[str] = None
    submitted_by: Optional[str] = None
    processing_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Related data
    party_roles: list[ApplicationPartyRole] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    poa_extractions: list[POAExtraction] = Field(default_factory=list)


class TransactionConfig(BaseModel):
    """Configuration for a transaction type."""
    id: int
    transaction_type_code: str
    required_parties: list[dict] = Field(default_factory=list)
    required_documents: list[dict] = Field(default_factory=list)
    optional_documents: list[dict] = Field(default_factory=list)
    tier1_checks: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    is_active: bool = True


# ============================================================================
# Tier 1 Validation Models
# ============================================================================

class Tier1CheckResult(BaseModel):
    """Result of a single Tier 1 check."""
    category: Tier1CheckCategory
    status: CheckStatus
    severity: Severity = Severity.NON_BLOCKING
    details: Optional[dict] = None
    message: Optional[str] = None


class Tier1ValidationResult(BaseModel):
    """Complete Tier 1 validation result."""
    application_id: str
    overall_status: Literal["PASS", "FAIL", "WARNINGS"]
    checks: list[Tier1CheckResult]
    blocking_failures: int = 0
    warnings: int = 0
    can_proceed_to_tier2: bool = False
    execution_time_ms: Optional[int] = None


# ============================================================================
# Tier 2 Legal Research Models
# ============================================================================

class SubQuestion(BaseModel):
    """A decomposed legal sub-question."""
    id: str
    category: str  # e.g., "GRANTOR_CAPACITY", "AGENT_CAPACITY"
    question: str
    relevant_facts: list[str] = Field(default_factory=list)
    legal_areas: list[str] = Field(default_factory=list)
    priority: Literal["critical", "important", "supplementary"] = "important"


class ArticleCitation(BaseModel):
    """A citation to a legal article."""
    article_number: int
    text_snippet: Optional[str] = None
    relevance: Optional[str] = None


class SubQuestionFinding(BaseModel):
    """Finding for a single sub-question."""
    sub_question_id: str
    finding: Literal["SUPPORTED", "NOT_SUPPORTED", "UNCLEAR", "NEEDS_MORE_INFO"]
    confidence: float  # 0.0 - 1.0
    analysis_text: str
    legal_basis: list[ArticleCitation] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_question: Optional[str] = None


class LegalOpinion(BaseModel):
    """Complete Tier 2 legal opinion."""
    application_id: str
    finding: LegalFinding
    confidence: float  # 0.0 - 1.0
    confidence_level: ConfidenceLevel
    analysis: dict[str, SubQuestionFinding] = Field(default_factory=dict)
    concerns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    legal_citations: list[ArticleCitation] = Field(default_factory=list)
    opinion_text: str = ""


# ============================================================================
# Case Bundle
# ============================================================================

class CaseBundle(BaseModel):
    """
    Complete information package for Tier 2 legal reasoning.
    Assembled by orchestrator from application data + Tier 1 results.
    """
    application: Application
    tier1_result: Tier1ValidationResult
    transaction_config: Optional[TransactionConfig] = None

    # Convenience accessors
    @property
    def grantors(self) -> list[ApplicationPartyRole]:
        return [r for r in self.application.party_roles if r.party_position == "grantor"]

    @property
    def agents(self) -> list[ApplicationPartyRole]:
        return [r for r in self.application.party_roles if r.party_position == "agent"]

    @property
    def poa_extraction(self) -> Optional[POAExtraction]:
        return self.application.poa_extractions[0] if self.application.poa_extractions else None

    def to_summary(self) -> str:
        """Generate a text summary of the case for LLM context."""
        poa = self.poa_extraction

        grantors_text = "\n".join([
            f"  - {r.personal_party.name_en or r.personal_party.name_ar} (QID: {r.personal_party.qid}, Role: {r.role_code})"
            for r in self.grantors if r.personal_party
        ])

        agents_text = "\n".join([
            f"  - {r.personal_party.name_en or r.personal_party.name_ar} (QID: {r.personal_party.qid}, Role: {r.role_code})"
            for r in self.agents if r.personal_party
        ])

        powers_text = "\n".join([f"  - {p}" for p in (poa.granted_powers_en if poa else [])])

        return f"""
=== CASE BUNDLE SUMMARY ===

Application ID: {self.application.id}
Case Number: {self.application.sak_case_number}
Transaction Type: {self.application.transaction_type_code}
Transaction Value: {self.application.transaction_value or "N/A"}

Subject (EN): {self.application.transaction_subject_en}
Subject (AR): {self.application.transaction_subject_ar}

GRANTORS:
{grantors_text or "  None"}

AGENTS:
{agents_text or "  None"}

POA DETAILS:
  Type: {"General" if poa and poa.is_general_poa else "Special" if poa and poa.is_special_poa else "Unknown"}
  POA Number: {poa.poa_number if poa else "N/A"}
  Issue Date: {poa.poa_date if poa else "N/A"}
  Expiry Date: {poa.poa_expiry if poa else "N/A"}
  Substitution Allowed: {poa.has_substitution_right if poa else "Unknown"}

GRANTED POWERS:
{powers_text or "  Not specified"}

TIER 1 VALIDATION:
  Status: {self.tier1_result.overall_status}
  Blocking Failures: {self.tier1_result.blocking_failures}
  Warnings: {self.tier1_result.warnings}

ATTACHMENTS:
  Total: {len(self.application.attachments)}
  Types: {", ".join(set(a.document_type_code or "Unknown" for a in self.application.attachments))}

=== END SUMMARY ===
"""


# ============================================================================
# Condenser Agent Models (Legal Brief)
# ============================================================================

class IssueCategory(str, Enum):
    """Categories of legal issues to analyze."""
    GRANTOR_CAPACITY = "grantor_capacity"
    AGENT_CAPACITY = "agent_capacity"
    POA_SCOPE = "poa_scope"
    SUBSTITUTION_RIGHTS = "substitution_rights"
    FORMALITIES = "formalities"
    VALIDITY = "validity"
    COMPLIANCE = "compliance"
    BUSINESS_RULES = "business_rules"


class PartyFact(BaseModel):
    """Structured facts about a party."""
    name_ar: str
    name_en: Optional[str] = None
    qid: str
    nationality: Optional[str] = None
    role: str  # grantor, agent, etc.
    capacity_type: Optional[str] = None
    capacity_source: Optional[str] = None  # Where capacity was verified (CR, ID, etc.)


class CompanyFact(BaseModel):
    """Structured facts about a company."""
    name_ar: str
    name_en: Optional[str] = None
    cr_number: str
    managers: list[dict] = Field(default_factory=list)  # List of managers with their authorities


class AuthorityFact(BaseModel):
    """Facts about authority/capacity."""
    grantor_authority_claimed: str  # What grantor claims
    grantor_authority_per_evidence: str  # What evidence shows
    authority_match: bool  # Do they match?
    authority_gap: Optional[str] = None  # Description of gap if any


class PowersFact(BaseModel):
    """Facts about powers being granted."""
    powers_requested: list[str] = Field(default_factory=list)
    powers_in_scope: list[str] = Field(default_factory=list)  # Powers within grantor's authority
    powers_out_of_scope: list[str] = Field(default_factory=list)  # Powers beyond grantor's authority


class OpenQuestion(BaseModel):
    """A question for Tier 2 legal research."""
    question_id: str
    category: IssueCategory
    question: str
    relevant_facts: list[str] = Field(default_factory=list)
    priority: Literal["critical", "important", "supplementary"] = "important"


class LegalBrief(BaseModel):
    """
    Output from the Condenser Agent.
    High-density artifact for Tier 2 legal reasoning.
    """
    application_id: str
    case_object_id: str

    # Structured Facts
    grantor: PartyFact
    agent: PartyFact
    company: Optional[CompanyFact] = None
    authority_facts: AuthorityFact
    powers_facts: PowersFact

    # Tier 1 Summary
    tier1_status: str
    tier1_warnings: list[str] = Field(default_factory=list)

    # Key Discrepancies
    discrepancies: list[dict] = Field(default_factory=list)

    # Questions for Tier 2
    open_questions: list[OpenQuestion] = Field(default_factory=list)

    # Raw case context
    poa_text_ar: Optional[str] = None
    poa_text_en: Optional[str] = None

    # Metadata
    generated_at: Optional[datetime] = None
    confidence_score: float = 0.0


# ============================================================================
# Legal Search Agent Models
# ============================================================================

class LegalIssue(BaseModel):
    """A decomposed legal issue to research."""
    issue_id: str
    category: IssueCategory
    primary_question: str
    sub_questions: list[str] = Field(default_factory=list)
    relevant_facts: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)  # Generated search queries
    priority: int = 1  # 1 = highest priority


class RetrievedArticle(BaseModel):
    """An article retrieved from the legal corpus."""
    article_number: int
    law_name: Optional[str] = None
    text_ar: Optional[str] = None
    text_en: Optional[str] = None
    similarity_score: float
    relevance_assessment: Optional[str] = None


class IssueFinding(BaseModel):
    """Finding for a single legal issue."""
    issue_id: str
    category: IssueCategory
    finding: Literal["SUPPORTED", "NOT_SUPPORTED", "PARTIALLY_SUPPORTED", "UNCLEAR"]
    confidence: float  # 0.0 - 1.0
    reasoning: str
    supporting_articles: list[RetrievedArticle] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class LegalResearchResult(BaseModel):
    """
    Complete output from Legal Search Agent.
    """
    application_id: str
    legal_brief_id: str

    # Decomposition
    issues_analyzed: list[LegalIssue] = Field(default_factory=list)

    # Findings per issue
    findings: list[IssueFinding] = Field(default_factory=list)

    # Overall Opinion
    overall_finding: LegalFinding
    confidence_score: float
    confidence_level: ConfidenceLevel

    # Decision
    decision_bucket: Literal["valid", "valid_with_remediations", "invalid", "needs_review"]

    # Opinion Text
    opinion_summary_ar: Optional[str] = None
    opinion_summary_en: Optional[str] = None
    detailed_analysis: str = ""

    # Citations
    all_citations: list[RetrievedArticle] = Field(default_factory=list)

    # Recommendations
    concerns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)  # If valid_with_remediations

    # Verification Metrics
    grounding_score: float = 0.0  # % of claims with citations
    retrieval_coverage: float = 0.0  # % of issues with relevant articles

    # Metadata
    generated_at: Optional[datetime] = None
    llm_model: Optional[str] = None
    total_tokens: Optional[int] = None

