"""
Temporal Workflow for Tier 1 Validation Agent.
Runs deterministic validation checks on POA applications.

Input Format (JSON):
  {"sak_case_number": "SAK-2024-POA-00001"}
  or
  {"application_id": "uuid-here"}

The workflow auto-starts after receiving input.
"""

import sys
from pathlib import Path
import json
from datetime import timedelta
from typing import Optional, Any

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from agentex.lib.types.acp import CreateTaskParams, SendEventParams
    from agentex.lib.core.temporal.workflows.workflow import BaseWorkflow
    from agentex.lib.core.temporal.types.workflow import SignalName
    from agentex.lib.environment_variables import EnvironmentVariables
    from agentex.lib.utils.logging import make_logger

    from project.schema import Tier1ValidationOutput
    from project.custom_activities import (
        LOAD_APPLICATION,
        LOAD_TRANSACTION_CONFIG,
        RUN_ALL_CHECKS,
        SAVE_VALIDATION_REPORT,
        UPDATE_WORKFLOW_STATUS,
        LOOKUP_APPLICATION_BY_CASE_NUMBER,
    )

environment_variables = EnvironmentVariables.refresh()
logger = make_logger(__name__)

WORKFLOW_NAME = environment_variables.WORKFLOW_NAME or "poa-tier1-validation-workflow"
AGENT_NAME = environment_variables.AGENT_NAME or "poa-tier1-validation-agent"

# Help message shown for invalid input
HELP_MESSAGE = """
**POA Tier 1 Validation Agent**

Please provide input as JSON:

```json
{"sak_case_number": "SAK-2024-POA-00001"}
```

or by application ID:

```json
{"application_id": "your-uuid-here"}
```

Available test case numbers:
- SAK-2024-POA-00001 (General POA - should pass)
- SAK-2024-POA-00002 (Litigation POA - should pass)
- SAK-2024-POA-00003 (Incomplete POA - Tier 1 fail)
- SAK-2024-POA-00004 (Expired POA - Tier 2 fail)
- SAK-2024-POA-00005 (Minor agent POA - Tier 2 fail)
""".strip()


