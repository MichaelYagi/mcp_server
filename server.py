import json
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

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
from tools.location.geolocate_util import geolocate_ip, CLIENT_IP
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
from tools.text_tools.explain_simplified import explain_simplified
from tools.text_tools.concept_contextualizer import concept_contextualizer
# ─────────────────────────────────────────────
# RAG Tools
# ─────────────────────────────────────────────
from tools.plex.ingest import ingest_next_batch
from tools.rag.rag_add import rag_add
from tools.rag.rag_search import rag_search
# ─────────────────────────────────────────────
# Plex Tools
# ─────────────────────────────────────────────
from tools.plex.semantic_media_search import semantic_media_search
from tools.plex.scene_locator import scene_locator

mcp = FastMCP("MCP server")
PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = Path(str(PROJECT_ROOT / "logs"))
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "mcp-server.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)

# If you want to see exactly what the MCP Server is saying
logging.getLogger("mcp").setLevel(logging.DEBUG)
logger = logging.getLogger("mcp_server")

# ─────────────────────────────────────────────
# To-do Tools
# ─────────────────────────────────────────────

@mcp.tool()
def add_entry(title: str, content: str, tags: List[str] | None = None) -> str:
    """
    Create a new knowledge base entry.

    • Requires a title and content.
    • Tags are optional and may be an empty list.
    • Returns the full stored entry, including its generated ID.

    Use this tool whenever the user wants to save information, notes, summaries, or structured knowledge.
    """
    logger.info(f"🛠 [server] add_entry called with title: {title}, content: {content}, tags: {tags}")
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
    logger.info(f"🛠 [server] search_entries called with query: {query}")
    results = kb_search(query)
    # Even if results is an empty list [], json.dumps makes it a string "[]"
    return json.dumps(results, indent=2)

@mcp.tool()
def search_by_tag(tag: str) -> str:
    """
    Retrieve all entries associated with a specific tag.

    Use this tool when the user asks for entries grouped by topic, category, or label.
    """
    logger.info(f"🛠 [server] search_by_tag called with tag: {tag}")
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
    logger.info(f"🛠 [server] search_semantic called with query: {query}")
    result = kb_search_semantic(query, top_k)
    return json.dumps(result, indent=2)

@mcp.tool()
def get_entry(entry_id: str) -> str:
    """
    Retrieve a single knowledge base entry by its ID.

    Use this tool when the user wants to view, inspect, or reference a specific saved entry.
    """
    logger.info(f"🛠 [server] get_entry called with entry_id: {entry_id}")
    result = kb_get(entry_id)
    return json.dumps(result)

@mcp.tool()
def delete_entry(entry_id: str) -> str:
    """
    Delete a single knowledge base entry by ID.

    Use this tool when the user wants to remove or clean up a specific entry.
    """
    logger.info(f"🛠 [server] delete_entry called with entry_id: {entry_id}")
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
    logger.info(f"🛠 [server] delete_entries called with entry_ids: {entry_ids}")
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
    logger.info(f"🛠 [server] update_entry called with entry_id: {entry_id}, title: {title}, content: {content}, tags: {tags}")
    result = kb_update(entry_id, title, content, tags)
    return json.dumps(result, indent=2)

@mcp.tool()
def list_entries() -> str:
    """
    List all entries in the knowledge base.

    Use this tool when the user wants an overview, index, or inventory of stored information.
    """
    logger.info(f"🛠 [server] list_entries called")
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
    logger.info(f"🛠 [server] update_entry_versioned called with entry_id: {entry_id}, title: {title}, content: {content}, tags: {tags}")
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
    logger.info(f"🛠 [server] get_system_info called")
    return get_system_stats()

@mcp.tool()
def list_system_processes(top_n: int = 10) -> str:
    """
    List active system processes.

    • Returns the top N processes by resource usage.
    • Useful for monitoring or debugging.

    Use this tool when the user asks what is running or wants to inspect system activity.
    """
    logger.info(f"🛠 [server] list_system_processes called with top_n: {top_n}")
    return list_processes(top_n)

