# MCP Multi-Server Architecture with A2A Protocol

A Model Context Protocol (MCP) implementation with distributed multi-server architecture, Agent-to-Agent (A2A) protocol support, and intelligent web search fallback via LangSearch.

## Architecture

### Multi-Server Design (stdio)

8 specialized MCP servers communicate via stdio (zero network overhead):

```
servers/
├── knowledge_base/    10 tools - Personal knowledge management
├── todo/              6 tools  - Task management
├── system_tools/      4 tools  - System info & processes
├── code_review/       5 tools  - Code analysis
├── location/          3 tools  - Location/time/weather
├── text_tools/        7 tools  - Text processing
├── rag/               4 tools  - Vector search
└── plex/             10 tools  - Media library

Total: 49 local tools across 8 servers
```

### A2A Protocol (HTTP)

Single A2A server exposes selected tools via HTTP for remote access:

```
┌─────────────────────────────────────┐
│   a2a_server.py (Port 8010)         │
│         ↓ stdio                     │
│   ┌─────────────────────┐           │
│   │  Selected MCP       │           │
│   │  Servers            │           │
│   └─────────────────────┘           │
│                                     │
│   Exposes via HTTP                  │
└─────────────────────────────────────┘
```

## Installation

### Prerequisites

* Python 3.10+
* 16GB+ RAM (for multi-agent)
* Ollama with llama3.1:8b or qwen2.5:14b

### Setup

**1. Install Ollama and dependencies**

```bash
curl -fsSL https://ollama.com/install.sh | sh
python -m venv .venv
```

Linux:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:
```powershell
.venv\Scripts\activate
.venv\Scripts\pip.exe install -r .\requirements.txt
```

**2. Configure environment (optional)**

Create `.env` file:
```bash
# A2A Configuration
A2A_ENDPOINTS=http://localhost:8010/.well-known/agent-card.json  # Comma-separated for multiple
A2A_EXPOSED_TOOLS=plex,location,text_tools  # Which tool categories to expose (empty = all)

# LangSearch Web Search
LANGSEARCH_TOKEN=your_api_key  # Optional: https://langsearch.com

# Weather API
WEATHER_TOKEN=your_key  # Optional

# Plex Integration
PLEX_URL=http://ip:32400  # Optional
PLEX_TOKEN=your_token     # Optional
```

All settings are optional - system works without `.env`.

**3. Download models**

```bash
ollama serve
ollama pull llama3.1:8b
ollama pull qwen2.5:14b  # Recommended for multi-agent
ollama pull bge-large
```

**4. Start the system**

**Standalone mode (local tools only):**
```bash
python client.py
```

**Distributed mode (with A2A):**

Terminal 1 - Start A2A server:
```bash
python a2a_server.py
```

Terminal 2 - Start client:
```bash
python client.py
```

Access web UI at: `http://localhost:9000`

## Features

* **Multi-Server Architecture**: 8 specialized stdio servers (49 tools)
* **A2A Protocol**: HTTP-based remote tool execution
* **A2A_EXPOSED_TOOLS**: Control which tool categories are publicly accessible
* **LangSearch Integration**: Automatic web search fallback
* **Multi-Agent Orchestration**: Parallel task execution
* **RAG System**: Vector-based semantic search
* **Plex Integration**: Media library search and analysis
* **Real-Time Monitoring**: WebSocket logs and system metrics

## A2A Server Configuration

### Controlling Exposed Tools

Use `A2A_EXPOSED_TOOLS` in `.env` to control which tool categories are exposed publicly:

**Example 1: Public server (read-only tools)**
```bash
A2A_EXPOSED_TOOLS=plex,location,text_tools
```
Result: Only Plex search, weather, and text processing (20 tools)

**Example 2: Expose everything**
```bash
A2A_EXPOSED_TOOLS=
# Or don't set it at all
```
Result: All 8 servers exposed (49 tools)

