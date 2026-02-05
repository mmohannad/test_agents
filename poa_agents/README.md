# POA Agents

Multi-agent system for Power of Attorney (POA) validation with a web frontend.

## Architecture

```
Browser  ──>  Next.js Frontend
                   |
                   |── Supabase (loads application context)
                   |
                   |──>  Condenser Agent    (Step 1: Legal Brief)
                   |         └── OpenAI LLM
                   |
                   └──>  Legal Search Agent (Step 2: Legal Opinion)
                             └── Agentic RAG + OpenAI
```

**Two modes of operation:**
- **DB View:** Load application context from Supabase -> inspect/edit in split-view UI -> run agents
- **Manual Entry:** Enter all application data by hand (parties, attachments, signatories) -> run agents

Both modes produce the same `AgentPayload` and feed into the same agent pipeline: Tier 1 validation -> Condenser Agent (Legal Brief) -> Legal Search Agent (Legal Opinion with citations).

Both agents use the AgentEx ACP protocol (JSON-RPC 2.0 over `POST /api`). The frontend sends data directly in the payload (Mode B), so agents skip their internal DB fetch and operate on the provided data. The entire chain runs in-memory through the frontend.

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.12+
- Node.js >= 22
- `agentex` CLI (`pip install agentex-sdk`)

### 1. Configure environment

```bash
cp condenser_agent/.env.example condenser_agent/.env
cp legal_search_agent/.env.example legal_search_agent/.env
```

