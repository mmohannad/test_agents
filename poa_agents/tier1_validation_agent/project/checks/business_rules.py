"""
Business Rules Check.
Validates transaction-specific business rules.
"""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from datetime import date, datetime, timedelta
from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity


def parse_date(date_val) -> date | None:
    """Parse a date value to date object."""
    if not date_val:
        return None
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, str):
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_val, fmt).date()
            except ValueError:
                continue
    return None


def check_business_rules(application: dict, config: dict) -> Tier1CheckResult:
    """
    Check transaction-specific business rules.
    
    Validates:
    - Transaction value limits
    - POA age limits (not too old)
    - Party count constraints
    - Transaction-specific requirements
    """
    violations = []
    warnings = []
    details = {
        "value_checks": {},
        "poa_age_checks": {},
        "party_count_checks": {},
        "transaction_specific": {},
    }
    
    transaction_type = application.get("transaction_type_code", "")
    transaction_value = application.get("transaction_value")
    party_roles = application.get("party_roles", [])
    poa_extractions = application.get("poa_extractions", [])
    
    # =========================================================================
    # Check 1: Transaction value limits (if specified in config)
    # =========================================================================
    value_limits = config.get("value_limits", {})
    min_value = value_limits.get("min")
    max_value = value_limits.get("max")
    
    if transaction_value is not None:
        if min_value is not None and transaction_value < min_value:
            violations.append(f"Transaction value ({transaction_value}) below minimum ({min_value})")
            details["value_checks"]["min_value"] = {
                "status": "fail",
                "value": transaction_value,
                "limit": min_value,
            }
        elif min_value is not None:
            details["value_checks"]["min_value"] = {"status": "pass"}
        
        if max_value is not None and transaction_value > max_value:
            warnings.append(f"Transaction value ({transaction_value}) exceeds threshold ({max_value})")
            details["value_checks"]["max_value"] = {
                "status": "warning",
                "value": transaction_value,
                "limit": max_value,
                "note": "High value transactions may require additional verification",
            }
        elif max_value is not None:
            details["value_checks"]["max_value"] = {"status": "pass"}
    
    # =========================================================================
    # Check 2: POA age (not too old - default 5 years)
    # =========================================================================
    max_poa_age_years = config.get("max_poa_age_years", 5)
    
    for idx, poa in enumerate(poa_extractions):
        poa_date = parse_date(poa.get("poa_date"))
        
        if poa_date:
            age_days = (date.today() - poa_date).days
            age_years = age_days / 365.25
            
            if age_years > max_poa_age_years:
                violations.append(
                    f"POA is too old ({age_years:.1f} years, max {max_poa_age_years} years)"
                )
                details["poa_age_checks"][f"poa_{idx}"] = {
                    "status": "fail",
                    "poa_date": str(poa_date),
                    "age_years": round(age_years, 1),
                    "max_years": max_poa_age_years,
                }
            elif age_years > max_poa_age_years * 0.8:  # 80% of max age
                warnings.append(
                    f"POA is aging ({age_years:.1f} years, max {max_poa_age_years} years)"
                )
                details["poa_age_checks"][f"poa_{idx}"] = {
                    "status": "warning",
                    "poa_date": str(poa_date),
                    "age_years": round(age_years, 1),
                    "max_years": max_poa_age_years,
                }
            else:
                details["poa_age_checks"][f"poa_{idx}"] = {
                    "status": "pass",
                    "poa_date": str(poa_date),
                    "age_years": round(age_years, 1),
                }
    
    # =========================================================================
    # Check 3: Party count constraints
    # =========================================================================
    # Count parties by position
    position_counts = {}
    for party_role in party_roles:
        position = party_role.get("party_position", "unknown").lower()
        position_counts[position] = position_counts.get(position, 0) + 1
    
    # Check against config
    required_parties = config.get("required_parties", [])
    for req in required_parties:
        position = req.get("position", "").lower()
        min_count = req.get("min_count", 1)
        max_count = req.get("max_count")
        
        actual_count = position_counts.get(position, 0)
        
        if actual_count < min_count:
            violations.append(f"Not enough {position}s: have {actual_count}, need at least {min_count}")
            details["party_count_checks"][position] = {
                "status": "fail",
                "actual": actual_count,
                "min": min_count,
            }
        elif max_count and actual_count > max_count:
            warnings.append(f"Too many {position}s: have {actual_count}, max is {max_count}")
            details["party_count_checks"][position] = {
                "status": "warning",
                "actual": actual_count,
                "max": max_count,
            }
        else:
            details["party_count_checks"][position] = {
                "status": "pass",
                "actual": actual_count,
            }
    
    # =========================================================================
    # Check 4: Transaction-specific rules
    # =========================================================================
    
    # Property transactions require property details
    if "property" in transaction_type.lower():
        subject = application.get("transaction_subject_ar") or application.get("transaction_subject_en")
        if not subject:
            warnings.append("Property transaction should have property details in subject")
            details["transaction_specific"]["property_details"] = {
                "status": "warning",
                "note": "Property description recommended",
            }
        else:
            details["transaction_specific"]["property_details"] = {"status": "pass"}
    
    # Litigation POA should have special_litigation flag
    if "litigation" in transaction_type.lower() or "cases" in transaction_type.lower():
        for idx, poa in enumerate(poa_extractions):
            granted_powers = poa.get("granted_powers", []) + poa.get("granted_powers_en", [])
            has_litigation_power = any(
                "litigation" in p.lower() or 
                "court" in p.lower() or 
                "legal" in p.lower() or
                "قضاء" in p or
                "محكمة" in p
                for p in granted_powers
            )
            
            if not has_litigation_power:
                warnings.append("Litigation transaction but POA may not include litigation powers")
                details["transaction_specific"]["litigation_power"] = {
                    "status": "warning",
                    "granted_powers": granted_powers,
                    "note": "Verify POA includes litigation/court representation powers",
                }
            else:
                details["transaction_specific"]["litigation_power"] = {"status": "pass"}
    
    # Company transactions may need board resolution
    if "company" in transaction_type.lower():
        attachments = application.get("attachments", [])
        has_resolution = any(
            "resolution" in (a.get("document_type_code") or "").lower() or
            "board" in (a.get("document_type_code") or "").lower()
            for a in attachments
        )
        
        if not has_resolution:
            warnings.append("Company transaction may require board resolution document")
            details["transaction_specific"]["board_resolution"] = {
                "status": "warning",
                "note": "Board resolution recommended for company transactions",
            }
        else:
            details["transaction_specific"]["board_resolution"] = {"status": "pass"}
    
    # Determine result
    if violations:
        return Tier1CheckResult(
            category=Tier1CheckCategory.BUSINESS_RULES,
            status=CheckStatus.FAIL,
            severity=Severity.BLOCKING,
            details=details,
            message=f"Business rule violations: {', '.join(violations[:2])}" +
                   (f" and {len(violations) - 2} more" if len(violations) > 2 else ""),
        )
    
    if warnings:
        return Tier1CheckResult(
            category=Tier1CheckCategory.BUSINESS_RULES,
            status=CheckStatus.WARNING,
            severity=Severity.NON_BLOCKING,
            details=details,
            message=f"Business rule warnings: {', '.join(warnings[:2])}" +
                   (f" and {len(warnings) - 2} more" if len(warnings) > 2 else ""),
        )
    
    return Tier1CheckResult(
        category=Tier1CheckCategory.BUSINESS_RULES,
        status=CheckStatus.PASS,
        severity=Severity.NON_BLOCKING,
        details=details,
        message="All business rules passed",
    )

