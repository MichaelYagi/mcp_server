import json
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pathlib import Path
import os
from dotenv import load_dotenv
import requests

CLIENT_IP = os.environ.get("CLIENT_IP")

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Verify critical environment variables
if not os.environ.get("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY not found in environment")

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
# ─────────────────────────────────────────────
# To-do Tools
# ─────────────────────────────────────────────
from tools.todo.add_todo import add_todo
from tools.todo.list_todos import list_todos
from tools.todo.update_todo import update_todo
from tools.todo.delete_todo import delete_todo
from tools.todo.search_todos import search_todos
from tools.todo.delete_all_todos import delete_all_todos
# ─────────────────────────────────────────────
# Code Review Tools
# ─────────────────────────────────────────────
from tools.code_review.scan_directory import scan_directory
from tools.code_review.summarize_codebase import summarize_codebase
from tools.code_review.fix_bug import fix_bug
from tools.code_review.search_code import search_code
# ─────────────────────────────────────────────
# Location Tools
# ─────────────────────────────────────────────
from tools.location.get_location import get_location as get_location_fn
from tools.location.get_time import get_time as get_time_fn
from tools.location.get_weather import get_weather as get_weather_fn
# ─────────────────────────────────────────────
# Text Tools
# ─────────────────────────────────────────────
from tools.text_tools.split_text import split_text
from tools.text_tools.summarize_chunk import summarize_chunk
from tools.text_tools.merge_summaries import merge_summaries
from tools.text_tools.summarize_text import summarize_text
from tools.text_tools.summarize_direct import summarize_direct

mcp = FastMCP("Knowledge Base Server")

@mcp.tool()
def add_entry(title: str, content: str, tags: List[str] | None = None) -> str:
    """
    Create a new knowledge base entry.

    • Requires a title and content.
    • Tags are optional and may be an empty list.
    • Returns the full stored entry, including its generated ID.

    Use this tool whenever the user wants to save information, notes, summaries, or structured knowledge.
    """
    tags = tags or []
    result = kb_add(title, content, tags)
    return json.dumps(result) # MUST be a string

@mcp.tool()
def search_entries(query: str) -> str:
    """
    Perform a full‑text search across all knowledge base entries.

    • Returns a list of matching entries.
    • Query may be keywords, phrases, or partial text.

    Use this tool when the user asks to find information, look something up, or retrieve entries by content.
    """
    results = kb_search(query)
    # Even if results is an empty list [], json.dumps makes it a string "[]"
    return json.dumps(results, indent=2)

@mcp.tool()
def search_by_tag(tag: str) -> str:
    """
    Retrieve all entries associated with a specific tag.

    Use this tool when the user asks for entries grouped by topic, category, or label.
    """
    result = kb_search_tags(tag)
    return json.dumps(result, indent=2)

@mcp.tool()
def search_semantic(query: str, top_k: int = 5) -> str:
    """
    Perform semantic (embedding‑based) search across the knowledge base.

    • Returns the most conceptually relevant entries.
    • top_k controls how many results to return.

    Use this tool when the user asks for related ideas, similar content, or concept‑level matches.
    """
    result = kb_search_semantic(query, top_k)
    return json.dumps(result, indent=2)

@mcp.tool()
def get_entry(entry_id: str) -> str:
    """
    Retrieve a single knowledge base entry by its ID.

    Use this tool when the user wants to view, inspect, or reference a specific saved entry.
    """
    result = kb_get(entry_id)
    return json.dumps(result)

@mcp.tool()
def delete_entry(entry_id: str) -> str:
    """
    Delete a single knowledge base entry by ID.

    Use this tool when the user wants to remove or clean up a specific entry.
    """
    result = kb_delete(entry_id)
    return json.dumps(result)

@mcp.tool()
def delete_entries(entry_ids: List[str]) -> str:
    """
    Delete multiple entries at once.

    • Accepts a list of entry IDs.
    • Returns which entries were removed.

    Use this tool for bulk cleanup or batch deletion.
    """
    result = kb_delete_many(entry_ids)
    return json.dumps(result, indent=2)

@mcp.tool()
def update_entry(entry_id: str,
                 title: str | None = None,
                 content: str | None = None,
                 tags: List[str] | None = None) -> str:
    """
    Update an existing entry.

    • All fields are optional except entry_id.
    • Only provided fields are modified.

    Use this tool when the user wants to revise, correct, or expand an entry.
    """
    result = kb_update(entry_id, title, content, tags)
    return json.dumps(result, indent=2)

