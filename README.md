# MCP Multi-Server Architecture with A2A Protocol

A Model Context Protocol (MCP) implementation with distributed multi-server architecture, Agent-to-Agent (A2A) protocol support, ML-powered Plex recommendations, and intelligent web search fallback via LangSearch.

## Installation

### Prerequisites

* Python 3.10+
* 16GB+ RAM (for multi-agent)
* Ollama installed with at least one model:
  * **Quick start**: `llama3.1:8b` (faster, lower resource usage)
  * **Better results**: `qwen2.5:14b` or larger models

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

Create `.env` file in project root:
```bash
# === Plex Media Server ===
PLEX_URL=http://192.168.0.199:32400    # Plex server URL
PLEX_TOKEN=***************************  # Plex authentication token

# === Weather API ===
WEATHER_TOKEN=***************************  # OpenWeatherMap API key

# === A2A Protocol ===
A2A_ENDPOINTS=http://localhost:8010    # Comma-separated A2A endpoints
A2A_EXPOSED_TOOLS=                     # Tool categories to expose (empty = all)

# === LangSearch Web Search ===
LANGSEARCH_TOKEN=***************************  # LangSearch API key (https://langsearch.com)

# === Agent Configuration ===
MAX_MESSAGE_HISTORY=30                 # Max conversation history (default: 20)

# === RAG Performance ===
CONCURRENT_LIMIT=2                     # Parallel ingestion jobs (default: 1)
EMBEDDING_BATCH_SIZE=50                # Embeddings per batch (default: 20)
DB_FLUSH_BATCH_SIZE=50                 # ChromaDB inserts per batch (default: 30)
```

**Performance tuning:**
- `EMBEDDING_BATCH_SIZE=50` + `DB_FLUSH_BATCH_SIZE=50` = ~6x faster ingestion with `nomic-embed-text`
- For RTX 3060 12GB, can increase to 100 for even faster processing
- `CONCURRENT_LIMIT=2` enables parallel media ingestion

All settings are optional - system works with defaults.

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
plex             - 10 tools (media search) + ML recommendations
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
└── plex/             17 tools  - Media library + ML recommendations

Total: 56 local tools across 8 servers
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

## Features

* **Multi-Server Architecture**: 8 specialized stdio servers (56 tools)
* **A2A Protocol**: HTTP-based remote tool execution
* **A2A_EXPOSED_TOOLS**: Control which tool categories are publicly accessible
* **ML-Powered Plex Recommendations**: Random Forest model trained on your viewing history
* **LangSearch Integration**: Automatic web search fallback
* **Multi-Agent Orchestration**: Parallel task execution
* **RAG System**: Vector-based semantic search
* **Plex Integration**: Media library search and analysis
* **Real-Time Monitoring**: WebSocket logs and system metrics

## ML-Powered Plex Recommendations

The system includes a **Random Forest Classifier** that learns your viewing preferences and provides personalized content recommendations.

### How It Works

**Training Phase (automatic on startup):**
1. **Data Collection**: Imports viewing history from Plex (default: 3000 items)
2. **Feature Engineering**: Extracts genre, rating, runtime, release year, finish/abandon status
3. **Model Training**: Random Forest (100 trees) learns patterns from what you finish vs. abandon
4. **Validation**: Trains on 80% of data, validates on 20% for accuracy

**Prediction Phase (on-demand):**
1. Fetches unwatched content from Plex library (movies & TV only, filters music)
2. Extracts same features for each unwatched item
3. Predicts probability you'll finish each item (0-100%)
4. Returns top recommendations ranked by ML score

### Algorithm Details

**Model:** Random Forest Classifier
- **Trees:** 100 decision trees voting on predictions
- **Features:** genre (encoded), year, rating, runtime, is_recent, is_short, is_highly_rated
- **Target:** Binary classification (finished=1, abandoned=0)
- **Training:** Learns YOUR unique patterns, not generic ratings