@mcp.tool()
def terminate_process(pid: int) -> str:
    """
    Terminate a process by PID.

    Use this tool when the user explicitly requests to stop or kill a specific process.
    """
    logger.info(f"🛠 [server] terminate_process called with pid: {pid}")
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
    logger.info(f"🛠 [server] add_todo_item called with title: {title}, description: {description}, due_date: {due_by}")
    result = add_todo(title, description, due_by)
    return json.dumps(result, indent=2)

@mcp.tool()
def list_todo_items() -> str:
    """
    List all to‑do items.

    Use this tool when the user wants an overview of their tasks or reminders.
    """
    logger.info(f"🛠 [server] list_todo_items called")
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
    logger.info(f"🛠 [server] search_todo_items called with text: {text}, status: {status}, due_before: {due_before}, due_after: {due_after}")
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
    logger.info(f"🛠 [server] update_todo_item called with todo_id: {todo_id}, title: {title}, description: {description}, status: {status}, due_date: {due_by}")
    result = update_todo(todo_id, title, description, status, due_by)
    return json.dumps(result, indent=2)

@mcp.tool()
def delete_todo_item(todo_id: str) -> str:
    """
    Delete a single to‑do item by ID.

    Use this tool when the user wants to remove a specific task.
    """
    logger.info(f"🛠 [server] delete_todo_item called with todo_id: {todo_id}")
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
    logger.info(f"🛠 [server] delete_all_todo_items called")
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
def summarize_code_file(path: str, max_bytes: int = 200_000) -> str:
    """
    Read a code file from disk and return a structured summary.

    • Reads the file at the given path.
    • Limits file size to prevent runaway reads.
    • Returns JSON containing:
        - path
        - size
        - summary
        - error (if any)

    Use this tool when the user wants to summarize or review a specific code file.
    """
    logger.info(f"🛠 [server] summarize_code_file called with path: {path}, max_bytes: {max_bytes}")
    from pathlib import Path
    import json

    p = Path(path)

    if not p.exists():
        return json.dumps({"error": f"File not found: {path}"})

    if not p.is_file():
        return json.dumps({"error": f"Not a file: {path}"})

    try:
        data = p.read_bytes()

        if len(data) > max_bytes:
            return json.dumps({
                "error": "File too large",
                "path": path,
                "size": len(data),
                "max_bytes": max_bytes
            })

        text = data.decode("utf-8", errors="replace")

        # --- Summarization logic (simple, LLM-friendly) ---
        import re

        lines = text.splitlines()
        num_lines = len(lines)

        # Extract imports, classes, functions
        imports = [l.strip() for l in lines if l.strip().startswith("import") or l.strip().startswith("from")]
        classes = re.findall(r"class\s+([A-Za-z0-9_]+)", text)
        functions = re.findall(r"def\s+([A-Za-z0-9_]+)", text)

        summary = {
            "path": path,
            "size": len(data),
            "num_lines": num_lines,
            "imports": imports,
            "classes": classes,
            "functions": functions,
            "preview": "\n".join(lines[:20])  # first 20 lines
        }

        return json.dumps(summary, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to read or summarize file: {str(e)}",
            "path": path
        })

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
    logger.info(f"🛠 [server] search_code_in_directory called with query: {query}, extension: {extension}, directory: {directory}")
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
    logger.info(f"🛠 [server] scan_code_directory called with path: {path}")
    result = scan_directory(path)
    return json.dumps(result, indent=2)

@mcp.tool()
def summarize_code() -> str:
    """
    Generate a high‑level summary of the entire codebase.

    • Useful for onboarding, documentation, or quick understanding.

    Use this tool when the user wants a broad overview of the project.
    """
    logger.info(f"🛠 [server] summarize_code called")
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
    logger.info(f"🛠 [server] debug_fix called with error_message: {error_message}, stack_trace: {stack_trace}, code_snippet: {code_snippet}, environment: {environment}")
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
    logger.info(f"🛠 [server] get_location_tool called with city: {city}, state: {state}, country: {country}")
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")

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
    logger.info(f"🛠 [server] get_time_tool called with city: {city}, state: {state}, country: {country}")
    if not city and CLIENT_IP:
        loc = geolocate_ip(CLIENT_IP)
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")

    return json.dumps(get_time_fn(city, state, country), indent=2)


