"""
Document Matching Check.
Validates that uploaded documents match party/application information.
"""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity


def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    if not name:
        return ""
    # Remove extra spaces, lowercase, remove common prefixes
    name = " ".join(name.lower().split())
    # Remove common Arabic/English prefixes
    prefixes = ["mr", "mr.", "mrs", "mrs.", "ms", "ms.", "dr", "dr.", "السيد", "السيدة"]
    for prefix in prefixes:
        if name.startswith(prefix + " "):
            name = name[len(prefix):].strip()
    return name


def names_match(name1: str, name2: str) -> bool:
    """Check if two names match (fuzzy)."""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    if not n1 or not n2:
        return False
    
    # Exact match
    if n1 == n2:
        return True
    
    # One is substring of the other (for partial names)
    if n1 in n2 or n2 in n1:
        return True
    
    # Check if first/last names match (split and compare)
    parts1 = set(n1.split())
    parts2 = set(n2.split())
    common = parts1 & parts2
    
    # At least 2 name parts in common
    if len(common) >= 2:
        return True
    
    return False


def check_document_matching(application: dict, config: dict) -> Tier1CheckResult:
    """
    Check that document content matches application/party information.
    
    Validates:
    - QID documents match party QIDs
    - Names in documents match party names
    - POA document matches application parties
    """
    mismatches = []
    warnings = []
    details = {
        "qid_matches": {},
        "name_matches": {},
        "poa_matches": {},
    }
    
    party_roles = application.get("party_roles", [])
    attachments = application.get("attachments", [])
    poa_extractions = application.get("poa_extractions", [])
    
    # Build lookup of party info
    party_info = {}
    for party_role in party_roles:
        party = party_role.get("personal_parties") or party_role.get("personal_party", {})
        if party:
            qid = party.get("qid")
            if qid:
                party_info[qid] = {
                    "name_ar": party.get("name_ar"),
                    "name_en": party.get("name_en"),
                    "position": party_role.get("party_position"),
                }
    
    # =========================================================================
    # Check QID documents
    # =========================================================================
    for attachment in attachments:
        doc_type = attachment.get("document_type_code", "").lower()
        
        if "qid" not in doc_type:
            continue
        
        extractions = attachment.get("document_extractions", [])
        for ext in extractions:
            extracted_fields = ext.get("extracted_fields", {})
            
            # Get extracted QID
            extracted_qid = (
                extracted_fields.get("qid") or 
                extracted_fields.get("id_number") or
                extracted_fields.get("document_number")
            )
            
            # Get extracted name
            extracted_name = (
                extracted_fields.get("name") or
                extracted_fields.get("full_name") or
                extracted_fields.get("holder_name")
            )
            
            if extracted_qid:
                # Check if this QID matches any party
                if extracted_qid in party_info:
                    details["qid_matches"][extracted_qid] = {
                        "status": "match",
                        "party_position": party_info[extracted_qid]["position"],
                    }
                    
                    # Also check name if available
                    if extracted_name:
                        party = party_info[extracted_qid]
                        name_match = (
                            names_match(extracted_name, party.get("name_ar", "")) or
                            names_match(extracted_name, party.get("name_en", ""))
                        )
                        
                        if name_match:
                            details["name_matches"][extracted_qid] = {
                                "status": "match",
                                "extracted_name": extracted_name,
                            }
                        else:
                            warnings.append(
                                f"Name mismatch for QID {extracted_qid}: "
                                f"document has '{extracted_name}', "
                                f"party has '{party.get('name_en') or party.get('name_ar')}'"
                            )
                            details["name_matches"][extracted_qid] = {
                                "status": "mismatch",
                                "extracted_name": extracted_name,
                                "party_name_en": party.get("name_en"),
                                "party_name_ar": party.get("name_ar"),
                            }
                else:
                    warnings.append(f"QID document for {extracted_qid} doesn't match any party")
                    details["qid_matches"][extracted_qid] = {
                        "status": "no_match",
                        "known_parties": list(party_info.keys()),
                    }
    
    # =========================================================================
    # Check POA document matches
    # =========================================================================
    for idx, poa in enumerate(poa_extractions):
        poa_key = f"poa_{idx}"
        
        # Check principal QID
        principal_qid = poa.get("principal_qid")
        if principal_qid:
            if principal_qid in party_info:
                details["poa_matches"][f"{poa_key}_principal_qid"] = {
                    "status": "match",
                    "qid": principal_qid,
                    "party_position": party_info[principal_qid]["position"],
                }
            else:
                mismatches.append(f"POA principal QID ({principal_qid}) not found in application parties")
                details["poa_matches"][f"{poa_key}_principal_qid"] = {
                    "status": "no_match",
                    "qid": principal_qid,
                }
        
        # Check agent QID
        agent_qid = poa.get("agent_qid")
        if agent_qid:
            if agent_qid in party_info:
                details["poa_matches"][f"{poa_key}_agent_qid"] = {
                    "status": "match",
                    "qid": agent_qid,
                    "party_position": party_info[agent_qid]["position"],
                }
            else:
                mismatches.append(f"POA agent QID ({agent_qid}) not found in application parties")
                details["poa_matches"][f"{poa_key}_agent_qid"] = {
                    "status": "no_match",
                    "qid": agent_qid,
                }
        
        # Check principal name
        principal_name_ar = poa.get("principal_name_ar")
        principal_name_en = poa.get("principal_name_en")
        if principal_qid and principal_qid in party_info:
            party = party_info[principal_qid]
            name_match = (
                names_match(principal_name_ar or "", party.get("name_ar", "")) or
                names_match(principal_name_en or "", party.get("name_en", ""))
            )
            if not name_match and (principal_name_ar or principal_name_en):
                warnings.append(f"POA principal name doesn't match party name for QID {principal_qid}")
                details["poa_matches"][f"{poa_key}_principal_name"] = {
                    "status": "mismatch",
                    "poa_name_ar": principal_name_ar,
                    "poa_name_en": principal_name_en,
                    "party_name_ar": party.get("name_ar"),
                    "party_name_en": party.get("name_en"),
                }
            else:
                details["poa_matches"][f"{poa_key}_principal_name"] = {"status": "match"}
    
    # Determine result
    if mismatches:
        return Tier1CheckResult(
            category=Tier1CheckCategory.DOCUMENT_MATCHING,
            status=CheckStatus.FAIL,
            severity=Severity.BLOCKING,
            details=details,
            message=f"Document mismatches: {', '.join(mismatches[:2])}" +
                   (f" and {len(mismatches) - 2} more" if len(mismatches) > 2 else ""),
        )
    
    if warnings:
        return Tier1CheckResult(
            category=Tier1CheckCategory.DOCUMENT_MATCHING,
            status=CheckStatus.WARNING,
            severity=Severity.NON_BLOCKING,
            details=details,
            message=f"Document warnings: {', '.join(warnings[:2])}" +
                   (f" and {len(warnings) - 2} more" if len(warnings) > 2 else ""),
        )
    
    return Tier1CheckResult(
        category=Tier1CheckCategory.DOCUMENT_MATCHING,
        status=CheckStatus.PASS,
        severity=Severity.NON_BLOCKING,
        details=details,
        message="All documents match application data",
    )

