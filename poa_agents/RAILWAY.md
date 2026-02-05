# Railway Deployment

Deploy all 3 services (frontend + 2 agents) from this repo to Railway.

## Prerequisites

- GitHub repo pushed (Railway deploys from GitHub)
- OpenAI API key
- Supabase project URL + anon key

## Setup

### 1. Create a Railway project

Go to [railway.app](https://railway.app) and create a new project.

### 2. Create 3 services from the same GitHub repo

Click **New Service > GitHub Repo** three times, selecting the same repo each time. Name them:

| Service Name | Root Directory | Dockerfile Path |
|--------------|---------------|-----------------|
| `frontend` | `poa_agents/frontend` | `Dockerfile` |
| `condenser-agent` | `poa_agents` | `condenser_agent/Dockerfile` |
| `legal-search-agent` | `poa_agents` | `legal_search_agent/Dockerfile` |

For each service, set the **Root Directory** and **Dockerfile Path** in **Settings > Build**.

> The agents use `poa_agents` as root (not their own subdirectory) because their Dockerfiles need access to `shared/`.

### 3. Set environment variables

Go to **Variables** tab for each service.

**condenser-agent:**
```
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
```

**legal-search-agent:**
```
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SIMILARITY_THRESHOLD=0.3
MAX_ARTICLES_PER_ISSUE=5
```

**frontend:**
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
CONDENSER_URL=http://condenser-agent.railway.internal:8012
LEGAL_SEARCH_URL=http://legal-search-agent.railway.internal:8013
```

> Replace `condenser-agent` and `legal-search-agent` in the URLs with your actual Railway service names if different.
>
> `NEXT_PUBLIC_*` vars are baked into the JS bundle at build time. The frontend Dockerfile declares them as `ARG` so Railway passes them during the Docker build.

### 4. Generate a public domain for the frontend

Go to frontend service **Settings > Networking > Generate Domain**.

Only the frontend needs a public URL. The agents are accessed via Railway's private network (`*.railway.internal`) — they don't need public domains.

### 5. Configure watch paths (optional, prevents unnecessary rebuilds)

In each service's **Settings > Build > Watch Paths**:

| Service | Watch Paths |
|---------|-------------|
| `frontend` | `/poa_agents/frontend/**` |
| `condenser-agent` | `/poa_agents/condenser_agent/**`, `/poa_agents/shared/**` |
| `legal-search-agent` | `/poa_agents/legal_search_agent/**`, `/poa_agents/shared/**` |

### 6. Deploy

Push to GitHub. Railway auto-builds and deploys all 3 services.

## How it works

```
Browser  --->  Frontend (public)  --private network-->  Condenser Agent (port 8012)
                                  --private network-->  Legal Search Agent (port 8013)
```

- Frontend runs on port 3000 (standalone Next.js)
- Agents run on ports 8012/8013 (agentex ACP servers)
- Frontend API routes (`/api/agent/condenser`, `/api/agent/legal-search`) proxy to agents server-side using the `CONDENSER_URL` and `LEGAL_SEARCH_URL` env vars
- No CORS issues since agent calls are server-to-server over Railway's private network

## Troubleshooting

**Frontend can't reach agents**: Check that `CONDENSER_URL` and `LEGAL_SEARCH_URL` match the actual Railway service names. The format is `http://<service-name>.railway.internal:<port>`.

**NEXT_PUBLIC_* vars undefined in browser**: These are build-time variables. After changing them, you need to trigger a redeploy (not just restart) so the Docker build runs again with the new values.

**Agent build fails on agentex-sdk**: If pip can't install `agentex-sdk==0.6.7`, check Railway build logs. You may need to add system deps to the Dockerfile:
```dockerfile
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
```
