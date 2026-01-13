FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy shared utilities
COPY shared/ /app/shared/

# Copy agent code
COPY tier1_validation_agent/ /app/tier1_validation_agent/

# Set working directory to agent
WORKDIR /app/tier1_validation_agent

# Install dependencies
RUN uv pip install --system -e .

# Set Python path to include shared
ENV PYTHONPATH=/app

# Run the worker
CMD ["python", "project/run_worker.py"]

