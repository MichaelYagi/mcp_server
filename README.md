# MCP Server & Client

A modular, extensible **Model Context Protocol (MCP)** architecture. This project provides a structured framework for both hosting diverse Python-based tools (Server) and interacting with them via an AI Agent (Client), exposing diverse Python-based tools to AI agents through a unified JSON-RPC interface.

The server is designed to be a "plug-and-play" system. You can introduce new capabilities—such as system automation, data management, or specialized calculators—by simply adding new modules to the directory structure.

---

## Key Features

* **Bidirectional Architecture**: Includes both a Server to expose local tools and a Client to act as the "brain" using LLMs.
* **Multi-Domain Support**: Organize tools into logical categories (e.g., `knowledge`, `system`, `math`) to keep the codebase clean and scalable.
* **Schema-Driven Validation**: Every tool is backed by a JSON schema, ensuring that AI agents provide correctly formatted inputs every time.
* **Versioned Storage**: Built-in support for file-backed data persistence with automatic snapshotting for "undo" or "recovery" workflows.
* **Offline Semantic Search**: A pure-Python implementation of TF-IDF search, providing conceptual retrieval without external APIs or vector databases.
* **Windows Optimized**: Pre-configured to handle encoding and stdio pipe challenges specific to Windows environments.

---

## Modular Architecture

The server separates tool logic from the protocol interface, allowing for rapid development of new features.

* **Client (client.py)**: The AI agent. It connects to the server, maintains conversation context, and invokes tools based on user intent.
* **Server (server.py)**: The hub. It registers local tools and provides the JSON-RPC interface for the client to discover them.
* **Tools Directory**: Contains the functional Python logic for each domain. Also contains local persistence via flat files that contain entries & snapshots
* **Schemas Directory**: Defines the "contract" between the AI and your code.

---

## Directory Structure

```text
mcp-server/
│
├── server.py                 # Core hub; registers and exposes tools
├── client.py                 # MCP Client; the AI Agent (powered by Groq/LLM)
├── .env                      # API keys and environment configuration
│
├── tools/
│   ├── knowledge_base/       # Domain: Structured data & search
│   │   └── kb_add.py
│   │   └── ...
│   └── location/             # Domain: External API integration
│       └── get_weather.py
│       └── ...
│
└── schemas/                  # JSON schemas defining tool inputs
│   ├── knowledge_base/       
│   │   └── kb_add.json
│   │   └── ...
│   └── location/             
│       └── get_weather.json
│       └── ...
```

## Included Tool Suite (Knowledge Domain)

As a starting point, the server includes a set of tools for information management:

| Tool | Function |
| :--- | :--- |
| **add_entry** | Stores structured text data with metadata and custom tags. |
| **search_entries** | Keyword-based text search over stored files. |
| **search_semantic** | Concepts-based search using TF-IDF and Cosine Similarity. |
| **update_versioned** | Updates a file while saving a timestamped backup in `snapshots/`. |
| **list_all** | Returns an inventory of all current data objects. |

---

## Semantic Search Logic

The search engine is built to be lightweight and dependency-free. It processes queries using:

* **Tokenization**: Parsing text into a searchable index.
* **TF-IDF Weighting**: Identifying the most unique and relevant terms across all documents.
* **Cosine Similarity**: Comparing the mathematical vector of the query against the document vectors.

---

## Setup & Integration

### 1. Prerequisites

* Python 3.10+
* Groq API Key: Get it at [console.groq.com](https://console.groq.com/) (Free)
* Weather API Key: Get it at [weatherapi.com](https://www.weatherapi.com/) (Free)

### 2. Environment Configuration

Create an ```.env``` file in the root of the project with the following details.
```
WEATHER_API_KEY="<weather_api_key>"
GROQ_API_KEY="<gsk_groq_api_key>"
GROQ_MODEL="llama-3.1-8b-instant"
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Running the Project
```
python client.py
```

### Option B: Connecting to Claude Desktop (External Client)

Install Claude Desktop and update the configuration. Windows example: Ensure you use **absolute paths** and the specific environment flags for Windows stability.

Edit `%APPDATA%\Roaming\Claude\claude_desktop_config.json` and edit the ```base_path```

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

Run it:
```
python server.py
```

Then open Claude Desktop to start using the MCP server.

---

## Extending the Server

Adding a new capability is a three-step process:

1. **Logic**: Add a Python script to `tools/<new_domain>/`.
2. **Schema**: Define the input parameters in `schemas/<new_domain>/<tool_name>.json`.
3. **Register**: Import the function into `server.py` and wrap it with the `@mcp.tool()` decorator.

This modular approach ensures the server remains maintainable even as you add dozens of specialized tools.