@workflow.defn(name=WORKFLOW_NAME)
class Tier1ValidationWorkflow(BaseWorkflow):
    """
    Workflow for running Tier 1 deterministic validation checks.
    
    Flow:
    1. Load application data from Supabase
    2. Load transaction config for the transaction type
    3. Run all Tier 1 checks
    4. Aggregate results and determine if can proceed to Tier 2
    5. Save validation report to Supabase
    """
    
    def __init__(self):
        super().__init__(display_name=AGENT_NAME)
        self._start_task = False
        self._event_application_id: Optional[str] = None
        self._event_case_number: Optional[str] = None
    
    @workflow.signal(name=SignalName.RECEIVE_EVENT)
    async def on_task_event_send(self, params: SendEventParams) -> None:
        """
        Handle incoming events from UI.
        
        Accepts JSON like:
        - {"application_id": "..."}
        - {"sak_case_number": "..."}
        - {"message": "start_task"} - explicit start
        """
        if params.event.content is None:
            return
            
        if params.event.content.type == "data":
            data = params.event.content.data
            
            # Extract application identifiers if provided
            if data.get("application_id"):
                self._event_application_id = data["application_id"]
                self._start_task = True  # Auto-start when ID provided
            if data.get("sak_case_number"):
                self._event_case_number = data["sak_case_number"]
                self._start_task = True  # Auto-start when case number provided
            
            # Explicit start signal
            if data.get("message") == "start_task":
                self._start_task = True

    def _parse_input_from_params(self, params: dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
        """
        Parse application_id and sak_case_number from various input formats.
        Returns (application_id, sak_case_number).
        """
        application_id = None
        sak_case_number = None
        
        # Check direct params
        if params.get("application_id"):
            return params["application_id"], params.get("sak_case_number")
        if params.get("sak_case_number"):
            return None, params["sak_case_number"]
        
        # Check nested input
        if params.get("input"):
            inp = params["input"]
            if isinstance(inp, dict):
                if inp.get("application_id"):
                    return inp["application_id"], inp.get("sak_case_number")
                if inp.get("sak_case_number"):
                    return None, inp["sak_case_number"]
        
        # Try to parse content/description as JSON (from UI)
        for field in ["content", "description"]:
            if field in params and isinstance(params[field], str):
                text = params[field].strip()
                
                # Skip empty or obviously non-JSON
                if not text:
                    continue
                    
                # Try JSON parse
                if text.startswith("{"):
                    try:
                        data = json.loads(text)
                        if data.get("application_id"):
                            return data["application_id"], data.get("sak_case_number")
                        if data.get("sak_case_number"):
                            return None, data["sak_case_number"]
                    except json.JSONDecodeError:
                        continue
                
                # Check if it looks like a case number (SAK-YYYY-POA-NNNNN)
                if text.upper().startswith("SAK-"):
                    return None, text
        
        return None, None
    
    @workflow.run
    async def on_task_create(self, params: CreateTaskParams) -> str:
        """Main workflow execution - implements BaseWorkflow abstract method."""
        workflow_id = workflow.info().workflow_id
        logger.info(f"[WORKFLOW] Started with params: {params.params}")
        
        # Parse input from task params immediately
        application_id, sak_case_number = self._parse_input_from_params(params.params or {})
        logger.info(f"[WORKFLOW] Parsed input - app_id: {application_id}, case_num: {sak_case_number}")
        
        # If no valid input, return help message
        if not application_id and not sak_case_number:
            logger.info("[WORKFLOW] No valid input, returning help message")
            return HELP_MESSAGE
        
        try:
            # If we have a case number but no ID, look it up
            if not application_id and sak_case_number:
                logger.info(f"Looking up application by case number: {sak_case_number}")
                lookup_result = await workflow.execute_activity(
                    LOOKUP_APPLICATION_BY_CASE_NUMBER,
                    {"sak_case_number": sak_case_number},
                    start_to_close_timeout=timedelta(seconds=30),
                )
                application_id = lookup_result.get("id")
                if not application_id:
                    return f"❌ Application not found for case number: {sak_case_number}\n\n{HELP_MESSAGE}"
            
            logger.info(f"Starting Tier 1 validation for application: {application_id}")
            
            # Step 1: Load application data
            application = await workflow.execute_activity(
                LOAD_APPLICATION,
                {"application_id": application_id},
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            if not application:
                return f"❌ Application not found: {application_id}"
            
            # Get transaction type
            transaction_type_code = application.get("transaction_type_code")
            
            if not transaction_type_code:
                return f"❌ Transaction type code not found for application {application_id}"
            
            # Step 2: Load transaction config
            transaction_config = await workflow.execute_activity(
                LOAD_TRANSACTION_CONFIG,
                {"transaction_type_code": transaction_type_code},
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            # Step 3: Run all Tier 1 checks
            validation_result = await workflow.execute_activity(
                RUN_ALL_CHECKS,
                {
                    "application_id": application_id,
                    "application_data": application,
                    "transaction_config": transaction_config,
                },
                start_to_close_timeout=timedelta(minutes=5),
            )
            
            # Step 4: Save validation report
            report = await workflow.execute_activity(
                SAVE_VALIDATION_REPORT,
                {
                    "application_id": application_id,
                    "result": validation_result,
                },
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            # Step 5: Update workflow status
            await workflow.execute_activity(
                UPDATE_WORKFLOW_STATUS,
                {
                    "workflow_id": workflow_id,
                    "status": "completed",
                },
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            # Build result
            output = Tier1ValidationOutput(
                validation_report_id=report["id"],
                overall_status=validation_result["overall_status"],
                blocking_failures=validation_result["blocking_failures"],
                warnings=validation_result["warnings"],
                can_proceed_to_tier2=validation_result["can_proceed_to_tier2"],
                checks=validation_result.get("checks", []),
            )
            
            # Return formatted result
            result = self._format_summary(output, application.get("sak_case_number"))
            logger.info(f"[WORKFLOW] Validation complete:\n{result}")
            return result
            
        except Exception as e:
            logger.error(f"Tier 1 validation failed: {e}")
            
            # Update workflow status to failed
            try:
                await workflow.execute_activity(
                    UPDATE_WORKFLOW_STATUS,
                    {
                        "workflow_id": workflow_id,
                        "status": "failed",
                        "error_message": str(e),
                    },
                    start_to_close_timeout=timedelta(seconds=30),
                )
            except Exception:
                pass  # Ignore status update errors
            
            return f"❌ Validation failed: {str(e)}"
    
    def _format_summary(self, output: Tier1ValidationOutput, case_number: str = None) -> str:
        """Format a human-readable summary for UI display."""
        status_emoji = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARNINGS": "⚠️",
        }
        
        emoji = status_emoji.get(output.overall_status, "❓")
        
        lines = [
            f"{emoji} **Tier 1 Validation: {output.overall_status}**",
        ]
        
        if case_number:
            lines.append(f"📋 Case: {case_number}")
        
        lines.append("")
        
        if output.blocking_failures > 0:
            lines.append(f"🚫 Blocking failures: {output.blocking_failures}")
        if output.warnings > 0:
            lines.append(f"⚠️ Warnings: {output.warnings}")
        
        lines.append("")
        
        if output.can_proceed_to_tier2:
            lines.append("✅ **Can proceed to Tier 2 (Legal Research)**")
        else:
            lines.append("❌ **Cannot proceed to Tier 2** - fix blocking issues first")
        
        # Add check details
        if output.checks:
            lines.append("")
            lines.append("**Check Results:**")
            for check in output.checks:
                check_emoji = "✅" if check.get("status") == "PASS" else "❌" if check.get("status") == "FAIL" else "⚠️"
                category = check.get("category", "unknown").replace("_", " ").title()
                lines.append(f"- {check_emoji} {category}: {check.get('message', check.get('status'))}")
        
        return "\n".join(lines)

