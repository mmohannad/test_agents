# POA Legal Reasoning Agent - Implementation Design Document

## Executive Summary

Transform the current simple semantic search agent into a **POA (Power of Attorney) Validation System** that performs legal reasoning to determine if a POA is sufficient for a given transaction.

---

## Current State vs. Target State

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| **Input** | Free-text question | Structured application data + OCR-extracted POA |
| **Processing** | Semantic search → LLM response | Legal rule matching → Structured reasoning |
| **Output** | Free-text answer | Structured verdict + citations + remediation |
| **Knowledge Base** | Civil Code articles | Civil Code + Commercial Law + SAK Manual |
| **Confidence** | None | Calibrated confidence score |
| **Routing** | None | PASS / BLOCKED / NEEDS_SME_REVIEW |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POA VALIDATION AGENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │  INPUT      │    │  REASONING  │    │  KNOWLEDGE  │    │  OUTPUT     │ │
│   │  PROCESSOR  │───▶│  ENGINE     │◀──▶│  BASE       │───▶│  GENERATOR  │ │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │                  │         │
│         ▼                  ▼                  ▼                  ▼         │
│   - Application      - Rule matching    - Civil Code       - Verdict      │
│     data parsing     - Scope analysis   - Commercial Law   - Citations    │
│   - OCR extraction   - Temporal check   - SAK Manual       - Remediation  │
│     parsing          - Confidence calc  - Precedents       - Templates    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Input Schema

### 1. Application Data (from SAK system)

```python
class ApplicationData(BaseModel):
    """Structured data from the SAK application form."""
    
    # Transaction details
    transaction_type: TransactionType  # Enum: SALE_OF_SHARES, LITIGATION, PROPERTY_SALE, etc.
    transaction_value: Optional[float] = None  # In QAR
    transaction_subject: str  # e.g., "25% shares of XYZ Trading Co."
    
    # Parties
    first_party: Party
    second_party: Optional[Party] = None
    
    # POA reference
    poa_reference_number: str
    agent_claimed_capacity: str  # e.g., "Agent under POA #12345"

class Party(BaseModel):
    name: str
    qid: str  # Qatar ID
    capacity: str  # e.g., "Principal", "Agent", "Buyer", "Seller"

class TransactionType(str, Enum):
    SALE_OF_SHARES = "sale_of_shares"
    PROPERTY_SALE = "property_sale"
    PROPERTY_PURCHASE = "property_purchase"
    LITIGATION = "litigation"
    COMPANY_REGISTRATION = "company_registration"
    CONTRACT_SIGNING = "contract_signing"
    LOAN_AGREEMENT = "loan_agreement"
    GENERAL_REPRESENTATION = "general_representation"
    # ... more types
```

### 2. OCR Extraction Data (from POA document)

```python
class POAExtraction(BaseModel):
    """Data extracted from POA document via OCR."""
    
    # Document metadata
    poa_number: str
    poa_date: date
    poa_expiry: Optional[date] = None  # None if no expiry stated
    issuing_authority: Optional[str] = None
    
    # Parties in the POA
    principal_name_ar: str
    principal_name_en: Optional[str] = None
    principal_qid: str
    
    agent_name_ar: str
    agent_name_en: Optional[str] = None
    agent_qid: str
    
    # The core legal content
    granted_powers: List[str]  # List of Arabic phrases describing powers
    granted_powers_translated: List[str]  # English translations
    
    # Special clauses
    is_general_poa: bool  # توكيل عام vs توكيل خاص
    has_substitution_right: bool  # Can agent delegate to someone else?
    geographic_scope: Optional[str] = None  # Limited to Qatar? International?
    
    # Raw text for reference
    full_text_ar: str
    full_text_en: Optional[str] = None
```

### 3. Combined Input

```python
class POAValidationRequest(BaseModel):
    """Complete input to the POA validation agent."""
    
    application: ApplicationData
    poa_document: POAExtraction
    
    # Context
    request_timestamp: datetime
    notary_id: Optional[str] = None
    urgency: str = "normal"  # normal, urgent, express
```

---

## Output Schema

