# Quick Setup Guide for POA Agents

This guide will help you get the POA Agents project running on your machine in under 5 minutes.

## Prerequisites

Before you begin, make sure you have:

- **Python 3.11+** installed ([python.org](https://www.python.org/downloads/))
- **Node.js 18+** installed ([nodejs.org](https://nodejs.org/))
- **pip** (Python package installer, usually comes with Python)
- **Git** (to clone the repository)

## Step-by-Step Setup

### 1. Install AgentEx CLI

```bash
pip install agentex-sdk
```

Verify installation:
```bash
agentex --version
```

### 2. Configure Environment Variables

You'll need API keys and Supabase credentials. If you don't have them, ask your team lead.

#### Condenser Agent
```bash
cp condenser_agent/.env.example condenser_agent/.env
```

Edit `condenser_agent/.env` and fill in:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Your Supabase anonymous key

#### Legal Search Agent
```bash
cp legal_search_agent/.env.example legal_search_agent/.env
```

Edit `legal_search_agent/.env` with the same credentials as above.

#### Frontend
```bash
cp frontend/.env.example frontend/.env.local
```

Edit `frontend/.env.local` with the same Supabase credentials.

### 3. Install Python Dependencies (Optional)

The agents will automatically use AgentEx to manage dependencies, but if you want to install them manually:

```bash
# For condenser agent
cd condenser_agent
pip install -r requirements.txt
cd ..

# For legal search agent
cd legal_search_agent
pip install -r requirements.txt
cd ..
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Start Everything

From the root directory, run:

```bash
./dev.sh
```

This single command starts all three services:
- **Condenser Agent** on port 8012
- **Legal Search Agent** on port 8013
- **Frontend** on port 3000

Wait for the "All services running" message (usually 10-30 seconds).

### 6. Open the App

Open your browser to:
```
http://localhost:3000
```

### 7. Stop Everything

Press `Ctrl+C` in the terminal, or run:

```bash
./dev.sh stop
```

## Troubleshooting

### "Port already in use"

Kill processes on the ports:
```bash
lsof -ti TCP:8012 -sTCP:LISTEN | xargs kill
lsof -ti TCP:8013 -sTCP:LISTEN | xargs kill
lsof -ti TCP:3000 -sTCP:LISTEN | xargs kill
```

### "agentex: command not found"

Make sure pip's bin directory is in your PATH:
```bash
# On macOS/Linux
export PATH="$PATH:$HOME/.local/bin"

# Or reinstall with
pip install --user agentex-sdk
```

### "Module not found" errors

Make sure you're running commands from the project root directory and have installed dependencies:
```bash
cd frontend && npm install && cd ..
```

### Frontend can't reach agents

Make sure:
1. All services are running (`./dev.sh` shows "All services running")
2. `frontend/.env.local` has the correct URLs (http://localhost:8012, http://localhost:8013)

## Next Steps

- Read [README.md](./README.md) for detailed architecture information
- Check [project_plan.md](./project_plan.md) for technical specifications
- See [SCHEMA.md](./SCHEMA.md) for database schema details

## Getting Help

If you encounter issues:
1. Check that all `.env` files are properly configured
2. Verify all prerequisites are installed
3. Check the terminal output for error messages
4. Ask your team lead for credentials if needed
