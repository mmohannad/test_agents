"""
Cross-Field Logic Check.
Validates logical consistency between related fields.
"""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity


def check_cross_field_logic(application: dict, config: dict) -> Tier1CheckResult:
    """
    Check logical consistency between related fields.
    
    Validates:
    - Grantor and agent are different people
    - POA dates are logical (issue before expiry)
    - Party positions match their roles
    - Transaction type matches POA type
    """
    logic_errors = []
    warnings = []
    details = {
        "party_uniqueness": {},
        "date_logic": {},
        "role_consistency": {},
        "type_consistency": {},
    }
    
    party_roles = application.get("party_roles", [])
    poa_extractions = application.get("poa_extractions", [])
    transaction_type = application.get("transaction_type_code", "")
    
    # =========================================================================
    # Check 1: Grantor and agent must be different people
    # =========================================================================
    grantors = []
    agents = []
    
    for party_role in party_roles:
        position = party_role.get("party_position", "").lower()
        party = party_role.get("personal_parties") or party_role.get("personal_party", {})
        qid = party.get("qid") if party else None
        
        if position == "grantor" and qid:
            grantors.append(qid)
        elif position == "agent" and qid:
            agents.append(qid)
    
    # Check for overlap
    overlap = set(grantors) & set(agents)
    if overlap:
        logic_errors.append(f"Same person is both grantor and agent: QID(s) {', '.join(overlap)}")
        details["party_uniqueness"]["grantor_agent_same"] = {
            "status": "fail",
            "overlapping_qids": list(overlap),
        }
    else:
        details["party_uniqueness"]["grantor_agent_same"] = {
            "status": "pass",
            "grantors": grantors,
            "agents": agents,
        }
    
    # =========================================================================
    # Check 2: POA dates are logical
    # =========================================================================
    for idx, poa in enumerate(poa_extractions):
        poa_date = poa.get("poa_date")
        poa_expiry = poa.get("poa_expiry")
        
        if poa_date and poa_expiry:
            # Compare dates (handle both string and date objects)
            try:
                if str(poa_date) > str(poa_expiry):
                    logic_errors.append(f"POA issue date ({poa_date}) is after expiry ({poa_expiry})")
                    details["date_logic"][f"poa_{idx}"] = {
                        "status": "fail",
                        "issue_date": str(poa_date),
                        "expiry_date": str(poa_expiry),
                    }
                else:
                    details["date_logic"][f"poa_{idx}"] = {
                        "status": "pass",
                        "issue_date": str(poa_date),
                        "expiry_date": str(poa_expiry),
                    }
            except Exception as e:
                warnings.append(f"Could not compare POA dates: {e}")
                details["date_logic"][f"poa_{idx}"] = {
                    "status": "warning",
                    "error": str(e),
                }
    
    # =========================================================================
    # Check 3: POA principal/agent QIDs match party QIDs
    # =========================================================================
    for idx, poa in enumerate(poa_extractions):
        principal_qid = poa.get("principal_qid")
        agent_qid = poa.get("agent_qid")
        
        # Principal should match a grantor
        if principal_qid and grantors:
            if principal_qid not in grantors:
                warnings.append(f"POA principal QID ({principal_qid}) doesn't match any grantor")
                details["role_consistency"][f"poa_{idx}_principal"] = {
                    "status": "warning",
                    "poa_principal_qid": principal_qid,
                    "application_grantors": grantors,
                }
            else:
                details["role_consistency"][f"poa_{idx}_principal"] = {
                    "status": "pass",
                    "poa_principal_qid": principal_qid,
                }
        
        # Agent should match an agent in the application
        if agent_qid and agents:
            if agent_qid not in agents:
                warnings.append(f"POA agent QID ({agent_qid}) doesn't match any application agent")
                details["role_consistency"][f"poa_{idx}_agent"] = {
                    "status": "warning",
                    "poa_agent_qid": agent_qid,
                    "application_agents": agents,
                }
            else:
                details["role_consistency"][f"poa_{idx}_agent"] = {
                    "status": "pass",
                    "poa_agent_qid": agent_qid,
                }
    
    # =========================================================================
    # Check 4: Transaction type matches POA type
    # =========================================================================
    for idx, poa in enumerate(poa_extractions):
        is_general = poa.get("is_general_poa", False)
        is_special = poa.get("is_special_poa", False)
        
        # If transaction type suggests special POA, ensure POA is special
        special_transaction_keywords = ["property", "litigation", "company", "inheritance", "govt"]
        is_special_transaction = any(kw in transaction_type.lower() for kw in special_transaction_keywords)
        
        if is_special_transaction and is_general and not is_special:
            warnings.append(f"Transaction type '{transaction_type}' may require special POA, but POA is marked as general")
            details["type_consistency"][f"poa_{idx}"] = {
                "status": "warning",
                "transaction_type": transaction_type,
                "poa_type": "general",
                "recommendation": "Verify that general POA covers this transaction type",
            }
        else:
            details["type_consistency"][f"poa_{idx}"] = {
                "status": "pass",
                "transaction_type": transaction_type,
                "poa_type": "special" if is_special else ("general" if is_general else "unknown"),
            }
    
    # Determine result
    if logic_errors:
        return Tier1CheckResult(
            category=Tier1CheckCategory.CROSS_FIELD_LOGIC,
            status=CheckStatus.FAIL,
            severity=Severity.BLOCKING,
            details=details,
            message=f"Logic errors: {', '.join(logic_errors[:2])}" +
                   (f" and {len(logic_errors) - 2} more" if len(logic_errors) > 2 else ""),
        )
    
    if warnings:
        return Tier1CheckResult(
            category=Tier1CheckCategory.CROSS_FIELD_LOGIC,
            status=CheckStatus.WARNING,
            severity=Severity.NON_BLOCKING,
            details=details,
            message=f"Logic warnings: {', '.join(warnings[:2])}" +
                   (f" and {len(warnings) - 2} more" if len(warnings) > 2 else ""),
        )
    
    return Tier1CheckResult(
        category=Tier1CheckCategory.CROSS_FIELD_LOGIC,
        status=CheckStatus.PASS,
        severity=Severity.NON_BLOCKING,
        details=details,
        message="All cross-field logic checks passed",
    )

