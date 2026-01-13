# search-agent - AgentEx Sync ACP Template

This is a starter template for building synchronous agents with the AgentEx framework. It provides a basic implementation of the Agent 2 Client Protocol (ACP) with immediate response capabilities to help you get started quickly.

✅ **Azure OpenAI Integration**: This agent is configured to use Azure OpenAI for intelligent responses. See the [Azure OpenAI Configuration](#configure-azure-openai-credentials) section below.

## What You'll Learn

- **Tasks**: A task is a grouping mechanism for related messages. Think of it as a conversation thread or a session.
- **Messages**: Messages are communication objects within a task. They can contain text, data, or instructions.
- **Sync ACP**: Synchronous Agent Communication Protocol that requires immediate responses
- **Message Handling**: How to process and respond to messages in real-time

## Running the Agent

1. Run the agent locally:
```bash
agentex agents run --manifest manifest.yaml
```

The agent will start on port 8000 and respond immediately to any messages it receives.

## What's Inside

This template:
- Sets up a basic sync ACP server
- Handles incoming messages with immediate responses
- Provides a foundation for building real-time agents
- Can include streaming support for long responses

## Next Steps

For more advanced agent development, check out the AgentEx tutorials:

- **Tutorials 00-08**: Learn about building synchronous agents with ACP
- **Tutorials 09-10**: Learn how to use Temporal to power asynchronous agents
  - Tutorial 09: Basic Temporal workflow setup
  - Tutorial 10: Advanced Temporal patterns and best practices

These tutorials will help you understand:
- How to handle long-running tasks
- Implementing state machines
- Managing complex workflows
- Best practices for async agent development

## The Manifest File

The `manifest.yaml` file is your agent's configuration file. It defines:
- How your agent should be built and packaged
- What files are included in your agent's Docker image
- Your agent's name and description
- Local development settings (like the port your agent runs on)

This file is essential for both local development and deployment of your agent.

## Project Structure

```
search_agent/
├── project/                  # Your agent's code
│   ├── __init__.py          # Python package marker
│   ├── acp.py               # ✅ REQUIRED: ACP server and message handlers (AgentEx core)
│   └── llm_client.py        # 🔧 CUSTOM: Azure OpenAI client wrapper (agent-specific)
├── .env                     # 🔧 CUSTOM: Environment variables (create this file)
├── Dockerfile               # Container definition
├── manifest.yaml            # ✅ REQUIRED: Agent configuration (AgentEx core)
├── dev.ipynb                # Development notebook for testing
└── pyproject.toml           # ✅ REQUIRED: Dependencies (uv)

```

### File Purposes

**Required Files (AgentEx Core):**
- `project/acp.py` - **REQUIRED**: This is the ACP (Agent Client Protocol) server that handles incoming messages. AgentEx expects this file to exist and contain your message handlers. This is the entry point for your agent.
- `manifest.yaml` - **REQUIRED**: AgentEx configuration file that defines how your agent is built, deployed, and configured.
- `pyproject.toml` - **REQUIRED**: Python dependencies and project metadata.

**Custom Files (Your Implementation):**
- `project/llm_client.py` - **CUSTOM**: A simple wrapper around Azure OpenAI that we created for this agent. This is NOT part of AgentEx core - it's specific to this agent's needs. You can modify or replace it as needed.
- `.env` - **CUSTOM**: Environment variables file for local development. Contains your Azure OpenAI credentials. Not committed to git (should be in `.gitignore`).

**Note**: The `acp.py` file is the only file that AgentEx requires. Everything else (`llm_client.py`, `.env`, etc.) is custom code we added to make the agent work with Azure OpenAI.

## Development

### 1. Customize Message Handlers
- Modify the handlers in `acp.py` to implement your agent's logic
- Add your own tools and capabilities
- Implement custom response generation

### 2. Test Your Agent with the Development Notebook
Use the included `dev.ipynb` Jupyter notebook to test your agent interactively:

```bash
# Start Jupyter notebook (make sure you have jupyter installed)
jupyter notebook dev.ipynb

# Or use VS Code to open the notebook directly
code dev.ipynb
```

The notebook includes:
- **Setup**: Connect to your local AgentEx backend
- **Non-streaming tests**: Send messages and get complete responses
- **Streaming tests**: Test real-time streaming responses
- **Task management**: Optional task creation and management

The notebook automatically uses your agent name (`search-agent`) and provides examples for both streaming and non-streaming message handling.

### 3. Manage Dependencies


You chose **uv** for package management. Here's how to work with dependencies:

```bash
# Add new dependencies
agentex uv add requests openai anthropic

# Install/sync dependencies
agentex uv sync

# Run commands with uv
uv run agentex agents run --manifest manifest.yaml
```

**Benefits of uv:**
- Faster dependency resolution and installation
- Better dependency isolation
- Modern Python packaging standards



### 4. Configure Azure OpenAI Credentials ✅

**Status**: This agent is configured and working with Azure OpenAI!

This agent uses Azure OpenAI for LLM responses. Configure credentials using one of these methods:

**Option 1: Create a `.env` file (Recommended for local development)**
```bash
# Create .env file in the search_agent directory
cat > .env << EOF
AZURE_OPENAI_API_KEY="REMOVED"
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
AZURE_OPENAI_API_VERSION="2025-01-01-preview"
LLM_MODEL="gpt-4o"
EOF
```

**Option 2: Export environment variables**
```bash
export AZURE_OPENAI_API_KEY="REMOVED"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_API_VERSION="2025-01-01-preview"
export LLM_MODEL="gpt-4o"
```

**Option 3: Use Azure AD Managed Identity (for production)**
- Configure Azure credentials (Azure CLI, managed identity, etc.)
- The agent will use `DefaultAzureCredential` automatically
- No `AZURE_OPENAI_API_KEY` needed

**Required Environment Variables:**
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key (for local dev)
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_VERSION`: API version (default: `2025-01-01-preview`)
- `LLM_MODEL`: Model deployment name (default: `gpt-4o`)

**Quick Setup** (Already done!):
The `.env` file has been created with your Azure OpenAI credentials. The agent automatically loads this file when it starts. You should see in the logs:
```
SimpleLLMClient initialization - AZURE_OPENAI_API_KEY present: True
Using API key authentication for Azure OpenAI
```

### 5. Configure Supabase Credentials ✅

**Status**: This agent performs semantic search over legal articles stored in Supabase!

This agent uses Supabase for vector similarity search over legal articles. Configure credentials:

**Option 1: Add to `.env` file (Recommended for local development)**
```bash
# Add to your existing .env file
cat >> .env << EOF
SUPABASE_URL="https://cjidkejfazctyqhkfmzz.supabase.co"
SUPABASE_ANON_KEY="your-supabase-anon-key"
EOF
```

**Option 2: Export environment variables**
```bash
export SUPABASE_URL="https://cjidkejfazctyqhkfmzz.supabase.co"
export SUPABASE_ANON_KEY="your-supabase-anon-key"
```

**Required Environment Variables:**
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous/public key
- `EMBEDDING_MODEL`: (Optional) Azure OpenAI embedding model deployment name
  - **Default**: `text-embedding-3-small` (1536 dimensions)
  - **Recommended**: `text-embedding-3-small` (1536 dimensions) - matches your schema
  - **Alternative**: `text-embedding-3-large` (3072 dimensions) - requires schema update
  - **Important**: This must match the model used to generate embeddings in your database
  - For Azure OpenAI, this is your deployment name in Azure Portal

**How Semantic Search Works:**
1. User sends a query/question
2. Agent generates an embedding vector for the query using Azure OpenAI
3. Agent searches Supabase `articles` table using vector similarity (cosine distance)
4. Agent retrieves top 5 most relevant articles
5. Agent uses the articles as context to generate an intelligent, cited response

**Database Schema:**
The agent works with the `articles` table with the following structure:
- `article_number` (INT PRIMARY KEY) - Unique identifier for each legal article
- `hierarchy_path` (JSONB) - Legal hierarchy structure (section, book, chapter, etc.)
- `text_arabic` (TEXT) - Original Arabic legal text
- `text_english` (TEXT) - English translation
- `embedding` (VECTOR(1536)) - English semantic embeddings (text-embedding-3-small)
- `arabic_embedding` (VECTOR(1536)) - Arabic semantic embeddings

**Setting Up Vector Search Function (Required):**

For semantic search to work, you need to create a database function in Supabase. Run this SQL in your Supabase SQL Editor:

```sql
-- Create a function for matching articles by embedding similarity
-- This function uses pgvector's cosine distance operator (<=>) for semantic search
CREATE OR REPLACE FUNCTION match_articles(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  language text DEFAULT 'english'
)
RETURNS TABLE (
  article_number integer,
  hierarchy_path jsonb,
  text_arabic text,
  text_english text,
  similarity float
)
LANGUAGE plpgsql
AS $$
DECLARE
  embedding_col text;
BEGIN
  -- Determine which embedding column to use based on language
  IF language = 'arabic' THEN
    embedding_col := 'arabic_embedding';
  ELSE
    embedding_col := 'embedding';
  END IF;
  
  -- Perform vector similarity search using cosine distance
  -- The <=> operator returns cosine distance (0 = identical, 2 = opposite)
  -- We convert to similarity: 1 - distance (higher = more similar)
  RETURN QUERY
  EXECUTE format('
    SELECT 
      a.article_number,
      a.hierarchy_path,
      a.text_arabic,
      a.text_english,
      1 - (a.%I <=> $1) as similarity
    FROM articles a
    WHERE 1 - (a.%I <=> $1) > $2
    ORDER BY a.%I <=> $1
    LIMIT $3
  ', embedding_col, embedding_col, embedding_col)
  USING query_embedding, match_threshold, match_count;
END;
$$;

-- Grant execute permission to authenticated users (adjust as needed)
GRANT EXECUTE ON FUNCTION match_articles(vector(1536), float, int, text) TO anon, authenticated;
```

**Note:** The function uses the exact table name `"Articles"` (quoted to preserve case) as per your schema. The function leverages the existing IVFFlat indexes on the embedding columns for fast approximate nearest neighbor search.

**Note:** This function uses pgvector's `<=>` operator for cosine distance. Make sure the `pgvector` extension is enabled in your Supabase project.

## Local Development

### 1. Start the Agentex Backend
```bash
# Navigate to the backend directory
cd agentex

# Start all services using Docker Compose
make dev

# Optional: In a separate terminal, use lazydocker for a better UI (everything should say "healthy")
lzd
```

### 3. Run Your Agent
```bash
# From this directory
export ENVIRONMENT=development && agentex agents run --manifest manifest.yaml
```

### 4. Interact with Your Agent

**Option 1: Web UI (Recommended)**
```bash
# Start the local web interface
cd agentex-web
make dev

# Then open http://localhost:3000 in your browser to chat with your agent
```

**Option 2: CLI (Deprecated)**
```bash
# Submit a task via CLI
agentex tasks submit --agent search-agent --task "Your task here"
```

## Development Tips

### Environment Variables
- Create a `.env` file in the `search_agent` directory (same level as `manifest.yaml`)
- The `.env` file is automatically loaded when the agent starts
- Required: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`
- Optional: `LLM_MODEL` (defaults to `gpt-4o`)

### Local Testing
- Use `export ENVIRONMENT=development` before running your agent
- This enables local service discovery and debugging features
- Your agent will automatically connect to locally running services

### Sync ACP Considerations
- Responses must be immediate (no long-running operations)
- Use streaming for longer responses
- Keep processing lightweight and fast
- Consider caching for frequently accessed data

### Debugging
- Check agent logs in the terminal where you ran the agent
- Use the web UI to inspect task history and responses
- Monitor backend services with `lzd` (LazyDocker)
- Test response times and optimize for speed

### To build the agent Docker image locally (normally not necessary):

1. Build the agent image:
```bash
agentex agents build --manifest manifest.yaml
```

```bash
# Build with uv
agentex agents build --manifest manifest.yaml --push
```



## Advanced Features

### Streaming Responses
Handle long responses with streaming:

```python
# In project/acp.py
@acp.on_message_send
async def handle_message_send(params: SendMessageParams):
    # For streaming responses
    async def stream_response():
        for chunk in generate_response_chunks():
            yield TaskMessageUpdate(
                content=chunk,
                is_complete=False
            )
        yield TaskMessageUpdate(
            content="",
            is_complete=True
        )
    
    return stream_response()
```

### Custom Response Logic
Add sophisticated response generation:

```python
# In project/acp.py
@acp.on_message_send
async def handle_message_send(params: SendMessageParams):
    # Analyze input
    user_message = params.content.content
    
    # Generate response
    response = await generate_intelligent_response(user_message)
    
    return TextContent(
        author=MessageAuthor.AGENT,
        content=response
    )
```

### Integration with External Services

```bash
# Add service clients
agentex uv add httpx requests-oauthlib

# Add AI/ML libraries
agentex uv add openai anthropic transformers

# Add fast processing libraries
agentex uv add numpy pandas
```


## Troubleshooting

### Common Issues

1. **Agent not appearing in web UI**
   - Check if agent is running on port 8000
   - Verify `ENVIRONMENT=development` is set
   - Check agent logs for errors

2. **Slow response times**
   - Profile your message handling code
   - Consider caching expensive operations
   - Optimize database queries and API calls

3. **Dependency issues**

   - Run `agentex uv sync` to ensure all dependencies are installed


4. **Port conflicts**
   - Check if another service is using port 8000
   - Use `lsof -i :8000` to find conflicting processes

5. **Azure OpenAI authentication errors**
   - Verify `.env` file exists in the `search_agent` directory (same level as `manifest.yaml`)
   - Check that `AZURE_OPENAI_API_KEY` is set correctly
   - Verify `AZURE_OPENAI_ENDPOINT` matches your Azure resource (no trailing slash)
   - Ensure `LLM_MODEL` matches your deployment name exactly

6. **"DeploymentNotFound" errors**
   - Verify your `LLM_MODEL` matches the deployment name in Azure OpenAI
   - Check that the deployment exists and is active in your Azure OpenAI resource

## How It Works

1. **User sends message** → UI sends text to agent
2. **ACP handler receives** → `acp.py` `handle_message_send` function processes the message
3. **Embedding generated** → `llm_client.py` generates embedding vector for the query using Azure OpenAI
4. **Semantic search** → `search_client.py` searches Supabase articles table using vector similarity
5. **Context built** → Relevant articles are retrieved and formatted as context
6. **LLM client called** → `llm_client.py` sends request to Azure OpenAI with article context
7. **Response generated** → Azure OpenAI returns intelligent response with citations
8. **Response sent back** → Agent returns response to user via UI

The agent accepts **normal text input** from the UI - no special JSON formatting required!

**Key Features:**
- ✅ Semantic search over legal articles using vector embeddings
- ✅ Automatic citation of article numbers in responses
- ✅ Support for both English and Arabic articles
- ✅ Configurable similarity threshold and result limits
- ✅ Fallback mechanisms if vector search fails

Happy building with Sync ACP! 🚀⚡