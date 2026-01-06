# MCP Server & Client

A modular **Model Context Protocol (MCP)** architecture for exposing Python-based tools to AI agents through a unified JSON-RPC interface.

The server is plug-and-play—add new capabilities by simply dropping modules into the directory structure.

---

## Key Features

* **Bidirectional Architecture**: Server exposes tools, Client acts as the AI brain using LLMs
* **Multi-Domain Support**: Organize tools into logical categories (`knowledge`, `system`, `math`)
* **Schema-Driven Validation**: JSON schemas ensure correctly formatted inputs
* **Versioned Storage**: File-backed persistence with automatic snapshotting
* **Offline Semantic Search**: Pure-Python TF-IDF implementation
* **Windows Optimized**: Handles encoding and stdio pipe challenges

---

## Architecture

* **Client (client.py)**: AI agent that connects to the server and invokes tools
* **Server (server.py)**: Hub that registers tools and provides JSON-RPC interface
* **Tools Directory**: Functional Python logic for each domain with local persistence
* **Schemas Directory**: Input contracts between AI and code

---

## Directory Structure

```
mcp-server/
│
├── server.py                 # Core hub; registers and exposes tools
├── client.py                 # AI Agent (powered by Qwen)
│
├── tools/
│   ├── knowledge_base/       # Structured data & search
│   │   └── kb_add.py
│   ├── location/             # External API integration
│   │   └── get_weather.py
│   └── more_tools/
│
├── schemas/                  # JSON schemas for tool inputs
│   ├── knowledge_base/       
│   │   └── kb_add.json
│   ├── location/             
│   │   └── get_weather.json
│   └── more_schemas/
```

---

## Setup

### Prerequisites

* Python 3.10+
* llama3.1:8b - Instructions below

---

**System requirements for llama3.1:8b**

**Minimum (Slow but Works)**
* RAM: 8GB total system RAM 
* Model will use: ~5-6GB RAM 
* Speed: Slow (2-5 tokens/sec)

**Optimal (Smooth)**
* RAM: 32GB+
* GPU: Any modern GPU with 6GB+ VRAM
* Speed: 30-100+ tokens/sec

---

### Installation

**1. Install dependencies**

```
curl -fsSL https://ollama.com/install.sh | sh
python -m venv .venv
source .venv/bin/activate (Linux)
.\.venv\bin\activate (Windows)
pip install -r requirements.txt (Linux)
.\.venv\Scripts\pip.exe install -r .\requirements.txt (Windows)
```

---

**Optional Environment Configuration**

* Create `.env` file if needed.

Weather API

Get a free key [Weather API Key](https://www.weatherapi.com/)
```
WEATHER_API_KEY=<Weather API Key>
```

Plex Integration
```
PLEX_BASE_URL=http://<ip>:32400
PLEX_TOKEN=<plex_token>
```

Conversation History Size
```
MAX_MESSAGE_HISTORY = 30
```
(Default: 20 messages)

---

**2. Run Ollama server and download model:**

```
ollama serve
ollama pull llama3.1:8b
```

**3. Start the client:**

```
python client.py (Linux)
.\.venv\Scripts\python.exe client.py (Windows)
```

### Interface

You can use a CLI terminal-based with full logs, ideal for debugging or visit the index.html page with chat UI and persistent history.

### Configuration

**Conversation History**

Make changes to the message history size. Make a `.env` file if not already there and make an entry `MAX_MESSAGE_HISTORY=<numebr>`. The default is 20.

**Alternative Models:**

Browse models at [ollama.com/library](https://ollama.com/library). Use models with advertised tool support:

```
ollama pull <model>
```

⚠️ Note: Some models may cause recursive loops or degraded tool behavior.

### Claude Desktop Integration

Edit `%APPDATA%\Roaming\Claude\claude_desktop_config.json` with **absolute paths**:

```
{ 
    "mcpServers": { 
        "mcp-server": { 
            "command": "C:\\<base_path>\\mcp_server\\.venv\\Scripts\\python.exe",
            "args": ["C:\\<base_path>\\mcp_server\\server.py"]
        } 
    } 
}
```

Run: `python server.py`

---

## Extending the Server

Three steps to add new tools:

1. **Logic**: Add Python script to `tools/<new_domain>/`
2. **Schema**: Define inputs in `schemas/<new_domain>/<tool_name>.json`
3. **Register**: Import in `server.py` and wrap with `@mcp.tool()`