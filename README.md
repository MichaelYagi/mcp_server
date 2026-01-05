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

```text
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
* [Weather API Key](https://www.weatherapi.com/) (Free)
* System requirements for `qwen2.5:3b`:

| Category            | Minimum                | Recommended           |
|---------------------|------------------------|-----------------------|
| **GPU VRAM (FP16)** | 6 GB                   | 20.6 GB               |
| **GPU VRAM (INT8)** | 4.27 GB                | 12.17 GB              |
| **System RAM**      | 16 GB                  | 32 GB                 |
| **Storage**         | ~50 GB SSD             | 50 GB+ SSD            |
| **GPU Type**        | 6 GB+ NVIDIA/AMD       | 24 GB NVIDIA          |
| **Context Length**  | 1k–4k tokens           | Full 32,768 tokens    |

### Installation

**1. Create `.env` file:**

```
WEATHER_API_KEY=<Weather API Key>
OLLAMA_MODEL=qwen2.5:3b
```

**2. Install dependencies:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Run Ollama and download model:**

```bash
ollama serve  # Run in separate terminal
ollama pull qwen2.5:3b  # 1.9GB download
```

**4. Start the client:**

```bash
python client.py
```

### Interface Modes

Choose your interaction mode when starting:

* **CLI Mode**: Terminal-based with full logs, ideal for debugging
* **Browser Mode**: WebSocket server with chat UI and persistent history

```
Choose interface:
1) Browser
2) CLI
```

Both modes use the same backend and tools.

### Configuration

**Conversation History:**  
Adjust in `client.py` (default: 20 messages):

```python
MAX_MESSAGE_HISTORY = 20
```

**Alternative Models:**  
Browse models at [ollama.com/library](https://ollama.com/library). Use models with advertised tool support:

```bash
ollama pull <model>
```

Update `.env`: `OLLAMA_MODEL=<model name>`

### Claude Desktop Integration

Edit `%APPDATA%\Roaming\Claude\claude_desktop_config.json` with **absolute paths**:

```json
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