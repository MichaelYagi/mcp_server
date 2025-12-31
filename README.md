# MCP Server

A modular, extensible **Model Context Protocol (MCP)** server architecture. This project provides a structured framework for exposing diverse Python-based tools to AI agents through a unified JSON-RPC interface.

The server is designed to be a "plug-and-play" system. You can introduce new capabilities—such as system automation, data management, or specialized calculators—by simply adding new modules to the directory structure.

---

## 🚀 Key Features

* **Multi-Domain Support**: Organize tools into logical categories (e.g., `knowledge`, `system`, `math`) to keep the codebase clean and scalable.
* **Schema-Driven Validation**: Every tool is backed by a JSON schema, ensuring that AI agents provide correctly formatted inputs every time.
* **Versioned Storage**: Built-in support for file-backed data persistence with automatic snapshotting for "undo" or "recovery" workflows.
* **Offline Semantic Search**: A pure-Python implementation of TF-IDF search, providing conceptual retrieval without external APIs or vector databases.
* **Windows Optimized**: Pre-configured to handle encoding and stdio pipe challenges specific to Windows environments.

---

## 🏗 Modular Architecture

The server separates tool logic from the protocol interface, allowing for rapid development of new features.



* **Tools Directory**: Contains the functional Python logic for each domain.
* **Schemas Directory**: Defines the "contract" between the AI and your code.
* **Data Directory**: A flat-file persistence layer that stores active entries and historical versions.

---

## 📂 Directory Structure

```text
mcp-server/
│
├── server.py                 # Core hub; registers and exposes tools to the protocol
├── tools/
│   └── knowledge/            # Example Domain: Structured data & search
│       ├── kb_add.py
│       ├── kb_search_semantic.py
│       └── kb_update_versioned.py
│
├── schemas/
│   └── knowledge/            # JSON schemas for the knowledge tools
│
└── data/                     # Local persistence layer
    ├── entries/              # Active JSON objects
    └── snapshots/            # Historical snapshots for versioning
```

## 🛠 Included Tool Suite (Knowledge Domain)

As a starting point, the server includes a set of tools for information management:

| Tool | Function |
| :--- | :--- |
| **add_entry** | Stores structured text data with metadata and custom tags. |
| **search_entries** | Keyword-based text search over stored files. |
| **search_semantic** | Concepts-based search using TF-IDF and Cosine Similarity. |
| **update_versioned** | Updates a file while saving a timestamped backup in `snapshots/`. |
| **list_all** | Returns an inventory of all current data objects. |

---

## 🧠 Semantic Search Logic

The search engine is built to be lightweight and dependency-free. It processes queries using:

* **Tokenization**: Parsing text into a searchable index.
* **TF-IDF Weighting**: Identifying the most unique and relevant terms across all documents.
* **Cosine Similarity**: Comparing the mathematical vector of the query against the document vectors.

---

## ⚡ Setup & Integration

Requirements:
```
Python 3.10 or newer
```

Install dependencies:
```
pip install mcp-use
pip install langchain-openai
pip install openai
```

### Configuration for client.py

Get OpenAI API key from https://console.groq.com/ (free)

```macOS / Linux
export OPENAI_API_KEY="gsk_XXXXXXXX"
export OPENAI_BASE_URL="https://api.groq.com/openai/v1"
export OPENAI_MODEL="llama-3.1-8b-instant"

Windows (PowerShell)
setx OPENAI_API_KEY "gsk_XXXXXXXX"
setx OPENAI_BASE_URL "https://api.groq.com/openai/v1"
setx OPENAI_MODEL "llama-3.1-8b-instant"
```

Run it:
```
python client.py
```

### Configuration for Claude Desktop

Update your configuration at `%APPDATA%\Roaming\Claude\claude_desktop_config.json` for Windows. Ensure you use **absolute paths** and the specific environment flags for Windows stability.

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

Then open Claude Desktop

---

## 🧩 Extending the Server

Adding a new capability is a three-step process:

1. **Logic**: Add a Python script to `tools/<new_domain>/`.
2. **Schema**: Define the input parameters in `schemas/<new_domain>/<tool_name>.json`.
3. **Register**: Import the function into `server.py` and wrap it with the `@mcp.tool()` decorator.

This modular approach ensures the server remains maintainable even as you add dozens of specialized tools.