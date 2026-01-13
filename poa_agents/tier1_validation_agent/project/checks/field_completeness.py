"""
Field Completeness Check.
Validates that all required fields are present and non-empty.
"""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from typing import Any
from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity


def check_field_completeness(application: dict, config: dict) -> Tier1CheckResult:
    """
    Check that all required fields are present in the application.
    
    Validates:
    - Application has required base fields
    - All required parties are present
    - Required documents are attached
    - Party information is complete
    """
    missing_fields = []
    details = {
        "application_fields": {},
        "party_fields": {},
        "document_fields": {},
    }
    
    # Check application base fields
    required_app_fields = ["id", "transaction_type_code", "status"]
    for field in required_app_fields:
        if not application.get(field):
            missing_fields.append(f"application.{field}")
            details["application_fields"][field] = "missing"
        else:
            details["application_fields"][field] = "present"
    
    # Check required parties from config
    required_parties = config.get("required_parties", [])
    party_roles = application.get("party_roles", [])
    
    for req_party in required_parties:
        position = req_party.get("position")
        min_count = req_party.get("min_count", 1)
        
        # Count parties with this position
        matching_parties = [
            p for p in party_roles 
            if p.get("party_position", "").lower() == position.lower()
        ]
        
        if len(matching_parties) < min_count:
            missing_fields.append(f"party.{position} (need {min_count}, have {len(matching_parties)})")
            details["party_fields"][position] = {
                "required": min_count,
                "found": len(matching_parties),
                "status": "insufficient",
            }
        else:
            details["party_fields"][position] = {
                "required": min_count,
                "found": len(matching_parties),
                "status": "ok",
            }
    
    # Check party information completeness
    for party_role in party_roles:
        party = party_role.get("personal_parties") or party_role.get("personal_party", {})
        if not party:
            continue
            
        party_id = party.get("id", "unknown")
        
        # Required party fields
        required_party_fields = ["qid", "name_ar"]
        party_missing = []
        
        for field in required_party_fields:
            if not party.get(field):
                party_missing.append(field)
        
        if party_missing:
            position = party_role.get("party_position", "unknown")
            missing_fields.append(f"party.{position}.{party_id}: {', '.join(party_missing)}")
            details["party_fields"][f"party_{party_id}"] = {
                "missing": party_missing,
                "status": "incomplete",
            }
    
    # Check required documents from config
    required_docs = config.get("required_documents", [])
    attachments = application.get("attachments", [])
    attachment_types = [a.get("document_type_code") for a in attachments if a.get("document_type_code")]
    
    for req_doc in required_docs:
        doc_type = req_doc.get("document_type_code")
        if doc_type and doc_type not in attachment_types:
            missing_fields.append(f"document.{doc_type}")
            details["document_fields"][doc_type] = "missing"
        else:
            details["document_fields"][doc_type or "unknown"] = "present"
    
    # Determine result
    if missing_fields:
        return Tier1CheckResult(
            category=Tier1CheckCategory.FIELD_COMPLETENESS,
            status=CheckStatus.FAIL,
            severity=Severity.BLOCKING,
            details=details,
            message=f"Missing required fields: {', '.join(missing_fields[:5])}" + 
                   (f" and {len(missing_fields) - 5} more" if len(missing_fields) > 5 else ""),
        )
    
    return Tier1CheckResult(
        category=Tier1CheckCategory.FIELD_COMPLETENESS,
        status=CheckStatus.PASS,
        severity=Severity.NON_BLOCKING,
        details=details,
        message="All required fields present",
    )

