    USER
    │
    ▼
    WEB UI  ───────►  MCP CLIENT  ───────►  LANGGRAPH AGENT/LLM
                                              │
                                              │ calls tools
                                              ▼
                                           MCP SERVER

* MCP server graph is the action space of the agent.
* LangGraph pipeline decides which node to activate.
* LLM is the reasoning engine inside the LangGraph agent.