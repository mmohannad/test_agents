# POA Agents

Multi-agent system for Power of Attorney (POA) validation with a web frontend.

## Architecture

```
Browser :3000  ──>  Next.js Frontend
                        |
                        |── Supabase (loads application context)
                        |
                        |──>  Condenser Agent :8012   (Step 1: Legal Brief)
                        |         └── Azure OpenAI LLM
                        |
                        └──>  Legal Search Agent :8013 (Step 2: Legal Opinion)
                                  └── Agentic RAG + Azure OpenAI
```

**Flow:** Load application context from Supabase -> inspect/edit in split-view UI -> run condenser agent (produces Legal Brief) -> auto-chain to legal search agent (produces Legal Opinion with citations) -> view results.

Both agents use the AgentEx ACP protocol (JSON-RPC 2.0 over `POST /api`). The frontend sends data directly in the payload (Mode B), so agents skip their internal DB fetch and operate on the provided data. The entire chain runs in-memory through the frontend.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js >= 18
- `agentex` CLI (`pip install agentex`)

### 1. Configure environment

Copy `.env.example` files and fill in secrets:

```bash
cp condenser_agent/.env.example condenser_agent/.env
cp legal_search_agent/.env.example legal_search_agent/.env
```

Required variables in each agent `.env`:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | API version (e.g. `2024-02-15-preview`) |
| `LLM_MODEL` | Deployment name (e.g. `gpt-4o`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |

Legal search agent also needs:

| Variable | Description |
|----------|-------------|
| `EMBEDDING_MODEL` | Embedding model deployment name |
| `SIMILARITY_THRESHOLD` | Min similarity for article retrieval (e.g. `0.75`) |
| `MAX_ARTICLES_PER_ISSUE` | Max articles per legal issue (e.g. `10`) |

Frontend env (`frontend/.env.local`):

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 2. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 3. Start everything (single command)

```bash
./dev.sh
```

This starts all three services:

| Service | Port | Description |
|---------|------|-------------|
| Condenser Agent | 8012 | Produces Legal Brief from case data |
| Legal Search Agent | 8013 | Produces Legal Opinion via agentic RAG |
| Frontend | 3000 | Next.js web UI |

The script waits for all services to be ready before printing URLs.

### 4. Stop everything

```bash
./dev.sh stop
```

Or press `Ctrl+C` in the terminal running `./dev.sh`.

---

## Manual Startup

If you prefer to start services individually:

```bash
# Terminal 1: Condenser agent
agentex agents run --manifest condenser_agent/manifest.yaml

# Terminal 2: Legal search agent
agentex agents run --manifest legal_search_agent/manifest.yaml

# Terminal 3: Frontend
cd frontend && npm run dev
```

---

## Usage

1. Open http://localhost:3000
2. Enter an Application ID and click **Load Context**
3. Inspect structured data (left panel) and document extractions (right panel)
4. Optionally edit any field inline (click to edit)
5. Click **Run Agents** -- the pipeline runs:
   - Tier 1 validation checks (blocks on errors, warns on issues)
   - Step 1/2: Condenser agent produces a Legal Brief
   - Step 2/2: Legal search agent produces a Legal Opinion
6. View results in the bottom drawer:
   - **Legal Brief** tab: case summary, parties, POA details, evidence, open questions
   - **Legal Opinion** tab: validity decision, confidence, per-issue analysis, citations, retrieval metrics
   - **Raw JSON** tab: full agent responses

---

## Project Structure

```
poa_agents/
├── condenser_agent/          # Agent 1: Case data -> Legal Brief
│   ├── manifest.yaml
│   ├── project/acp.py        # ACP handler (JSON-RPC 2.0)
│   └── .env.example
├── legal_search_agent/       # Agent 2: Legal Brief -> Legal Opinion
│   ├── manifest.yaml
│   ├── project/acp.py        # ACP handler (JSON-RPC 2.0)
│   └── .env.example
├── frontend/                 # Next.js 16 web UI
│   ├── src/app/page.tsx      # Main page + state management
│   ├── src/app/api/agent/    # Server-side proxies (CORS)
│   │   ├── condenser/route.ts
│   │   └── legal-search/route.ts
│   ├── src/components/       # UI components
│   └── src/lib/              # Supabase client, agent API, validation
├── shared/                   # Shared schemas
├── dev.sh                    # Single-command startup script
└── project_plan.md           # Detailed architecture docs
```

---

## Agents

### Condenser Agent (port 8012)

Takes structured case data + document extractions and produces a **Legal Brief** summarizing the case for legal analysis.

- **Input (Mode B):** `{ case_data, document_extractions, additional_context }`
- **Output:** Markdown with embedded JSON containing case summary, party analysis, POA details, evidence assessment, open questions
- **LLM:** Azure OpenAI (configurable model)

### Legal Search Agent (port 8013)

Takes a Legal Brief and produces a **Legal Opinion** with citations to Qatari law.

- **Input (Mode B):** `{ legal_brief: {...} }`
- **Output:** Markdown with embedded JSON containing overall finding, confidence score, per-issue analysis, article citations, retrieval metrics
- **Pipeline:** Decompose issues -> HyDE article generation -> Agentic RAG retrieval -> Coverage analysis -> Synthesis
- **LLM:** Azure OpenAI (chat + embeddings)

### ACP Protocol

Both agents use the AgentEx ACP protocol:

- **Endpoint:** `POST /api`
- **Protocol:** JSON-RPC 2.0, `method: "message/send"`
- **Response nesting:** `result.content.content` (SendMessageResponse -> TextContent -> string)

---

## Test Data

The system has test POA applications in Supabase:

| # | Case | Expected Outcome |
|---|------|-----------------|
| 1 | SAK-2024-POA-00001 | VALID |
| 2 | SAK-2024-POA-00002 | VALID |
| 3 | SAK-2024-POA-00003 | TIER 1 FAIL (missing QID) |
| 4 | SAK-2024-POA-00004 | VALID |
| 5 | SAK-2024-POA-00005 | REQUIRES_REVIEW |
| 6 | SAK-2024-POA-00006 | REQUIRES_REVIEW |
| 7 | SAK-2024-POA-00007 | TIER 1 FAIL (expired QID) |
| 8 | SAK-2024-POA-00008 | VALID |
| 9 | SAK-2024-POA-00009 | TIER 2 FAIL (sub-delegation prohibited) |
| 10 | SAK-2024-POA-00010 | TIER 2 FAIL (unlicensed attorney) |
| 11 | SAK-2024-POA-00011 | TIER 2 FAIL (minor grantor) |

---

## Troubleshooting

### Agent won't start
```bash
# Check if agentex is installed
agentex --version

# Check if ports are free
lsof -ti TCP:8012 -sTCP:LISTEN
lsof -ti TCP:8013 -sTCP:LISTEN
lsof -ti TCP:3000 -sTCP:LISTEN
```

### "SUPABASE_ANON_KEY is required" error
Make sure `.env` file exists in the agent directory.

### Frontend can't reach agents
The frontend proxies through Next.js API routes to avoid CORS. Check that agents are running on the expected ports. The proxy routes are at `frontend/src/app/api/agent/condenser/route.ts` and `frontend/src/app/api/agent/legal-search/route.ts`.

### Condenser returns non-JSON
The agent returns markdown with JSON embedded in a `<details>` block. The `parseAgentContent` function in `frontend/src/lib/agentApi.ts` extracts the JSON. If extraction fails, the raw markdown is displayed.

---

## License

Internal use only.
