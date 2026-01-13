# Agentex: Complete Framework Guide

> **Agentex** is an open-source agentic infrastructure platform for building, deploying, and scaling intelligent AI agents. It handles all infrastructure concerns while letting you write pure Python code.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Architecture](#core-architecture)
3. [Agent Types](#agent-types)
4. [Core Concepts](#core-concepts)
5. [Configuration Files](#configuration-files)
6. [Getting Started](#getting-started)
7. [Example Agents](#example-agents)
8. [Deployment](#deployment)
9. [API Reference](#api-reference)

---

## Overview

### What is Agentex?

Agentex is an **unopinionated Python framework** for building AI agents at any complexity level:

| Level | Description | Example |
|-------|-------------|---------|
| 1-2 | Simple chatbots, Q&A | FAQ bots, lookups |
| 3 | Stateful assistants | Multi-turn conversations |
| 4-5 | Autonomous agents | Complex workflows, orchestration |

**Core Philosophy**: "Agents are just code" - write standard Python that adheres to the Agent-to-Client Protocol (ACP), and Agentex handles:
- Message routing and streaming
- State persistence
- Task lifecycle management
- Deployment and scaling
- Observability and tracing

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
│         (Web UIs, APIs, Other Systems, Agentex UI)              │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ REST API / WebSocket
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTEX SERVER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  FastAPI    │  │   Message   │  │    Task Orchestration   │  │
│  │  Port 5003  │  │   Routing   │  │    State Management     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  PostgreSQL │  │    Redis    │  │        Temporal         │  │
│  │   (state)   │  │  (streams)  │  │      (workflows)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ ACP Protocol
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      YOUR AGENTS                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│   │  Sync Agent  │  │ Async Agent  │  │  Temporal Workflow   │  │
│   │   (simple)   │  │   (base)     │  │     (durable)        │  │
│   └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Architecture

### Agent-to-Client Protocol (ACP)

The ACP is the standardized interface that all agents implement. Clients invoke any agent the same way, regardless of internal complexity.

```python
from agentex.lib.sdk.fastacp.fastacp import FastACP

# Create ACP server (type determines which handlers are available)
acp = FastACP.create(acp_type="sync")  # or "agentic"
```

### Backend Services (Docker Compose)

When running `make dev` in the agentex directory:

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Primary database |
| PostgreSQL (Temporal) | 5433 | Temporal workflow database |
| Redis | 6379 | Streams and caching |
| MongoDB | 27017 | Document storage |
| Temporal Server | 7233 | Workflow orchestration |
| Temporal Web UI | 8080 | Workflow monitoring |
| FastAPI Backend | 5003 | Agentex API server |

### Frontend (Agentex UI)

Modern Next.js 15 / React 19 interface for testing agents:
- Agent discovery and listing
- Task creation and history
- Real-time chat interface
- Message streaming
- Execution traces

---

## Agent Types

Agentex supports three agent architectures with different tradeoffs:

### 1. Sync Agents (Simplest)

**Use for**: Simple chatbots, FAQs, lookups, single request-response

**Handlers**: `@acp.on_message_send`

**Complexity**: ~30 lines, 1 file

```python
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.sdk.adk import adk
from agentex.lib.types.acp import SendMessageParams
from agentex.lib.types.task_message import TextContent, MessageAuthor

acp = FastACP.create(acp_type="sync")

@acp.on_message_send
async def handle_message(params: SendMessageParams):
    """Handle incoming message and return response."""
    user_message = params.content.content
    task = params.task

    # Your logic here - call LLM, search, etc.
    response = f"You said: {user_message}"

    return TextContent(
        author=MessageAuthor.AGENT,
        content=response
    )
```

**Key Characteristics**:
- Single handler for all messages
- Blocking synchronous execution
- Automatic task lifecycle management
- Return value becomes the response message

---

### 2. Async Agents - Base (Intermediate)

**Use for**: Complex stateful apps, multi-step workflows, concurrent request handling

**Handlers**: `@acp.on_task_create`, `@acp.on_task_event_send`, `@acp.on_task_cancel`

**Complexity**: ~80 lines, 1 file

```python
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.sdk.adk import adk
from agentex.lib.types.acp import CreateTaskParams, SendEventParams, CancelTaskParams
from agentex.lib.types.task_message import TextContent, MessageAuthor

acp = FastACP.create(acp_type="agentic")

@acp.on_task_create
async def handle_task_create(params: CreateTaskParams):
    """Initialize task state and send initial message."""
    task = params.task

    await adk.messages.create(
        task_id=task.id,
        content=TextContent(
            author=MessageAuthor.AGENT,
            content="Task created! Send me events to process."
        )
    )

@acp.on_task_event_send
async def handle_event_send(params: SendEventParams):
    """Process incoming events."""
    task = params.task
    event_content = params.content

    # Process event and create response message
    await adk.messages.create(
        task_id=task.id,
        content=TextContent(
            author=MessageAuthor.AGENT,
            content=f"Processed event: {event_content}"
        )
    )

@acp.on_task_cancel
async def handle_task_cancel(params: CancelTaskParams):
    """Clean up when task is cancelled."""
    pass
```

**Key Characteristics**:
- Non-blocking asynchronous execution
- Explicit message creation via `adk.messages.create()`
- Handle multiple concurrent requests
- Full control over task lifecycle

---

### 3. Async Agents - Temporal (Advanced)

**Use for**: Enterprise integrations, multi-day processes, durable workflows, crash recovery

**Structure**: Workflow class inheriting from `BaseWorkflow`

**Complexity**: 150+ lines, 4 files

```python
# workflow.py
from temporalio import workflow
from agentex.lib.sdk.temporal import BaseWorkflow
from agentex.lib.types.acp import CreateTaskParams, SendEventParams
from project.custom_activities import process_document, generate_report

@workflow.defn(name="my-agent-workflow")
class MyAgentWorkflow(BaseWorkflow):
    """Durable workflow with automatic state persistence."""

    def __init__(self):
        super().__init__(display_name="my-agent")
        self.processed_items = []
        self.status = "initialized"

    @workflow.run
    async def run(self, params: CreateTaskParams):
        """Main workflow execution - survives crashes."""
        self.status = "running"

        # Execute activity (runs in separate process, retries on failure)
        result = await workflow.execute_activity(
            process_document,
            params.input.document_id,
            start_to_close_timeout=timedelta(minutes=30),
        )

        self.processed_items.append(result)

        # Execute another activity
        report = await workflow.execute_activity(
            generate_report,
            self.processed_items,
            start_to_close_timeout=timedelta(minutes=10),
        )

        self.status = "completed"
        return {"report": report}

    @workflow.signal(name="receive_event")
    async def on_event(self, params: SendEventParams):
        """Handle events sent to running workflow."""
        # Process event, update state
        pass
```

```python
# custom_activities.py
from temporalio import activity

@activity.defn(name="process_document")
async def process_document(document_id: str) -> dict:
    """Long-running activity - automatically retried on failure."""
    # Fetch document, process with LLM, etc.
    return {"document_id": document_id, "status": "processed"}

@activity.defn(name="generate_report")
async def generate_report(items: list) -> str:
    """Generate report from processed items."""
    return f"Report with {len(items)} items"
```

```python
# run_worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from project.workflow import MyAgentWorkflow
from project.custom_activities import process_document, generate_report

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="my_agent_queue",
        workflows=[MyAgentWorkflow],
        activities=[process_document, generate_report],
    )

    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Key Characteristics**:
- Durable execution (survives crashes, restarts)
- Automatic state persistence via workflow variables
- Built-in retry logic for activities
- Complex multi-step workflows
- Distributed coordination

---

### Choosing an Agent Type

| Factor | Sync | Async Base | Async Temporal |
|--------|------|------------|----------------|
| **Complexity** | Low | Medium | High |
| **Concurrency** | Single request | Multiple requests | Distributed |
| **State** | Request-scoped | ADK state API | Workflow variables |
| **Durability** | None | Optional | Automatic |
| **Use Cases** | Chatbots, lookups | Stateful apps | Enterprise workflows |
| **Recovery** | Restart | Manual | Automatic |
| **Lines of Code** | ~30 | ~80 | 150+ |

---

## Core Concepts

### Tasks

A **Task** represents a conversation or workflow instance:

```python
class TaskEntity:
    id: str                    # Unique identifier
    name: str | None           # Optional display name
    status: TaskStatus         # RUNNING, COMPLETED, FAILED, etc.
    params: dict[str, Any]     # Input parameters
    task_metadata: dict        # Custom metadata
    created_at: datetime
    updated_at: datetime
```

### Messages

**Messages** are individual communications within a task:

```python
# Text message
TextContent(
    author=MessageAuthor.AGENT,  # or USER
    content="Hello, how can I help?"
)

# Data message
DataContent(
    author=MessageAuthor.AGENT,
    data={"key": "value", "results": [...]}
)

# Tool request (agent asking to use a tool)
ToolRequestContent(
    author=MessageAuthor.AGENT,
    tool_name="search",
    tool_arguments={"query": "python async"}
)

# Tool response
ToolResponseContent(
    author=MessageAuthor.USER,
    tool_name="search",
    tool_response={"results": [...]}
)
```

### Events

**Events** are ephemeral notifications (not persisted):

- Tell agents "there's work to do"
- Trigger `@acp.on_task_event_send` handlers
- You decide what becomes a message

```python
# Sending event to an agent
await adk.events.send(
    task_id=task.id,
    agent_name="my-agent",
    content=DataContent(data={"action": "process"})
)
```

### State

**State** provides persistent key-value storage per (task_id, agent_id):

```python
from pydantic import BaseModel

class MyState(BaseModel):
    conversation_history: list[dict]
    turn_number: int = 0

# Create state
await adk.state.create(
    task_id=task.id,
    agent_id=agent.id,
    state=MyState(conversation_history=[], turn_number=0)
)

# Retrieve state
task_state = await adk.state.get_by_task_and_agent(
    task_id=task.id,
    agent_id=agent.id
)
state = MyState.model_validate(task_state.state)

# Update state
state.turn_number += 1
await adk.state.update(task_state.id, state)
```

### Streaming

Real-time message delivery as agents generate content:

```python
@acp.on_message_send
async def handle_message(params: SendMessageParams):
    # Yield partial updates for streaming
    for chunk in generate_response_chunks():
        yield TaskMessageUpdate(
            content=TextContent(
                author=MessageAuthor.AGENT,
                content=chunk
            )
        )

    # Final return is the complete message
    return TextContent(
        author=MessageAuthor.AGENT,
        content=complete_response
    )
```

---

## Configuration Files

### manifest.yaml

Defines how your agent is built and configured:

```yaml
# BUILD CONFIGURATION
build:
  context:
    root: ../                              # Build context root
    include_paths:
      - my-agent                           # Directories to include
    dockerfile: my-agent/Dockerfile        # Path to Dockerfile
    dockerignore: my-agent/.dockerignore   # Optional

# LOCAL DEVELOPMENT
local_development:
  agent:
    port: 8000                             # ACP server port
    host_address: host.docker.internal     # Docker host address
  paths:
    acp: project/acp.py                    # Path to ACP server
    worker: project/run_worker.py          # Temporal worker (optional)

# AGENT CONFIGURATION
agent:
  name: my-agent                           # Unique agent name
  acp_type: sync                           # "sync" or "agentic"
  description: "Description of what this agent does"

  # Temporal configuration (for agentic agents)
  temporal:
    enabled: true
    workflows:
      - name: my-agent-workflow
        queue_name: my_agent_queue

  # Credentials (injected as environment variables)
  credentials:
    - env_var_name: OPENAI_API_KEY
      secret_name: openai-api-key
      secret_key: api-key
    - env_var_name: DATABASE_URL
      secret_name: database-credentials
      secret_key: url

  # Environment variables
  env:
    LOG_LEVEL: "INFO"
    MAX_RETRIES: "3"

# DEPLOYMENT CONFIGURATION
deployment:
  image:
    repository: "gcr.io/my-project/my-agent"
    tag: "latest"
  imagePullSecrets:
    - name: "gcr-pull-secret"
  global:
    replicaCount: 1
    resources:
      requests:
        cpu: "500m"
        memory: "1Gi"
      limits:
        cpu: "1000m"
        memory: "2Gi"
```

### environments.yaml

Defines per-environment settings:

```yaml
schema_version: "v1"

environments:
  dev:
    kubernetes:
      namespace: "my-team-dev"
    auth:
      principal:
        user_id: "dev-user-uuid"
        account_id: "dev-account-uuid"
    helm_overrides:
      replicaCount: 2
      env:
        - name: LOG_LEVEL
          value: "DEBUG"
      # Temporal worker config
      temporal-worker:
        enabled: true
        replicaCount: 2

  production:
    kubernetes:
      namespace: "my-team-prod"
    auth:
      principal:
        user_id: "prod-user-uuid"
        account_id: "prod-account-uuid"
    helm_overrides:
      replicaCount: 5
      resources:
        requests:
          cpu: "1000m"
          memory: "2Gi"
      temporal-worker:
        enabled: true
        replicaCount: 10
```

### pyproject.toml

Python project configuration:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-agent"
version = "0.1.0"
description = "An Agentex agent"
requires-python = ">=3.12"

dependencies = [
    "agentex-sdk",                # Core Agentex SDK
    "openai>=1.0.0",              # OpenAI SDK
    "pydantic>=2.0.0",            # Data validation
    "python-dotenv>=1.0.0",       # Environment variables
    "httpx",                      # Async HTTP client
    "temporalio>=1.0.0",          # Temporal SDK (for agentic)
]

[tool.hatch.build.targets.wheel]
packages = ["project"]
```

### Dockerfile

Container definition:

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.6.4 /uv /uvx /bin/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN uv pip install --system --upgrade pip setuptools wheel
ENV UV_HTTP_TIMEOUT=1000

# Copy and install Python dependencies
COPY my-agent/pyproject.toml /app/my-agent/pyproject.toml
WORKDIR /app/my-agent
RUN uv pip install --system .

# Copy source code
COPY my-agent/project /app/my-agent/project
ENV PYTHONPATH=/app

# Run ACP server (default)
CMD ["uvicorn", "project.acp:acp", "--host", "0.0.0.0", "--port", "8000"]

# For Temporal worker: override CMD
# CMD ["python", "-m", "project.run_worker"]
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- `uv` package manager
- Agentex CLI (`agentex`)

### 1. Start Backend Services

```bash
# Clone and start Agentex
cd /path/to/scale-agentex/agentex
uv venv && source .venv/bin/activate && uv sync
make dev

# This starts: PostgreSQL, Redis, MongoDB, Temporal, FastAPI (port 5003)
```

### 2. Start Frontend (Optional)

```bash
cd /path/to/scale-agentex/agentex-ui
npm install
npm run dev
# Next.js dev server on localhost:3000
```

### 3. Create New Agent

```bash
# Initialize agent from template
agentex init

# Follow prompts to configure:
# - Agent name
# - Agent type (sync/agentic)
# - Port number
```

### 4. Develop Locally

**For Sync Agent:**

```bash
cd my-agent
uv venv && source .venv/bin/activate && uv sync

# Set environment
export ENVIRONMENT=development

# Run agent
agentex agents run --manifest manifest.yaml
# Agent runs on configured port (e.g., 8000)
```

**For Agentic Agent (with Temporal):**

Terminal 1 - ACP Server:
```bash
cd my-agent
export ENVIRONMENT=development
agentex agents run --manifest manifest.yaml
```

Terminal 2 - Temporal Worker:
```bash
cd my-agent
source .venv/bin/activate
python -m project.run_worker
```

### 5. Test Agent

Open Agentex UI at `http://localhost:3000`:
1. Find your agent in the agent list
2. Create a new task
3. Send messages and observe responses

Or use the API directly:
```bash
# Create task
curl -X POST http://localhost:5003/tasks \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "my-agent", "params": {}}'

# Send message
curl -X POST http://localhost:5003/messages \
  -H "Content-Type: application/json" \
  -d '{"task_id": "...", "content": {"type": "text", "content": "Hello"}}'
```

---

## Example Agents

### Sync Agent: Search Agent

Simple semantic search over documents:

```python
# project/acp.py
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.sdk.adk import adk
from agentex.lib.types.acp import SendMessageParams
from agentex.lib.types.task_message import TextContent, MessageAuthor
from pydantic import BaseModel

acp = FastACP.create(acp_type="sync")

class StateModel(BaseModel):
    input_list: list[dict] = []
    turn_number: int = 0

@acp.on_message_send
async def handle_message_send(params: SendMessageParams):
    message_text = params.content.content
    task = params.task
    agent = params.agent

    # Get or create state
    task_state = await adk.state.get_by_task_and_agent(
        task_id=task.id, agent_id=agent.id
    )
    if not task_state:
        state = StateModel()
        task_state = await adk.state.create(
            task_id=task.id, agent_id=agent.id, state=state
        )
    else:
        state = StateModel.model_validate(task_state.state)

    # Add user message
    state.input_list.append({"role": "user", "content": message_text})

    # Call LLM with tools
    result = await adk.providers.openai.run_agent_auto_send(
        task_id=task.id,
        input_list=state.input_list,
        agent_name="Search Agent",
        agent_instructions="You help users search for information...",
        model="gpt-4o-mini",
        tools=[search_tool],
    )

    # Update state
    state.input_list = result.to_input_list()
    state.turn_number += 1
    await adk.state.update(task_state.id, state)

    # Return response
    return TextContent(
        author=MessageAuthor.AGENT,
        content=result.final_response
    )
```

### Agentic Agent: Benchmarking Workflow

Complex multi-stage document comparison:

```python
# project/workflow.py
from temporalio import workflow
from datetime import timedelta
from agentex.lib.sdk.temporal import BaseWorkflow
from project.custom_activities import (
    search_stage_1, search_stage_2, search_stage_3, run_comparison
)
from project.schema import (
    BenchmarkingWorkflowParams, SearchWorkflowParams, ComparisonWorkflowParams
)

@workflow.defn(name="benchmarking-agent")
class BenchmarkingWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__(display_name="benchmarking-agent")
        self.failed_countries = set()
        self.total_tokens = 0

    @workflow.run
    async def run(self, params: BenchmarkingWorkflowParams):
        countries = params.input.countries
        storage_path = params.input.storage_path

        # Process countries in parallel
        search_tasks = []
        for country in countries:
            search_tasks.append(
                workflow.execute_child_workflow(
                    SearchWorkflow.run,
                    SearchWorkflowParams(country=country, storage_path=storage_path),
                    id=f"search-{country}",
                )
            )

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Process comparison results
        comparison_tasks = []
        for result in search_results:
            if isinstance(result, Exception):
                continue
            for url in result.urls:
                comparison_tasks.append(
                    workflow.execute_activity(
                        run_comparison,
                        ComparisonWorkflowParams(url=url, storage_path=storage_path),
                        start_to_close_timeout=timedelta(hours=2),
                    )
                )

        comparisons = await asyncio.gather(*comparison_tasks, return_exceptions=True)

        return {
            "search_results": search_results,
            "comparisons": comparisons,
            "failed_countries": list(self.failed_countries),
            "total_tokens": self.total_tokens,
        }


@workflow.defn(name="search-workflow")
class SearchWorkflow(BaseWorkflow):
    @workflow.run
    async def run(self, params: SearchWorkflowParams):
        # Stage 1: Generate search terms
        search_terms = await workflow.execute_activity(
            search_stage_1,
            params,
            start_to_close_timeout=timedelta(minutes=10),
        )

        # Stage 2: Execute searches
        raw_results = await workflow.execute_activity(
            search_stage_2,
            {"country": params.country, "terms": search_terms},
            start_to_close_timeout=timedelta(minutes=30),
        )

        # Stage 3: Classify and rank
        ranked_results = await workflow.execute_activity(
            search_stage_3,
            {"country": params.country, "results": raw_results},
            start_to_close_timeout=timedelta(minutes=20),
        )

        return ranked_results
```

### Orchestrator Pattern

Coordinating multiple child agents:

```python
# project/workflow.py
from temporalio import workflow
from agentex.lib.sdk.temporal import BaseWorkflow
from agentex.lib.sdk.adk import adk

@workflow.defn(name="orchestrator-workflow")
class OrchestratorWorkflow(BaseWorkflow):
    @workflow.run
    async def run(self, params):
        application_id = params.input.application_id

        # Step 1: Run Tier 1 validation
        tier1_result = await self.invoke_child_agent(
            agent_name="tier1-validation-agent",
            input={"application_id": application_id}
        )

        if not tier1_result.can_proceed:
            return {"status": "failed", "reason": "tier1_validation"}

        # Step 2: Run Tier 2 legal research
        tier2_result = await self.invoke_child_agent(
            agent_name="legal-research-agent",
            input={
                "application_id": application_id,
                "validation_report": tier1_result.report
            }
        )

        # Step 3: Make final decision
        return {
            "status": "completed",
            "tier1": tier1_result,
            "tier2": tier2_result,
        }

    async def invoke_child_agent(self, agent_name: str, input: dict):
        """Helper to invoke child agent and wait for result."""
        task = await adk.tasks.create(
            agent_name=agent_name,
            params={"input": input}
        )

        await adk.events.send(
            task_id=task.id,
            agent_name=agent_name,
            content=DataContent(data={"action": "start"})
        )

        # Wait for completion (simplified)
        return await self.wait_for_task_completion(task.id)
```

---

## Deployment

### Build and Push Image

```bash
# Build container image
agentex agents build \
  --manifest manifest.yaml \
  --registry gcr.io/my-project \
  --push
```

### Sync Secrets

```bash
# Sync secrets from vault to Kubernetes
agentex secrets sync \
  --manifest manifest.yaml \
  --cluster production \
  --namespace my-agent-namespace \
  --values secrets.yaml \
  --no-interactive
```

### Deploy to Kubernetes

```bash
# Deploy agent to environment
agentex agents deploy \
  --environment prod \
  --manifest manifest.yaml
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy Agent

on:
  push:
    branches: [main]
    paths:
      - 'my-agent/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and Push
        run: |
          agentex agents build \
            --manifest my-agent/manifest.yaml \
            --registry gcr.io/${{ secrets.GCP_PROJECT }} \
            --push

      - name: Deploy to Dev
        run: |
          agentex agents deploy \
            --environment dev \
            --manifest my-agent/manifest.yaml
```

---

## API Reference

### REST Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/agents` | GET | List all agents |
| `/agents` | POST | Register agent |
| `/agents/{id}` | GET | Get agent by ID |
| `/agents/name/{name}` | GET | Get agent by name |
| `/tasks` | GET | List tasks |
| `/tasks` | POST | Create task |
| `/tasks/{id}` | GET | Get task by ID |
| `/messages` | POST | Create message |
| `/messages` | GET | List messages |
| `/events` | POST | Send event |
| `/states` | POST/GET/DELETE | Manage state |
| `/spans` | GET | Get execution traces |
| `/swagger` | - | Interactive API docs |

### Python SDK (ADK)

```python
from agentex.lib.sdk.adk import adk

# Tasks
task = await adk.tasks.create(agent_name="my-agent", params={})
task = await adk.tasks.get(task_id)

# Messages
await adk.messages.create(task_id, content=TextContent(...))
messages = await adk.messages.list(task_id)

# Events
await adk.events.send(task_id, agent_name, content=DataContent(...))

# State
await adk.state.create(task_id, agent_id, state={})
state = await adk.state.get_by_task_and_agent(task_id, agent_id)
await adk.state.update(state_id, new_state)

# Providers (LLM)
result = await adk.providers.openai.run_agent_auto_send(
    task_id=task_id,
    input_list=[...],
    agent_name="My Agent",
    agent_instructions="...",
    model="gpt-4o",
    tools=[...],
)
```

---

## Key Design Patterns

1. **Unopinionated Architecture**: Pure Python - use any library, model, database
2. **Unified Interface**: All agents accessible via same API regardless of type
3. **Separation of Concerns**: Domain logic isolated from infrastructure
4. **Async-First Design**: Built for scalability and real-time streaming
5. **State Isolation**: Each (task_id, agent_id) pair has independent state
6. **Event-Driven**: Async agents process events without blocking
7. **Durable Workflows**: Temporal integration for crash-resistant execution
8. **Cloud-Agnostic**: Kubernetes-native, deployable anywhere

---

## Repository Structure

```
your-agent/
├── manifest.yaml          # Agent configuration
├── environments.yaml      # Per-environment settings
├── pyproject.toml         # Python dependencies
├── Dockerfile             # Container definition
├── .dockerignore          # Build filtering
└── project/               # Source code
    ├── acp.py             # ACP server (entry point)
    ├── workflow.py        # Temporal workflow (if agentic)
    ├── run_worker.py      # Temporal worker runner
    ├── custom_activities.py  # Temporal activities
    ├── tools.py           # Tool definitions
    └── schema.py          # Data models
```

---

## Resources

- **Main Framework**: `/Users/musa.mohannad/dev/work/scale-agentex`
- **Example Agents**: `/Users/musa.mohannad/dev/work/agentex-agents`
- **Your Agents**: `/Users/musa.mohannad/dev/work/test_agents`
- **Documentation**: `/Users/musa.mohannad/dev/work/scale-agentex/agentex/docs/`
- **API Docs**: `http://localhost:5003/swagger` (when running)
- **Temporal UI**: `http://localhost:8080` (when running)
