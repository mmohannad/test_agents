# Project Plan: POA Agent UI Shell

> **Goal:** Build a thin UI shell over the existing agent pipeline so that any user can supply an Application Number, inspect the agent context (structured + unstructured), run the agents, and see results — without re-implementing agent logic.

---

## Implementation Status

### Completed

| Item | Phase | Status |
|------|-------|--------|
| Next.js 16 project scaffolded (App Router, React 19, Tailwind v4, TS strict) | Phase 2 | Done |
| `ControlRow` component — app ID input, Load, Run Agents, agent status display, timestamps, counters | Phase 2 | Done |
| `StructuredPanel` — renders application, parties, capacity_proofs as grouped editable cards | Phase 2+3 | Done |
| `UnstructuredPanel` — tabbed document extractions with metadata, raw text, extracted fields | Phase 2+3 | Done |
| `EditableField` — click-to-edit inline fields (scalar, multiline, RTL support) | Phase 3 | Done |
| `JsonViewer` — collapsible raw JSON viewer on both panels | Phase 2 | Done |
| Supabase direct context loading (`loadContext` in `lib/supabase.ts`) — same queries as condenser agent | Phase 2 | Done |
| Mutation helpers for structured data (application, parties, capacity_proofs) | Phase 3 | Done |
| Mutation helpers for unstructured data (extraction metadata, extracted_fields including nested objects/arrays) | Phase 3 | Done |
| Tier 1 deterministic validation (`lib/validation.ts`) — expiry checks, cross-validation (structured↔unstructured), missing data | Phase 2 | Done |
| `ValidationModal` — modal overlay showing errors/warnings, blocks agents on errors, allows proceeding with warnings | Phase 2 | Done |
| Test data: 2 QID document+extraction records for app `a0000001` in Supabase | — | Done |
| Agent API client (`lib/agentApi.ts`) — JSON-RPC 2.0 over `POST /api` via server-side proxy | Phase 2 | Done |
| Next.js API route proxy (`app/api/agent/condenser/route.ts`) — avoids CORS, proxies to `localhost:8012/api` | Phase 2 | Done |
| Wired Run Agents → Tier 1 validation → condenser agent call → results display | Phase 2 | Done |
| `ResultsDrawer` — structured report with dedicated section components + raw JSON tab | Phase 2 | Done |
| JSON extraction from markdown — `parseAgentContent` extracts embedded JSON from agent's `<details>` block | Phase 2 | Done |
| Next.js API route proxy (`app/api/agent/legal-search/route.ts`) — proxies to `localhost:8013/api` | Phase 2 | Done |
| Legal Search Agent integration — condenser → legal search auto-chain (Mode B, in-memory) | Phase 2 | Done |
| Per-agent state management — separate status/result/error for condenser and legal search | Phase 2 | Done |
| Two-step progress in ControlRow — "Step 1/2: Running condenser..." → "Step 2/2: Running legal search..." | Phase 2 | Done |
| Legal Opinion tab in ResultsDrawer — DecisionBanner, IssuesAnalyzed, Citations, RetrievalMetrics sections | Phase 2 | Done |
| Three-tab ResultsDrawer — Legal Brief, Legal Opinion, Raw JSON tabs with loading/error states | Phase 2 | Done |
| `dev.sh` — single-command startup script for all services (condenser, legal search, frontend) | — | Done |

### Discovered: ACP Protocol Details

During implementation, the following was discovered about the AgentEx ACP protocol:

| Detail | Value |
|--------|-------|
| **HTTP endpoint** | `POST /api` (NOT `/acp/send` as initially assumed) |
| **Protocol** | JSON-RPC 2.0 with `method: "message/send"` |
| **Required params** | `agent` (id, name, acp_type, description, created_at, updated_at), `task` (id), `content` (type, author, content) |
| **Response nesting** | `result.content.content` — `result` is a `SendMessageResponse`, `result.content` is a `TextContent` object, `result.content.content` is the actual string |
| **Agent output format** | Markdown string with embedded JSON in `<details><summary>...</summary>\n```json\n{...}\n```\n</details>` |

### Discovered: Mode B Does NOT Save to DB

In Mode B (frontend path), the condenser agent does **not** save the Legal Brief to the database. This is because `application_id` is `None` when data is sent directly in the payload, and the `save_legal_brief()` call is guarded by `if application_id:` (condenser `acp.py:291`). The entire condenser → legal search chain runs in-memory through the frontend — no DB writes for legal briefs or opinions in Mode B.

### Not Started