**Example 3: Keep private data safe**
```bash
A2A_EXPOSED_TOOLS=plex,location,text_tools,system_tools,code_review
```
Result: Exclude `todo`, `knowledge_base`, `rag` (personal data)

### Available Tool Categories

```
knowledge_base   - 10 tools (notes, KB management)
todo             - 6 tools (task management)
system_tools     - 4 tools (system info, processes)
code_review      - 5 tools (code analysis)
location         - 3 tools (location, time, weather)
text_tools       - 7 tools (text processing)
rag              - 4 tools (vector search)
plex             - 10 tools (media search)
```

### Checking Available Tools

**Method 1: Startup output**
```bash
python a2a_server.py
```
Shows available and exposed tool categories.

**Method 2: HTTP endpoint**
```bash
curl http://localhost:8010/tool-categories
```

Returns JSON with available, exposed, and not-exposed categories.

## Multi-Endpoint A2A Support

Connect to multiple A2A servers simultaneously:

**In `.env`:**
```bash
# Multiple endpoints (comma-separated)
A2A_ENDPOINTS=http://localhost:8010/.well-known/agent-card.json,http://gpu-server:8020/.well-known/agent-card.json

# Single endpoint (backward compatible)
A2A_ENDPOINT=http://localhost:8010/.well-known/agent-card.json
```

**Client behavior:**
- Attempts to register tools from ALL endpoints
- Continues if some endpoints fail
- Tracks which endpoints are active
- Aggregates tools from all successful connections

**Example output:**
```
🌐 Attempting to register 2 A2A endpoint(s)
   [1/2] ✅ Registered successfully (+10 tools)
   [2/2] ✅ Registered successfully (+5 tools)
🔌 A2A Summary: 2/2 successful, 15 new tools
```

## LangSearch Web Search

### Intelligent Fallback Chain

```
User Query
    ↓
1. Check for appropriate tools → Found? → Use tools
    ↓ Not found
2. Try LangSearch web search → Success? → Augment context
    ↓ Failed/unavailable
3. Fall back to base LLM knowledge
```

### Examples

**Tool-based (no search):**
```
> What's the weather in Tokyo?
```
Uses `get_weather_tool` directly.

**General knowledge (LangSearch):**
```
> Who won the 2024 NBA championship?
```
No tool matches → LangSearch performs web search → LLM answers with search results.

**LangSearch unavailable:**
```
> What is quantum computing?
```
No tool matches → LangSearch unavailable → Falls back to LLM training knowledge.

### Configuration

Get API key from https://langsearch.com

```bash
# In .env
LANGSEARCH_TOKEN=your_api_key_here
```

## Multi-Agent System

### Agents

* **Orchestrator** - Plans and coordinates
* **Researcher** - Gathers information (RAG, web, Plex)
* **Coder** - Generates code
* **Analyst** - Analyzes data
* **Writer** - Creates content
* **Planner** - Manages tasks

### Automatic Triggers

**Multi-Agent:**
- Sequential: "then", "after that", "and then"
- Multi-step: "research AND analyze"
- Complex queries (30+ words)

**Single-Agent:**
- Simple questions
- Direct tool calls
- Quick lookups

## Usage

### CLI Commands

```
:commands       List available commands
:tools          List all tools (local + A2A)
:tool <name>    Tool description
:models         List models
:model <name>   Switch model
:clear history  Clear conversation
:multi on/off   Toggle multi-agent
:a2a on/off     Toggle A2A mode
:a2a status     Check A2A status
```

### Example Workflows

**Weather via A2A:**
```
> what's the weather in Vancouver?
```

**Todo management:**
```
> add "deploy feature" to my todos
> list my todos
```

**Plex media search:**
```
> search my plex library for sci-fi movies
> find scenes with explosions
```

**General knowledge (LangSearch):**
```
> Who won the 2024 NBA championship?
> What are the latest AI developments?
```

**Multi-agent:**
```
> Research Python frameworks, analyze their performance, and create a comparison
```

