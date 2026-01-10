# MCP Server & Client

A modular **Model Context Protocol (MCP)** architecture for exposing Python-based tools to AI agents through a unified JSON-RPC interface.

The server is plug-and-play—add new capabilities by simply dropping modules into the directory structure.

This started as a tool for me to learn about implementing MCP and its core components.

---

## Key Features

* **Bidirectional Architecture**: Server exposes tools, Client acts as the AI brain using LLMs
* **Multi-Domain Support**: Organize tools into logical categories (`knowledge`, `system`, `math`)
* **Schema-Driven Validation**: JSON schemas ensure correctly formatted inputs
* **Versioned Storage**: File-backed persistence with automatic snapshotting
* **Offline Semantic Search**: Pure-Python TF-IDF implementation
* **RAG System**: Vector-based retrieval with OllamaEmbeddings (bge-large) for semantic search over ingested content
* **Plex Media Integration**: Automated subtitle and metadata ingestion with batch processing
* **Real-Time Log Streaming**: WebSocket-based live log viewer with filtering (NEW!)
* **Mobile-Friendly UI**: Fully responsive interface for phones, tablets, and desktop (NEW!)
* **Windows Optimized**: Handles encoding and stdio pipe challenges

---

## Architecture

* **Client (client.py)**: AI agent that connects to the server and invokes tools
* **Server (server.py)**: Hub that registers tools and provides JSON-RPC interface
* **Web UI (index.html)**: Modern chat interface with real-time log streaming
* **Tools Directory**: Functional Python logic for each domain with local persistence
* **Schemas Directory**: Input contracts (prompts) between AI and code

---

## Directory Structure

```
mcp-server/
│
├── server.py                 # Registers and exposes tools and prompts (schemas)
├── client.py                 # AI Agent, interprets requests, and decides when to call tools
├── index.html                # Web UI with chat and real-time log streaming
│
├── tools/                    # Python tools - defines tools
│   ├── knowledge_base/       # Structured data & search
│   │   └── kb_add.py
│   ├── location/             # External API integration
│   │   └── get_weather.py
│   └── more_tools/
│
├── schemas/                  # JSON schemas for tool inputs - defines prompts
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
* bge-large - Instructions below

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

From `mcp_server` root:

```
curl -fsSL https://ollama.com/install.sh | sh
python -m venv .venv
```

WSL
```
source .venv-wsl/bin/activate
pip install -r requirements.txt
```

Linux
```
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell
```
.venv\Scripts\activate
.venv\Scripts\pip.exe install -r .\requirements.txt
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
MAX_MESSAGE_HISTORY=30
```
(Default: 20 messages)

---

**2. Run Ollama server and download models:**

```
ollama serve
ollama pull llama3.1:8b
ollama pull bge-large
```

**3. Start the client:**

Linux
```
python client.py
```

Windows PowerShell
```
.venv\Scripts\python.exe client.py
```

The client will start three services:
- **Port 8765**: WebSocket for chat
- **Port 8766**: WebSocket for real-time logs
- **Port 9000**: HTTP server for web UI

Your browser will automatically open to `http://localhost:9000/index.html`

---

### Interface Options

**Web UI (Recommended)**

Modern chat interface with advanced features:

* **Chat Window** - Conversational interface with message history
* **Real-Time Log Viewer** - Live streaming logs with filtering
  - Toggle with "📊 Show Logs" button
  - Filter by level: DEBUG, INFO, WARNING, ERROR
  - Auto-scroll or manual control
  - Clear logs on demand
* **Model Switcher** - Change Ollama models on the fly
* **Mobile-Friendly** - Responsive design for phones and tablets
  - Desktop: Side-by-side chat and logs
  - Mobile: Full-screen log overlay with dedicated close button
* **Persistent History** - Chat history saved in browser localStorage

Access at: `http://localhost:9000/index.html`

**CLI Terminal (Advanced)**

Full logging output in terminal, ideal for debugging:
- All log messages printed to console
- Tool call inspection
- Detailed error traces
- Direct input/output

Both interfaces can be used simultaneously and share the same conversation state!

---

### Web UI Features

