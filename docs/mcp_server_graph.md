                          ┌──────────────────────────┐
                          │        MCP SERVER        │
                          │  (Tool Provider Layer)   │
                          └─────────────┬────────────┘
                                        │
                                        │ exposes tools
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │                           TOOLS                           │
        └───────────────────────────────────────────────────────────┘
            │                     │                     │
            │                     │                     │
            ▼                     ▼                     ▼

    ┌────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │  Embedding     │     │   Vector Search  │     │   Plex Metadata  │
    │   Tool         │     │     Tool         │     │      Tool        │
    └────────────────┘     └──────────────────┘     └──────────────────┘
             │                     │                     │
             │                     │                     │
             ▼                     ▼                     ▼

    ┌────────────────┐     ┌──────────────────┐     ┌──────────────────┐
    │  bge-large     │     │ LanceDB / RAG    │     │  Local Library   │
    │  CPU Embedding │     │ Similarity Query │     │  Movie Metadata  │
    └────────────────┘     └──────────────────┘     └──────────────────┘


            ┌──────────────────────────────────────────────────────────┐
            │                        LOGGING                           │
            │      (WebSocket stream of server + tool events)          │
            └──────────────────────────────────────────────────────────┘


            ┌──────────────────────────────────────────────────────────┐
            │                        METRICS                           │
            │   (CPU/GPU/RAM monitoring streamed to your Web UI)       │
            └──────────────────────────────────────────────────────────┘


            ┌──────────────────────────────────────────────────────────┐
            │                        FILE OPS                          │
            │   (read/write, ingest, chunking, indexing)               │
            └──────────────────────────────────────────────────────────┘

## How this graph behaves inside the agent system:
The MCP server is the tool layer.

The graph above shows:
* Nodes = tools or subsystems
* Edges = how tools are exposed to the MCP client
* Top-level node = the MCP server itself

The LangGraph agent sees this graph as a capability map.

When the agent needs to:
* embed text → it calls the Embedding Tool
* search your library → it calls the Vector Search Tool
* fetch movie info → it calls the Plex Metadata Tool
* stream logs → it connects to the Logging WebSocket
* monitor system load → it connects to the Metrics WebSocket

The MCP server is the structured interface that exposes all of these nodes.