@mcp.tool()
def get_weather_tool(city: str | None = None, state: str | None = None, country: str | None = None) -> str:
    """
    Get current weather conditions for any location.

    If a user does not provide a city, it will use the users IP address.

    When parsing locations:
    • City = city name (e.g., Surrey)
    • State = province or prefecture or state (e.g., BC, Ontario, Kanagawa, California)
    • Country = full country name (e.g., Canada, Japan, United States)

    Never put a province or state into the country field.
    """
    logger.info(f"🛠 [server] get_weather_tool called with city: {city}, state: {state}, country: {country}")
    logger.info(f"🌤️  get_weather_tool called with: city={city}, state={state}, country={country}")
    logger.info(f"🌤️  CLIENT_IP = {CLIENT_IP}")

    # If the LLM didn't provide a city, but we have a CLIENT_IP, let's use it.
    if not city and CLIENT_IP:
        logger.info(f"🌤️  No city provided, using IP geolocation...")
        loc = geolocate_ip(CLIENT_IP)
        logger.info(f"🌤️  Geolocation result: {loc}")
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")
            logger.info(f"🌤️  Resolved to: city={city}, state={state}, country={country}")

    # This calls your get_weather.py which now cleans the query string
    result = get_weather_fn(city, state, country)
    logger.info(f"🌤️  Result: {result}")
    logger.info(f"🌤️  Returning weather result")
    return result

# ─────────────────────────────────────────────
# Text Tools
# ─────────────────────────────────────────────

@mcp.tool()
def split_text_tool(text: str, max_chunk_size: int = 2000) -> str:
    logger.info(f"🛠 [server] split_text_tool called with text: {text}, max_chunk_size: {max_chunk_size}")
    return json.dumps(split_text(text, max_chunk_size))

@mcp.tool()
def summarize_chunk_tool(chunk: str, style: str = "short") -> str:
    logger.info(f"🛠 [server] summarize_chunk_tool called with chunk: {chunk}, style: {style}")
    return json.dumps(summarize_chunk(chunk, style))

@mcp.tool()
def merge_summaries_tool(summaries: List[str], style: str = "medium") -> str:
    logger.info(f"🛠 [server] merge_summaries_tool called with summaries: {summaries}, style: {style}")
    return json.dumps(merge_summaries(summaries, style))

@mcp.tool()
def summarize_text_tool(text: str | None = None,
                        file_path: str | None = None,
                        style: str = "medium") -> str:
    logger.info(f"🛠 [server] summarize_text_tool called with text: {text}, file_path: {file_path}, style: {style}")
    return json.dumps(summarize_text(text, file_path, style))

@mcp.tool()
def summarize_direct_tool(text: str, style: str = "medium") -> str:
    """
    Prepare text for direct summarization in a single LLM call.
    """
    logger.info(f"🛠 [server] summarize_direct_tool called with text: {text}, style: {style}")
    return json.dumps(summarize_direct(text, style))

@mcp.tool()
def explain_simplified_tool(concept: str) -> str:
    """
    MCP-exposed tool that returns a JSON string.
    Produce a structured, simple explanation of a complex concept
    using the Ladder of Abstraction:
    1. Analogy
    2. Simple explanation
    3. Technical definition
    """
    logger.info(f"🛠 [server] explain_simplified_tool called with concept: {concept}")
    result = explain_simplified(concept)
    return json.dumps(result)

@mcp.tool()
def concept_contextualizer_tool(concept: str) -> str:
    """
    MCP-exposed tool that returns a JSON string.
    """
    logger.info(f"🛠 [server] concept_contextualizer_tool called with concept: {concept}")
    result = concept_contextualizer(concept)
    return json.dumps(result)

