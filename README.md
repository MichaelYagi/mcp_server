# MCP and A2A Server & Client with Multi-Agent System

A Model Context Protocol (MCP) architecture for exposing Python‑based tools to AI agents through a JSON‑RPC interface, with multi‑agent orchestration and an A2A (Agent‑to‑Agent) bridge for remote tool execution and cross‑agent coordination.

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

Create `.env` file with any optional settings:

```bash
WEATHER_API_KEY=<your_key>        # For weather tool
PLEX_BASE_URL=http://<ip>:32400   # For Plex integration
PLEX_TOKEN=<your_token>           # For Plex integration
```

All settings are optional. The system works without a `.env` file.

**3. Download models**

```bash
ollama serve
ollama pull llama3.1:8b
ollama pull qwen2.5:14b  # Recommended for multi-agent
ollama pull bge-large
```

**4. Start the client**

```bash
python client.py
```

Access web UI at: `http://localhost:9000`

## Features

* Multi-Agent Orchestration: Automatic task decomposition with parallel execution  
* Bidirectional Architecture: Server exposes tools, Client uses LLMs  
* RAG System: Vector-based retrieval with semantic search  
* Plex Media Integration: Automated subtitle and metadata ingestion  
* Real-Time Log Streaming: WebSocket-based live log viewer  
* System Monitor: Real-time CPU, GPU, and memory monitoring  
* Web UI: Responsive interface with chat, logs, and system monitor  

## Multi-Agent System

### Agents

* Orchestrator – Plans task decomposition and coordinates execution  
* Researcher – Gathers information using RAG, web search, and Plex media  
* Coder – Generates code with best practices  
* Analyst – Analyzes data and identifies patterns  
* Writer – Creates structured content  
* Planner – Manages tasks and creates roadmaps  

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

* Port 8765: WebSocket chat  
* Port 8766: WebSocket logs  
* Port 9000: HTTP server  

Features:

* Multi-agent toggle switch in header  
* Model switcher  
* Real-time logs with filtering  
* System monitor  
* Performance dashboard  

### CLI Commands

```
:commands       List available commands
:tools          List MCP tools
:tool <name>    Tool description
:models         List available models
:model <name>   Switch model
:clear history  Clear conversation
:multi on       Enable multi-agent
:multi off      Disable multi-agent
:multi status   Check status
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
```

Linux:

```bash
sudo ufw allow 8765/tcp
sudo ufw allow 8766/tcp
sudo ufw allow 9000/tcp
```

## Troubleshooting

**Multi-agent not activating:**

* Run `:multi status` to check if enabled  
* Run `:multi on` to enable  

**Multi-agent poor quality:**

* Switch to better model: `:model qwen2.5:14b`  
* Be more specific in queries  

**Web UI won't load:**

* Check all three ports are available  
* Verify firewall rules  
* Try `http://localhost:9000/index.html` directly  

**Chat not responding:**

* Check Ollama is running: `ollama list`  
* Try switching models: `:model llama3.1:8b`  

## Directory Structure

```
mcp_a2a/
├── server.py              # Registers and exposes tools
├── client.py              # AI Agent with multi-agent orchestration
├── index.html             # Web UI
├── dashboard.html         # Performance metrics
├── client/
│   ├── multi_agent.py     # Multi-agent orchestration
│   ├── langgraph.py       # Single-agent execution
│   ├── commands.py        # CLI commands
│   └── websocket.py       # WebSocket server
└── tools/                 # Python tools
    ├── knowledge_base/
    ├── location/
    ├── system_monitor/
    └── plex/
```

## Extending

### Adding Tools

1. Add Python script to `tools/<domain>/`  
2. Register in `server.py` with `@mcp.tool()`  

### Customizing Agent Flows

Edit `client/multi_agent.py`:

```python
class AgentRole(Enum):
    CUSTOM_AGENT = "custom_agent"

custom_prompt = """You are a Custom Agent..."""

role_tools = {
    AgentRole.CUSTOM_AGENT: ["tool1", "tool2"],
}
```

## Browser Compatibility

* Chrome 90+  
* Firefox 88+  
* Safari 14+  
* Edge 90+  
* Mobile browsers with WebSocket support  

---

# A2A (Agent-to-Agent) Bridge

The A2A bridge allows **remote agents** to call your MCP tools over HTTP using JSON-RPC 2.0.

This is useful for:

* Multi-machine orchestration  
* Remote tool execution  
* Connecting multiple MCP servers  
* Allowing external agents to call your tools  

## A2A Server

Start the A2A server:

```bash
python a2a_server.py
```

It exposes:

```
POST /a2a
```

### Discover tools

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "a2a.discover",
  "params": {}
}
```

### Call a tool

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "a2a.call",
  "params": {
    "tool": "add_entry",
    "arguments": {
      "text": "hello world"
    }
  }
}
```

## A2A Client Integration

Enable A2A:

```bash
export A2A_ENDPOINT="http://localhost:8010"
```

Then run:

```bash
python client.py
```

If reachable:

```
🌐 Loading A2A tools from http://localhost:8010
🔌 Registered A2A tool: a2a_add_entry
```

If unreachable:

```
⚠️ A2A connection failed → Skipping A2A integration
```

## A2A Troubleshooting

**No response from A2A server:**

```bash
curl -v -X POST http://localhost:8010/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":"1","method":"a2a.discover","params":{}}'
```

**500 errors:**

* Check MCP server logs  
* Ensure tools are registered and not blocking  

**A2A tools not visible:**

* Confirm `A2A_ENDPOINT` is set  
* Look for A2A registration logs  


