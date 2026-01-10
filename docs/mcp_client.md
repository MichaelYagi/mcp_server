                         ┌──────────────────────────┐
                         │        MCP CLIENT        │
                         │ (Protocol + Tool Bridge) │
                         └─────────────┬────────────┘
                                       │
                                       │ connects to
                                       ▼
                         ┌──────────────────────────┐
                         │       MCP SERVER(S)      │
                         │   (Tool Providers)       │
                         └─────────────┬────────────┘
                                       │
                                       │ registers tools with
                                       ▼
        ┌───────────────────────────────────────────────────────────┐
        │                    CLIENT TOOL REGISTRY                   │
        │ (Local representation of all MCP tools available to agent)│
        └───────────────────────────────────────────────────────────┘
                                       │
                                       │ provides tools to
                                       ▼

        ┌───────────────────────────────────────────────────────────┐
        │                     LANGGRAPH AGENT                       │
        │   (Reasoning, Planning, Tool-Orchestration, State Flow)   │
        └───────────────────────────────────────────────────────────┘
            │                     │                     │
            │ decides             │ loops/branches      │ finalizes
            ▼                     ▼                     ▼

    ┌────────────────┐     ┌──────────────────┐     ┌──────────────────┐ 
    │  Tool Call     │     │  State Update    │     │  LLM Reasoning   │
    │  Node          │     │  Node            │     │  Node            │
    └────────────────┘     └──────────────────┘     └──────────────────┘
            │                     │                     │
            │ invokes             │ stores              │ interprets
            ▼                     ▼                     ▼

        ┌───────────────────────────────────────────────────────────┐
        │                     MCP CLIENT API                        │
        │ (send tool calls, receive results, stream logs/metrics)   │
        └───────────────────────────────────────────────────────────┘
                                       │
                                       │ streams to
                                       ▼

                         ┌──────────────────────────┐
                         │         WEB UI           │
                         │ (Chat, Logs, Metrics)    │
                         └──────────────────────────┘

### LangGraph is part of the client’s reasoning layer
* It’s not “next to” the client — it lives inside the client as the agent brain.

### The MCP client provides tools to LangGraph
* The client discovers tools → registers them → LangGraph uses them.

### The agent is the combination of:
* LangGraph (flow + state machine)
* LLM (reasoning engine)
* MCP tools (actions)

### The Web UI is downstream
It only displays:

* messages 
* tool results 
* logs 
* metrics

It doesn’t decide anything.