```python
class POAValidationResult(BaseModel):
    """Structured output from the POA validation agent."""
    
    # Core verdict
    verdict: Verdict  # PASS, BLOCKED, NEEDS_SME_REVIEW
    confidence: float  # 0.0 to 1.0
    
    # Issue details (if not PASS)
    primary_issue: Optional[ValidationIssue] = None
    secondary_issues: List[ValidationIssue] = []
    
    # Legal backing
    legal_basis: List[LegalCitation]
    
    # What to do next
    remediation: Optional[Remediation] = None
    
    # Metadata
    processing_time_ms: int
    reasoning_trace: List[ReasoningStep]  # For auditability

class Verdict(str, Enum):
    PASS = "pass"  # POA is sufficient, proceed
    BLOCKED = "blocked"  # POA is insufficient, reject
    NEEDS_SME_REVIEW = "needs_sme_review"  # Uncertain, escalate

class ValidationIssue(BaseModel):
    code: str  # e.g., "POA_SCOPE_INSUFFICIENT", "POA_EXPIRED"
    title_ar: str
    title_en: str
    explanation_ar: str
    explanation_en: str
    severity: str  # "blocking", "warning", "info"

class LegalCitation(BaseModel):
    source: str  # "Civil Code", "Commercial Law", "SAK Manual"
    article_or_section: str  # "714", "4.3.2"
    text_ar: str
    text_en: str
    relevance: str  # Why this citation matters

class Remediation(BaseModel):
    action: str  # "REJECT", "REQUEST_AMENDMENT", "APPROVE_WITH_CONDITIONS"
    steps: List[RemediationStep]
    template_text_ar: Optional[str] = None
    template_text_en: Optional[str] = None

class RemediationStep(BaseModel):
    step_number: int
    instruction_ar: str
    instruction_en: str
    sak_navigation: Optional[str] = None  # UI guidance

class ReasoningStep(BaseModel):
    """For audit trail and explainability."""
    step_name: str
    input_facts: dict
    rule_applied: str
    evaluation: str
    result: str
```

---

## Knowledge Base Structure

### Current: Civil Code Articles (1,148 articles)
- `article_number`: INT
- `hierarchy_path`: JSONB (section, book, chapter structure)
- `text_arabic`: TEXT
- `text_english`: TEXT
- `embedding`: VECTOR(1536)
- `arabic_embedding`: VECTOR(1536)

### To Add: Transaction Requirements Table

```sql
CREATE TABLE transaction_requirements (
    id SERIAL PRIMARY KEY,
    transaction_type VARCHAR(100),  -- SALE_OF_SHARES, LITIGATION, etc.
    
    -- What this transaction legally requires
    required_poa_type VARCHAR(50),  -- "special" or "general_sufficient"
    required_keywords_ar TEXT[],    -- Must contain these Arabic phrases
    required_keywords_en TEXT[],    -- English equivalents
    
    -- Legal basis
    primary_law_source VARCHAR(100),
    primary_article VARCHAR(20),
    
    -- Value thresholds
    value_threshold_qar DECIMAL,    -- Above this, stricter requirements
    
    -- Additional checks
    requires_explicit_mention BOOLEAN,
    is_act_of_disposition BOOLEAN,  -- تصرف vs إدارة
    
    -- Embedding for semantic matching
    description_embedding VECTOR(1536)
);
```

### To Add: POA Validation Rules Table

```sql
CREATE TABLE poa_validation_rules (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE,   -- "CIVIL_CODE_714", "SAK_4_3_2"
    
    -- Rule definition
    source VARCHAR(100),            -- "Civil Code", "SAK Manual"
    article_or_section VARCHAR(50),
    rule_text_ar TEXT,
    rule_text_en TEXT,
    
    -- Applicability
    applies_to_transaction_types TEXT[],  -- Which transaction types
    
    -- Logic
    condition_type VARCHAR(50),     -- "SCOPE_CHECK", "TEMPORAL_CHECK", "KEYWORD_REQUIRED"
    condition_params JSONB,         -- Parameters for the check
    
    -- Embedding for retrieval
    rule_embedding VECTOR(1536)
);
```

### To Add: SAK Manual Sections

```sql
CREATE TABLE sak_manual_sections (
    id SERIAL PRIMARY KEY,
    section_number VARCHAR(20),
    title_ar TEXT,
    title_en TEXT,
    content_ar TEXT,
    content_en TEXT,
    
    -- Categorization
    chapter VARCHAR(50),
    topic VARCHAR(100),
    
    -- Embedding
    embedding VECTOR(1536)
);
```

---

## Reasoning Engine Logic

### Step 1: Determine Transaction Requirements

```python
async def determine_requirements(
    transaction_type: TransactionType,
    transaction_value: float
) -> TransactionRequirements:
    """
    Given a transaction type and value, determine what the POA must contain.
    """
    # 1. Look up base requirements for this transaction type
    base_req = await db.query("""
        SELECT * FROM transaction_requirements
        WHERE transaction_type = $1
    """, transaction_type.value)
    
    # 2. Check if value triggers additional requirements
    if transaction_value and base_req.value_threshold_qar:
        if transaction_value > base_req.value_threshold_qar:
            # Higher scrutiny needed
            base_req.requires_explicit_mention = True
    
    # 3. Retrieve relevant legal rules
    rules = await retrieve_applicable_rules(transaction_type)
    
    return TransactionRequirements(
        poa_type_required=base_req.required_poa_type,
        required_keywords=base_req.required_keywords_ar,
        is_disposition=base_req.is_act_of_disposition,
        applicable_rules=rules
    )
```