# ─────────────────────────────────────────────
# RAG Tools
# ─────────────────────────────────────────────
@mcp.tool()
def rag_add_tool(text: str):
    return rag_add(text)

@mcp.tool()
def rag_search_tool(query: str):
    return rag_search(query)

@mcp.tool()
def plex_ingest_batch(limit: int = 5):
    """
    Ingests up to `limit` unprocessed Plex items into RAG.
    Returns a summary of what was ingested.
    """
    return ingest_next_batch(limit)

# ─────────────────────────────────────────────
# Plex Tools
# ─────────────────────────────────────────────

@mcp.tool()
def semantic_media_search_text(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for movies and TV shows in the Plex library.

    Use this tool to find media by title, genre, actor, or description.
    Returns a list of matching items with their Plex ratingKey (id field).

    REQUIRED FIRST STEP: If you need to locate scenes in a movie/show,
    you MUST call this tool first to get the ratingKey, then use that
    ratingKey with the scene_locator_tool.

    Args:
        query: Search terms (movie title, genre, actor name, etc.)
        limit: Maximum number of results (default: 10)

    Returns:
        Dictionary with 'results' array. Each result contains:
        - id: The Plex ratingKey (USE THIS for scene_locator_tool)
        - title: Media title
        - summary: Description
        - genres: List of genres
        - year: Release year
        - score: Search relevance score
    """
    if not query or not query.strip():
        raise ValueError("semantic_media_search_text called with empty query")
    logger.info(f"🛠 [server] semantic_media_search called with query: {query}, limit: {limit}")
    return semantic_media_search(query=query, limit=limit)

@mcp.tool()
def scene_locator_tool(media_id: str, query: str, limit: int = 5):
    """
    Find specific scenes within a movie or TV show using subtitle search.

    CRITICAL: media_id MUST be a Plex ratingKey (numeric ID), NOT a title.

    REQUIRED WORKFLOW:
    1. If you only have a movie/show title, call semantic_media_search_text FIRST
    2. Extract the 'id' field from the search results (this is the ratingKey)
    3. Then call this tool with that ratingKey

    WRONG: scene_locator_tool(media_id="3:10 to Yuma", ...)
    RIGHT: scene_locator_tool(media_id="12345", ...)

    Args:
        media_id: Plex ratingKey (numeric ID) - get this from semantic_media_search_text
        query: Description of the scene to find (e.g., "first confrontation")
        limit: Maximum number of scenes to return (default: 5)

    Returns:
        List of matching scenes with timestamps and subtitle text
    """
    logger.info(f"🛠 [server] scene_locator_tool called with media_id: {media_id}, query: {query}, limit: {limit}")
    return scene_locator(media_id=media_id, query=query, limit=limit)

@mcp.tool()
def find_scene_by_title(movie_title: str, scene_query: str, limit: int = 5):
    """
    Find a specific scene in a movie by searching for the movie first, then locating the scene.

    This is a convenience tool that combines semantic_media_search and scene_locator.
    Use this when you have a movie title and want to find a scene.

    Args:
        movie_title: The name of the movie (e.g., "3:10 to Yuma")
        scene_query: Description of the scene (e.g., "first confrontation")
        limit: Number of scenes to return (default: 5)

    Returns:
        Matching scenes with timestamps
    """
    logger.info(f"🛠 [server] find_scene_by_title called with movie_title: {movie_title}, query: {scene_query}, limit: {limit}")
    # Step 1: Search for the movie
    search_results = semantic_media_search(query=movie_title, limit=1)

    if not search_results.get("results"):
        return {"error": f"Could not find movie '{movie_title}' in Plex library"}

    # Step 2: Get the ratingKey
    media_id = search_results["results"][0]["id"]
    movie_name = search_results["results"][0]["title"]

    # Step 3: Find the scene
    scenes = scene_locator(media_id=media_id, query=scene_query, limit=limit)

    return {
        "movie": movie_name,
        "media_id": media_id,
        "scenes": scenes
    }

if __name__ == "__main__":
    logger.info(f"🛠 [server] mcp server running with stdio enabled")
    mcp.run(transport="stdio")