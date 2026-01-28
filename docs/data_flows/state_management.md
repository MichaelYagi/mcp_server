    ┌──────────────────────────────────────────────┐
    │           STATE MANAGEMENT FLOW              │
    └───────────────────────┬──────────────────────┘
                            │
                            │ three independent state stores
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ CONVERSATION│   │ MULTI-AGENT │   │  METRICS    │
    │    STATE    │   │    STATE    │   │   STATE     │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           │                 │                 │
           ▼                 ▼                 ▼

    CONVERSATION STATE:
    Location: GLOBAL_CONVERSATION_STATE dict
    Structure:
    {
      "messages": [
        SystemMessage(...),
        HumanMessage(...),
        AIMessage(...),
        ToolMessage(...)
      ],
      "loop_count": 0
    }
    
    Shared Between:
    ├─ CLI input loop
    ├─ WebSocket handler
    └─ LangGraph agent
    
    Modifications:
    ├─ Add message (CLI/Web)
    ├─ Agent adds messages
    └─ History sync (Web → CLI)
    
    Persistence:
    ├─ Web UI: localStorage
    └─ CLI: memory only (lost on restart)

           │
           ▼
    MAX_MESSAGE_HISTORY: 20 (configurable)


    MULTI-AGENT STATE:
    Location: MULTI_AGENT_STATE dict (mutable reference)
    Structure:
    {
      "enabled": False  # or True
    }
    
    Shared Between:
    ├─ main.py (creates dict)
    ├─ CLI commands (:multi on/off)
    ├─ WebSocket handler (toggle)
    └─ run_agent_wrapper (checks state)
    
    Modifications:
    ├─ :multi on  → enabled = True
    ├─ :multi off → enabled = False
    ├─ Web toggle → enabled = True/False
    └─ .env default → initial value
    
    Why Mutable Dict:
    * Changes propagate to all references
      * No need for global keyword
      * Shared state across modules

             │
             ▼
      Default: False (single-agent)
      Can override: MULTI_AGENT_ENABLED in .env


    METRICS STATE:
    Location: metrics.py module-level dict
    Structure:
    {
      "agent_runs": 0,
      "agent_errors": 0,
      "agent_times": [(timestamp, duration), ...],
      "llm_calls": 0,
      "llm_errors": 0,
      "llm_times": [(timestamp, duration), ...],
      "tool_calls": {"tool_name": count},
      "tool_errors": {"tool_name": count},
      "tool_times": {"tool_name": [(ts, dur), ...]}
    }
    
    Shared Between:
    ├─ langgraph.py (tracks agent/LLM)
    ├─ All tools (track tool usage)
    ├─ WebSocket (broadcasts to dashboard)
    └─ :stats command (formats for CLI)
    
    Modifications:
    ├─ Increment counters on events
    ├─ Append (timestamp, duration) tuples
    ├─ prepare_metrics() for consumption
    └─ Auto-cleanup (keeps last 100 entries)
    
    Consumption:
    ├─ Dashboard: Real-time charts
    ├─ CLI: :stats command (formatted table)
    └─ Web: metrics_request message

           │
           ▼
    No persistence: Memory only
    Resets: On server restart


    STATE SYNCHRONIZATION:
    ┌─────────────────────────────────────────────┐
    │  User changes state via CLI or Web          │
    │  ├─ :multi on in CLI                        │
    │  └─ Toggle switch in Web                    │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  State dict updated (mutable reference)     │
    │  MULTI_AGENT_STATE["enabled"] = True        │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  All modules see change immediately         │
    │  ├─ run_agent_wrapper checks state          │
    │  ├─ CLI sees new state                      │
    │  └─ Web UI updates toggle                   │
    └─────────────────────────────────────────────┘


    CONVERSATION SYNCHRONIZATION:
    ┌─────────────────────────────────────────────┐
    │  User sends message from CLI or Web         │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  Message added to GLOBAL_CONVERSATION_STATE │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  Agent processes with full history          │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  Response added to state                    │
    └─────────────┬───────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────────────────┐
    │  Both CLI and Web see updated conversation  │
    │  ├─ CLI: Prints to terminal                 │
    │  └─ Web: Broadcasts via WebSocket           │
    └─────────────────────────────────────────────┘


KEY PRINCIPLES:
* Conversation state: Shared list (both interfaces)
* Multi-agent state: Mutable dict (all modules)
* Metrics state: Module-level dict (all consumers)
* No locks needed: Python GIL + single event loop
* Web persistence: localStorage (survives refresh)
* CLI persistence: None (session-based)