@mcp.tool()
def list_entries() -> str:
    """
    List all entries in the knowledge base.

    Use this tool when the user wants an overview, index, or inventory of stored information.
    """
    result = kb_list()
    return json.dumps(result, indent=2)

@mcp.tool()
def update_entry_versioned(entry_id: str,
                           title: str | None = None,
                           content: str | None = None,
                           tags: List[str] | None = None) -> str:
    """
    Update an entry while preserving version history.

    • Creates a new version instead of overwriting the old one.
    • Only provided fields are updated.

    Use this tool when the user wants safe, versioned edits or audit‑friendly changes.
    """
    result = kb_update_versioned(entry_id, title, content, tags)
    return json.dumps(result, indent=2)

# ─────────────────────────────────────────────
# System MCP Tools
# ─────────────────────────────────────────────
@mcp.tool()
def get_system_info() -> str:
    """
    Retrieve current system health and resource usage.

    • Includes OS, CPU load, RAM usage, and disk statistics.
    • Returns structured JSON.

    Use this tool when the user asks about system performance, diagnostics, or machine status.
    """
    return get_system_stats()

@mcp.tool()
def list_system_processes(top_n: int = 10) -> str:
    """
    List active system processes.

    • Returns the top N processes by resource usage.
    • Useful for monitoring or debugging.

    Use this tool when the user asks what is running or wants to inspect system activity.
    """
    return list_processes(top_n)

@mcp.tool()
def terminate_process(pid: int) -> str:
    """
    Terminate a process by PID.

    Use this tool when the user explicitly requests to stop or kill a specific process.
    """
    return kill_process(pid)

# ─────────────────────────────────────────────
# To-do MCP Tools
# ─────────────────────────────────────────────
@mcp.tool()
def add_todo_item(title: str,
                  description: Optional[str] = None,
                  due_by: Optional[str] = None) -> str:
    """
    Create a new to‑do item.

    • Title is required.
    • Description and due date are optional.

    Use this tool when the user wants to track tasks, reminders, or deadlines.
    """
    result = add_todo(title, description, due_by)
    return json.dumps(result, indent=2)

@mcp.tool()
def list_todo_items() -> str:
    """
    List all to‑do items.

    Use this tool when the user wants an overview of their tasks or reminders.
    """
    result = list_todos()
    return json.dumps(result, indent=2)

@mcp.tool()
def search_todo_items(text: Optional[str] = None,
                      status: Optional[str] = None,
                      due_before: Optional[str] = None,
                      due_after: Optional[str] = None,
                      order_by: Optional[str] = None,
                      ascending: bool = True) -> str:
    """
    Search and filter to‑do items.

    • All filters are optional.
    • Supports text search, status filtering, date ranges, and sorting.

    Use this tool when the user wants to find, filter, or organize tasks.
    """
    result = search_todos(
        text=text,
        status=status,
        due_before=due_before,
        due_after=due_after,
        order_by=order_by or "due_by",
        ascending=ascending
    )
    return json.dumps(result, indent=2)

@mcp.tool()
def update_todo_item(todo_id: str,
                     title: Optional[str] = None,
                     description: Optional[str] = None,
                     status: Optional[str] = None,
                     due_by: Optional[str] = None) -> str:
    """
    Update a to‑do item.

    • Only provided fields are changed.
    • Supports updating title, description, status, and due date.

    Use this tool when the user wants to modify or correct a task.
    """
    result = update_todo(todo_id, title, description, status, due_by)
    return json.dumps(result, indent=2)

@mcp.tool()
def delete_todo_item(todo_id: str) -> str:
    """
    Delete a single to‑do item by ID.

    Use this tool when the user wants to remove a specific task.
    """
    result = delete_todo(todo_id)
    return json.dumps(result, indent=2)

@mcp.tool()
def delete_all_todo_items() -> str:
    """
    Delete all to‑do items.

    • Returns how many items were removed.
    • Use with caution.

    Use this tool when the user wants to clear their entire task list.
    """
    deleted_ids = delete_all_todos()
    result = {
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids
    }
    return json.dumps(result, indent=2)