**Example patterns discovered:**
- "User finishes 92% of SciFi movies under 140 minutes"
- "User abandons 98% of movies over 150 minutes"
- "User prefers ratings in 7.5-8.5 range"

**Performance:**
- Typical accuracy: 85-100% (depends on data consistency)
- Minimum data: 20 viewing events required
- Optimal data: 50+ events for reliable predictions

### Usage

**Auto-setup:**
```
# Automatic on first startup with Plex configured
✅ Imported 211 viewing events (total: 4858)
🤖 Training ML model...
✅ Model trained! Accuracy: 100.0%, Samples: 4858
```

**Get recommendations:**
```
> What should I watch tonight?
> Recommend unwatched SciFi movies
> Show me my best unwatched content
```

**Manual operations:**
```
> Show recommender stats
> Import Plex history
> Train recommender
```

**Model persists** between sessions and auto-updates with new viewing history on each startup.

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

### CLI/Web UI Commands

These commands work in both the CLI and Web UI interfaces:
```
:commands              List all available commands
:stop                  Stop current operation (Note: ingestion completes current batch before stopping)
:stats                 Show performance metrics
:tools                 List all available tools
:tool <tool>           Get the tool description
:model                 View the current active model
:model <model>         Use the model passed
:models                List available models
:multi on              Enable multi-agent mode
:multi off             Disable multi-agent mode
:multi status          Check multi-agent status
:a2a on                Enable agent-to-agent mode
:a2a off               Disable agent-to-agent mode
:a2a status            Check A2A system status
:env                   Show environment configuration
:clear history         Clear the chat history
```

**Note:** The `:stop` command will gracefully halt most operations, but media ingestion will complete the current batch before stopping to prevent database corruption.

### Example Workflows

**ML Recommendations:**
```
> What should I watch tonight?
> Recommend movies: Dune, Knives Out, The Northman
> Show my recommender stats
```

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

**5. Tool Control  (optional):**

### Overview

The `DISABLED_TOOLS` environment variable lets you disable specific tools or entire categories without modifying code. Disabled tools are hidden from the `:tools` list and return an error if called.

### Patterns

1. **Specific tool**: `DISABLED_TOOLS=delete_all_todo_items,terminate_process`
2. **Category-specific**: `DISABLED_TOOLS=todo:delete_all_todo_items,system:terminate_process`
3. **All in category**: `DISABLED_TOOLS=system:*,rag:*`

### Use Cases

**Disable destructive operations:**
```bash
DISABLED_TOOLS=delete_all_todo_items,terminate_process,delete_all_entries
```

**Disable slow operations:**
```bash
DISABLED_TOOLS=rag:plex_ingest_batch,rag:*
```

**Disable experimental tools:**
```bash
DISABLED_TOOLS=code:debug_fix,system:*
```

### Behavior

- Hidden from `:tools` list
- Returns error if called
- Use `:tools --all` to see disabled tools (marked)

New tools are automatically:
- Discovered by client (local access via stdio)
- Exposed by A2A server (if in A2A_EXPOSED_TOOLS or all exposed)
- Available to remote clients (via A2A protocol)

## Troubleshooting

**Stopping long-running operations:**
- ✅ **Safe**: Use `:stop` command - completes current batch, prevents corruption
- ⚠️ **Unsafe**: `Ctrl+C` force-exit during ingestion may corrupt the database
- Monitor progress with `:stats` or `:metrics`
- For stuck operations, try `:stop` first and wait for current batch to complete

**`:stop` command not immediately responding during ingestion:**
- This is expected behavior - ingestion must complete current batch
- Database integrity is protected by finishing atomic operations
- Operation will stop after current batch finishes

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
│       ├── server.py      # Plex MCP server
│       ├── ml_recommender.py  # ML recommendation engine
│       └── skills/
│           └── ml_recommendations.md  # ML skill documentation
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