"""Supabase client for the Condenser Agent."""
import os
from typing import Optional
from datetime import datetime

from supabase import create_client, Client
from agentex.lib.utils.logging import make_logger

logger = make_logger(__name__)


class CondenserSupabaseClient:
    """Client for loading case data and saving Legal Briefs."""

    def __init__(self):
        """Initialize the Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables"
            )

        logger.info(f"Initializing Supabase client - URL: {supabase_url}")
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_case_object(self, application_id: str) -> Optional[dict]:
        """
        Get the current case object for an application.

        Args:
            application_id: The application UUID

        Returns:
            Case object row or None
        """
        try:
            response = (
                self.client.table("case_objects")
                .select("*")
                .eq("application_id", application_id)
                .eq("is_current", True)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Failed to get case object: {e}")
            return None

    def get_fact_sheet(self, application_id: str) -> Optional[dict]:
        """
        Get the fact sheet for an application.

        Args:
            application_id: The application UUID

        Returns:
            Fact sheet row or None
        """
        try:
            response = (
                self.client.table("fact_sheets")
                .select("*")
                .eq("application_id", application_id)
                .order("generated_at", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get fact sheet: {e}")
            return None

    def get_validation_report(self, application_id: str, tier: str = "tier1") -> Optional[dict]:
        """
        Get the validation report for an application.

        Args:
            application_id: The application UUID
            tier: The tier level (tier1 or tier2)

        Returns:
            Validation report row or None
        """
        try:
            response = (
                self.client.table("validation_reports")
                .select("*")
                .eq("application_id", application_id)
                .eq("tier", tier)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Failed to get validation report: {e}")
            return None

    def save_legal_brief(self, application_id: str, brief_data: dict) -> Optional[dict]:
        """
        Save a Legal Brief to the database.

        Args:
            application_id: The application UUID
            brief_data: The Legal Brief data

        Returns:
            Saved row or None
        """
        try:
            row = {
                "application_id": application_id,
                "brief_content": brief_data,
                "status": "ready",
                "completeness_score": brief_data.get("extraction_confidence", 0),
                "fact_count": len(brief_data.get("fact_comparisons", [])) + len(brief_data.get("open_questions", [])),
                "uncertainty_count": len([q for q in brief_data.get("open_questions", []) if q.get("priority") == "critical"]),
                "issues_to_analyze": brief_data.get("open_questions", []),
                "generated_at": datetime.now().isoformat()
            }

            response = (
                self.client.table("legal_briefs")
                .insert(row)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"Failed to save legal brief: {e}")
            return None

    def get_application(self, application_id: str) -> Optional[dict]:
        """
        Get application details.

        Args:
            application_id: The application UUID

        Returns:
            Application row or None
        """
        try:
            response = (
                self.client.table("applications")
                .select("*")
                .eq("id", application_id)
                .single()
                .execute()
            )
            return response.data if response.data else None
        except Exception as e:
            logger.error(f"Failed to get application: {e}")
            return None

    def get_parties(self, application_id: str) -> list[dict]:
        """
        Get all parties for an application.

        Args:
            application_id: The application UUID

        Returns:
            List of party rows
        """
        try:
            response = (
                self.client.table("parties")
                .select("*")
                .eq("application_id", application_id)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get parties: {e}")
            return []

    def get_capacity_proofs(self, party_ids: list[str]) -> list[dict]:
        """
        Get capacity proofs for parties.

        Args:
            party_ids: List of party UUIDs

        Returns:
            List of capacity proof rows
        """
        try:
            response = (
                self.client.table("capacity_proofs")
                .select("*")
                .in_("party_id", party_ids)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error(f"Failed to get capacity proofs: {e}")
            return []

    def get_document_extractions(self, application_id: str) -> list[dict]:
        """
        Get document extractions for an application.

        Args:
            application_id: The application UUID

        Returns:
            List of document extraction rows
        """
        try:
            # First get documents for the application
            docs_response = (
                self.client.table("documents")
                .select("id")
                .eq("application_id", application_id)
                .execute()
            )

            if not docs_response.data:
                return []

            doc_ids = [d["id"] for d in docs_response.data]

            # Then get extractions for those documents
            response = (
                self.client.table("document_extractions")
                .select("*")
                .in_("document_id", doc_ids)
                .execute()
            )
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to get document extractions: {e}")
            return []
