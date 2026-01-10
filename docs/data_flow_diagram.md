    ┌──────────────────────────────────────────────────────────────┐
    │                           USER QUERY                         │
    │                 (text typed into your Web UI)                │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                           WEB UI                             │
    │         (sends raw text to MCP Client over WS/HTTP)          │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                         MCP CLIENT                           │
    │     (forwards user message into LangGraph agent state)       │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                       LANGGRAPH AGENT                        │
    │     (LLM decides whether to call RAG, tools, or answer)      │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    │ if RAG needed
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     QUERY EMBEDDING (bge-large)              │
    │     MCP tool call → bge-large → 1024d embedding vector       │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     VECTOR SEARCH (LanceDB)                  │
    │   input: query vector → cosine similarity → top-k matches    │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     RETRIEVED CONTEXT                        │
    │   (movie summaries, metadata, chunks, descriptions, etc.)    │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     CONTEXT PACKAGING                        │
    │   (LangGraph merges retrieved text into LLM input prompt)    │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     LLM ANSWER (Llama 3.1 8B)                │
    │   (reasoning + synthesis using retrieved context)            │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                     LANGGRAPH FINALIZER                      │
    │   (formats final answer, updates state, returns output)      │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                         MCP CLIENT                           │
    │   (streams final answer + logs + metrics back to UI)         │
    └───────────────────────────────┬──────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                           WEB UI                             │
    │                 (renders final answer to user)               │
    └──────────────────────────────────────────────────────────────┘

**This diagram is for understanding:**

* where performance bottlenecks can occur
* where embeddings matter
* how RAG interacts with LangGraph
* how the MCP client/server moves data
* how the LLM consumes retrieved context

**This diagram shows pure data movement, not logic**

* where text becomes vectors
* where vectors become search results
* where search results become LLM context
* where LLM output becomes the final answer