### Step 2: Analyze POA Powers

```python
async def analyze_poa_powers(
    granted_powers: List[str],
    requirements: TransactionRequirements
) -> PowerAnalysis:
    """
    Check if the POA's granted powers satisfy the requirements.
    """
    analysis = PowerAnalysis()
    
    # 1. Keyword matching
    for required_keyword in requirements.required_keywords:
        found = any(required_keyword in power for power in granted_powers)
        analysis.keyword_matches[required_keyword] = found
    
    # 2. Semantic similarity check
    # For powers that don't exactly match, check semantic similarity
    for power in granted_powers:
        power_embedding = await llm_client.get_embedding(power)
        
        for req_keyword in requirements.required_keywords:
            if not analysis.keyword_matches[req_keyword]:
                req_embedding = await llm_client.get_embedding(req_keyword)
                similarity = cosine_similarity(power_embedding, req_embedding)
                if similarity > 0.8:
                    analysis.semantic_matches[req_keyword] = (power, similarity)
    
    # 3. General vs Special POA check
    if requirements.poa_type_required == "special":
        if poa.is_general_poa:
            analysis.issues.append("GENERAL_POA_FOR_SPECIAL_TRANSACTION")
    
    # 4. Act of disposition check (Article 714)
    if requirements.is_disposition:
        disposition_keywords = ["بيع", "تصرف", "نقل الملكية", "التنازل"]
        has_disposition_authority = any(
            kw in " ".join(granted_powers) for kw in disposition_keywords
        )
        if not has_disposition_authority:
            analysis.issues.append("NO_DISPOSITION_AUTHORITY")
    
    return analysis
```

### Step 3: Apply Legal Rules

```python
async def apply_legal_rules(
    poa: POAExtraction,
    requirements: TransactionRequirements,
    power_analysis: PowerAnalysis
) -> List[RuleEvaluation]:
    """
    Apply each relevant legal rule to the facts.
    """
    evaluations = []
    
    for rule in requirements.applicable_rules:
        eval_result = RuleEvaluation(rule=rule)
        
        if rule.condition_type == "SCOPE_CHECK":
            # Check if POA scope covers the transaction
            eval_result.passed = len(power_analysis.issues) == 0
            eval_result.explanation = (
                "POA scope is sufficient" if eval_result.passed 
                else f"POA scope insufficient: {power_analysis.issues}"
            )
            
        elif rule.condition_type == "TEMPORAL_CHECK":
            # Check if POA is still valid
            if poa.poa_expiry and poa.poa_expiry < date.today():
                eval_result.passed = False
                eval_result.explanation = f"POA expired on {poa.poa_expiry}"
            else:
                eval_result.passed = True
                eval_result.explanation = "POA is temporally valid"
                
        elif rule.condition_type == "KEYWORD_REQUIRED":
            # Check for specific required keywords
            required_kw = rule.condition_params.get("keyword")
            eval_result.passed = required_kw in " ".join(poa.granted_powers)
            eval_result.explanation = (
                f"Required keyword '{required_kw}' found" if eval_result.passed
                else f"Required keyword '{required_kw}' not found in POA"
            )
        
        evaluations.append(eval_result)
    
    return evaluations
```

### Step 4: Calculate Confidence & Verdict

```python
def calculate_verdict(
    rule_evaluations: List[RuleEvaluation],
    power_analysis: PowerAnalysis
) -> Tuple[Verdict, float]:
    """
    Determine final verdict and confidence score.
    """
    total_rules = len(rule_evaluations)
    passed_rules = sum(1 for e in rule_evaluations if e.passed)
    failed_rules = [e for e in rule_evaluations if not e.passed]
    
    # Base confidence from rule pass rate
    base_confidence = passed_rules / total_rules if total_rules > 0 else 0.5
    
    # Adjust for semantic matches (less certain than exact matches)
    if power_analysis.semantic_matches:
        # Some matches were semantic, not exact - reduce confidence
        semantic_penalty = len(power_analysis.semantic_matches) * 0.05
        base_confidence -= semantic_penalty
    
    # Determine verdict
    if len(failed_rules) == 0 and base_confidence >= 0.85:
        return Verdict.PASS, min(base_confidence, 0.99)
    
    elif any(e.rule.source == "Civil Code" for e in failed_rules):
        # Hard legal requirement failed - blocked
        return Verdict.BLOCKED, max(base_confidence, 0.85)
    
    elif base_confidence < 0.85:
        # Uncertain - needs human review
        return Verdict.NEEDS_SME_REVIEW, base_confidence
    
    else:
        return Verdict.BLOCKED, base_confidence
```

