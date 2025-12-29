import sys
import io
import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

# ─────────────────────────────────────────────
# Knowledge Base Tools
# ─────────────────────────────────────────────
from tools.knowledge_base.kb_add import kb_add
from tools.knowledge_base.kb_get import kb_get
from tools.knowledge_base.kb_search import kb_search
from tools.knowledge_base.kb_update import kb_update
from tools.knowledge_base.kb_delete import kb_delete
from tools.knowledge_base.kb_delete_many import kb_delete_many
from tools.knowledge_base.kb_list import kb_list
from tools.knowledge_base.kb_search_tags import kb_search_tags
from tools.knowledge_base.kb_search_semantic import kb_search_semantic
from tools.knowledge_base.kb_update_versioned import kb_update_versioned
# ─────────────────────────────────────────────
# System Tools
# ─────────────────────────────────────────────
from tools.system.system_info import get_system_stats
from tools.system.processes import list_processes, kill_process

mcp = FastMCP("Knowledge Base Server")

@mcp.tool()
def add_entry(title: str, content: str, tags: List[str] | None = None) -> str:
    """Add an entry. Returns JSON string."""
    tags = tags or []
    result = kb_add(title, content, tags)
    return json.dumps(result) # MUST be a string

@mcp.tool()
def search_entries(query: str) -> str:
    """Search entries. Returns JSON string of the list."""
    results = kb_search(query)
    # Even if results is an empty list [], json.dumps makes it a string "[]"
    return json.dumps(results, indent=2)

@mcp.tool()
def search_by_tag(tag: str) -> str:
    result = kb_search_tags(tag)
    return json.dumps(result, indent=2)

@mcp.tool()
def search_semantic(query: str, top_k: int = 5) -> str:
    result = kb_search_semantic(query, top_k)
    return json.dumps(result, indent=2)

@mcp.tool()
def get_entry(entry_id: str) -> str:
    """Get entry. Returns JSON string."""
    result = kb_get(entry_id)
    return json.dumps(result)

@mcp.tool()
def delete_entry(entry_id: str) -> str:
    """Delete a single entry by ID. Returns JSON string."""
    result = kb_delete(entry_id)
    return json.dumps(result)

@mcp.tool()
def delete_entries(entry_ids: List[str]) -> str:
    """Delete multiple entries. Returns JSON string."""
    result = kb_delete_many(entry_ids)
    return json.dumps(result, indent=2)

@mcp.tool()
def update_entry(entry_id: str, title: str | None = None,
                 content: str | None = None,
                 tags: List[str] | None = None) -> str:
    result = kb_update(entry_id, title, content, tags)
    return json.dumps(result, indent=2)

@mcp.tool()
def list_entries() -> str:
    result = kb_list()
    return json.dumps(result, indent=2)

@mcp.tool()
def update_entry_versioned(entry_id: str,
                           title: str | None = None,
                           content: str | None = None,
                           tags: List[str] | None = None) -> str:
    result = kb_update_versioned(entry_id, title, content, tags)
    return json.dumps(result, indent=2)

@mcp.tool()
def get_system_info() -> str:
    """Provides current system health and resource usage.

    Returns a JSON string of OS, CPU, RAM, and Disk stats.
    """
    return get_system_stats()

@mcp.tool()
def list_system_processes(top_n: int = 10) -> str:
    """Provides a list of active system processes."""
    return list_processes(top_n)

@mcp.tool()
def terminate_process(pid: int) -> str:
    """Kills a specific process by PID."""
    return kill_process(pid)

if __name__ == "__main__":
    mcp.run(transport="stdio")