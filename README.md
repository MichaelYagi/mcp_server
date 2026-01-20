# MCP Server & Client with Multi-Agent System and A2A Protocol

A Model Context Protocol (MCP) architecture for exposing Python-based tools to AI agents through a JSON-RPC interface, with multi-agent orchestration, Agent-to-Agent (A2A) protocol support for distributed tool execution, and LangSearch web search fallback.

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

Linux
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell
```powershell
.venv\Scripts\activate
.venv\Scripts\pip.exe install -r .\requirements.txt
```

**2. Configure environment (optional)**

Create `.env` file with any optional settings:
```bash
# A2A Protocol Configuration
A2A_ENDPOINT=http://localhost:8010  # A2A server endpoint (optional)

# LangSearch Web Search API
LANGSEARCH_TOKEN=your_langsearch_api_key  # Get from https://langsearch.com (optional)

# Weather API (optional)
WEATHER_TOKEN=<your_key>

# Plex Integration (optional)
PLEX_URL=http://<ip>:32400
PLEX_TOKEN=<your_token>
```

All settings are optional. The system works without a `.env` file.

**3. Download models**

```bash
ollama serve
ollama pull llama3.1:8b
ollama pull qwen2.5:14b  # Recommended for multi-agent
ollama pull bge-large
```

**4. Start the system**

**For A2A testing (distributed mode):**

Start the A2A server in one terminal:
```bash
python a2a_server.py
```

Start the client in another terminal:
```bash
python client.py
```

**For standalone mode (no A2A):**
```bash
python client.py
```

Access web UI at: `http://localhost:9000`

## Features

* **LangSearch Web Search**: Automatic web search fallback when no appropriate tools are found
* **A2A Protocol**: Agent-to-Agent communication for distributed tool execution
* **Multi-Agent Orchestration**: Automatic task decomposition with parallel execution
* **Bidirectional Architecture**: Server exposes tools, Client uses LLMs
* **RAG System**: Vector-based retrieval with semantic search
* **Plex Media Integration**: Automated subtitle and metadata ingestion
* **Real-Time Log Streaming**: WebSocket-based live log viewer
* **System Monitor**: Real-time CPU, GPU, and memory monitoring
* **Web UI**: Responsive interface with chat, logs, and system monitor

## LangSearch Web Search Integration

### Intelligent Fallback Chain

The system uses a 3-tier fallback approach for answering queries:

```
User Query
    ↓
1. Check for appropriate tools
    ↓
   Tools Found? → YES → Use filtered tools
    ↓ NO
2. Try LangSearch web search
    ↓
   Search Success? → YES → Augment context with results
    ↓ NO (API error/limit/missing key)
3. Fall back to base LLM knowledge
```

### How It Works

**Scenario 1: Tool-based query**
```
> What's the weather in Tokyo?
```
- Weather intent detected → Uses `get_weather_tool`
- LangSearch is NOT triggered

**Scenario 2: General knowledge query (LangSearch available)**
```
> Who won the 2024 NBA championship?
```
- No specific tool matches
- LangSearch performs web search
- Results added to context
- LLM answers using search results

**Scenario 3: LangSearch unavailable/fails**
```
> What is quantum computing?
```
- No specific tool matches
- LangSearch not configured or fails
- Falls back to LLM's training knowledge

### Configuration

Get a LangSearch API key from: https://langsearch.com

Add to `.env`:
```bash
LANGSEARCH_TOKEN=your_api_key_here
```

### Monitoring LangSearch Activity

Watch logs for LangSearch usage:
```
🎯 No tools needed - trying LangSearch web search
🔍 Performing LangSearch web search: 'Who won the 2024 NBA championship?'
✅ LangSearch returned results (112961 chars)
✅ LangSearch search successful - augmenting context
```

Or graceful fallback:
```
🎯 No tools needed - trying LangSearch web search
❌ LangSearch: Invalid API key
⚠️ LangSearch failed: Invalid LangSearch API key - using base LLM
```

### Error Handling

LangSearch errors are handled gracefully:
- **401 Invalid API key** → Falls back to base LLM
- **429 Rate limit exceeded** → Falls back to base LLM
- **Network timeout** → Falls back to base LLM
- **Token not configured** → Falls back to base LLM

The system never blocks or fails due to LangSearch issues.

## A2A (Agent-to-Agent) Protocol

### Architecture

The A2A protocol enables distributed agent communication where one agent can discover and call tools from another agent over HTTP:

