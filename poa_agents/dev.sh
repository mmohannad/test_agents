#!/usr/bin/env bash
#
# Start all POA Agent services for local development.
#
# Usage:
#   ./dev.sh          Start all services (condenser, legal search, frontend)
#   ./dev.sh stop     Kill all running services
#
# Prerequisites:
#   - Node.js >= 18 (for frontend)
#   - Python 3.11+ (for agents)
#   - agentex CLI installed (pip install agentex)
#   - Agent .env files configured (see .env.example in each agent dir)
#   - Frontend dependencies installed (cd frontend && npm install)
#
# Ports:
#   3000  Frontend (Next.js)
#   8012  Condenser Agent (AgentEx ACP)
#   8013  Legal Search Agent (AgentEx ACP)
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()  { echo -e "${CYAN}[dev]${NC} $*"; }
ok()   { echo -e "${GREEN}[dev]${NC} $*"; }
warn() { echo -e "${YELLOW}[dev]${NC} $*"; }
err()  { echo -e "${RED}[dev]${NC} $*" >&2; }

PIDS_FILE="$ROOT_DIR/.dev-pids"

stop_services() {
  if [[ -f "$PIDS_FILE" ]]; then
    log "Stopping services..."
    while IFS= read -r pid; do
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null && ok "Killed PID $pid" || true
      fi
    done < "$PIDS_FILE"
    rm -f "$PIDS_FILE"
  fi

  # Also kill by port as a fallback
  for port in 8012 8013 3000; do
    pid=$(lsof -ti TCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1 || true)
    if [[ -n "$pid" ]]; then
      kill "$pid" 2>/dev/null && warn "Killed leftover process on port $port (PID $pid)" || true
    fi
  done

  ok "All services stopped."
}

if [[ "${1:-}" == "stop" ]]; then
  stop_services
  exit 0
fi

# --- Pre-flight checks ---

if ! command -v agentex &>/dev/null; then
  err "agentex CLI not found. Install with: pip install agentex"
  exit 1
fi

if ! command -v node &>/dev/null; then
  err "node not found. Install Node.js >= 18."
  exit 1
fi

if [[ ! -f "$ROOT_DIR/condenser_agent/.env" ]]; then
  err "condenser_agent/.env not found. Copy from .env.example and fill in secrets."
  exit 1
fi

if [[ ! -f "$ROOT_DIR/legal_search_agent/.env" ]]; then
  err "legal_search_agent/.env not found. Copy from .env.example and fill in secrets."
  exit 1
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  log "Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

# --- Stop any existing services ---
stop_services 2>/dev/null || true

# --- Start services ---
rm -f "$PIDS_FILE"

log "Starting condenser agent on port 8012..."
(cd "$ROOT_DIR" && agentex agents run --manifest condenser_agent/manifest.yaml > /dev/null 2>&1) &
echo $! >> "$PIDS_FILE"

log "Starting legal search agent on port 8013..."
(cd "$ROOT_DIR" && agentex agents run --manifest legal_search_agent/manifest.yaml > /dev/null 2>&1) &
echo $! >> "$PIDS_FILE"

log "Starting frontend on port 3000..."
(cd "$ROOT_DIR/frontend" && npm run dev > /dev/null 2>&1) &
echo $! >> "$PIDS_FILE"

# --- Wait for services to be ready ---
log "Waiting for services to start..."

wait_for_port() {
  local port=$1 name=$2 timeout=30
  for ((i=0; i<timeout; i++)); do
    if lsof -ti TCP:"$port" -sTCP:LISTEN &>/dev/null; then
      ok "$name ready on port $port"
      return 0
    fi
    sleep 1
  done
  err "$name failed to start on port $port within ${timeout}s"
  return 1
}

wait_for_port 8012 "Condenser agent"
wait_for_port 8013 "Legal search agent"
wait_for_port 3000 "Frontend"

echo ""
ok "=== All services running ==="
echo ""
echo -e "  Frontend:       ${GREEN}http://localhost:3000${NC}"
echo -e "  Condenser:      ${CYAN}http://localhost:8012/api${NC}"
echo -e "  Legal Search:   ${CYAN}http://localhost:8013/api${NC}"
echo ""
echo -e "  Stop all:       ${YELLOW}./dev.sh stop${NC}"
echo ""
log "Press Ctrl+C to stop all services."

# --- Keep running until Ctrl+C ---
cleanup() {
  echo ""
  stop_services
  exit 0
}
trap cleanup INT TERM

wait
