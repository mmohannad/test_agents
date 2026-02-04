FROM python:3.12-slim

WORKDIR /app

# Install agentex-sdk (provides all deps: openai, supabase, fastapi, uvicorn, etc.)
RUN pip install --no-cache-dir agentex-sdk==0.6.7

# Copy shared utilities
COPY shared/ /app/shared/

# Copy agent code
COPY condenser_agent/ /app/condenser_agent/

# Set Python path so imports work
ENV PYTHONPATH=/app

WORKDIR /app/condenser_agent

# agentex agents run reads the manifest and starts the ACP server
CMD ["agentex", "agents", "run", "--manifest", "manifest.yaml"]
