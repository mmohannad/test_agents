"""
Temporal Worker for Tier 1 Validation Agent.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for shared imports (must be before other imports)
_parent_dir = Path(__file__).parent.parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

import dotenv

# Load environment variables early
env_path = Path(__file__).parent.parent / ".env"
dotenv.load_dotenv(env_path)

from agentex.lib.core.temporal.activities import get_all_activities
from agentex.lib.core.temporal.workers.worker import AgentexWorker
from agentex.lib.utils.logging import make_logger
from agentex.lib.utils.debug import setup_debug_if_enabled
from agentex.lib.environment_variables import EnvironmentVariables

from project.workflow import Tier1ValidationWorkflow
from project.custom_activities import CustomActivities

environment_variables = EnvironmentVariables.refresh()
logger = make_logger(__name__)


async def main():
    """Run the Temporal worker."""
    # Setup debug mode if enabled
    setup_debug_if_enabled()
    
    task_queue_name = environment_variables.WORKFLOW_TASK_QUEUE
    if task_queue_name is None:
        raise ValueError("WORKFLOW_TASK_QUEUE is not set")
    
    logger.info(f"Starting Tier 1 Validation Worker")
    logger.info(f"  Queue: {task_queue_name}")
    
    # Create worker
    worker = AgentexWorker(task_queue=task_queue_name)
    
    # Get AgentEx built-in activities
    agentex_activities = get_all_activities()
    
    # Initialize custom activities
    custom_activities = CustomActivities()
    
    # Run worker
    await worker.run(
        activities=[
            # Custom activities
            custom_activities.load_application_activity,
            custom_activities.load_transaction_config_activity,
            custom_activities.lookup_application_by_case_number_activity,
            custom_activities.run_all_checks_activity,
            custom_activities.save_validation_report_activity,
            custom_activities.update_workflow_status_activity,
            # AgentEx built-in activities
            *agentex_activities,
        ],
        workflows=[
            Tier1ValidationWorkflow,
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())

