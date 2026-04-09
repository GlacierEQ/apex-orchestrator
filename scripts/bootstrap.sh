#!/usr/bin/env bash
# APEX Activated Connector Bootstrap
# GlacierEQ — Case 1FDV-23-0001009
set -euo pipefail

echo "🌊 APEX Bootstrap — GlacierEQ | Casey Barton"
echo "================================================"

# Check required env vars
REQUIRED_VARS=(GITHUB_PAT SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY OPENAI_API_KEY)
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "❌ Missing: $var"
    exit 1
  fi
  echo "✅ $var present"
done

# Install dependencies
echo ""
echo "📦 Installing APEX dependencies..."
npm install \
  @langchain/langgraph \
  @langchain/openai \
  @langchain/community \
  @supabase/supabase-js \
  @modelcontextprotocol/sdk \
  dotenv tsx

# Install MCP servers globally
echo ""
echo "🔌 Installing MCP servers..."
npx -y @modelcontextprotocol/server-github --version 2>/dev/null || true
npx -y @modelcontextprotocol/server-memory --version 2>/dev/null || true
npx -y @modelcontextprotocol/server-sequential-thinking --version 2>/dev/null || true
npx -y @supabase/mcp-server-supabase@latest --version 2>/dev/null || true

# Bootstrap Supabase schema
echo ""
echo "🗄️  Bootstrapping Supabase vector schema..."
npx tsx -e "import { bootstrapSupabaseSchema } from './src/apex-swarm.ts'; bootstrapSupabaseSchema();"

echo ""
echo "✅ APEX activated. Run:"
echo "   npx tsx src/apex-swarm.ts \"your task here\""
