"""
Format Validation Check.
Validates that field values match expected formats.
"""

import sys
from pathlib import Path

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

import re
from datetime import date, datetime
from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity


# Qatar ID (QID) format: 11 digits starting with 2 or 3
QID_PATTERN = re.compile(r'^[23]\d{10}$')

# Date formats
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]

# Phone format: +974 followed by 8 digits, or just 8 digits
PHONE_PATTERN = re.compile(r'^(\+974)?[0-9]{8}$')

# Email format
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_qid(qid: str) -> tuple[bool, str]:
    """Validate Qatar ID format."""
    if not qid:
        return False, "QID is empty"
    qid_clean = qid.replace(" ", "").replace("-", "")
    if not QID_PATTERN.match(qid_clean):
        return False, f"Invalid QID format: {qid}"
    return True, "Valid QID"


def validate_date(date_str: str) -> tuple[bool, str]:
    """Validate date string."""
    if not date_str:
        return True, "No date provided"  # Empty is ok for optional dates
    
    # If already a date object
    if isinstance(date_str, (date, datetime)):
        return True, "Valid date"
    
    for fmt in DATE_FORMATS:
        try:
            datetime.strptime(str(date_str), fmt)
            return True, "Valid date"
        except ValueError:
            continue
    
    return False, f"Invalid date format: {date_str}"


def validate_date_not_expired(date_str: str, field_name: str) -> tuple[bool, str]:
    """Validate that a date is not in the past (not expired)."""
    if not date_str:
        return True, "No date provided"
    
    # If already a date object
    if isinstance(date_str, date):
        check_date = date_str
    elif isinstance(date_str, datetime):
        check_date = date_str.date()
    else:
        # Parse the date string
        for fmt in DATE_FORMATS:
            try:
                check_date = datetime.strptime(str(date_str), fmt).date()
                break
            except ValueError:
                continue
        else:
            return False, f"Cannot parse date: {date_str}"
    
    if check_date < date.today():
        return False, f"{field_name} is expired: {date_str}"
    
    return True, f"{field_name} is valid"


def validate_phone(phone: str) -> tuple[bool, str]:
    """Validate phone number format."""
    if not phone:
        return True, "No phone provided"  # Optional field
    phone_clean = phone.replace(" ", "").replace("-", "")
    if not PHONE_PATTERN.match(phone_clean):
        return False, f"Invalid phone format: {phone}"
    return True, "Valid phone"


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email format."""
    if not email:
        return True, "No email provided"  # Optional field
    if not EMAIL_PATTERN.match(email):
        return False, f"Invalid email format: {email}"
    return True, "Valid email"


def check_format_validation(application: dict, config: dict) -> Tier1CheckResult:
    """
    Check that all field values match expected formats.
    
    Validates:
    - QID formats for all parties
    - Date formats and expiry
    - Phone number formats
    - Email formats
    """
    format_errors = []
    warnings = []
    details = {
        "qid_validations": {},
        "date_validations": {},
        "contact_validations": {},
    }
    
    # Validate party QIDs
    party_roles = application.get("party_roles", [])
    for party_role in party_roles:
        party = party_role.get("personal_parties") or party_role.get("personal_party", {})
        if not party:
            continue
        
        position = party_role.get("party_position", "unknown")
        party_id = party.get("id", "unknown")
        key = f"{position}_{party_id}"
        
        # Validate QID
        qid = party.get("qid")
        if qid:
            valid, msg = validate_qid(qid)
            details["qid_validations"][key] = {"qid": qid, "valid": valid, "message": msg}
            if not valid:
                format_errors.append(f"{position} QID: {msg}")
        else:
            # Missing QID is handled by field_completeness, but note it here
            details["qid_validations"][key] = {"qid": None, "valid": False, "message": "QID not provided"}
        
        # Validate phone
        phone = party.get("phone")
        if phone:
            valid, msg = validate_phone(phone)
            details["contact_validations"][f"{key}_phone"] = {"value": phone, "valid": valid, "message": msg}
            if not valid:
                warnings.append(f"{position} phone: {msg}")
        
        # Validate email
        email = party.get("email")
        if email:
            valid, msg = validate_email(email)
            details["contact_validations"][f"{key}_email"] = {"value": email, "valid": valid, "message": msg}
            if not valid:
                warnings.append(f"{position} email: {msg}")
    
    # Validate dates in POA extractions
    poa_extractions = application.get("poa_extractions", [])
    for idx, poa in enumerate(poa_extractions):
        # Check POA expiry
        expiry = poa.get("poa_expiry")
        if expiry:
            valid, msg = validate_date_not_expired(expiry, "POA expiry")
            details["date_validations"][f"poa_{idx}_expiry"] = {"value": str(expiry), "valid": valid, "message": msg}
            if not valid:
                format_errors.append(msg)
        
        # Check POA date format
        poa_date = poa.get("poa_date")
        if poa_date:
            valid, msg = validate_date(str(poa_date))
            details["date_validations"][f"poa_{idx}_date"] = {"value": str(poa_date), "valid": valid, "message": msg}
            if not valid:
                format_errors.append(f"POA date: {msg}")
    
    # Validate QID expiry in attachments (if document extraction includes it)
    attachments = application.get("attachments", [])
    for attachment in attachments:
        doc_type = attachment.get("document_type_code", "")
        if "qid" in doc_type.lower():
            extractions = attachment.get("document_extractions", [])
            for ext in extractions:
                extracted_fields = ext.get("extracted_fields", {})
                expiry = extracted_fields.get("expiry_date") or extracted_fields.get("document_expiry")
                if expiry:
                    valid, msg = validate_date_not_expired(expiry, f"QID document ({doc_type})")
                    details["date_validations"][f"attachment_{attachment.get('id')}_expiry"] = {
                        "value": str(expiry),
                        "valid": valid,
                        "message": msg,
                    }
                    if not valid:
                        format_errors.append(msg)
    
    # Determine result
    if format_errors:
        return Tier1CheckResult(
            category=Tier1CheckCategory.FORMAT_VALIDATION,
            status=CheckStatus.FAIL,
            severity=Severity.BLOCKING,
            details=details,
            message=f"Format errors: {', '.join(format_errors[:3])}" +
                   (f" and {len(format_errors) - 3} more" if len(format_errors) > 3 else ""),
        )
    
    if warnings:
        return Tier1CheckResult(
            category=Tier1CheckCategory.FORMAT_VALIDATION,
            status=CheckStatus.WARNING,
            severity=Severity.NON_BLOCKING,
            details=details,
            message=f"Format warnings: {', '.join(warnings[:3])}" +
                   (f" and {len(warnings) - 3} more" if len(warnings) > 3 else ""),
        )
    
    return Tier1CheckResult(
        category=Tier1CheckCategory.FORMAT_VALIDATION,
        status=CheckStatus.PASS,
        severity=Severity.NON_BLOCKING,
        details=details,
        message="All formats valid",
    )