## Network Access

**Find your IP:**
```bash
hostname -I | awk '{print $1}'  # Linux/WSL
ipconfig                         # Windows
```

**Access from other devices:**
```
http://[your-ip]:9000
```

**Configure firewall:**

Windows (PowerShell):
```powershell
New-NetFirewallRule -DisplayName "MCP Chat" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "MCP Logs" -Direction Inbound -LocalPort 8766 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "MCP HTTP" -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "A2A Server" -Direction Inbound -LocalPort 8010 -Protocol TCP -Action Allow
```

Linux:
```bash
sudo ufw allow 8765,8766,9000,8010/tcp
```

## Adding New Tools

**1. Create server directory:**
```bash
mkdir servers/email_tools
cp servers/todo/server.py servers/email_tools/server.py
```

**2. Add tools to server:**
```python
# servers/email_tools/server.py
@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"
```

**3. Restart systems:**
```bash
# A2A server
python a2a_server.py  # Auto-discovers new server

# Client
python client.py  # Auto-discovers new server
```

**4. Control exposure (optional):**
```bash
# In .env
A2A_EXPOSED_TOOLS=plex,location,email_tools  # Include new category
```

New tools are automatically:
- Discovered by client (local access via stdio)
- Exposed by A2A server (if in A2A_EXPOSED_TOOLS or all exposed)
- Available to remote clients (via A2A protocol)

## Troubleshooting

**A2A server not connecting:**
```bash
# Verify server is running
curl http://localhost:8010/.well-known/agent-card.json

# Check .env
A2A_ENDPOINTS=http://localhost:8010/.well-known/agent-card.json

# Check logs for registration messages
```

**Tools not appearing:**
```bash
# List available tool categories
curl http://localhost:8010/tool-categories

# Check A2A_EXPOSED_TOOLS in .env
# Empty or not set = all tools exposed
```

**LangSearch not working:**
- Check `LANGSEARCH_TOKEN` in `.env`
- Verify API key at https://langsearch.com
- Check logs for LangSearch activity
- System falls back to LLM if unavailable

**Multi-agent not activating:**
```
:multi status  # Check if enabled
:multi on      # Enable multi-agent
```

**Web UI won't load:**
- Check ports available: 8765, 8766, 9000, 8010
- Verify firewall rules
- Try `http://localhost:9000` directly

## Directory Structure

```
mcp_a2a/
├── servers/               # 8 specialized MCP servers (stdio)
│   ├── knowledge_base/
│   ├── todo/
│   ├── system_tools/
│   ├── code_review/
│   ├── location/
│   ├── text_tools/
│   ├── rag/
│   └── plex/
├── a2a_server.py         # A2A HTTP server (exposes selected tools)
├── client.py             # AI Agent with multi-server support
├── index.html            # Web UI
├── dashboard.html        # Performance metrics
├── client/
│   ├── a2a_client.py     # A2A client
│   ├── langsearch_client.py  # LangSearch web search
│   ├── multi_agent.py    # Multi-agent orchestration
│   ├── langgraph.py      # Single-agent execution
│   └── websocket.py      # WebSocket server
└── tools/                # Tool implementations
```

## API Details

### A2A Protocol

**Agent Card** (`/.well-known/agent-card.json`):
```json
{
  "name": "Local A2A Agent",
  "version": "1.0.0",
  "endpoints": {
    "a2a": "http://localhost:8010/a2a"
  }
}
```

**RPC Methods:**
- `a2a.discover` - List available tools
- `a2a.call` - Execute tool

**Example Call:**
```json
{
  "jsonrpc": "2.0",
  "method": "a2a.call",
  "params": {
    "tool": "get_weather_tool",
    "arguments": {"city": "London"}
  }
}
```

### LangSearch API

**Endpoint**: `https://api.langsearch.com/v1/web-search`

**Authentication**: Bearer token

**Error handling**: Automatic fallback on 401/429/timeout

## License

MIT License