| Item | Phase | Notes |
|------|-------|-------|
| Context API (`shared/context_api.py`) | Phase 1 | Frontend uses direct Supabase for now |
| `return_format` branch in `condenser_agent/project/acp.py` | Phase 1 | Agent currently returns markdown; frontend parses embedded JSON from markdown |
| `return_format` + `include_artifacts` branch in `legal_search_agent/project/acp.py` | Phase 1 | Not yet needed |
| Dockerfiles for condenser + legal search + context API | Phase 1 | |
| `docker-compose.yml` | Phase 1 | |
| `RetrievalTraceView`, `LogsView` components | Phase 2 | Optional deep-dive views |
| Dirty-state tracking (highlight edited fields) | Phase 3 | |
| Diff summary before running agents ("You modified 3 fields") | Phase 3 | |
| Cloud VM deployment | Phase 4 | |
| Nginx reverse proxy + TLS | Phase 4 | |

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Backend / Agent Changes](#2-backend--agent-changes)
3. [Deployment Options](#3-deployment-options)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Implementation Steps](#5-implementation-steps)

---

## 1. Current State Analysis

### How data flows today (CLI / Agentex UI)

```
User provides application_id
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│               CONDENSER AGENT (port 8012, sync)                  │
│                                                                  │
│  1. Receives {"application_id": "..."} via ACP message/send     │
│  2. Queries Supabase DIRECTLY inside agent:                      │
│       ├─ applications      (get_application)                     │
│       ├─ parties            (get_parties)                        │
│       ├─ capacity_proofs    (get_capacity_proofs)                │
│       ├─ documents          (get_document_extractions)           │
│       └─ document_extractions (joined via document_id)           │
│  3. Assembles case_data dict:                                    │
│       { application, parties, capacity_proofs }                  │
│     and document_extractions list                                │
│  4. Sends both to LLM via ANALYSIS_PROMPT_TEMPLATE              │
│  5. Parses JSON response → Legal Brief                           │
│  6. Saves Legal Brief to legal_briefs table                      │
│  7. Returns formatted markdown                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │  Legal Brief stored in DB
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│           LEGAL SEARCH AGENT (port 8013, sync)                   │
│                                                                  │
│  1. Receives {"application_id": "..."}                           │
│  2. Loads Legal Brief from legal_briefs table                    │
│  3. Phase 1 — Decomposer: break into sub-issues                 │
│  4. Phase 2 — Agentic RAG: HyDE + iterative retrieval           │
│  5. Phase 3 — Synthesizer: produce legal opinion                 │
│  6. Saves opinion to legal_opinions table                        │
│  7. Saves retrieval artifact to retrieval_eval_artifacts         │
│  8. Returns formatted markdown                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key files

| File | What it does |
|------|-------------|
| `condenser_agent/project/acp.py` | ACP handler, prompts, data assembly, LLM call, output formatting |
| `condenser_agent/project/supabase_client.py` | 7 DB queries: application, parties, capacity_proofs, documents, document_extractions, case_objects, fact_sheets |
| `condenser_agent/project/llm_client.py` | OpenAI AsyncClient wrapper (chat only) |
| `legal_search_agent/project/acp.py` | ACP handler, orchestrates decompose → retrieve → synthesize |
| `legal_search_agent/project/supabase_client.py` | Legal brief loading, semantic search via `match_articles` RPC, result storage |
| `legal_search_agent/project/llm_client.py` | OpenAI AsyncClient (chat + embeddings) |
| `legal_search_agent/project/components/decomposer.py` | LLM prompt to break brief into sub-issues |
| `legal_search_agent/project/components/hyde_generator.py` | LLM prompt to generate hypothetical Arabic articles |
| `legal_search_agent/project/components/retrieval_agent.py` | Agentic RAG loop: HyDE → embed → search → coverage → iterate |
| `legal_search_agent/project/components/coverage_analyzer.py` | LLM prompt to assess legal area coverage |
| `legal_search_agent/project/components/synthesizer.py` | LLM prompt to produce final legal opinion |
| `shared/schema.py` | Pydantic models for all data types |

### The problem with the current flow (for a UI)

1. **Condenser re-pulls data inside the agent** — there is no way for a UI to show the user what the agent will see, let alone let the user edit it, before the agent runs.
2. **No separate "load context" endpoint** — context assembly and LLM inference are fused in one `handle_message_send`.
3. **Legal Search Agent also re-pulls** the Legal Brief from DB rather than receiving it in the payload.
4. **No structured JSON API** — agents return markdown text (formatted for Agentex UI chat), not machine-readable JSON that a custom frontend can render.

---

## 2. Backend / Agent Changes

### 2.1 Design Principle: Two Modes, One Codebase

> **The existing CLI / Agentex UI flow is preserved exactly as-is.** No existing code paths are modified, removed, or re-routed. The frontend is a second entry point that runs through the same agent logic but enters at a different point.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DUAL-MODE ARCHITECTURE                          │
│                                                                          │
│  MODE A: CLI / Agentex UI (EXISTING — UNCHANGED)                         │
│  ─────────────────────────────────────────────────                        │
│  User sends {"application_id": "..."}                                    │
│    → Condenser agent fetches from Supabase internally                    │
│    → Condenser runs LLM, saves Legal Brief to DB                         │
│    → Legal Search agent fetches Legal Brief from DB                      │
│    → Legal Search runs pipeline, saves opinion to DB                     │
│    → Returns formatted markdown                                          │
│                                                                          │
│  Nothing changes. Same code, same DB pulls, same prompts, same output.   │
│                                                                          │
│  MODE B: Frontend (NEW — ADDITIVE)                                       │
│  ─────────────────────────────────                                        │
│  1. Frontend calls Context API to load raw data from Supabase            │
│  2. User inspects / edits the data in the UI                             │
│  3. Frontend sends the data bundle directly to agents:                   │
│       Condenser receives {"case_data": ..., "document_extractions": ...} │
│       Legal Search receives {"legal_brief": ...}                         │
│  4. Agents skip the DB fetch (data already in payload) and run LLM       │
│  5. Agents return JSON (not markdown) for frontend to render             │
│                                                                          │
│  The "Edit → Run" principle applies only here: after context is loaded,  │
│  the UI is the source of truth. Agents run on the provided payload and   │
│  do NOT re-pull from DB.                                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**How the two modes coexist in code:**

Both agents already have branching logic in `handle_message_send` that checks whether `application_id` or direct data was provided. This is the existing code in `condenser_agent/project/acp.py:215-250`:

```python
# EXISTING CODE — NOT CHANGED
if application_id:
    # MODE A: Agent fetches from DB (CLI / Agentex UI path)
    application = supabase.get_application(application_id)
    parties = supabase.get_parties(application_id)
    capacity_proofs = supabase.get_capacity_proofs(party_ids)
    doc_extractions = supabase.get_document_extractions(application_id)
    case_data = {"application": application, "parties": parties, ...}
else:
    # MODE B: Direct input (frontend path) — ALSO EXISTING CODE
    case_data = input_data.get("case_data", {})
    document_extractions = input_data.get("document_extractions", [])
```

The agent already routes correctly. The only new code is at the **response** layer (how the result is returned), not at the input or processing layers.

### 2.2 Summary of What Changes vs What Stays

| Component | CLI mode (Mode A) | Frontend mode (Mode B) | Code change? |
|-----------|-------------------|----------------------|-------------|
| **Condenser: data loading** | Agent queries Supabase | Frontend sends data in payload | **None** — both paths already exist |
| **Condenser: LLM call** | Same prompt, same model | Same prompt, same model | **None** |
| **Condenser: DB save** | Saves Legal Brief to `legal_briefs` | Saves Legal Brief to `legal_briefs` | **None** |
| **Condenser: response format** | Returns `TextContent` (markdown) | Returns `TextContent` (markdown) **or** JSON | **ADD** `return_format` branch |
| **Legal Search: data loading** | Fetches Legal Brief from DB | Frontend sends Legal Brief in payload | **None** — both paths already exist |
| **Legal Search: pipeline** | Decompose → Retrieve → Synthesize | Decompose → Retrieve → Synthesize | **None** |
| **Legal Search: DB save** | Saves opinion + artifact | Saves opinion + artifact | **None** |
| **Legal Search: response format** | Returns `TextContent` (markdown) | Returns `TextContent` (markdown) **or** JSON | **ADD** `return_format` branch |
| **Context API** | N/A (doesn't exist) | New service, DB reads only | **NEW** service |

**Total agent code changes: ~15 lines per agent** (response format branching only). All existing behavior is untouched.

### 2.3 New Shared Service: Context Loader API (Frontend Only)

This service exists **only for the frontend**. CLI mode does not use it — in CLI mode the condenser agent fetches data internally as it does today.

**File:** `shared/context_api.py` (new)

```
GET /context/{application_id}
```

**Response:**

```json
{
  "application_id": "uuid",
  "loaded_at": "2026-02-03T...",
  "structured": {
    "application": { ... },         // from applications table
    "parties": [ ... ],             // from parties table
    "capacity_proofs": [ ... ],     // from capacity_proofs table
    "transaction_config": { ... }   // from transaction_configs table (if applicable)
  },
  "unstructured": {
    "document_extractions": [       // from document_extractions table
      {
        "document_id": "...",
        "file_name": "...",
        "document_type_code": "...",
        "raw_text_ar": "...",
        "raw_text_en": "...",
        "extracted_fields": { ... },
        "confidence_overall": 0.92
      }
    ],
    "poa_extractions": [ ... ]      // from poa_extractions table (if old schema)
  }
}
```

This endpoint re-uses the existing `CondenserSupabaseClient` queries but returns the raw data to the frontend **before** any LLM processing. The frontend displays it in the split view and allows edits. The CLI never calls this service.

### 2.4 Additive Changes to Condenser Agent

**File:** `condenser_agent/project/acp.py`

**What stays the same (the entire existing flow):**
- `application_id` path: fetches from Supabase, assembles `case_data`, calls LLM, saves to DB, returns markdown — **zero changes**
- Direct-input path: accepts `case_data` + `document_extractions`, calls LLM, saves to DB, returns markdown — **zero changes**
- `SYSTEM_PROMPT` — **unchanged**
- `ANALYSIS_PROMPT_TEMPLATE` — **unchanged**
- `format_legal_brief()` — **unchanged**

**What is added (additive only):**

A single branch at the response layer (~10 lines), after the Legal Brief is generated:

```python
# ---- NEW CODE (additive) ----
# After line 298 (after legal_brief is generated and saved):

return_format = input_data.get("return_format", "markdown")

if return_format == "json":
    # Frontend mode: return raw JSON for structured rendering
    return TextContent(
        author="agent",
        content=json.dumps({
            "type": "legal_brief_result",
            "legal_brief": legal_brief,
            "application_id": application_id or "direct_input",
        }, ensure_ascii=False, default=str)
    )

# ---- EXISTING CODE (unchanged) ----
# Existing markdown formatting path continues here:
output = format_legal_brief(legal_brief)
return TextContent(author="agent", content=output)
```

### 2.5 Additive Changes to Legal Search Agent

**File:** `legal_search_agent/project/acp.py`

Same pattern. The entire existing flow is untouched. One additive branch at the response layer:

**What stays the same:**
- `application_id` path: loads Legal Brief from DB, runs pipeline — **unchanged**
- Direct `legal_brief` path: skips DB fetch, runs pipeline — **unchanged**
- All components (decomposer, retrieval_agent, synthesizer) — **unchanged**
- `format_legal_opinion()` — **unchanged**

**What is added:**

```python
# ---- NEW CODE (additive) ----
# After line 312 (after opinion is generated and saved):

return_format = input_data.get("return_format", "markdown")
include_artifacts = input_data.get("include_artifacts", False)

if return_format == "json":
    response_data = {
        "type": "legal_opinion_result",
        "opinion": opinion,
    }
    if include_artifacts:
        response_data["retrieval_artifact"] = {
            "iterations": [...],  # from retrieval_artifact
            "stop_reason": retrieval_artifact.stop_reason,
            "coverage_score": retrieval_artifact.coverage_score,
            # ... full trace
        }
        response_data["decomposed_issues"] = issues
    return TextContent(
        author="agent",
        content=json.dumps(response_data, ensure_ascii=False, default=str)
    )

# ---- EXISTING CODE (unchanged) ----
output = format_legal_opinion(opinion)
return TextContent(author="agent", content=output)
```

### 2.6 Visual: Both Modes Side by Side

```
MODE A: CLI / Agentex UI (UNCHANGED)          MODE B: Frontend (NEW)
═══════════════════════════════                ═══════════════════════

User: {"application_id": "X"}                 User enters app ID in browser
         │                                              │
         ▼                                              ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│ Condenser Agent         │                   │ Context API (NEW)       │
│ 1. Fetch from Supabase  │                   │ GET /context/X          │
│ 2. Assemble case_data   │                   │ Returns raw JSON        │
│ 3. LLM → Legal Brief    │                   └───────────┬─────────────┘
│ 4. Save to DB           │                               │
│ 5. Return markdown      │                    User sees data, edits it
└───────────┬─────────────┘                               │
            │                                              │ clicks "Run"
            │                                              ▼
            │                                   ┌─────────────────────────┐
            │                                   │ Condenser Agent         │
            │                                   │ 1. Skip DB (data in    │
            │                                   │    payload already)     │
            │                                   │ 2. Same LLM call       │
            │                                   │ 3. Save to DB          │
            │                                   │ 4. Return JSON         │
            │                                   └───────────┬─────────────┘
            │                                               │
            ▼                                               ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│ Legal Search Agent      │                   │ Legal Search Agent      │
│ 1. Fetch Brief from DB  │                   │ 1. Skip DB (brief in   │
│ 2. Decompose            │                   │    payload already)     │
│ 3. Retrieve (RAG)       │                   │ 2. Same Decompose      │
│ 4. Synthesize           │                   │ 3. Same Retrieve (RAG) │
│ 5. Save to DB           │                   │ 4. Same Synthesize     │
│ 6. Return markdown      │                   │ 5. Save to DB          │
└─────────────────────────┘                   │ 6. Return JSON +       │
                                               │    artifacts (optional)│
                                               └─────────────────────────┘
```

**Key point:** Steps 2-5 in the condenser and steps 2-5 in legal search are **identical code paths** in both modes. The only difference is how data enters (DB fetch vs payload) and how results exit (markdown vs JSON).

---

## 3. Deployment Options

The agents currently run locally via `agentex agents run --manifest manifest.yaml`. For a publicly accessible frontend, both the agents and the AgentEx backend need to be deployed.

### Option A: Cloud VM (Simplest — Recommended for MVP)

Deploy everything on a single cloud VM (Azure VM, AWS EC2, GCP Compute).

```
┌──────────────────────────────────────────────────────────────────┐
│                     Cloud VM (e.g. Azure B4ms)                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ Docker Compose                                                │ │
│  │                                                               │ │
│  │  ┌────────────┐  ┌────────┐  ┌─────────┐  ┌──────────────┐  │ │
│  │  │ PostgreSQL │  │ Redis  │  │Temporal │  │  AgentEx     │  │ │
│  │  │   :5432    │  │ :6379  │  │  :7233  │  │  Server:5003 │  │ │
│  │  └────────────┘  └────────┘  └─────────┘  └──────────────┘  │ │
│  │                                                               │ │
│  │  ┌────────────┐  ┌─────────────────┐  ┌─────────────────┐   │ │
│  │  │ Context    │  │ Condenser Agent │  │ Legal Search    │   │ │
│  │  │ API :8080  │  │     :8012       │  │ Agent :8013     │   │ │
│  │  └────────────┘  └─────────────────┘  └─────────────────┘   │ │
│  │                                                               │ │
│  │  ┌──────────────────────────────────────────────────────────┐ │ │
│  │  │  Frontend (Next.js)  :3000                                │ │ │
│  │  └──────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Nginx reverse proxy :443 → frontend :3000                        │
│                             → /api/context/* → context API :8080   │
│                             → /api/agents/* → AgentEx :5003        │
└──────────────────────────────────────────────────────────────────┘
```

**Pros:** Simple, single deployment, low cost (~$50-100/mo), fast iteration.
**Cons:** Single point of failure, no auto-scaling.

**Steps:**
1. Provision VM (recommend: 4 vCPU, 16GB RAM)
2. Install Docker + Docker Compose
3. Create a single `docker-compose.yml` with all services
4. Add Nginx for TLS termination + reverse proxy
5. Point a domain to the VM IP

### Option B: Kubernetes (AgentEx Native)

Deploy using AgentEx's built-in Helm charts on an existing K8s cluster.

```bash
# Build and push agent images
agentex agents build --manifest condenser_agent/manifest.yaml \
  --registry agentex.azurecr.io --push

agentex agents build --manifest legal_search_agent/manifest.yaml \
  --registry agentex.azurecr.io --push

# Deploy agents
agentex agents deploy --cluster prod --manifest condenser_agent/manifest.yaml
agentex agents deploy --cluster prod --manifest legal_search_agent/manifest.yaml
```

**Pros:** Production-grade, auto-scaling, AgentEx-native tooling.
**Cons:** Requires existing K8s cluster, more complex setup.

### Option C: Hybrid — Agents on VM, Frontend on Vercel/Cloudflare

```
┌─────────────────┐         ┌──────────────────────────────┐
│  Frontend        │ ──────▶ │  Cloud VM                     │
│  (Vercel/CF)     │  HTTPS  │  AgentEx + Agents + Context   │
│  :443            │         │  API :5003                     │
└─────────────────┘         └──────────────────────────────┘
```

**Pros:** Frontend gets CDN, SSL, easy deploys via git push. Backend is isolated.
**Cons:** CORS configuration needed. Two deployment targets.

### Recommended: Option A for MVP

Start with Docker Compose on a single VM. Everything in one place, easy to debug, no infra overhead. Migrate to K8s or hybrid when needed.

### Required Dockerfiles

Two Dockerfiles are missing. Create them based on the existing `tier1_validation_agent/Dockerfile`:

**`condenser_agent/Dockerfile`** (new)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY shared/ /app/shared/
COPY condenser_agent/ /app/condenser_agent/
WORKDIR /app/condenser_agent
RUN uv pip install --system -e .
ENV PYTHONPATH=/app
CMD ["uvicorn", "project.acp:acp", "--host", "0.0.0.0", "--port", "8012"]
```

**`legal_search_agent/Dockerfile`** (new)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY shared/ /app/shared/
COPY legal_search_agent/ /app/legal_search_agent/
WORKDIR /app/legal_search_agent
RUN uv pip install --system -e .
ENV PYTHONPATH=/app
CMD ["uvicorn", "project.acp:acp", "--host", "0.0.0.0", "--port", "8013"]
```

### Docker Compose (all services)

**`docker-compose.yml`** (new, at `poa_agents/` root)

```yaml
version: "3.8"
services:
  context-api:
    build:
      context: .
      dockerfile: shared/Dockerfile
    ports:
      - "8080:8080"
    env_file:
      - shared/.env

  condenser-agent:
    build:
      context: .
      dockerfile: condenser_agent/Dockerfile
    ports:
      - "8012:8012"
    env_file:
      - condenser_agent/.env

  legal-search-agent:
    build:
      context: .
      dockerfile: legal_search_agent/Dockerfile
    ports:
      - "8013:8013"
    env_file:
      - legal_search_agent/.env

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_CONTEXT_API_URL=http://context-api:8080
      - NEXT_PUBLIC_CONDENSER_URL=http://condenser-agent:8012
      - NEXT_PUBLIC_LEGAL_SEARCH_URL=http://legal-search-agent:8013
```

Note: If using AgentEx backend (for task management), add the AgentEx docker-compose services here too. If going direct (agents only, no AgentEx), the above is sufficient since both agents are `sync` type and don't need Temporal.

### Direct vs AgentEx-mediated

Since both the condenser and legal search agents are `acp_type: sync`, you have a choice:

| Approach | How frontend calls agents | Needs AgentEx backend? |
|----------|--------------------------|----------------------|
| **Direct** | Frontend → Next.js proxy → Agent ACP endpoint (JSON-RPC 2.0 POST to `:8012/api`) | No |
| **AgentEx-mediated** | Frontend → AgentEx Gateway `:5003` → routes to agent | Yes |

**Recommendation for MVP:** Go **direct** (currently implemented). Both agents are stateless sync handlers. The frontend proxies through a Next.js API route to avoid CORS, then hits each agent's ACP endpoint directly. This avoids needing to deploy the full AgentEx stack (PostgreSQL, Redis, MongoDB, Temporal).

**Note:** The ACP endpoint is `POST /api` using JSON-RPC 2.0 with `method: "message/send"`, NOT REST at `/acp/send`.

If you later need task history, streaming, or the Agentex UI alongside your custom frontend, add the AgentEx backend then.

---

## 4. Frontend Architecture

### Technology

- **Next.js 16** (App Router, Turbopack) — latest stable
- **React 19** with Server Components where appropriate
- **Tailwind CSS v4** for styling (CSS-based config, no `tailwind.config.ts`)
- **TypeScript** (strict mode)
- No UI library — custom components with Tailwind utilities

### Page Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  TOP CONTROL ROW                                                     │
│  ┌──────────────────┐  ┌──────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Application # ___│  │ Load │  │ Run Agents│  │ Status: idle   │  │
│  └──────────────────┘  └──────┘  └──────────┘  │ Loaded: —      │  │
│                                   (disabled     │ Run: —         │  │
│                                   until loaded)  └────────────────┘  │
├─────────────────────────────────┬───────────────────────────────────┤
│  LEFT: Structured Context       │  RIGHT: Unstructured Context      │
│                                 │                                    │
│  ┌─ Application ──────────────┐│  ┌─ Document 1: QID_card.pdf ───┐ │
│  │  SAK-2026-POA-TEST001      ││  │  Raw Text (AR):              │ │
│  │  Type: POA_SPECIAL_COMPANY ││  │  اسم: حمزة عوض               │ │
│  │  Status: pending           ││  │  الرقم الشخصي: 13572468      │ │
│  └────────────────────────────┘│  │  ...                         │ │
│                                 │  │  Extracted Fields: { ... }   │ │
│  ┌─ Parties ──────────────────┐│  │  Confidence: 92%             │ │
│  │  GRANTOR: Hamza Awad       ││  └──────────────────────────────┘ │
│  │    QID: 13572468           ││                                    │
│  │    Capacity: Manager       ││  ┌─ Document 2: POA.pdf ────────┐ │
│  │  AGENT: ...                ││  │  Raw Text (AR): ...          │ │
│  └────────────────────────────┘│  │  Raw Text (EN): ...          │ │
│                                 │  │  Extracted Fields: { ... }   │ │
│  ┌─ Capacity Proofs ─────────┐│  └──────────────────────────────┘ │
│  │  CR #3333                  ││                                    │
│  │  Manager: Hamza (Passports)││  ┌─ [Raw JSON View] ────────────┐ │
│  └────────────────────────────┘│  │  { full JSON toggle }        │ │
│                                 │  └──────────────────────────────┘ │
│  ┌─ [Raw JSON View] ─────────┐│                                    │
│  │  { full JSON toggle }      ││                                    │
│  └────────────────────────────┘│                                    │
├─────────────────────────────────┴───────────────────────────────────┤
│  RESULTS DRAWER (slides up on run completion)                        │
│                                                                      │
│  ┌─ Tabs: [Legal Brief] [Legal Opinion] [Retrieval Trace] [Logs] ─┐ │
│  │                                                                  │ │
│  │  Legal Brief tab:                                                │ │
│  │    Rendered view of condenser output                             │ │
│  │    + Raw JSON toggle                                             │ │
│  │                                                                  │ │
│  │  Legal Opinion tab:                                              │ │
│  │    ✅/❌ verdict, confidence, findings per issue,                │ │
│  │    citations, concerns, recommendations                         │ │
│  │    + Raw JSON toggle                                             │ │
│  │                                                                  │ │
│  │  Retrieval Trace tab:                                            │ │
│  │    Iterations, queries, HyDE outputs, coverage, similarities    │ │
│  │                                                                  │ │
│  │  Logs tab:                                                       │ │
│  │    Agent stdout/stderr (polled or streamed)                      │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Frontend API Calls (Mode B sequence — Implemented)

The frontend always uses **Mode B** (direct-input). CLI/Agentex UI continues to use **Mode A** unchanged.

```
1. User enters application_id, clicks "Load"
   └─► Frontend queries Supabase directly via @supabase/supabase-js
       └─► Same tables: applications, parties, capacity_proofs, documents, document_extractions
       └─► Returns { structured, unstructured }
       └─► Renders split view (StructuredPanel + UnstructuredPanel)
       └─► Enables "Run Agents" button

2. User (optionally edits context), clicks "Run Agents"

   Step 2a — Tier 1 Validation:
   └─► Runs deterministic checks (lib/validation.ts)
       └─► Expiry checks, cross-field validation, missing data
       └─► If errors: ValidationModal blocks; if warnings: user can proceed

   Step 2b — Condenser Agent (JSON-RPC 2.0):
   └─► POST /api/agent/condenser (Next.js proxy route)
       └─► Proxied to http://localhost:8012/api
       Body (JSON-RPC 2.0): {
         "jsonrpc": "2.0",
         "method": "message/send",
         "params": {
           "agent": { id, name, acp_type: "sync", description, created_at, updated_at },
           "task": { id: "frontend-{timestamp}" },
           "content": {
             "type": "text",
             "author": "user",
             "content": JSON.stringify({
               "case_data": <structured from UI state (possibly edited)>,
               "document_extractions": <unstructured from UI state>
             })
           }
         },
         "id": "req-{timestamp}"
       }
       Agent behavior:
         - Sees case_data in payload → skips Supabase fetch (existing Mode B path)
         - Runs same LLM prompt as CLI mode
         - Saves Legal Brief to DB (same as CLI mode)
         - Returns markdown with embedded JSON in <details> block
       Response nesting: result.content.content → markdown string
       └─► parseCondenserContent extracts JSON from ```json fence
       └─► ResultsDrawer renders structured report sections

   Step 2c — Legal Search Agent (JSON-RPC 2.0, auto-chained):
   └─► POST /api/agent/legal-search (Next.js proxy route)
       └─► Proxied to http://localhost:8013/api
       Body (JSON-RPC 2.0): same structure as condenser, content is:
         JSON.stringify({ "legal_brief": <condenser output JSON> })
       Agent behavior:
         - Sees legal_brief in payload → skips DB fetch (existing Mode B path)
         - Runs same decompose → retrieve → synthesize pipeline as CLI
         - Returns markdown with embedded JSON in <details> block
       Response nesting: result.content.content → markdown string
       └─► parseAgentContent extracts JSON from ```json fence
       └─► ResultsDrawer renders Legal Opinion tab
```

**Parity note:** If a user runs the same application through CLI (Mode A) and then through the frontend (Mode B) without editing any fields, the LLM receives the **exact same prompt** with the **exact same data**. The only difference is how the result enters (DB fetch vs direct payload) and is consumed (markdown display vs parsed JSON).

### Key Frontend Components (Implemented)

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                          # Root layout (dark theme, Inter font)
│   │   ├── page.tsx                            # Main page — state, handlers, layout
│   │   ├── globals.css                         # Tailwind v4 imports
│   │   └── api/
│   │       └── agent/
│   │           ├── condenser/
│   │           │   └── route.ts                # Server-side proxy → localhost:8012/api (CORS)
│   │           └── legal-search/
│   │               └── route.ts                # Server-side proxy → localhost:8013/api (CORS)
│   ├── components/
│   │   ├── ControlRow.tsx                      # App ID input, Load, Run Agents, status badges
│   │   ├── StructuredPanel.tsx                 # Left panel: application, parties, capacity_proofs cards
│   │   ├── UnstructuredPanel.tsx               # Right panel: tabbed document extractions
│   │   ├── EditableField.tsx                   # Click-to-edit inline fields (scalar, multiline, RTL)
│   │   ├── JsonViewer.tsx                      # Collapsible raw JSON viewer
│   │   ├── ValidationModal.tsx                 # Error/warning modal before agent run
│   │   └── ResultsDrawer.tsx                   # Structured report: header, case summary, parties,
│   │                                           #   entity info, POA details, evidence, fact comparisons,
│   │                                           #   open questions, missing info + raw JSON tab
│   └── lib/
│       ├── agentApi.ts                         # JSON-RPC 2.0 client, payload builder, JSON extractor
│       ├── supabase.ts                         # Direct Supabase context loading (loadContext)
│       └── validation.ts                       # Tier 1 deterministic checks
├── package.json
├── postcss.config.mjs
├── next.config.ts
└── tsconfig.json
```

### Key Architecture Decisions

1. **Server-side proxy for CORS**: Browser cannot call `localhost:8012` directly. The Next.js API route at `/api/agent/condenser` proxies requests server-side.

2. **JSON-RPC 2.0 protocol**: The ACP endpoint is `POST /api` with `method: "message/send"`. The `agent` param requires all fields (id, name, acp_type, description, created_at, updated_at).

3. **Response nesting**: The JSON-RPC result is a `SendMessageResponse` wrapping a `TextContent`. The actual content string is at `result.content.content`.

4. **JSON extraction from markdown**: The agent returns markdown with embedded JSON in a fenced code block inside `<details>`. `parseCondenserContent` extracts and parses this JSON for structured rendering.

5. **Direct Supabase loading**: Frontend queries Supabase directly (same tables as condenser agent) rather than requiring a separate Context API service. This simplifies the MVP.

### Parity Guarantee (Frontend Mode B vs CLI Mode A)

The UI guarantees that an unedited frontend run produces the same agent behavior as a CLI run:

1. **Load step:** The Context API uses the **same `CondenserSupabaseClient` queries** (`get_application()`, `get_parties()`, etc.) as the condenser agent's internal fetch. Both modes query the same tables with the same filters.

2. **Display step:** Both panels have a "Raw JSON" toggle. This JSON is the **exact payload that will be sent to the agent**. Users can compare it to what the agent assembles internally in Mode A.

3. **Run step (no edits):** The UI sends the data using the **existing direct-input code path** (`case_data` + `document_extractions` keys in the payload). This path is already in the condenser agent at `acp.py:246-250`. No new agent code path is needed for input processing.

4. **Run step (with edits):** If the user modifies fields in the UI, the edited data flows into the payload. The agent runs on whatever data it receives — it does not re-fetch from DB because the `case_data` key is present. This is the "Edit → Run" principle and it only applies in Mode B.

5. **CLI remains the reference implementation:** Mode A (CLI) continues to work exactly as before. If there's ever a discrepancy between Mode A and Mode B outputs for the same unedited data, Mode A is correct and Mode B has a bug in the Context API.

---

## 5. Implementation Steps

### Phase 1: Backend Changes (Context API + Agent Response Format)

> **Golden rule: existing behavior must not change.** Every change in this phase is additive. After these changes, running agents via CLI / Agentex UI with `{"application_id": "..."}` must produce byte-for-byte identical results to today.

1. **Create `shared/context_api.py`** (new file — does not touch agents)
   - FastAPI app with `GET /context/{application_id}`
   - Reuses `CondenserSupabaseClient` queries (import, don't duplicate)
   - Returns JSON with `{ structured, unstructured }` split
   - Add `Dockerfile` for this service
   - **Test:** curl the endpoint, compare output to what the condenser agent assembles internally for the same application_id

2. **Add `return_format` branch to `condenser_agent/project/acp.py`** (additive — ~10 lines)
   - Insert AFTER line 298 (after `legal_brief` is generated and saved)
   - If `return_format == "json"` in input_data, return JSON-wrapped response
   - Otherwise, fall through to existing `format_legal_brief()` path (unchanged)
   - **Do NOT modify** the `application_id` fetch path (lines 215-243)
   - **Do NOT modify** the direct-input path (lines 246-250) — it already works
   - **Do NOT modify** prompts, LLM calls, or DB saves
   - **Test (Mode A preserved):** send `{"application_id": "..."}` → must return markdown exactly as before
   - **Test (Mode B works):** send `{"case_data": ..., "return_format": "json"}` → must return JSON

3. **Add `return_format` + `include_artifacts` branch to `legal_search_agent/project/acp.py`** (additive — ~20 lines)
   - Insert AFTER line 312 (after `opinion` is generated and saved)
   - If `return_format == "json"`, return JSON-wrapped response
   - If `include_artifacts == true`, include decomposed issues and retrieval trace
   - Otherwise, fall through to existing `format_legal_opinion()` path (unchanged)
   - **Do NOT modify** the `application_id` fetch path (lines 194-202)
   - **Do NOT modify** the direct `legal_brief` path — it already works
   - **Do NOT modify** any component (decomposer, retriever, synthesizer)
   - **Test (Mode A preserved):** send `{"application_id": "..."}` → must return markdown exactly as before
   - **Test (Mode B works):** send `{"legal_brief": ..., "return_format": "json"}` → must return JSON

4. **Create missing Dockerfiles**
   - `condenser_agent/Dockerfile`
   - `legal_search_agent/Dockerfile`
   - `shared/Dockerfile` (for Context API)

5. **Create `docker-compose.yml`** at `poa_agents/` root
   - Context API, condenser, legal search, frontend
   - Env file references
   - Port mappings

6. **Test both modes end-to-end in Docker Compose**
   - `docker-compose up --build`
   - **Mode A test:** POST `{"application_id": "..."}` directly to condenser `:8012` → markdown response (existing behavior)
   - **Mode B test:** GET context from `:8080`, POST data to condenser with `return_format=json` → JSON response
   - Verify Legal Brief in DB is identical for both modes (same application, same data → same LLM output)

### Phase 2: Frontend MVP

7. **Scaffold Next.js project** in `frontend/`
   - Next.js 15 + TypeScript + Tailwind + shadcn/ui

8. **Build ControlRow component**
   - Application number input
   - Load button → calls Context API
   - Run Agents button (disabled until loaded)
   - Status indicators: idle / loading / loaded / running / completed / failed
   - Timestamps

9. **Build SplitView + panels**
   - StructuredPanel: renders application, parties, capacity_proofs as cards/tables
   - UnstructuredPanel: renders document_extractions as tabbed per-document views
   - RawJsonViewer: collapsible JSON display on each panel

10. **Build Run flow**
    - On "Run Agents": POST to condenser → wait → POST to legal search → wait
    - Show progress: "Running condenser..." → "Running legal search..."
    - Handle errors at each stage

11. **Build ResultsDrawer**
    - Tabs: Legal Brief, Legal Opinion, Retrieval Trace, Logs
    - LegalBriefView: rendered cards for parties, POA details, discrepancies, open questions
    - LegalOpinionView: verdict banner, confidence, per-issue findings, citations
    - RetrievalTraceView: iteration table, queries, coverage heatmap
    - Raw JSON toggle on each tab

### Phase 3: Edit Support

12. **Make structured fields editable**
    - Inline editing for key fields (party names, QIDs, capacities)
    - JSON editor for power users
    - Track dirty state: highlight edited fields

13. **Make unstructured text editable**
    - Text area for raw_text_ar/en
    - JSON editor for extracted_fields
    - Track dirty state

14. **Wire edited data into Run payload**
    - On "Run Agents", serialize current UI state (with edits) into the payload
    - Never send `application_id` alone (prevents agent from re-fetching)
    - Show diff: "You modified 3 fields" before running

### Phase 4: Deployment

15. **Provision cloud VM** (Azure / AWS / GCP)
    - 4 vCPU, 16GB RAM, 50GB disk
    - Install Docker + Docker Compose
    - Open ports 443 (HTTPS)

16. **Configure Nginx reverse proxy**
    - TLS via Let's Encrypt
    - Route `/` → frontend `:3000`
    - Route `/api/context/*` → context API `:8080`
    - Route `/api/agents/condenser/*` → condenser `:8012`
    - Route `/api/agents/legal-search/*` → legal search `:8013`

17. **Deploy**
    - `docker-compose up -d`
    - Verify all services healthy
    - Test end-to-end from browser

18. **DNS + Domain**
    - Point domain to VM IP
    - Verify HTTPS works

---

## Appendix: Data Shapes

### Context API Response (what the frontend renders)

```typescript
interface ContextResponse {
  application_id: string;
  loaded_at: string;
  structured: {
    application: {
      id: string;
      sak_case_number: string;
      status: string;
      transaction_type_code: string;
      transaction_value: number | null;
      transaction_subject_ar: string | null;
      transaction_subject_en: string | null;
      created_at: string;
    };
    parties: Array<{
      id: string;
      party_position: string;       // grantor, agent, etc.
      qid: string;
      name_ar: string;
      name_en: string;
      nationality: string;
      capacity_fields: Record<string, any>;
    }>;
    capacity_proofs: Array<{
      id: string;
      party_id: string;
      proof_type: string;
      details: Record<string, any>;
    }>;
  };
  unstructured: {
    document_extractions: Array<{
      id: string;
      document_id: string;
      file_name: string;
      document_type_code: string;
      raw_text_ar: string | null;
      raw_text_en: string | null;
      extracted_fields: Record<string, any>;
      confidence_overall: number;
    }>;
  };
}
```

### Condenser Agent Input (what frontend sends)

```typescript
interface CondenserInput {
  case_data: {
    application: ContextResponse["structured"]["application"];
    parties: ContextResponse["structured"]["parties"];
    capacity_proofs: ContextResponse["structured"]["capacity_proofs"];
  };
  document_extractions: ContextResponse["unstructured"]["document_extractions"];
  additional_context?: Record<string, any>;
  return_format: "json";
}
```

### Legal Search Agent Input (what frontend sends)

```typescript
interface LegalSearchInput {
  legal_brief: Record<string, any>;     // output from condenser
  application_id?: string;               // for tracking only
  return_format: "json";
  include_artifacts?: boolean;
}
```
