FROM python:3.12-slim

WORKDIR /app

# Install agentex-sdk + additional deps it doesn't bundle
RUN pip install --no-cache-dir agentex-sdk==0.6.7 supabase python-dotenv pyyaml

# Copy shared utilities
COPY shared/ /app/shared/

# Copy agent code
COPY legal_search_agent/ /app/legal_search_agent/

# Set Python path so imports work
ENV PYTHONPATH=/app

WORKDIR /app/legal_search_agent

# agentex agents run reads the manifest and starts the ACP server
CMD ["agentex", "agents", "run", "--manifest", "manifest.yaml"]