```
┌─────────────────┐         A2A Protocol         ┌─────────────────┐
│   MCP Client    │◄──────────────────────────►  │   A2A Server    │
│  (Agent Host)   │    JSON-RPC over HTTP        │  (Tool Provider)│
└─────────────────┘                              └─────────────────┘
        │                                                  │
        │  - Discovers remote tools                       │  - Exposes 48+ MCP tools
        │  - Registers as local tools                     │  - Handles tool execution
        │  - Calls via a2a_ prefix                        │  - Returns results
        └────────────────────────────────────────────────┘
```

### Starting the A2A Server

The A2A server exposes all MCP tools over the A2A protocol:

```bash
python a2a_server.py
```

**Server details:**
- **Listen address**: `http://localhost:8010`
- **Agent card**: `http://localhost:8010/.well-known/agent-card.json`
- **RPC endpoint**: `http://localhost:8010/a2a`
- **Exposed tools**: 48+ tools including weather, todo, RAG, Plex, system info, and more

**Verify server is running:**
```bash
curl http://localhost:8010/.well-known/agent-card.json
```

You should see a JSON response with agent information and available tools.

### Starting the MCP Client with A2A

**With A2A server running:**
```bash
# In .env file
A2A_ENDPOINT=http://localhost:8010

# Start client
python client.py
```

The client will:
1. Discover tools from the A2A server
2. Register remote tools with `a2a_` prefix
3. Make them available alongside local tools

**Without A2A server (standalone mode):**
```bash
# Remove or comment out A2A_ENDPOINT in .env
python client.py
```

The client will continue normally with local tools only.

### Using A2A Tools

#### Method 1: Automatic A2A Tools (Recommended)

When the A2A server is running, remote tools are automatically registered and used transparently:

```
> what's the weather in Vancouver?
```

The agent will automatically select and use `a2a_get_weather_tool` from the remote server.

**All A2A tools available** (when server is running):
```
a2a_add_entry                    a2a_search_entries
a2a_search_by_tag                a2a_search_semantic
a2a_get_entry                    a2a_delete_entry
a2a_update_entry                 a2a_list_entries
a2a_get_hardware_specs_tool      a2a_get_system_info
a2a_list_system_processes        a2a_terminate_process
a2a_add_todo_item                a2a_list_todo_items
a2a_search_todo_items            a2a_update_todo_item
a2a_delete_todo_item             a2a_delete_all_todo_items
a2a_summarize_code_file          a2a_search_code_in_directory
a2a_scan_code_directory          a2a_summarize_code
a2a_debug_fix                    a2a_get_location_tool
a2a_get_time_tool                a2a_get_weather_tool
a2a_rag_add_tool                 a2a_rag_search_tool
a2a_rag_diagnose_tool            a2a_rag_status_tool
a2a_plex_ingest_batch            a2a_semantic_media_search_text
a2a_scene_locator_tool           a2a_find_scene_by_title
a2a_plex_find_unprocessed        a2a_plex_ingest_items
a2a_plex_ingest_single           a2a_plex_get_stats
... and more
```

#### Method 2: Explicit A2A Messaging

Force the use of A2A messaging tools for explicit remote calls:

```
> using a2a tools, what's the weather in Surrey BC?
> using a2a, add "finish documentation" to my todos
```

This uses the `send_a2a` messaging tool to explicitly call remote tools.

#### Method 3: Discover Remote Tools

```
> discover a2a tools
```

Returns a complete list of all tools exposed by the A2A server with their descriptions.

### Testing A2A Integration

**Complete test workflow:**

1. **Start the A2A server** (Terminal 1):
   ```bash
   python a2a_server.py
   ```
   
   You should see:
   ```
   🌐 A2A Server listening on http://0.0.0.0:8010
   Agent card available at: http://localhost:8010/.well-known/agent-card.json
   ```

2. **Start the client** (Terminal 2):
   ```bash
   python client.py
   ```
   
   You should see:
   ```
   🌐 Attempting A2A connection to http://localhost:8010
   🔌 Registered A2A tool: a2a_add_entry
   🔌 Registered A2A tool: a2a_search_entries
   ... (48+ tools registered)
   🔌 A2A integration complete. Total tools: 98
   ```

3. **Verify A2A tools are available**:
   ```
   > :tools
   ```
   
   You should see both local and `a2a_` prefixed tools.

4. **Test automatic remote tool execution**:
   ```
   > what's the weather in London?
   ```
   
   The agent uses `a2a_get_weather_tool` automatically.

5. **Test todo management via A2A**:
   ```
   > add "test A2A integration" to my todos
   > list my todos
   > mark the first todo as complete
   ```

6. **Test Plex search via A2A**:
   ```
   > search my plex library for action movies
   > find scenes with explosions in my plex library
   ```

7. **Test explicit A2A messaging**:
   ```
   > using a2a, get the weather in Tokyo
   > discover a2a tools
   ```