---

## Implementation Phases

### Phase 1: Enhanced Semantic Search (Current → 2 weeks)
- [x] Basic semantic search over articles
- [ ] Add transaction type classification
- [ ] Add keyword extraction from queries
- [ ] Improve search result ranking

### Phase 2: Structured Input/Output (2-3 weeks)
- [ ] Define Pydantic models for input/output schemas
- [ ] Create API endpoints for structured POA validation requests
- [ ] Add SAK Manual sections to knowledge base
- [ ] Add transaction requirements table

### Phase 3: Rule-Based Reasoning (3-4 weeks)
- [ ] Implement transaction requirement lookup
- [ ] Implement POA power analysis
- [ ] Implement rule evaluation logic
- [ ] Add confidence scoring

### Phase 4: Integration & Testing (2-3 weeks)
- [ ] Integrate with OCR extraction service (separate agent)
- [ ] Add remediation generation
- [ ] Add template text generation
- [ ] Comprehensive testing with real POA cases

### Phase 5: Production Readiness (2 weeks)
- [ ] Audit logging for all decisions
- [ ] SME feedback loop for confidence calibration
- [ ] Performance optimization
- [ ] Monitoring and alerting

---

## API Endpoints

### Current Endpoint
```
POST /api (ACP message/send)
Input: { "content": "What are the rules about sales?" }
Output: { "content": "Based on Article 714..." }
```

### New Endpoints

```
POST /api/validate-poa
Input: POAValidationRequest (structured)
Output: POAValidationResult (structured)

POST /api/analyze-transaction
Input: { transaction_type, value }
Output: { requirements, relevant_articles }

POST /api/search-legal-rules
Input: { query, transaction_type, limit }
Output: { articles: [...], sak_sections: [...] }
```

---

## Sample Test Cases

### Test Case 1: POA Insufficient for Share Sale
```json
{
  "application": {
    "transaction_type": "sale_of_shares",
    "transaction_value": 500000,
    "transaction_subject": "25% shares of XYZ Trading Co."
  },
  "poa_document": {
    "granted_powers": [
      "إدارة شؤوني العامة",
      "التوقيع على المستندات الرسمية"
    ]
  }
}
```
**Expected:** BLOCKED (no "بيع" or "أسهم" in powers)

### Test Case 2: POA Sufficient for Litigation
```json
{
  "application": {
    "transaction_type": "litigation"
  },
  "poa_document": {
    "granted_powers": [
      "التقاضي والصلح والإقرار",
      "تمثيلي أمام المحاكم"
    ]
  }
}
```
**Expected:** PASS (explicit litigation authority)

### Test Case 3: POA Expired
```json
{
  "application": {
    "transaction_type": "property_sale"
  },
  "poa_document": {
    "poa_expiry": "2024-06-01",
    "granted_powers": ["بيع العقارات"]
  }
}
```
**Expected:** BLOCKED (expired)

### Test Case 4: Needs SME Review
```json
{
  "application": {
    "transaction_type": "loan_agreement"
  },
  "poa_document": {
    "granted_powers": [
      "إدارة الشؤون المالية",
      "التعامل مع البنوك"
    ]
  }
}
```
**Expected:** NEEDS_SME_REVIEW (unclear if financial management covers creating debt)

---

## Dependencies & Prerequisites

### Data Requirements
1. **Civil Code Articles** ✅ (have 1,148 articles)
2. **Commercial Companies Law** ❌ (need to add)
3. **SAK Manual Sections** ❌ (need to add)
4. **Transaction Requirements Matrix** ❌ (need to create)
5. **POA Validation Rules** ❌ (need to create)

### External Services
1. **OCR Extraction Agent** - Extracts text from POA PDFs (separate agent)
2. **Arabic NLP** - For keyword extraction and analysis
3. **Translation Service** - For consistent AR/EN output

### Infrastructure
1. **Supabase** ✅ (already using)
2. **Azure OpenAI** ✅ (already using for embeddings and LLM)
3. **AgentEx Framework** ✅ (already using)

---

## Next Steps

1. **Immediate**: Populate knowledge base with more legal sources
2. **Short-term**: Define structured input/output schemas
3. **Medium-term**: Implement rule-based reasoning engine
4. **Long-term**: Integrate with OCR agent and SAK system

---

## Questions for Stakeholders

1. Do you have the SAK Manual content available digitally?
2. Is there an existing transaction type taxonomy?
3. What's the format of POA documents (consistent template or varied)?
4. Who are the SMEs for edge case review?
5. What's the acceptable false positive/negative rate?

