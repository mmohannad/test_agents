"""
Supabase client for POA agents.
"""

import os
from typing import Optional
from supabase import create_client, Client


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client singleton."""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url:
            raise ValueError("SUPABASE_URL environment variable is required")
        if not key:
            raise ValueError("SUPABASE_ANON_KEY environment variable is required")
        
        _supabase_client = create_client(url, key)
    
    return _supabase_client


# ============================================================================
# Data Access Functions
# ============================================================================

def load_application(application_id: str) -> dict:
    """Load application with all related data."""
    client = get_supabase_client()
    
    # Get application
    app_result = client.table("applications").select("*").eq("id", application_id).single().execute()
    application = app_result.data
    
    # Get party roles with party details
    roles_result = client.table("application_party_roles").select(
        "*, personal_parties(*)"
    ).eq("application_id", application_id).execute()
    application["party_roles"] = roles_result.data
    
    # Get attachments with extractions
    attachments_result = client.table("attachments").select(
        "*, document_extractions(*)"
    ).eq("application_id", application_id).execute()
    application["attachments"] = attachments_result.data
    
    # Get POA extractions
    poa_result = client.table("poa_extractions").select("*").eq("application_id", application_id).execute()
    application["poa_extractions"] = poa_result.data
    
    return application


def load_transaction_config(transaction_type_code: str) -> dict:
    """Load transaction configuration for validation."""
    client = get_supabase_client()
    
    result = client.table("transaction_configs").select("*").eq(
        "transaction_type_code", transaction_type_code
    ).single().execute()
    
    return result.data


def save_validation_report(report: dict) -> dict:
    """Save a validation report."""
    client = get_supabase_client()
    result = client.table("validation_reports").insert(report).execute()
    return result.data[0]


def save_legal_opinion(opinion: dict) -> dict:
    """Save a legal opinion."""
    client = get_supabase_client()
    result = client.table("legal_opinions").insert(opinion).execute()
    return result.data[0]


def save_research_trace(trace: dict) -> dict:
    """Save a research trace."""
    client = get_supabase_client()
    result = client.table("research_traces").insert(trace).execute()
    return result.data[0]


def update_research_trace(trace_id: str, updates: dict) -> dict:
    """Update a research trace."""
    client = get_supabase_client()
    result = client.table("research_traces").update(updates).eq("id", trace_id).execute()
    return result.data[0]


def save_escalation(escalation: dict) -> dict:
    """Save an escalation."""
    client = get_supabase_client()
    result = client.table("escalations").insert(escalation).execute()
    return result.data[0]


def update_application_status(application_id: str, status: str, **kwargs) -> dict:
    """Update application status."""
    client = get_supabase_client()
    updates = {"status": status, **kwargs}
    result = client.table("applications").update(updates).eq("id", application_id).execute()
    return result.data[0]

