"""
Custom Activities for Tier 1 Validation Agent.
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add parent directory to path for shared imports
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from temporalio import activity
from agentex.lib.utils.logging import make_logger

from shared.supabase_client import (
    get_supabase_client,
    load_application,
    load_transaction_config,
    save_validation_report,
)
from shared.schema import Tier1CheckResult, Tier1CheckCategory, CheckStatus, Severity

from project.checks.field_completeness import check_field_completeness
from project.checks.format_validation import check_format_validation
from project.checks.cross_field_logic import check_cross_field_logic
from project.checks.document_matching import check_document_matching
from project.checks.business_rules import check_business_rules

logger = make_logger(__name__)

# Activity names
LOAD_APPLICATION = "load_application"
LOAD_TRANSACTION_CONFIG = "load_transaction_config"
LOOKUP_APPLICATION_BY_CASE_NUMBER = "lookup_application_by_case_number"
RUN_ALL_CHECKS = "run_all_checks"
SAVE_VALIDATION_REPORT = "save_validation_report"
UPDATE_WORKFLOW_STATUS = "update_workflow_status"


class CustomActivities:
    """Custom activities for Tier 1 validation."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    @activity.defn(name=LOAD_APPLICATION)
    async def load_application_activity(self, params: dict) -> dict:
        """Load application with all related data."""
        application_id = params.get("application_id")
        logger.info(f"Loading application: {application_id}")
        return load_application(application_id)
    
    @activity.defn(name=LOAD_TRANSACTION_CONFIG)
    async def load_transaction_config_activity(self, params: dict) -> dict:
        """Load transaction configuration."""
        transaction_type_code = params.get("transaction_type_code")
        logger.info(f"Loading transaction config: {transaction_type_code}")
        return load_transaction_config(transaction_type_code)
    
    @activity.defn(name=LOOKUP_APPLICATION_BY_CASE_NUMBER)
    async def lookup_application_by_case_number_activity(self, params: dict) -> dict:
        """Look up application by SAK case number."""
        sak_case_number = params.get("sak_case_number")
        logger.info(f"Looking up application by case number: {sak_case_number}")
        
        result = self.supabase.table("applications").select("id, sak_case_number").eq(
            "sak_case_number", sak_case_number
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return {"id": None, "error": f"Application not found: {sak_case_number}"}
    
    @activity.defn(name=RUN_ALL_CHECKS)
    async def run_all_checks_activity(self, params: dict) -> dict:
        """Run all Tier 1 validation checks."""
        application_id = params.get("application_id")
        application = params.get("application_data")
        config = params.get("transaction_config")
        
        case_number = application.get("sak_case_number", application_id)
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"[TIER 1] Starting validation for: {case_number}")
        logger.info(f"{'='*60}")
        start_time = time.time()
        
        checks: list[Tier1CheckResult] = []
        
        # Define which checks to run (from config or default all)
        check_functions = {
            "field_completeness": check_field_completeness,
            "format_validation": check_format_validation,
            "cross_field_logic": check_cross_field_logic,
            "document_matching": check_document_matching,
            "business_rules": check_business_rules,
        }
        
        # Get configured checks or run all
        configured_checks = config.get("tier1_checks", list(check_functions.keys())) if config else list(check_functions.keys())
        
        logger.info(f"[TIER 1] Will run {len(configured_checks)} checks: {', '.join(configured_checks)}")
        logger.info(f"")
        
        # Run each check
        for i, check_name in enumerate(configured_checks, 1):
            if check_name in check_functions:
                check_display = check_name.replace("_", " ").title()
                logger.info(f"[CHECK {i}/{len(configured_checks)}] Running: {check_display}")
                
                try:
                    result = check_functions[check_name](application, config)
                    checks.append(result)
                    
                    # Log result with emoji
                    status_emoji = "✅" if result.status == CheckStatus.PASS else "❌" if result.status == CheckStatus.FAIL else "⚠️"
                    severity_tag = f" [{result.severity.value}]" if result.status != CheckStatus.PASS else ""
                    logger.info(f"  {status_emoji} Result: {result.status.value}{severity_tag}")
                    logger.info(f"     Message: {result.message}")
                    if result.details:
                        for key, value in result.details.items():
                            logger.info(f"     - {key}: {value}")
                    logger.info(f"")
                    
                except Exception as e:
                    logger.error(f"  ❌ Check failed with exception: {e}")
                    checks.append(Tier1CheckResult(
                        category=Tier1CheckCategory(check_name),
                        status=CheckStatus.FAIL,
                        severity=Severity.NON_BLOCKING,
                        message=f"Check failed with error: {str(e)}",
                    ))
                    logger.info(f"")
        
        # Aggregate results
        blocking_failures = sum(
            1 for c in checks 
            if c.status == CheckStatus.FAIL and c.severity == Severity.BLOCKING
        )
        non_blocking_failures = sum(
            1 for c in checks 
            if c.status == CheckStatus.FAIL and c.severity == Severity.NON_BLOCKING
        )
        warnings = sum(1 for c in checks if c.status == CheckStatus.WARNING)
        passed = sum(1 for c in checks if c.status == CheckStatus.PASS)
        
        # Determine overall status
        if blocking_failures > 0:
            overall_status = "FAIL"
        elif warnings > 0:
            overall_status = "WARNINGS"
        else:
            overall_status = "PASS"
        
        # Can proceed to Tier 2 only if no blocking failures
        can_proceed_to_tier2 = blocking_failures == 0
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Log summary
        logger.info(f"{'='*60}")
        logger.info(f"[TIER 1] VALIDATION SUMMARY for {case_number}")
        logger.info(f"{'='*60}")
        overall_emoji = "✅" if overall_status == "PASS" else "❌" if overall_status == "FAIL" else "⚠️"
        logger.info(f"  {overall_emoji} Overall Status: {overall_status}")
        logger.info(f"  ")
        logger.info(f"  📊 Results:")
        logger.info(f"     ✅ Passed:             {passed}")
        logger.info(f"     ❌ Blocking failures:  {blocking_failures}")
        logger.info(f"     ⚠️  Non-blocking fails: {non_blocking_failures}")
        logger.info(f"     ⚠️  Warnings:           {warnings}")
        logger.info(f"  ")
        if can_proceed_to_tier2:
            logger.info(f"  ✅ Can proceed to Tier 2 (Legal Research)")
        else:
            logger.info(f"  ❌ Cannot proceed to Tier 2 - fix blocking issues first")
        logger.info(f"  ")
        logger.info(f"  ⏱️  Execution time: {execution_time_ms}ms")
        logger.info(f"{'='*60}")
        logger.info(f"")
        
        return {
            "application_id": application_id,
            "overall_status": overall_status,
            "checks": [c.model_dump() for c in checks],
            "blocking_failures": blocking_failures,
            "warnings": warnings,
            "can_proceed_to_tier2": can_proceed_to_tier2,
            "execution_time_ms": execution_time_ms,
        }
    
    @activity.defn(name=SAVE_VALIDATION_REPORT)
    async def save_validation_report_activity(self, params: dict) -> dict:
        """Save validation report to Supabase."""
        application_id = params.get("application_id")
        result_data = params.get("result")
        
        logger.info(f"Saving validation report for: {application_id}")
        
        # Map to validation_reports table columns
        report = {
            "application_id": application_id,
            "tier": "tier1",
            "verdict": result_data.get("overall_status"),
            "rules_passed": len([c for c in result_data.get("checks", []) if c.get("status") == "PASS"]),
            "rules_failed": result_data.get("blocking_failures", 0),
            "rules_warned": result_data.get("warnings", 0),
            "blocking_failures": result_data.get("blocking_failures", 0),
            "warnings_count": result_data.get("warnings", 0),
            "can_proceed_to_tier2": result_data.get("can_proceed_to_tier2", False),
            "checks_run": result_data.get("checks", []),
            "processing_time_ms": result_data.get("execution_time_ms"),
            "agent_name": "poa-tier1-validation-agent",
        }
        
        return save_validation_report(report)
    
    @activity.defn(name=UPDATE_WORKFLOW_STATUS)
    async def update_workflow_status_activity(self, params: dict) -> None:
        """Update workflow status (for tracking)."""
        workflow_id = params.get("workflow_id")
        status = params.get("status")
        error_message = params.get("error_message")
        
        logger.info(f"Updating workflow {workflow_id} status to: {status}")
        
        # This could update a workflows table or send an event
        # For now, just log it
        if error_message:
            logger.error(f"Workflow {workflow_id} failed: {error_message}")

