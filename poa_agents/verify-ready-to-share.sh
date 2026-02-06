#!/usr/bin/env bash
# Quick verification script to check if project is ready to share

echo "🔍 Verifying project is ready to share..."
echo ""

ERRORS=0
WARNINGS=0

# Check essential files exist
echo "📋 Checking essential files..."
FILES=(
  ".gitignore"
  "SETUP.md"
  "SHARING_CHECKLIST.md"
  "README.md"
  "dev.sh"
  "condenser_agent/.env.example"
  "condenser_agent/requirements.txt"
  "legal_search_agent/.env.example"
  "legal_search_agent/requirements.txt"
  "frontend/.env.example"
  "frontend/package.json"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✅ $file"
  else
    echo "  ❌ $file (MISSING)"
    ((ERRORS++))
  fi
done

echo ""
echo "🔒 Checking for sensitive files..."

# Check no actual .env files exist
if find . -name ".env" -not -name ".env.example" -not -path "*/node_modules/*" -not -path "*/.venv/*" 2>/dev/null | grep -q .; then
  echo "  ⚠️  WARNING: Found .env files (should not be shared):"
  find . -name ".env" -not -name ".env.example" -not -path "*/node_modules/*" -not -path "*/.venv/*" 2>/dev/null | sed 's/^/     /'
  ((WARNINGS++))
else
  echo "  ✅ No .env files found (good!)"
fi

# Check for .dev-pids
if [ -f ".dev-pids" ]; then
  echo "  ⚠️  WARNING: Found .dev-pids (should be cleaned)"
  ((WARNINGS++))
else
  echo "  ✅ No .dev-pids file"
fi

echo ""
echo "📦 Checking documentation..."

# Check if SETUP.md mentions all key steps
if grep -q "agentex" SETUP.md && grep -q ".env" SETUP.md && grep -q "npm install" SETUP.md; then
  echo "  ✅ SETUP.md has installation instructions"
else
  echo "  ❌ SETUP.md missing key setup steps"
  ((ERRORS++))
fi

echo ""
echo "═══════════════════════════════════════"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo "✨ Perfect! Project is ready to share."
  echo ""
  echo "Next steps:"
  echo "  1. Review SHARING_CHECKLIST.md"
  echo "  2. Compress: tar -czf poa_agents.tar.gz poa_agents/"
  echo "  3. Send to colleague with credentials"
elif [ $ERRORS -eq 0 ]; then
  echo "⚠️  Project is mostly ready, but has $WARNINGS warning(s)."
  echo "Review warnings above before sharing."
else
  echo "❌ Project has $ERRORS error(s) and $WARNINGS warning(s)."
  echo "Fix errors before sharing."
  exit 1
fi