# ─────────────────────────────────────────────
# Code Review MCP Tools
# ─────────────────────────────────────────────
@mcp.tool()
def search_code_in_directory(
        query: str,
        extension: Optional[str] = None,
        directory: Optional[str] = "."
) -> str:
    """
    Search source code for text or regex patterns.

    • Returns file paths, line numbers, and matching lines.
    • Optional file extension filter.
    • Optional directory selection.

    Use this tool when the user wants to locate code, patterns, definitions, or references.
    Returns file paths, line numbers, and the matching text.

    Args:
        query: The string or regex to find (e.g., 'class Weather' or 'to-do').
        extension: Filter by file type (e.g., 'py', 'js').
        directory: The folder to start searching from.
    """
    # Call the logic function
    result = search_code(query, extension, directory)

    # Return as a string for the AI to process
    return json.dumps(result, indent=2)

@mcp.tool()
def scan_code_directory(path: str) -> str:
    """
    Recursively scan a directory and summarize its code structure.

    • Returns files, sizes, languages, and basic metrics.

    Use this tool when the user wants an overview of a codebase or folder.
    """
    result = scan_directory(path)
    return json.dumps(result, indent=2)

@mcp.tool()
def summarize_code() -> str:
    """
    Generate a high‑level summary of the entire codebase.

    • Useful for onboarding, documentation, or quick understanding.

    Use this tool when the user wants a broad overview of the project.
    """
    result = summarize_codebase()
    return json.dumps(result, indent=2)

@mcp.tool()
def debug_fix(error_message: str,
              stack_trace: Optional[str] = None,
              code_snippet: Optional[str] = None,
              environment: Optional[str] = None) -> str:
    """
    Analyze a bug and propose fixes.

    • Accepts error messages, stack traces, code snippets, and environment details.
    • Returns structured suggestions and likely root causes.

    Use this tool when the user wants help diagnosing or fixing code issues.
    """
    result = fix_bug(
        error_message=error_message,
        stack_trace=stack_trace,
        code_snippet=code_snippet,
        environment=environment
    )
    return json.dumps(result, indent=2)

# ─────────────────────────────────────────────
# Location Tools
# ─────────────────────────────────────────────
def geolocate_ip(ip: str):
    if not ip:
        return None

    try:
        resp = requests.get(f"https://ipapi.co/{ip}/json/")
        return resp.json()
    except:
        return None

@mcp.tool()
def get_location_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Retrieve structured geographic information for any location.

    • City/state/country are OPTIONAL.
    • If the user provides a city (with or without state/country), that is enough.
    • Timezone is NEVER required — the server determines it automatically.
    • If no location is provided, the server uses the client's IP address to infer city, region, country, latitude, longitude, and timezone.

    Use this tool whenever the user asks about:
    • where a place is
    • what country/region a city belongs to
    • geographic context
    • “my location” or “where am I”

    Always call this tool directly without asking the user for timezone or coordinates.
    """
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country_name")

    return json.dumps(get_location_fn(city, state, country), indent=2)

@mcp.tool()
def get_time_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Get the local time for any city in the world.

    • City/state/country are OPTIONAL.
    • Timezone is NEVER required — the server automatically determines it from the location.
    • If the user provides only a city name, that is sufficient.
    • If no location is provided, the server uses the client's IP address to determine the correct city, region, country, and timezone.

    Use this tool whenever the user asks:
    • “What time is it in X”
    • “What time is it here”
    • “Local time for [city/country]”

    Do NOT ask the user for timezone — the server handles it automatically.
    """
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country_name")

    return json.dumps(get_time_fn(city, state, country), indent=2)

@mcp.tool()
def get_weather_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Get current weather conditions for any location.
    """
    # If the LLM didn't provide a city, but we have a CLIENT_IP, let's use it.
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country_name")

    # This calls your get_weather.py which now cleans the query string
    return get_weather_fn(city, state, country)

# ─────────────────────────────────────────────
# Text Tools
# ─────────────────────────────────────────────

@mcp.tool()
def split_text_tool(text: str, max_chunk_size: int = 2000) -> str:
    return json.dumps(split_text(text, max_chunk_size))

@mcp.tool()
def summarize_chunk_tool(chunk: str, style: str = "short") -> str:
    return json.dumps(summarize_chunk(chunk, style))

@mcp.tool()
def merge_summaries_tool(summaries: List[str], style: str = "medium") -> str:
    return json.dumps(merge_summaries(summaries, style))

@mcp.tool()
def summarize_text_tool(text: str | None = None,
                        file_path: str | None = None,
                        style: str = "medium") -> str:
    return json.dumps(summarize_text(text, file_path, style))

@mcp.tool()
def summarize_direct_tool(text: str, style: str = "medium") -> str:
    """
    Prepare text for direct summarization in a single LLM call.
    """
    return json.dumps(summarize_direct(text, style))

if __name__ == "__main__":
    mcp.run(transport="stdio")