Required variables in each agent `.env`:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `LLM_MODEL` | Model name (e.g. `gpt-4o`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |

Legal search agent also needs:

| Variable | Description |
|----------|-------------|
| `EMBEDDING_MODEL` | Embedding model (e.g. `text-embedding-3-small`) |
| `SIMILARITY_THRESHOLD` | Min similarity for article retrieval (e.g. `0.3`) |
| `MAX_ARTICLES_PER_ISSUE` | Max articles per legal issue (e.g. `5`) |

Frontend env (`frontend/.env`):

```bash
cp frontend/.env.example frontend/.env
```

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL (client-side) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key (client-side) |
| `CONDENSER_URL` | Condenser agent URL (server-side, default `http://localhost:8012`) |
| `LEGAL_SEARCH_URL` | Legal search agent URL (server-side, default `http://localhost:8013`) |

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

### 4. Stop everything

```bash
./dev.sh stop
```

Or press `Ctrl+C` in the terminal running `./dev.sh`.

---

## Deploy to Railway

Railway gives you git-push deploys with automatic HTTPS -- no VM, no reverse proxy, no domain setup.

### How it works

Each service gets its own Dockerfile. Railway builds and runs them as separate services in one project. The frontend talks to agents via Railway's private networking (internal URLs, no public exposure needed for agents).

### Setup steps

1. **Create a Railway project** at [railway.app](https://railway.app)

2. **Create 3 services** from the same GitHub repo, each with a different root directory:

   | Service | Root Directory | Dockerfile Path |
   |---------|---------------|-----------------|
   | `condenser-agent` | `/poa_agents` | `condenser_agent/Dockerfile` |
   | `legal-search-agent` | `/poa_agents` | `legal_search_agent/Dockerfile` |
   | `frontend` | `/poa_agents/frontend` | `Dockerfile` |

3. **Set environment variables** for each service in Railway's dashboard:

   **condenser-agent:**
   ```
   OPENAI_API_KEY=sk-...
   LLM_MODEL=gpt-4o
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=...
   PORT=8012
   ```

   **legal-search-agent:**
   ```
   OPENAI_API_KEY=sk-...
   LLM_MODEL=gpt-4o
   EMBEDDING_MODEL=text-embedding-3-small
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=...
   SIMILARITY_THRESHOLD=0.3
   MAX_ARTICLES_PER_ISSUE=5
   PORT=8013
   ```

   **frontend:**
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=...
   CONDENSER_URL=http://condenser-agent.railway.internal:8012
   LEGAL_SEARCH_URL=http://legal-search-agent.railway.internal:8013
   ```

   > The `CONDENSER_URL` and `LEGAL_SEARCH_URL` use Railway's private networking.
   > Replace `condenser-agent` and `legal-search-agent` with your actual Railway service names.

4. **Generate a domain** for the frontend service only (Settings > Networking > Generate Domain). The agents don't need public URLs -- they're only accessed by the frontend's server-side proxy routes.

5. **Push to GitHub** -- Railway auto-deploys on every push.

### What you get

- Frontend at `https://your-project.up.railway.app`
- Agents running privately (not exposed to internet)
- Auto-deploys on `git push`
- No VM, no SSL config, no reverse proxy

---

## Manual Startup (Alternative)

```bash
# Terminal 1: Condenser agent
agentex agents run --manifest condenser_agent/manifest.yaml

# Terminal 2: Legal search agent
agentex agents run --manifest legal_search_agent/manifest.yaml

# Terminal 3: Frontend
cd frontend && npm run dev
```

---

## Manual Entry Mode

The Manual Entry tab lets you enter application data without a Supabase record:

**Application Form (left panel):**
- Application type selector (7 POA types)
- First Party: capacity (~60 Arabic options), ID type (~12 options), ID number, expiry date, citizenship, full name, phone, email
- Second Party: same fields
- Namadhij (free text for granted powers)

**Attachment Panel (right panel):**
- Add attachment instances by document type (Personal ID, Commercial Registration, Passport, POA, Authorization, Trade License, Foundation Contract, Establishment Record)
- Each type has specific extracted fields with proper date pickers for date fields
- Commercial Registration attachments support authorized signatories (name, QID, nationality, percentage, position)
- Save/unsave state per attachment

## Tier 1 Validation

Before agents run, deterministic pre-flight checks catch data issues:

| Check | Severity | Description |
|-------|----------|-------------|
| Missing application type | Warning | No transaction type selected |
| Missing party names/IDs | Warning | First or second party missing key data |
| No attachments | Warning | No attachment instances added |
| Unsaved attachments | Warning | Attachments with edits not saved |
| No Personal ID attachments | Error | Parties exist but no ID documents |
| ID expiry in past | Error | Party ID or attachment expiry date has passed |
| CR expiry in past | Error | Commercial Registration expired |
| CR status not Active | Error | CR status is not "Active" or "نشط" |
| Party vs ID mismatch | Error/Warning | Name, citizenship, or expiry doesn't match between form and attachment |
| CR signatory vs party mismatch | Error/Warning | Signatory ID or name doesn't match any declared party |

Errors block submission. Warnings allow "Proceed Anyway".

---

## Usage

### DB View
1. Open http://localhost:3000
2. Enter an Application ID and click **Load Context**
3. Inspect structured data (left) and document extractions (right)
4. Optionally edit any field inline
5. Click **Run Agents**

### Manual Entry
1. Switch to the **Manual Entry** tab
2. Fill in application type, first/second party details
3. Add attachments with extracted fields, save each one
4. Click **Run Agents**

### Agent Pipeline (both modes)
- Tier 1 validation runs first (blocks on errors, warns on issues)
- Step 1/2: Condenser agent produces a Legal Brief
- Step 2/2: Legal search agent produces a Legal Opinion
- Results appear in the bottom drawer with Legal Brief, Legal Opinion, and Raw JSON tabs

---

## Project Structure

```
poa_agents/
├── condenser_agent/          # Agent 1: Case data -> Legal Brief
│   ├── Dockerfile
│   ├── manifest.yaml
│   ├── project/acp.py        # ACP handler (JSON-RPC 2.0)
│   └── .env.example
├── legal_search_agent/       # Agent 2: Legal Brief -> Legal Opinion
│   ├── Dockerfile
│   ├── manifest.yaml
│   ├── project/acp.py        # ACP handler (JSON-RPC 2.0)
│   └── .env.example
├── frontend/                 # Next.js 16, React 19, Tailwind v4
│   ├── Dockerfile
│   ├── src/app/
│   │   ├── page.tsx          # Main page (DB View + Manual Entry tabs)
│   │   └── api/agent/        # Server-side proxies (avoids CORS)
│   │       ├── condenser/route.ts
│   │       └── legal-search/route.ts
│   ├── src/components/
│   │   ├── ControlRow.tsx        # DB View header bar
│   │   ├── StructuredPanel.tsx   # Structured data (parties, proofs)
│   │   ├── UnstructuredPanel.tsx  # Document extractions (OCR)
│   │   ├── ManualEntryTab.tsx    # Manual Entry container
│   │   ├── ValidationModal.tsx   # Tier 1 findings modal
│   │   ├── ResultsDrawer.tsx     # Agent results drawer
│   │   └── manual/
│   │       ├── ApplicationForm.tsx  # Party + namadhij form
│   │       └── AttachmentPanel.tsx  # Attachment instances + signatories
│   └── src/lib/
│       ├── agentApi.ts       # ACP JSON-RPC 2.0 client
│       ├── supabase.ts       # Supabase client (lazy init for Docker)
│       ├── validation.ts     # Tier 1 checks (DB View + Manual Entry)
│       └── manualDefaults.ts # Dropdown options, field schemas, types
├── shared/                   # Shared schemas
├── dev.sh                    # Single-command local startup script
└── project_plan.md           # Detailed architecture docs
```

---

## Agents

### Condenser Agent

Takes structured case data + document extractions and produces a **Legal Brief** summarizing the case for legal analysis.

- **Input (Mode B):** `{ case_data, document_extractions, additional_context }`
- **Output:** Markdown with embedded JSON containing case summary, party analysis, POA details, evidence assessment, open questions
- **LLM:** OpenAI (configurable model)

### Legal Search Agent

Takes a Legal Brief and produces a **Legal Opinion** with citations to Qatari law.

- **Input (Mode B):** `{ legal_brief: {...} }`
- **Output:** Markdown with embedded JSON containing overall finding, confidence score, per-issue analysis, article citations, retrieval metrics
- **Pipeline:** Decompose issues -> HyDE article generation -> Agentic RAG retrieval -> Coverage analysis -> Synthesis
- **LLM:** OpenAI (chat + embeddings)

### ACP Protocol

Both agents use the AgentEx ACP protocol:

- **Endpoint:** `POST /api`
- **Protocol:** JSON-RPC 2.0, `method: "message/send"`
- **Response nesting:** `result.content.content` (SendMessageResponse -> TextContent -> string)

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

### Frontend can't reach agents
The frontend proxies through Next.js API routes to avoid CORS. Check that agents are running on the expected ports. For Railway, verify the `CONDENSER_URL` and `LEGAL_SEARCH_URL` env vars point to the correct internal service URLs.

### Condenser returns non-JSON
The agent returns markdown with JSON embedded in a `<details>` block. The `parseAgentContent` function in `frontend/src/lib/agentApi.ts` extracts the JSON. If extraction fails, the raw markdown is displayed.

---

## License

Internal use only.
