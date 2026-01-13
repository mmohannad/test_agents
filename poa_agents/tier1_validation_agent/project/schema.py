"""
Schema definitions for Tier 1 Validation Agent.
"""

import sys
from pathlib import Path
import json
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, model_validator

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

# Re-export shared schemas
from shared.schema import (
    Application,
    Tier1CheckResult,
    Tier1ValidationResult,
    Tier1CheckCategory,
    CheckStatus,
    Severity,
    TransactionConfig,
)


class Tier1ValidationInput(BaseModel):
    """Input for Tier 1 validation workflow."""
    application_id: str
    transaction_type_code: Optional[str] = None  # Will be loaded from application if not provided
    sak_case_number: Optional[str] = None  # Alternative lookup by case number


class Tier1ValidationOutput(BaseModel):
    """Output from Tier 1 validation workflow."""
    validation_report_id: str
    overall_status: Literal["PASS", "FAIL", "WARNINGS"]
    blocking_failures: int
    warnings: int
    can_proceed_to_tier2: bool
    checks: list[Tier1CheckResult] = Field(default_factory=list)


class WorkflowParams(BaseModel):
    """
    Parameters passed to the workflow.
    
    Supports multiple input formats:
    1. Programmatic: { "input": { "application_id": "..." } }
    2. AgentEx UI: { "description": "...", "content": "{\"application_id\": \"...\"}" }
    3. Simple: { "application_id": "..." }
    """
    input: Optional[Tier1ValidationInput] = None
    inputs_to_rerun: list[str] = Field(default_factory=list)
    
    # AgentEx UI fields
    description: Optional[str] = None
    content: Optional[str] = None
    
    # Direct fields (simple format)
    application_id: Optional[str] = None
    sak_case_number: Optional[str] = None
    
    @model_validator(mode='after')
    def resolve_input(self) -> 'WorkflowParams':
        """Resolve input from various formats."""
        if self.input is not None:
            # Already have structured input
            return self
        
        app_id = self.application_id
        case_number = self.sak_case_number
        
        # Try to parse from content (AgentEx UI JSON mode)
        if self.content:
            try:
                content_data = json.loads(self.content)
                if isinstance(content_data, dict):
                    app_id = app_id or content_data.get("application_id")
                    case_number = case_number or content_data.get("sak_case_number")
            except (json.JSONDecodeError, TypeError):
                # Content is not JSON, might be plain text
                pass
        
        # Build input if we have identifiers
        if app_id or case_number:
            self.input = Tier1ValidationInput(
                application_id=app_id or "",
                sak_case_number=case_number,
            )
        
        return self


# Activity parameter schemas
class LoadApplicationParams(BaseModel):
    application_id: str


class RunCheckParams(BaseModel):
    application_id: str
    check_category: str
    application_data: dict
    transaction_config: dict


class SaveValidationReportParams(BaseModel):
    application_id: str
    result: Tier1ValidationResult


class UpdateWorkflowStatusParams(BaseModel):
    workflow_id: str
    status: str
    error_message: Optional[str] = None

