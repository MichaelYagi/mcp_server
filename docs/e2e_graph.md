    ┌──────────────────────────────────────────────────────────────────────────┐
    │                                WEB UI                                    │
    │     (Chat, Streaming Output, Logs Panel, Metrics Panel)                  │
    └───────────────────────────────┬──────────────────────────────────────────┘
                                    │  WebSocket / HTTP
                                    ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                               MCP CLIENT                                 │
    │   (Protocol, Tool Registry, Transport, Bridges UI ↔ Agent ↔ MCP Server)  │
    └───────────────┬──────────────────────────────────────────────────────────┘
                    │ registers tools with
                    ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                         CLIENT TOOL REGISTRY                             │
    │   (Local representation of all MCP tools exposed by the server)          │
    └───────────────┬──────────────────────────────────────────────────────────┘
                    │ provides tools to
                    ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                            LANGGRAPH AGENT                               │
    │   (Reasoning, Planning, State Machine, Tool-Orchestration, Memory Flow)  │
    └───────────────┬──────────────────────────────────────────────────────────┘
                    │ decides next step
                    ▼
        ┌────────────────────────────────────────────────────────┐
        │                    AGENT NODES                         │
        └────────────────────────────────────────────────────────┘
                │                     │                     │
                │                     │                     │
                ▼                     ▼                     ▼
       ┌──────────────────┐   ┌────────────────────┐   ┌────────────────────┐
       │  LLM Reasoning   │   │  Tool Call Node    │   │  State Update Node │
       │  (llama3.1:8b)   │   │  (MCP invocation)  │   │  (Graph memory)    │
       └──────────────────┘   └────────────────────┘   └────────────────────┘
                │                     │
                │                     │ invokes
                │                     ▼
                │        ┌──────────────────────────────────────────────┐
                │        │                 MCP CLIENT API               │
                │        │ (send tool calls, receive results, streams)  │
                │        └──────────────────────────────────────────────┘
                │                     │
                │                     │ forwards to
                ▼                     ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                               MCP SERVER                                 │
    │        (Tool Provider Layer: RAG, Embeddings, Search, Metadata, etc.)    │
    └───────────────┬──────────────────────────────────────────────────────────┘
                    │ exposes tools
                    ▼
    ┌──────────────────────────────────────────────────────────────────────────┐
    │                                   TOOLS                                  │
    └──────────────────────────────────────────────────────────────────────────┘
           │                     │                        │                 │
           ▼                     ▼                        ▼                 ▼

    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ Embedding Tool   │   │ Vector Search    │   │ Plex Metadata    │   │ File Ops Tool    │
    │ (bge-large CPU)  │   │ (LanceDB RAG)    │   │ (Local Library)  │   │ (Read/Write)     │
    └──────────────────┘   └──────────────────┘   └──────────────────┘   └──────────────────┘
           │                     │                        │
           │ uses                │ queries                │ fetches
           ▼                     ▼                        ▼

    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │ Embedding Model  │   │ Vector Database  │   │ Movie Metadata DB│
    │ (bge-large CPU)  │   │ (LanceDB)        │   │ (Your Plex data) │
    └──────────────────┘   └──────────────────┘   └──────────────────┘


    ┌──────────────────────────────────────────────────────────────────────────┐
    │                             LOGS STREAM (WS)                             │
    │     (Server logs, tool logs, agent logs streamed to Web UI)              │
    └──────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────┐
    │                           METRICS STREAM (WS)                            │
    │     (CPU %, GPU %, VRAM, RAM, temps streamed to Web UI)                  │
    └──────────────────────────────────────────────────────────────────────────┘


### The Web UI is the user-facing layer
It receives:

* chat output
* tool results
* logs
* metrics

### The MCP Client is the bridge
It:

* connects to the MCP server
* registers tools
* exposes them to LangGraph
* streams logs + metrics

### LangGraph is the agent brain
It:

* interprets user intent
* decides which tool to call
* loops until done
* maintains state
* orchestrates everything

### The LLM is the reasoning engine
It:

* thinks
* plans
* interprets tool results
* generates final answers

### The MCP Server is the toolbox
It provides:

* embeddings
* vector search
* metadata
* file ops
* logs
* metrics

### The Vector DB + Embedding Model power RAG
* bge-large runs on GPU
* LanceDB stores your movie embeddings
* RAG retrieval feeds context to the LLM