**Log Panel**
- Real-time streaming via WebSocket (no polling!)
- Color-coded log levels (INFO=blue, WARNING=yellow, ERROR=red, DEBUG=green)
- Filter logs by clicking level badges
- Auto-scroll toggle to follow new logs
- Keeps last 500 logs for performance
- Auto-reconnect if connection drops

**Mobile Optimizations**
- Touch-friendly 44px minimum button targets
- Full-screen log panel on phones
- No iOS zoom on input focus (16px font size)
- Optimized layout for tablets and small screens
- Swipe-friendly scrolling

**Responsive Breakpoints**
- Desktop (>1024px): Side panel at 500px width
- Tablet (768-1024px): Side panel at 400px width
- Mobile (<768px): Full-screen log overlay
- Small phones (<480px): Compact optimized layout

---

### Configuration

**Conversation History**

Make changes to the message history size. Make a `.env` file if not already there and make an entry `MAX_MESSAGE_HISTORY=<number>`. The default is 20.

**Alternative Models:**

Browse models at [ollama.com/library](https://ollama.com/library). Use models with advertised tool support:

```
ollama pull <model>
```

To switch models in the web UI, use the dropdown in the header. In CLI, type:
```
:model <model_name>
```

⚠️ Note: Some models may cause recursive loops or degraded tool behavior.

**Log Levels**

Adjust what logs are streamed to the web UI in `client.py`:

```python
ws_log_handler.setLevel(logging.INFO)  # Change to DEBUG, WARNING, ERROR
```

---

### Network Access

**Local Network Access**

To access the Web UI from other devices on your network (phones, tablets, other computers):

1. Find your server's local IP address:
   ```bash
   # Linux/Mac/WSL
   hostname -I | awk '{print $1}'
   
   # Windows PowerShell
   ipconfig
   # Look for "IPv4 Address" under your active network adapter
   ```

2. Access from other devices using the IP address:
   ```
   http://[your-ip]:9000/index.html
   
   Example: http://192.168.0.185:9000/index.html
   ```

**Firewall Configuration**

The Web UI requires three ports to be accessible:
- **Port 8765** - Chat WebSocket
- **Port 8766** - Log streaming WebSocket  
- **Port 9000** - HTTP server

**Windows with WSL2 (Most Common Setup):**

WSL2 uses a virtual network adapter that Windows Firewall blocks by default. You need to add firewall rules:

```powershell
# Open PowerShell as Administrator and run:

New-NetFirewallRule -DisplayName "MCP WebSocket Chat" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "MCP WebSocket Logs" -Direction Inbound -LocalPort 8766 -Protocol TCP -Action Allow

New-NetFirewallRule -DisplayName "MCP HTTP Server" -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow
```

**If firewall rules don't work on WSL2**, set up port forwarding:

```powershell
# In PowerShell as Administrator:
# First, get your WSL IP address (run 'hostname -I' in WSL)

netsh interface portproxy add v4tov4 listenport=8765 listenaddress=0.0.0.0 connectport=8765 connectaddress=[WSL_IP]

netsh interface portproxy add v4tov4 listenport=8766 listenaddress=0.0.0.0 connectport=8766 connectaddress=[WSL_IP]

netsh interface portproxy add v4tov4 listenport=9000 listenaddress=0.0.0.0 connectport=9000 connectaddress=[WSL_IP]

# To verify:
netsh interface portproxy show all
```

**Linux (using ufw):**

```bash
sudo ufw allow 8765/tcp
sudo ufw allow 8766/tcp
sudo ufw allow 9000/tcp
```

**Linux (using firewalld):**

```bash
sudo firewall-cmd --permanent --add-port=8765/tcp
sudo firewall-cmd --permanent --add-port=8766/tcp
sudo firewall-cmd --permanent --add-port=9000/tcp
sudo firewall-cmd --reload
```

**Verification:**

After configuring the firewall, verify the ports are accessible:

```bash
# On the server, check ports are listening:
netstat -an | grep -E '8765|8766|9000'

# Should show:
# tcp    0    0 0.0.0.0:8765    0.0.0.0:*    LISTEN
# tcp    0    0 0.0.0.0:8766    0.0.0.0:*    LISTEN
# tcp    0    0 0.0.0.0:9000    0.0.0.0:*    LISTEN
```

From another device on your network:
1. Open browser to `http://[server-ip]:9000/index.html`
2. Check browser console (F12) for connection messages
3. Verify "Connected" status in the Web UI
4. Click "📊 Show Logs" and verify green "Live" indicator appears

---

### Claude Desktop Integration

Edit `%APPDATA%\Roaming\Claude\claude_desktop_config.json` with **absolute paths**:

```json
{ 
    "mcpServers": { 
        "mcp-server": { 
            "command": "C:\\\\mcp_server\\.venv\\Scripts\\python.exe",
            "args": ["C:\\\\mcp_server\\server.py"]
        } 
    } 
}
```

Run:

```
.venv\Scripts\activate
.venv\Scripts\python.exe server.py
```

---

## CLI Commands

When using the terminal interface, type these commands:

* `:commands` - List all available commands
* `:tools` - List all available MCP tools
* `:tool <name>` - Get description of a specific tool
* `:models` - List available Ollama models
* `:model` - Show current model
* `:model <name>` - Switch to a different model
* `:clear history` - Clear conversation history

---

## Extending the Server

Three steps to add new tools:

1. **Logic**: Add Python script to `tools/<new_domain>/`
2. **Schema**: Define inputs in `schemas/<new_domain>/<tool_name>.json`
3. **Register**: Import in `server.py` and wrap with `@mcp.tool()`

---

## WebSocket API

The client exposes two WebSocket endpoints:

**Chat WebSocket (Port 8765)**
```javascript
ws://localhost:8765
```

Message types:
- `user` - Send user message
- `assistant_message` - Receive AI response
- `history_request` - Request conversation history
- `history_sync` - Receive conversation history
- `switch_model` - Request model change
- `model_switched` - Confirm model change
- `models_list` - Receive available models

**Log WebSocket (Port 8766)**
```javascript
ws://localhost:8766
```

Message format:
```json
{
    "type": "log",
    "timestamp": "2024-01-09T10:30:45.123456",
    "level": "INFO",
    "name": "mcp_client",
    "message": "🧠 Calling LLM with 5 messages"
}
```

---

## Troubleshooting

**Web UI won't load**
- Check that all three ports (8765, 8766, 9000) are available
- Look for "HTTP server running" message in terminal
- Try accessing `http://localhost:9000/index.html` directly

**Can't connect from another device on the network**
- Verify firewall rules are configured (see Network Access section)
- Check ports are listening on `0.0.0.0` not `127.0.0.1`:
  ```bash
  netstat -an | grep -E '8765|8766|9000'
  ```
- For WSL2, you may need port forwarding (see Network Access section)
- Test port accessibility from the other device:
  - Try `http://[server-ip]:9000` in a browser
  - If you get "Connection refused", firewall is blocking

**Logs not streaming**
- Open browser console (F12) and check for WebSocket errors
- Verify "📊 Log WebSocket listening" message in terminal
- Check connection indicator in log panel (should be green)
- On network connections, ensure port 8766 is not blocked by firewall

**Logs work on localhost but not on network IP**
- This is a firewall issue - WebSocket port 8766 is blocked
- Add firewall rule for port 8766 (see Network Access section)
- For WSL2, add port forwarding for 8766

**Mobile issues**
- If zoom occurs on input, the UI uses 16px fonts to prevent this
- On iOS, try refreshing the page
- For log panel, use "✖ Close" button in mobile view

**Chat not responding**
- Check Ollama is running: `ollama list`
- Verify WebSocket connection in browser console
- Check terminal for error messages

**Model switching fails**
- Ensure model is installed: `ollama list`
- Pull missing models: `ollama pull <model>`
- Check terminal for error messages

**WebSocket connection errors in browser console**
- Common error: "WebSocket connection to 'ws://192.168.x.x:8766' failed"
- Solution: Add Windows Firewall rules (see Network Access section)
- Verify with `netstat -an | grep 8766` that port is listening on `0.0.0.0`

---

## Browser Compatibility

**Desktop**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Mobile**
- Safari (iOS 14+)
- Chrome (Android 90+)
- Samsung Internet
- Mobile Firefox

All features work on modern browsers with WebSocket support.

---

## Performance Notes

- Log panel keeps only last 500 entries for memory efficiency
- WebSocket connections auto-reconnect if dropped
- Chat history stored in browser localStorage
- Multiple clients can connect simultaneously
- Minimal CPU usage even with high-frequency logging