8. **Test graceful degradation**:
   - Stop the A2A server (Ctrl+C in Terminal 1)
   - Try a query in the client
   - Client should continue with local tools only

### A2A vs Local Tools

**When A2A server is running:**
- Client has ~98 tools (48 local + 48 remote via A2A)
- Remote tools are called over HTTP
- Slightly slower due to network latency
- Enables distributed architectures

**When A2A server is stopped:**
- Client has ~50 local tools
- All execution is local
- Faster response times
- Standalone operation

**Best practice:**
- Use A2A when you need distributed tool execution
- Use standalone when all tools are local
- The system automatically handles both modes

## Multi-Agent System

### Agents

* **Orchestrator** - Plans task decomposition and coordinates execution
* **Researcher** - Gathers information using RAG, web search, and Plex media
* **Coder** - Generates code with best practices
* **Analyst** - Analyzes data and identifies patterns
* **Writer** - Creates structured content
* **Planner** - Manages tasks and creates roadmaps

### Automatic Mode Selection

**Multi-Agent triggers:**
* Sequential indicators: "then", "after that", "and then"
* Multi-step patterns: "research AND analyze", "find AND compare"
* Complex queries (30+ words)

**Single-Agent triggers:**
* Simple questions
* Direct tool calls
* Quick lookups

## Usage

### Web UI

* **Port 8765**: WebSocket chat
* **Port 8766**: WebSocket logs
* **Port 9000**: HTTP server
* **Port 8010**: A2A server (when running)

Features:
* Multi-agent toggle switch in header
* Model switcher
* Real-time logs with filtering
* System monitor
* Performance dashboard

### CLI Commands

**General:**
```
:commands       List available commands
:tools          List MCP tools (includes A2A tools if server running)
:tool <name>    Tool description
:models         List available models
:model <name>   Switch model
:clear history  Clear conversation
:multi on       Enable multi-agent
:multi off      Disable multi-agent
:multi status   Check multi-agent status
```

**A2A Commands:**
```
:a2a on         Enable A2A mode
:a2a off        Disable A2A mode
:a2a status     Check A2A system status
```

### Example Workflows

**General knowledge with LangSearch:**
```
> Who won the 2024 NBA championship?
> What are the latest developments in AI?
> What's happening in the tech industry today?
```

**Weather queries via A2A:**
```
> what's the weather in Vancouver?
> compare weather in London and Paris
```

**Todo management via A2A:**
```
> add "deploy new feature" to my todos
> list all incomplete todos
> mark todo 3 as complete
```

**Plex media search via A2A:**
```
> search my plex library for sci-fi movies
> find scenes with car chases
> find the scene in "The Matrix" where Neo dodges bullets
```

**Knowledge base via A2A:**
```
> add a note about Python decorators
> search my notes for information about decorators
> what do I know about design patterns?
```

**System information via A2A:**
```
> what are my system specs?
> show me running processes
> what's my current location?
```

### Multi-Agent Examples

**Research + Analysis + Writing:**
```
Research the top 5 Python frameworks, analyze their performance, and create a comparison
```

**Code + Documentation:**
```
Write a Fibonacci function, analyze its complexity, and document it
```

**Data + Planning:**
```
Find Docker learning resources and create a 30-day study plan
```

## Network Access

To access from other devices on your network:

1. Find your IP:
```bash
hostname -I | awk '{print $1}'  # Linux/WSL
ipconfig                         # Windows
```

2. Access from other devices:
```
http://[your-ip]:9000/index.html
```

3. Configure firewall (Windows with WSL2):
```powershell
New-NetFirewallRule -DisplayName "MCP WebSocket Chat" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "MCP WebSocket Logs" -Direction Inbound -LocalPort 8766 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "MCP HTTP Server" -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "A2A Server" -Direction Inbound -LocalPort 8010 -Protocol TCP -Action Allow
```

Linux:
```bash
sudo ufw allow 8765/tcp
sudo ufw allow 8766/tcp
sudo ufw allow 9000/tcp
sudo ufw allow 8010/tcp
```

## Troubleshooting

**LangSearch not working:**
* Check `LANGSEARCH_TOKEN` is set in `.env`
* Verify API key is valid: Test at https://langsearch.com
* Check logs for LangSearch activity
* Ensure query doesn't match specific tool intents (LangSearch only triggers when no tools match)

**LangSearch rate limits:**
* System automatically falls back to base LLM
* Check logs for "429 Rate limit exceeded"
* Wait for rate limit reset or upgrade plan

**A2A server not connecting:**
* Verify A2A server is running: `curl http://localhost:8010/.well-known/agent-card.json`
* Check `A2A_ENDPOINT` in `.env` is set to `http://localhost:8010`
* Check firewall rules allow port 8010
* Review client startup logs for A2A registration messages

