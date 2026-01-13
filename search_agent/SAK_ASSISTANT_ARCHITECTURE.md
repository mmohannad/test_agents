# SAK Assistant Architecture
## Deep Research Legal Reasoning System

---

## Executive Summary

This document describes a **two-tier validation architecture** for processing Power of Attorney (POA) applications at the Ministry of Justice. The system combines:

1. **Deterministic Validation** — Fast, coded checks for structural integrity
2. **Deep Legal Reasoning** — Multi-step LLM-based analysis with sub-question decomposition and verification

The architecture is designed to handle ambiguity, cite legal sources, and produce legal opinion-style outputs with appropriate confidence levels.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [System Overview](#system-overview)
3. [Tier 1: Deterministic Validation](#tier-1-deterministic-validation)
4. [Tier 2: Deep Legal Reasoning](#tier-2-deep-legal-reasoning)
5. [The Case Bundle](#the-case-bundle)
6. [Deep Research Agent Architecture](#deep-research-agent-architecture)
7. [Data Models](#data-models)
8. [Agent Communication Protocol](#agent-communication-protocol)
9. [Confidence & Escalation Framework](#confidence--escalation-framework)
10. [Implementation Phases](#implementation-phases)

---

## Design Philosophy

### What We're NOT Building

❌ An exhaustive rule database that encodes all legal knowledge  
❌ A simple pass/fail checkbox system  
❌ A single-shot LLM call that hopes for the best  

### What We ARE Building

✅ A **layered system** that separates structural checks from legal reasoning  
✅ A **research-style agent** that decomposes complex legal questions  
✅ A **citation-grounded system** that traces conclusions to legal sources  
✅ A **reflection-enabled architecture** that verifies its own reasoning  

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Separate concerns** | Structural validation ≠ Legal interpretation |
| **Ground in sources** | Every legal claim cites articles/regulations |
| **Decompose complexity** | Break "is this valid?" into sub-questions |
| **Verify reasoning** | Reflection pass catches logical errors |
| **Express uncertainty** | Confidence scores, not binary pass/fail |
| **Human in the loop** | Escalation paths for edge cases |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            APPLICATION INTAKE                                │
│                     (Documents, Forms, Party Information)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT PROCESSING LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  OCR Agent  │  │  VLM Agent  │  │  Synthesis  │  │  Extraction │        │
│  │             │  │             │  │    Agent    │  │    Agent    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TIER 1: DETERMINISTIC VALIDATION                          │
│                                                                              │
│  • Field Completeness        • Format Validation       • Cross-field Logic  │
│  • Referential Integrity     • Document Matching       • Business Rules     │
│                                                                              │
│  Output: Structured pass/fail results with specific failure reasons          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CASE BUNDLE ASSEMBLY                               │
│                                                                              │
│  Combines: Application Data + Extractions + Tier 1 Results + Legal Context  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TIER 2: DEEP LEGAL REASONING                              │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    QUESTION DECOMPOSITION                              │  │
│  │  "Is this POA valid?" →                                                │  │
│  │    Q1: Does the grantor have capacity to delegate this power?         │  │
│  │    Q2: Is the agent legally permitted to exercise this power?         │  │
│  │    Q3: Are the required documents sufficient and authentic?           │  │
│  │    Q4: Are there any legal restrictions or conflicts?                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MULTI-STEP RESEARCH                                 │  │
│  │  For each sub-question:                                                │  │
│  │    1. Retrieve relevant legal articles (RAG)                          │  │
│  │    2. Analyze against case facts                                      │  │
│  │    3. Form preliminary conclusion                                     │  │
│  │    4. Identify follow-up questions if needed                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    SYNTHESIS & REFLECTION                              │  │
│  │    1. Combine sub-question findings                                   │  │
│  │    2. Check for logical consistency                                   │  │
│  │    3. Verify citations support conclusions                            │  │
│  │    4. Assess overall confidence                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LEGAL OPINION OUTPUT                               │
│                                                                              │
│  • Finding (Valid/Invalid/Requires Review)                                  │
│  • Analysis (per sub-question)                                              │
│  • Legal Basis (cited articles)                                             │
│  • Concerns & Recommendations                                               │
│  • Confidence Level & Reasoning                                             │
└─────────────────────────────────────────────────────────────────────────────┘
---

## Tier 1: Deterministic Validation

### Purpose

Fast, reliable checks that don't require legal expertise. These are **structural validations** implemented in code, not a database of rules.

### Check Categories

#### 1. Field Completeness

```yaml
check: field_completeness
description: All required fields for the transaction type are present
implementation: Code-driven, per transaction type config

examples:
  - "Grantor Emirates ID is missing"
  - "Agent date of birth not provided"
  - "POA purpose field is empty"
```

#### 2. Format Validation

```yaml
check: format_validation
description: Data matches expected formats and patterns

validations:
  emirates_id: "^784-[0-9]{4}-[0-9]{7}-[0-9]$"
  phone_uae: "^\\+971[0-9]{9}$"
  date: ISO 8601 format, valid calendar date
  email: RFC 5322 compliant
```

#### 3. Cross-Field Logic

```yaml
check: cross_field_logic
description: Fields are internally consistent

validations:
  - expiry_date > issue_date
  - grantor_age >= 21 (calculated from DOB)
  - if capacity = "guardian", then ward_info present
  - if grantor_type = "company", then trade_license present
```

#### 4. Referential Integrity

```yaml
check: referential_integrity
description: References resolve correctly

validations:
  - All party_ids in roles exist in parties table
  - All attachment_ids in extractions exist in attachments
  - Transaction type is valid enum value
```

#### 5. Document Matching

```yaml
check: document_matching
description: Declared documents match actual attachments

validations:
  - Count of attachments matches declaration
  - Each required document type is present
  - No duplicate document types (unless allowed)
```

#### 6. Business Rules

```yaml
check: business_rules
description: Transaction-specific requirements

examples:
  litigation_poa:
    - Agent must have attorney capacity indicator
    - Court jurisdiction must be specified
  
  property_sale_poa:
    - Property details must be provided
    - Title deed attachment required
  
  company_poa:
    - Board resolution required if value > threshold
    - Signatory authority document required
```

### Tier 1 Output Structure

```json
{
  "tier1_validation": {
    "overall_status": "PASS" | "FAIL" | "WARNINGS",
    "execution_time_ms": 145,
    "checks": [
      {
        "category": "field_completeness",
        "status": "PASS",
        "details": null
      },
      {
        "category": "cross_field_logic",
        "status": "FAIL",
        "details": {
          "field": "expiry_date",
          "issue": "Expiry date (2023-01-15) is before issue date (2024-03-20)",
          "severity": "BLOCKING"
        }
      },
      {
        "category": "document_matching",
        "status": "WARNING",
        "details": {
          "issue": "Trade license attachment present but not declared",
          "severity": "NON_BLOCKING"
        }
      }
    ],
    "blocking_failures": 1,
    "warnings": 1,
    "can_proceed_to_tier2": false
  }
}
```

### Tier 1 Decision Logic

```
IF blocking_failures > 0:
    → Return to applicant with specific errors
    → Do NOT proceed to Tier 2 (waste of resources)

IF blocking_failures == 0 AND warnings > 0:
    → Proceed to Tier 2 with warnings attached
    → Tier 2 may consider warnings in analysis

IF all checks pass:
    → Proceed to Tier 2
```

---

## Tier 2: Deep Legal Reasoning

### Purpose

Interpret the legal validity of the POA by reasoning over laws, regulations, and case facts. This is where the **research-style agent** operates.

### Why Not Just Encode Rules?

| Approach | Problem |
|----------|---------|
| Encode all legal checks as rules | Would require 1000s of rules; laws change; interpretations vary |
| Single LLM call | Shallow reasoning; misses nuances; hard to verify |
| **Multi-step research** | Decomposes complexity; cites sources; verifiable; handles ambiguity |

### The Deep Research Approach

Instead of asking:
> "Is this POA valid?"

We decompose into research questions and investigate each:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER QUESTION                               │
│        "Is this Power of Attorney legally valid?"                │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   SUB-QUESTION 1  │ │   SUB-QUESTION 2  │ │   SUB-QUESTION 3  │
│                   │ │                   │ │                   │
│ GRANTOR CAPACITY  │ │  AGENT CAPACITY   │ │ DOCUMENT SUFFIC.  │
│                   │ │                   │ │                   │
│ Can this grantor  │ │ Can this agent    │ │ Are the provided  │
│ legally delegate  │ │ legally exercise  │ │ documents legally │
│ this power?       │ │ this power?       │ │ sufficient?       │
└───────────────────┘ └───────────────────┘ └───────────────────┘
         │                     │                     │
         ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ Follow-up Q1.1    │ │ Follow-up Q2.1    │ │ Follow-up Q3.1    │
│ If company: does  │ │ If litigation:    │ │ If heir capacity: │
│ board resolution  │ │ is agent a        │ │ is inheritance    │
│ authorize this?   │ │ licensed attorney?│ │ doc authenticated?│
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## The Case Bundle

### Definition

The **Case Bundle** is the complete information package sent to the Deep Legal Reasoning agent. It contains everything needed to form a legal opinion.

### Structure

```yaml
case_bundle:
  # ─────────────────────────────────────────────────────────────
  # Section 1: Application Metadata
  # ─────────────────────────────────────────────────────────────
  application:
    id: "APP-2024-00123"
    transaction_type: "litigation_poa"
    submission_date: "2024-03-20"
    jurisdiction: "Dubai Courts"
    urgency: "standard"
  
  # ─────────────────────────────────────────────────────────────
  # Section 2: Party Information
  # ─────────────────────────────────────────────────────────────
  parties:
    grantors:
      - id: "P001"
        type: "individual"
        name_en: "Ahmed Mohammed Al-Rashid"
        name_ar: "أحمد محمد الراشد"
        emirates_id: "784-1985-1234567-1"
        nationality: "UAE"
        capacity: "principal"  # Acting for self
        
    agents:
      - id: "P002"
        type: "individual"
        name_en: "Fatima Hassan Al-Mansoori"
        emirates_id: "784-1990-7654321-2"
        capacity: "attorney"
        bar_license_number: "DXB-ATT-2015-1234"
        
    witnesses:
      - id: "P003"
        name_en: "Khalid Omar"
        emirates_id: "784-1988-9999999-3"
  
  # ─────────────────────────────────────────────────────────────
  # Section 3: Document Extractions
  # ─────────────────────────────────────────────────────────────
  extractions:
    poa_document:
      poa_type: "special"
      purpose: "Represent grantor in civil case #2024/1234"
      scope: 
        - "File lawsuits"
        - "Attend hearings"
        - "Submit evidence"
        - "Accept or reject settlements"
      effective_date: "2024-03-20"
      expiry_date: "2025-03-20"
      restrictions:
        - "Limited to case #2024/1234 only"
        - "Settlement acceptance requires grantor approval if > 100,000 AED"
    
    supporting_documents:
      - type: "emirates_id"
        party_ref: "P001"
        extracted_name: "Ahmed Mohammed Al-Rashid"
        extracted_id: "784-1985-1234567-1"
        expiry: "2028-05-15"
        
      - type: "bar_license"
        party_ref: "P002"
        license_number: "DXB-ATT-2015-1234"
        status: "Active"
        jurisdiction: "Dubai"
        expiry: "2025-12-31"
  
  # ─────────────────────────────────────────────────────────────
  # Section 4: Tier 1 Validation Results
  # ─────────────────────────────────────────────────────────────
  tier1_results:
    overall_status: "PASS"
    blocking_failures: 0
    warnings: 1
    details:
      - check: "field_completeness"
        status: "PASS"
      - check: "format_validation"
        status: "PASS"
      - check: "cross_field_logic"
        status: "PASS"
      - check: "document_matching"
        status: "WARNING"
        note: "Court case filing receipt mentioned but not attached"
  
  # ─────────────────────────────────────────────────────────────
  # Section 5: Retrieved Legal Context
  # (Populated by RAG during reasoning)
  # ─────────────────────────────────────────────────────────────
  legal_context:
    retrieved_articles: []  # Populated during research
    retrieved_regulations: []
    retrieved_circulars: []
```

---

## Deep Research Agent Architecture

### Agent Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEEP RESEARCH AGENT                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      ORCHESTRATOR                                    │    │
│  │  • Manages research flow                                            │    │
│  │  • Tracks sub-questions and their status                            │    │
│  │  • Decides when to go deeper vs. synthesize                         │    │
│  │  • Enforces depth limits and token budgets                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                       │
│         ┌────────────────────────────┼────────────────────────────┐         │
│         ▼                            ▼                            ▼         │
│  ┌─────────────┐            ┌─────────────┐            ┌─────────────┐      │
│  │  DECOMPOSER │            │ RESEARCHER  │            │  VERIFIER   │      │
│  │             │            │             │            │             │      │
│  │ Breaks down │            │ Investigates│            │ Checks for  │      │
│  │ questions   │            │ sub-question│            │ consistency │      │
│  │ into sub-   │            │ using RAG + │            │ and logical │      │
│  │ questions   │            │ reasoning   │            │ errors      │      │
│  └─────────────┘            └─────────────┘            └─────────────┘      │
│                                      │                                       │
│                                      ▼                                       │
│                            ┌─────────────┐                                  │
│                            │ SYNTHESIZER │                                  │
│                            │             │                                  │
│                            │ Combines    │                                  │
│                            │ findings    │                                  │
│                            │ into legal  │                                  │
│                            │ opinion     │                                  │
│                            └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Research Flow

#### Phase 1: Question Decomposition

```python
# Orchestrator prompts the Decomposer

DECOMPOSITION_PROMPT = """
Given this POA application for {transaction_type}, decompose the validity 
assessment into specific sub-questions.

Standard decomposition framework:
1. GRANTOR CAPACITY - Can this grantor legally delegate this power?
2. AGENT CAPACITY - Can this agent legally receive/exercise this power?
3. DOCUMENT SUFFICIENCY - Are the provided documents legally adequate?
4. SCOPE & RESTRICTIONS - Is the POA scope clear and legally permissible?
5. PROCEDURAL COMPLIANCE - Are all procedural requirements met?

For each sub-question, identify:
- The specific legal question
- What facts from the case bundle are relevant
- What legal sources might apply (laws, articles, circulars)
- Priority (critical/important/supplementary)

Case Bundle Summary:
{case_bundle_summary}
"""
```

**Example Output:**

```yaml
decomposition:
  sub_questions:
    - id: "SQ1"
      category: "GRANTOR_CAPACITY"
      question: "Can Ahmed Mohammed Al-Rashid, as an individual UAE national, grant a special POA for litigation?"
      relevant_facts:
        - "Grantor is individual, not company"
        - "Grantor is UAE national, age 39"
        - "POA is for litigation representation"
      legal_areas:
        - "Civil Procedure Law - representation rights"
        - "Personal Status Law - legal capacity"
      priority: "critical"
      
    - id: "SQ2"
      category: "AGENT_CAPACITY"
      question: "Can Fatima Hassan Al-Mansoori act as litigation agent given her bar license?"
      relevant_facts:
        - "Agent has bar license DXB-ATT-2015-1234"
        - "License jurisdiction is Dubai"
        - "Case is in Dubai Courts"
      legal_areas:
        - "Legal Profession Law - who can represent"
        - "Court procedures - attorney requirements"
      priority: "critical"
      
    - id: "SQ3"
      category: "DOCUMENT_SUFFICIENCY"
      question: "Are the attached documents sufficient to establish the POA?"
      relevant_facts:
        - "Emirates IDs provided for both parties"
        - "Bar license attached for agent"
        - "Court filing receipt mentioned but not attached (Tier 1 warning)"
      legal_areas:
        - "Evidence Law - document requirements"
        - "Notarization requirements"
      priority: "important"
      
    - id: "SQ4"
      category: "SCOPE_RESTRICTIONS"
      question: "Is the settlement acceptance restriction (>100K AED requires approval) legally valid?"
      relevant_facts:
        - "POA includes settlement authority"
        - "Conditional restriction on settlement amounts"
      legal_areas:
        - "Contract Law - conditional authorities"
        - "Civil Procedure - settlement procedures"
      priority: "supplementary"
```

#### Phase 2: Multi-Step Research

For each sub-question, the Researcher component:

```
┌─────────────────────────────────────────────────────────────────┐
│                 RESEARCH LOOP (per sub-question)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: RETRIEVE                                                 │
│                                                                  │
│ Query the legal corpus (articles table) with semantic search:    │
│ "litigation representation requirements UAE Civil Procedure"     │
│                                                                  │
│ Retrieved:                                                       │
│ - Article 58: Legal representation in civil proceedings          │
│ - Article 162: Powers of attorney for litigation                 │
│ - Circular 2023/15: Attorney licensing requirements              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: ANALYZE                                                  │
│                                                                  │
│ LLM analyzes retrieved articles against case facts:              │
│                                                                  │
│ "Article 58(2) states that parties may be represented by         │
│  licensed attorneys in civil proceedings. The agent holds        │
│  active license DXB-ATT-2015-1234 in Dubai jurisdiction,         │
│  matching the case jurisdiction."                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: PRELIMINARY CONCLUSION                                   │
│                                                                  │
│ Form initial finding for this sub-question:                      │
│                                                                  │
│ Finding: SUPPORTED                                               │
│ Confidence: HIGH                                                 │
│ Basis: Article 58(2), verified license status                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: FOLLOW-UP CHECK                                          │
│                                                                  │
│ Are there unanswered aspects? Need more depth?                   │
│                                                                  │
│ → License is Dubai-specific; case is Dubai Courts ✓              │
│ → No conflict identified                                         │
│ → No follow-up needed for this sub-question                      │
└─────────────────────────────────────────────────────────────────┘
```

**Research Prompt Template:**

```python
RESEARCH_PROMPT = """
You are investigating a specific legal question for a POA validity assessment.

SUB-QUESTION: {sub_question}

RELEVANT FACTS FROM CASE:
{relevant_facts}

RETRIEVED LEGAL SOURCES:
{retrieved_articles}

TASK:
1. Analyze how the legal sources apply to the facts
2. Identify any gaps or ambiguities
3. Form a preliminary conclusion with confidence level
4. Determine if follow-up research is needed

OUTPUT FORMAT:
{
  "analysis": "Your reasoning connecting law to facts",
  "finding": "SUPPORTED | NOT_SUPPORTED | UNCLEAR | NEEDS_MORE_INFO",
  "confidence": "HIGH | MEDIUM | LOW",
  "legal_basis": ["Article X", "Circular Y"],
  "concerns": ["Any issues identified"],
  "follow_up_needed": true/false,
  "follow_up_question": "If needed, what else to research"
}
"""
```

#### Phase 3: Synthesis

After all sub-questions are researched:

```python
SYNTHESIS_PROMPT = """
You have completed research on all sub-questions for this POA validity assessment.

CASE SUMMARY:
{case_bundle_summary}

SUB-QUESTION FINDINGS:
{all_findings}

TASK:
Synthesize these findings into a cohesive legal opinion. Consider:
1. How do the sub-question findings relate to each other?
2. Are there any conflicts between findings?
3. What is the overall validity assessment?
4. What are the key concerns or conditions?

Your opinion should be structured as a legal analysis, not a checklist.
"""
```

#### Phase 4: Verification/Reflection

Before finalizing, the Verifier component checks:

```python
VERIFICATION_PROMPT = """
Review the following legal opinion for consistency and accuracy.

DRAFT OPINION:
{draft_opinion}

VERIFICATION CHECKLIST:
1. CITATION ACCURACY
   - Does each claim have a cited legal basis?
   - Are the citations actually relevant to the claims?
   
2. LOGICAL CONSISTENCY
   - Do the sub-findings logically support the overall conclusion?
   - Are there any contradictions between sections?
   
3. FACT ALIGNMENT
   - Does the opinion accurately reflect the case facts?
   - Are any facts misrepresented or omitted?
   
4. COMPLETENESS
   - Were all critical sub-questions addressed?
   - Are there obvious gaps in the analysis?
   
5. CONFIDENCE CALIBRATION
   - Is the confidence level appropriate given the evidence?
   - Are uncertainties properly acknowledged?

OUTPUT:
{
  "verification_passed": true/false,
  "issues_found": ["list of issues"],
  "suggested_revisions": ["specific fixes"],
  "final_confidence": "HIGH | MEDIUM | LOW"
}
"""
```

### Handling Follow-Up Questions

When a sub-question needs deeper investigation:

```
┌─────────────────────────────────────────────────────────────────┐
│  Original: "Can this company grant litigation POA?"              │
│                                                                  │
│  Initial finding: UNCLEAR - need to verify board authorization   │
│                                                                  │
│  Follow-up generated:                                            │
│  "Does the board resolution attached authorize the CEO to        │
│   grant litigation POAs on behalf of the company?"               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  New research cycle for follow-up question:                      │
│                                                                  │
│  1. Retrieve: Company law on board delegations                   │
│  2. Analyze: Board resolution text vs. POA scope                 │
│  3. Conclude: Resolution authorizes "legal proceedings" -        │
│               litigation POA falls within this scope             │
│  4. Update parent question's finding                             │
└─────────────────────────────────────────────────────────────────┘
```

### Depth Limits

To prevent infinite research loops:

```yaml
research_limits:
  max_depth: 3  # Maximum levels of follow-up questions
  max_retrievals_per_question: 5  # RAG calls per sub-question
  max_total_sub_questions: 10  # Total questions including follow-ups
  token_budget: 50000  # Total tokens for reasoning
  
  escalation_on_limit:
    action: "synthesize_with_disclaimer"
    disclaimer: "Analysis limited by research depth; human review recommended"
```

---

## Data Models

### Simplified Schema

Given the two-tier architecture, we need fewer database tables:

```
┌─────────────────────────────────────────────────────────────────┐
│                      CORE TABLES                                 │
├─────────────────────────────────────────────────────────────────┤
│  applications          - Application metadata                    │
│  parties               - All parties (grantors, agents, etc.)   │
│  party_roles           - Links parties to applications w/ roles │
│  attachments           - Uploaded documents                      │
│  document_extractions  - OCR/VLM extraction results             │
├─────────────────────────────────────────────────────────────────┤
│                      LEGAL CORPUS                                │
├─────────────────────────────────────────────────────────────────┤
│  articles              - Laws, regulations, circulars (RAG)     │
├─────────────────────────────────────────────────────────────────┤
│                      VALIDATION OUTPUT                           │
├─────────────────────────────────────────────────────────────────┤
│  validation_reports    - Complete validation results             │
│  research_traces       - Audit trail of reasoning steps          │
│  escalations           - Cases sent to human review              │
├─────────────────────────────────────────────────────────────────┤
│                      CONFIGURATION                               │
├─────────────────────────────────────────────────────────────────┤
│  transaction_types     - Supported transaction types             │
│  transaction_configs   - Per-type requirements (docs, parties)   │
└─────────────────────────────────────────────────────────────────┘
```

### Transaction Configuration (Replaces Complex Rules)

Instead of encoding legal rules, we configure **structural requirements**:

```yaml
# transaction_configs table entry
transaction_type: "litigation_poa"
config:
  required_parties:
    - role: "grantor"
      min_count: 1
      allowed_types: ["individual", "company"]
    - role: "agent"
      min_count: 1
      max_count: 3
      allowed_types: ["individual"]
      required_attributes:
        - "bar_license_number"  # Must have this field
  
  required_documents:
    - type: "emirates_id"
      for_parties: ["grantor", "agent"]
    - type: "bar_license"
      for_parties: ["agent"]
    - type: "poa_document"
      count: 1
  
  optional_documents:
    - type: "board_resolution"
      condition: "grantor.type == 'company'"
    - type: "court_filing"
      note: "Recommended but not required at POA stage"
  
  tier1_checks:
    - "grantor_adult"  # Age >= 21
    - "agent_licensed" # Has bar license
    - "valid_dates"    # Expiry > Issue
```

### Research Trace (Audit Trail)

```yaml
# research_traces table
trace:
  application_id: "APP-2024-00123"
  timestamp: "2024-03-20T14:30:00Z"
  
  decomposition:
    sub_questions:
      - id: "SQ1"
        question: "Can grantor delegate litigation authority?"
        
  research_steps:
    - step: 1
      sub_question_id: "SQ1"
      action: "retrieve"
      query: "litigation representation UAE Civil Procedure"
      results: ["Article 58", "Article 162"]
      
    - step: 2
      sub_question_id: "SQ1"
      action: "analyze"
      input_tokens: 2340
      output_tokens: 456
      finding: "SUPPORTED"
      confidence: "HIGH"
      
  verification:
    passed: true
    issues: []
    
  final_opinion:
    finding: "VALID"
    confidence: "HIGH"
    
  total_tokens: 12450
  total_rag_calls: 8
  processing_time_ms: 4500
```

---

## Agent Communication Protocol

### Message Types

```yaml
message_types:
  # ─────────────────────────────────────────────────────────────
  # Intake → Document Processing
  # ─────────────────────────────────────────────────────────────
  PROCESS_APPLICATION:
    payload:
      application_id: string
      attachments: Attachment[]
    response:
      extractions: Extraction[]
      
  # ─────────────────────────────────────────────────────────────
  # Document Processing → Tier 1
  # ─────────────────────────────────────────────────────────────
  VALIDATE_TIER1:
    payload:
      application_id: string
      case_bundle_partial: CaseBundle  # Without legal context
    response:
      tier1_results: Tier1Results
      can_proceed: boolean
      
  # ─────────────────────────────────────────────────────────────
  # Tier 1 → Deep Research Agent
  # ─────────────────────────────────────────────────────────────
  RESEARCH_VALIDITY:
    payload:
      application_id: string
      case_bundle: CaseBundle
    response:
      legal_opinion: LegalOpinion
      research_trace: ResearchTrace
      
  # ─────────────────────────────────────────────────────────────
  # Deep Research Agent ↔ Legal Corpus (RAG)
  # ─────────────────────────────────────────────────────────────
  SEMANTIC_SEARCH:
    payload:
      query: string
      filters:
        article_type: string[]  # law, regulation, circular
        jurisdiction: string
      limit: number
    response:
      articles: Article[]
      
  # ─────────────────────────────────────────────────────────────
  # Deep Research Agent → Escalation
  # ─────────────────────────────────────────────────────────────
  ESCALATE:
    payload:
      application_id: string
      legal_opinion: LegalOpinion
      escalation_reason: string
      priority: "standard" | "urgent"
    response:
      escalation_id: string
      assigned_to: string
```

### Async Processing Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Intake  │────▶│   OCR   │────▶│ Tier 1  │────▶│  Deep   │────▶│ Output  │
│         │     │  Agent  │     │  Valid  │     │Research │     │         │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
     │               │               │               │               │
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          MESSAGE QUEUE                                   │
│                    (Redis / RabbitMQ / Kafka)                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Confidence & Escalation Framework

### Confidence Levels

```yaml
confidence_levels:
  HIGH:
    definition: "Clear legal basis, no ambiguity, all facts verified"
    threshold: 0.85
    action: "Auto-approve (with supervisor spot-check)"
    
  MEDIUM:
    definition: "Legal basis found but some uncertainty or missing info"
    threshold: 0.60
    action: "Manual review before approval"
    
  LOW:
    definition: "Significant ambiguity, conflicting articles, or novel case"
    threshold: 0.0
    action: "Mandatory SME review with full research trace"
```

### Escalation Triggers

```yaml
escalation_triggers:
  automatic:
    - "Confidence < 0.6"
    - "Conflicting legal articles found"
    - "Research depth limit reached"
    - "Novel transaction type"
    - "High-value transaction (> threshold)"
    
  discretionary:
    - "Agent requests human review"
    - "Unusual party configuration"
    - "Cross-border elements"
```
---

## Appendix A: Standard Sub-Question Framework

For consistency, all POA validity assessments use this framework [JUST EXAMPLE CAN BE MORE ROBUST OR LESS, DEPENDING ON TYPE OF POA]

```yaml
standard_sub_questions:
  SQ1_GRANTOR_CAPACITY:
    question_template: "Does {grantor} have legal capacity to grant {poa_type} for {purpose}?"
    research_areas:
      - "Legal capacity requirements"
      - "Restrictions on delegation"
      - "Entity-specific rules (if company)"
    
  SQ2_AGENT_CAPACITY:
    question_template: "Can {agent} legally receive and exercise {powers}?"
    research_areas:
      - "Professional licensing requirements"
      - "Capacity to act"
      - "Conflict of interest rules"
    
  SQ3_DOCUMENT_SUFFICIENCY:
    question_template: "Are the provided documents legally sufficient to establish this POA?"
    research_areas:
      - "Document requirements per transaction type"
      - "Authentication/notarization needs"
      - "Evidentiary standards"
    
  SQ4_SCOPE_VALIDITY:
    question_template: "Is the POA scope of {scope} legally permissible?"
    research_areas:
      - "Delegable vs. non-delegable powers"
      - "Scope limitations"
      - "Conditional authorities"
    
  SQ5_PROCEDURAL_COMPLIANCE:
    question_template: "Have all procedural requirements been met?"
    research_areas:
      - "Filing requirements"
      - "Witness requirements"
      - "Registration/notification needs"
```

---

## Appendix B: Example Legal Opinion Output

```markdown
# LEGAL OPINION
## POA Validity Assessment

**Application ID:** APP-2024-00123  
**Transaction Type:** Special Power of Attorney - Litigation  
**Assessment Date:** 2024-03-20  
**Confidence Level:** HIGH (0.89)

---

### FINDING

The Power of Attorney is **VALID** and may proceed to execution.

---

### ANALYSIS

#### 1. Grantor Capacity ✓

Ahmed Mohammed Al-Rashid, as an adult UAE national (age 39), has full legal 
capacity to grant a special power of attorney for litigation representation.

**Legal Basis:** Civil Code Article 85 (legal capacity), Civil Procedure Law 
Article 58 (representation rights)

**Finding:** SUPPORTED | Confidence: HIGH

#### 2. Agent Capacity ✓

Fatima Hassan Al-Mansoori holds active Dubai Bar License #DXB-ATT-2015-1234, 
valid through 2025-12-31. As a licensed attorney in Dubai jurisdiction, she 
is qualified to provide litigation representation in Dubai Courts.

**Legal Basis:** Legal Profession Law Article 12, Dubai Courts Regulation 2019/3

**Finding:** SUPPORTED | Confidence: HIGH

#### 3. Document Sufficiency ⚠️

Required documents are present (Emirates IDs, bar license, POA document). 
However, the court case filing receipt mentioned in the POA purpose is not 
attached. This is not blocking but recommended for completeness.

**Legal Basis:** Evidence Law Article 34, Notarization Circular 2022/8

**Finding:** SUPPORTED with RESERVATION | Confidence: MEDIUM

#### 4. Scope Validity ✓

The POA scope (file lawsuits, attend hearings, submit evidence, 
accept/reject settlements) is within standard litigation authority bounds.
The conditional restriction on settlements >100,000 AED is legally valid 
under contract law principles of conditional authorization.

**Legal Basis:** Civil Procedure Law Article 162, Contract Law Article 215

**Finding:** SUPPORTED | Confidence: HIGH

---

### CONCERNS

1. **Minor:** Court filing receipt not attached (non-blocking)

---

### RECOMMENDATIONS

1. Request court filing receipt for file completeness (optional)
2. Proceed to execution with standard witness requirements

---

### LEGAL BASIS SUMMARY

| Article | Relevance |
|---------|-----------|
| Civil Code Art. 85 | Grantor legal capacity |
| Civil Procedure Law Art. 58 | Right to representation |
| Civil Procedure Law Art. 162 | POA scope for litigation |
| Legal Profession Law Art. 12 | Attorney licensing |
| Contract Law Art. 215 | Conditional authorities |

---

*This opinion was generated by the SAK Legal Research Agent. Research trace 
ID: RT-2024-00123-001 available for audit.*
```

---