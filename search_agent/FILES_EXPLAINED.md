# Files Explained

## Required Files (AgentEx Core)

These files are **required** by AgentEx and must exist for your agent to work:

### 1. `project/acp.py` ✅ REQUIRED
- **Purpose**: ACP (Agent Client Protocol) server that handles incoming messages
- **Why Required**: AgentEx expects this file to exist. It's the entry point for your agent.
- **What it does**: Contains message handlers (like `@acp.on_message_send`) that process user messages
- **Can you modify it?**: YES - This is where you implement your agent's logic
- **Can you delete it?**: NO - AgentEx will fail without it

### 2. `manifest.yaml` ✅ REQUIRED
- **Purpose**: AgentEx configuration file
- **Why Required**: Defines how your agent is built, deployed, and configured
- **What it does**: Specifies agent name, port, dependencies, environment variables, etc.
- **Can you modify it?**: YES - You should customize it for your agent
- **Can you delete it?**: NO - AgentEx needs this to run your agent

### 3. `pyproject.toml` ✅ REQUIRED
- **Purpose**: Python project configuration and dependencies
- **Why Required**: Defines what Python packages your agent needs
- **What it does**: Lists dependencies, Python version, build configuration
- **Can you modify it?**: YES - Add/remove dependencies as needed
- **Can you delete it?**: NO - AgentEx needs this to install dependencies

### 4. `project/__init__.py` ✅ REQUIRED
- **Purpose**: Makes `project/` a Python package
- **Why Required**: Python needs this to import modules from the `project/` directory
- **What it does**: Usually empty, just marks the directory as a package
- **Can you modify it?**: Usually not needed, but you can add package-level code
- **Can you delete it?**: NO - Python imports will fail without it

## Custom Files (Your Implementation)

These files are **custom** code we added - they're NOT part of AgentEx core:

### 1. `project/llm_client.py` 🔧 CUSTOM
- **Purpose**: Simple wrapper around Azure OpenAI for making LLM calls
- **Why Custom**: AgentEx doesn't provide this - we created it for Azure OpenAI integration
- **What it does**: Handles Azure OpenAI authentication (API key or Azure AD) and makes chat completion calls
- **Can you modify it?**: YES - Feel free to customize or replace it
- **Can you delete it?**: YES - But you'll need to update `acp.py` to not use it

### 2. `.env` 🔧 CUSTOM
- **Purpose**: Environment variables for local development
- **Why Custom**: Standard practice for storing secrets locally (not committed to git)
- **What it does**: Stores Azure OpenAI credentials and other environment variables
- **Can you modify it?**: YES - Update with your own credentials
- **Can you delete it?**: YES - But you'll need to set environment variables another way

### 3. `Dockerfile` 🔧 CUSTOM (but recommended)
- **Purpose**: Defines how to build your agent's Docker image
- **Why Custom**: You can customize the build process
- **What it does**: Specifies base image, installs dependencies, sets up the agent
- **Can you modify it?**: YES - Customize for your needs
- **Can you delete it?**: YES - But you won't be able to build Docker images

### 4. `dev.ipynb` 🔧 CUSTOM (optional)
- **Purpose**: Jupyter notebook for testing your agent
- **Why Custom**: Optional development tool
- **What it does**: Provides interactive testing of your agent
- **Can you modify it?**: YES - Customize for your testing needs
- **Can you delete it?**: YES - Not required for the agent to work

## Summary

**Minimum Required Files:**
- `project/acp.py` - Message handlers
- `manifest.yaml` - Agent configuration
- `pyproject.toml` - Dependencies
- `project/__init__.py` - Python package marker

**Everything else is optional/custom** and can be modified or removed as needed.

## Quick Answer

**Q: Do we need `llm_client.py` and `acp.py` files?**

**A:**
- **`acp.py`**: ✅ **YES, REQUIRED** - This is part of AgentEx core. You MUST have this file.
- **`llm_client.py`**: 🔧 **NO, CUSTOM** - This is custom code we created. You can modify or replace it, but it's needed for Azure OpenAI integration.

The `acp.py` file is the only file that AgentEx framework requires. The `llm_client.py` file is just helper code we wrote to make Azure OpenAI calls easier.