**A2A tools not appearing:**
* Run `:tools` to verify tool list
* Run `:a2a status` to check A2A system status
* Check client logs for "🔌 Registered A2A tool" messages
* Verify A2A server shows "Agent card available" on startup

**A2A calls failing:**
* Check A2A server is still running
* Verify network connectivity: `curl http://localhost:8010/.well-known/agent-card.json`
* Review server logs for error messages
* Try restarting both server and client

**Multi-agent not activating:**
* Run `:multi status` to check if enabled
* Run `:multi on` to enable

**Multi-agent poor quality:**
* Switch to better model: `:model qwen2.5:14b`
* Be more specific in queries

**Web UI won't load:**
* Check all ports are available (8765, 8766, 9000, 8010)
* Verify firewall rules
* Try `http://localhost:9000/index.html` directly

**Chat not responding:**
* Check Ollama is running: `ollama list`
* Try switching models: `:model llama3.1:8b`

## Directory Structure

```
mcp_a2a/
├── a2a_server.py          # A2A protocol server (exposes tools)
├── server.py              # MCP server (registers and exposes tools)
├── client.py              # AI Agent with multi-agent orchestration
├── index.html             # Web UI
├── dashboard.html         # Performance metrics
├── client/
│   ├── a2a_client.py      # A2A client implementation
│   ├── a2a_tools.py       # A2A tool registration
│   ├── langsearch_client.py  # LangSearch web search client
│   ├── multi_agent.py     # Multi-agent orchestration
│   ├── langgraph.py       # Single-agent execution with LangSearch
│   ├── commands.py        # CLI commands
│   └── websocket.py       # WebSocket server
└── tools/                 # Python tools
    ├── knowledge_base/
    ├── location/
    ├── system_monitor/
    └── plex/
```

## Extending

### Adding Tools (Available via A2A)

1. Add Python script to `tools/<domain>/`
2. Register in `server.py` with `@mcp.tool()`
3. Tool automatically exposed via A2A server
4. Tool automatically discovered by A2A clients

Example:
```python
# In server.py
@mcp.tool()
def custom_tool(param: str) -> str:
    """My custom tool that does something."""
    return f"Result: {param}"
```

When A2A server starts, this tool is automatically:
- Exposed at `/a2a` endpoint
- Listed in agent card at `/.well-known/agent-card.json`
- Discoverable by A2A clients
- Available as `a2a_custom_tool` in connected clients

### Customizing Agent Flows

Edit `client/multi_agent.py`:

```python
class AgentRole(Enum):
    CUSTOM_AGENT = "custom_agent"

# Add system prompt
custom_prompt = """You are a Custom Agent..."""

# Map tools to agent
role_tools = {
    AgentRole.CUSTOM_AGENT: ["tool1", "tool2"],
}
```

### Deploying A2A Server on Remote Machine

1. **On the remote server:**
   ```bash
   # Configure to listen on all interfaces
   python a2a_server.py
   ```

2. **On the client:**
   ```bash
   # Update .env
   A2A_ENDPOINT=http://remote-server-ip:8010
   
   # Start client
   python client.py
   ```

3. **Configure firewall on server:**
   ```bash
   # Allow incoming connections on port 8010
   sudo ufw allow 8010/tcp
   ```

## Browser Compatibility

* Chrome 90+
* Firefox 88+
* Safari 14+
* Edge 90+
* Mobile browsers with WebSocket support

## API Integration Details

### LangSearch API

**Endpoint**: `https://api.langsearch.com/v1/web-search`

**Authentication**: Bearer token in `Authorization` header

**Request format**:
```json
{
  "query": "user's search query"
}
```

**Response handling**:
- Success: Search results extracted and added to LLM context
- 401: Invalid API key → Graceful fallback
- 429: Rate limit → Graceful fallback
- Network errors → Graceful fallback

### A2A Protocol Specification

**Agent Card** (`/.well-known/agent-card.json`):
```json
{
  "name": "Local A2A Agent",
  "description": "Your MCP tools exposed over A2A protocol",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false
  },
  "endpoints": {
    "a2a": "http://localhost:8010/a2a"
  }
}
```

**RPC Methods**:
- `a2a.discover` - Returns list of available tools with schemas
- `a2a.call` - Executes a tool with given arguments

**Example RPC Call**:
```json
{
  "jsonrpc": "2.0",
  "id": "uuid",
  "method": "a2a.call",
  "params": {
    "tool": "get_weather_tool",
    "arguments": {
      "city": "London"
    }
  }
}
```

## License

MIT License - See LICENSE file for details