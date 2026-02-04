# Sharing Checklist

Use this checklist before compressing and sending the project to a colleague.

## ✅ Already Done

These files are now included and ready:

- [x] `.gitignore` - Excludes sensitive files, node_modules, Python caches
- [x] `condenser_agent/.env.example` - Template with placeholders
- [x] `legal_search_agent/.env.example` - Template with placeholders
- [x] `frontend/.env.example` - Template with placeholders
- [x] `condenser_agent/requirements.txt` - Python dependencies
- [x] `legal_search_agent/requirements.txt` - Python dependencies
- [x] `frontend/package.json` - Node.js dependencies (already existed)
- [x] `SETUP.md` - Quick setup guide for new developers
- [x] `README.md` - Comprehensive documentation
- [x] `dev.sh` - Single-command startup script
- [x] Dockerfiles for all services

## ⚠️ Before Sharing

1. **Remove sensitive files** (already handled by .gitignore):
   ```bash
   # Make sure these don't exist:
   rm -f condenser_agent/.env
   rm -f legal_search_agent/.env
   rm -f frontend/.env.local
   rm -f .dev-pids
   ```

2. **Verify .env files are removed**:
   ```bash
   find . -name ".env" -not -name ".env.example" | grep -v node_modules
   # Should return nothing
   ```

3. **Clean build artifacts**:
   ```bash
   # Frontend
   rm -rf frontend/.next
   rm -rf frontend/node_modules  # Optional - they can reinstall
   
   # Python
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null
   ```

## 📦 Compress the Project

From the **parent directory** of poa_agents:

```bash
# Using tar (recommended - preserves permissions)
tar -czf poa_agents.tar.gz poa_agents/

# Or using zip
zip -r poa_agents.zip poa_agents/ -x "*.git/*" "*/node_modules/*" "*/__pycache__/*" "*/.venv/*"
```

## 📤 What to Send

Send your colleague:

1. **The compressed file**: `poa_agents.tar.gz` or `poa_agents.zip`
2. **Credentials separately** (via secure channel):
   - OpenAI API key
   - Supabase URL
   - Supabase Anon Key

## 📝 Instructions for Your Colleague

Tell them to:

1. Extract the archive
2. Read `SETUP.md` and follow the steps
3. Use the credentials you provided to fill in the `.env` files
4. Run `./dev.sh` to start everything

## ✨ What Works Out of the Box

After following SETUP.md, your colleague will have:

- ✅ All dependencies defined (they just need to install)
- ✅ Environment variable templates (they just need to fill in)
- ✅ Single command to start everything (`./dev.sh`)
- ✅ Clear documentation for setup and architecture
- ✅ Railway deployment instructions
- ✅ Troubleshooting guide

## 🔒 What They Need

Your colleague will need to provide/install:

- Python 3.11+ (system requirement)
- Node.js 18+ (system requirement)
- `pip install agentex-sdk` (one command)
- API keys and Supabase credentials (you provide these)

## Estimated Setup Time

- **First-time setup**: 5-10 minutes
- **Subsequent runs**: < 30 seconds (`./dev.sh`)

---

## Quick Verification

Before sharing, run this from the project root:

```bash
# Verify all setup files exist
ls -la .gitignore SETUP.md README.md
ls -la condenser_agent/.env.example condenser_agent/requirements.txt
ls -la legal_search_agent/.env.example legal_search_agent/requirements.txt
ls -la frontend/.env.example frontend/package.json
ls -la dev.sh

# Verify no sensitive files
! find . -name ".env" -not -name ".env.example" | grep -v node_modules | grep -q .
echo "✅ No .env files found (good!)"
```

All files should exist, and the last command should print "✅ No .env files found (good!)".
