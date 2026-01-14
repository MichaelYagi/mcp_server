import json
from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
import logging

# Load environment variables from .env file
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers (in case something already configured it)
root_logger.handlers.clear()

# Create formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Create file handler
file_handler = logging.FileHandler(LOG_DIR / "mcp-server.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Add handlers to root logger
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Disable propagation to avoid duplicate logs
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("mcp_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp-server.log")

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
from tools.system import get_hardware_specs
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
from tools.rag.rag_add import rag_add
from tools.rag.rag_search import rag_search
from tools.rag.rag_diagnose import diagnose_rag
# ─────────────────────────────────────────────
# Plex Tools
# ─────────────────────────────────────────────
from tools.plex.semantic_media_search import semantic_media_search
from tools.plex.scene_locator import scene_locator
from tools.plex.ingest import ingest_next_batch

mcp = FastMCP("MCP server")


# ─────────────────────────────────────────────
# Knowledge Base Tools
# ─────────────────────────────────────────────

@mcp.tool()
def add_entry(title: str, content: str, tags: List[str] | None = None) -> str:
    """
    Create a new KNOWLEDGE BASE entry (for storing information, notes, URLs).

    NOT for todo items - use add_todo_item for tasks.

    Args:
        title (str, required): Title or heading for the entry
        content (str, required): The actual content/text to store
        tags (List[str], optional): List of category tags for organization

    Returns:
        JSON string containing the created entry with:
        - id: Generated unique identifier
        - title: Entry title
        - content: Stored content
        - tags: Associated tags
        - created_at: Timestamp

    Use when user wants to save information, notes, URLs, or structured knowledge.
    """
    logger.info(f"🛠 [server] add_entry called with title: {title}, content: {content}, tags: {tags}")
    tags = tags or []
    result = kb_add(title, content, tags)
    return json.dumps(result)


@mcp.tool()
def search_entries(query: str) -> str:
    """
    Perform full-text search across all knowledge base entries.

    Args:
        query (str, required): Keywords, phrases, or text to search for

    Returns:
        JSON string with array of matching entries, each containing:
        - id: Entry identifier
        - title: Entry title
        - content: Entry content
        - tags: Associated tags
        - relevance_score: Match quality

    Use when user wants to find, look up, or retrieve entries by content.
    """
    logger.info(f"🛠 [server] search_entries called with query: {query}")
    results = kb_search(query)
    return json.dumps(results, indent=2)


@mcp.tool()
def search_by_tag(tag: str) -> str:
    """
    Retrieve all knowledge base entries with a specific tag.

    Args:
        tag (str, required): The tag name to filter by

    Returns:
        JSON string with array of entries having that tag, each containing:
        - id: Entry identifier
        - title: Entry title
        - content: Entry content
        - tags: All associated tags

    Use when user asks for entries grouped by topic, category, or label.
    """
    logger.info(f"🛠 [server] search_by_tag called with tag: {tag}")
    result = kb_search_tags(tag)
    return json.dumps(result, indent=2)


@mcp.tool()
def search_semantic(query: str, top_k: int = 5) -> str:
    """
    Perform semantic (embedding-based) search across the knowledge base.

    Args:
        query (str, required): Concept or question to find related content
        top_k (int, optional): Number of results to return (default: 5)

    Returns:
        JSON string with array of most relevant entries, each containing:
        - id: Entry identifier
        - title: Entry title
        - content: Entry content
        - tags: Associated tags
        - similarity_score: Semantic relevance (0-1)

    Use for finding conceptually related ideas, similar content, or concept-level matches.
    """
    logger.info(f"🛠 [server] search_semantic called with query: {query}")
    result = kb_search_semantic(query, top_k)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_entry(entry_id: str) -> str:
    """
    Retrieve a single knowledge base entry by its ID.

    Args:
        entry_id (str, required): The unique identifier of the entry

    Returns:
        JSON string containing:
        - id: Entry identifier
        - title: Entry title
        - content: Full entry content
        - tags: Associated tags
        - created_at: Creation timestamp
        - updated_at: Last modification timestamp

    Use when user wants to view, inspect, or reference a specific saved entry.
    """
    logger.info(f"🛠 [server] get_entry called with entry_id: {entry_id}")
    result = kb_get(entry_id)
    return json.dumps(result)


@mcp.tool()
def delete_entry(entry_id: str) -> str:
    """
    Delete a single knowledge base entry by ID.

    Args:
        entry_id (str, required): The unique identifier of the entry to delete

    Returns:
        JSON string with:
        - success: Boolean indicating if deletion succeeded
        - deleted_id: ID of the deleted entry
        - message: Confirmation or error message

    Use when user wants to remove or clean up a specific entry.
    """
    logger.info(f"🛠 [server] delete_entry called with entry_id: {entry_id}")
    result = kb_delete(entry_id)
    return json.dumps(result)


@mcp.tool()
def delete_entries(entry_ids: List[str]) -> str:
    """
    Delete multiple knowledge base entries at once.

    Args:
        entry_ids (List[str], required): List of entry IDs to delete

    Returns:
        JSON string with:
        - deleted_count: Number of entries successfully deleted
        - deleted_ids: List of IDs that were removed
        - failed_ids: List of IDs that couldn't be deleted (if any)

    Use for bulk cleanup or batch deletion operations.
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
    Update an existing knowledge base entry.

    NOT for todo items - use update_todo_item for tasks.

    Args:
        entry_id (str, required): ID of the entry to update
        title (str, optional): New title (omit to keep current)
        content (str, optional): New content (omit to keep current)
        tags (List[str], optional): New tags list (omit to keep current)

    Returns:
        JSON string with the updated entry containing:
        - id: Entry identifier
        - title: Updated title
        - content: Updated content
        - tags: Updated tags
        - updated_at: New modification timestamp

    Use when user wants to revise, correct, or expand an entry.
    """
    logger.info(
        f"🛠 [server] update_entry called with entry_id: {entry_id}, title: {title}, content: {content}, tags: {tags}")
    result = kb_update(entry_id, title, content, tags)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_entries() -> str:
    """
    List all entries in the knowledge base.

    Args:
        None

    Returns:
        JSON string with array of all entries, each containing:
        - id: Entry identifier
        - title: Entry title
        - content: Entry content (may be truncated)
        - tags: Associated tags
        - created_at: Creation timestamp

    Use when user wants an overview, index, or inventory of stored information.
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

    Args:
        entry_id (str, required): ID of the entry to update
        title (str, optional): New title
        content (str, optional): New content
        tags (List[str], optional): New tags list

    Returns:
        JSON string with:
        - current: The new version with all fields
        - version_number: Version identifier
        - previous_version: Reference to the old version
        - change_summary: What was modified

    Use when user wants safe, versioned edits or audit-friendly changes.
    """
    logger.info(
        f"🛠 [server] update_entry_versioned called with entry_id: {entry_id}, title: {title}, content: {content}, tags: {tags}")
    result = kb_update_versioned(entry_id, title, content, tags)
    return json.dumps(result, indent=2)


# ─────────────────────────────────────────────
# System Tools
# ─────────────────────────────────────────────
@mcp.tool()
def get_hardware_specs_tool() -> str:
    """
    Get detailed hardware specifications including CPU, GPU, and RAM.

    Args:
        None

    Returns:
        JSON string with:
        - cpu: {model, cores, threads, frequency}
        - gpu: [{name, vram, driver_version}] (array of GPUs)
        - ram: {total_gb, type, speed_mhz}
        - platform: Operating system name

    Works across Windows, Linux, and macOS.

    Use when user asks about hardware specs, system specs, CPU, GPU, graphics card, or RAM.
    """
    logger.info(f"🛠 [server] get_hardware_specs_tool called")
    result = get_hardware_specs()
    return json.dumps(result, indent=2)


@mcp.tool()
def get_system_info() -> str:
    """
    Retrieve current system health and resource usage.

    Args:
        None

    Returns:
        JSON string with:
        - os: {name, version, architecture}
        - cpu: {usage_percent, load_average}
        - memory: {total_gb, used_gb, available_gb, percent_used}
        - disk: {total_gb, used_gb, free_gb, percent_used}
        - uptime: System uptime in seconds

    Use when user asks about system performance, diagnostics, or machine status.
    """
    logger.info(f"🛠 [server] get_system_info called")
    return get_system_stats()


@mcp.tool()
def list_system_processes(top_n: int = 10) -> str:
    """
    List active system processes sorted by resource usage.

    Args:
        top_n (int, optional): Number of top processes to return (default: 10)

    Returns:
        JSON string with array of processes, each containing:
        - pid: Process ID
        - name: Process name
        - cpu_percent: CPU usage percentage
        - memory_percent: RAM usage percentage
        - status: Process status (running, sleeping, etc.)

    Use when user asks what is running or wants to inspect system activity.
    """
    logger.info(f"🛠 [server] list_system_processes called with top_n: {top_n}")
    return list_processes(top_n)


@mcp.tool()
def terminate_process(pid: int) -> str:
    """
    Terminate a process by its process ID (PID).

    Args:
        pid (int, required): The process ID to terminate

    Returns:
        JSON string with:
        - success: Boolean indicating if termination succeeded
        - pid: The process ID that was terminated
        - message: Confirmation or error message

    Use when user explicitly requests to stop or kill a specific process.
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
    Create a new TODO/TASK item.

    NOT for knowledge base entries - use add_entry for notes.

    Args:
        title (str, required): Task title or name
        description (str, optional): Additional details about the task
        due_by (str, optional): Due date in YYYY-MM-DD format

    Returns:
        JSON string with the created todo containing:
        - id: Unique task identifier (use this for updates)
        - title: Task title
        - description: Task description
        - status: Current status ("open" by default)
        - due_by: Due date
        - created_at: Creation timestamp

    Use when user wants to track tasks, reminders, or deadlines.
    """
    logger.info(f"🛠 [server] add_todo_item called with title: {title}, description: {description}, due_date: {due_by}")
    result = add_todo(title, description, due_by)
    return json.dumps(result, indent=2)


@mcp.tool()
def list_todo_items() -> str:
    """
    List all todo items.

    Args:
        None

    Returns:
        JSON string with array of all todos, each containing:
        - id: Task identifier (CRITICAL: use this ID for update_todo_item)
        - title: Task title
        - description: Task description
        - status: Current status (open/complete)
        - due_by: Due date
        - created_at: When it was created

    IMPORTANT: Extract the 'id' field to use with update_todo_item or delete_todo_item.

    Use when user wants an overview of their tasks or reminders.
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
    Search and filter todo items with multiple criteria.

    Args:
        text (str, optional): Search in title/description
        status (str, optional): Filter by status ("open" or "complete")
        due_before (str, optional): Due before this date (YYYY-MM-DD)
        due_after (str, optional): Due after this date (YYYY-MM-DD)
        order_by (str, optional): Sort field (due_by, created_at, title)
        ascending (bool, optional): Sort direction (default: True)

    Returns:
        JSON string with array of matching todos, each containing:
        - id: Task identifier
        - title: Task title
        - description: Task description
        - status: Current status
        - due_by: Due date
        - created_at: Creation timestamp

    Use when user wants to find, filter, or organize tasks by specific criteria.
    """
    logger.info(
        f"🛠 [server] search_todo_items called with text: {text}, status: {status}, due_before: {due_before}, due_after: {due_after}")
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
    Update a TODO/TASK item (e.g., mark complete).

    FOR TODO LISTS ONLY. Use update_entry for knowledge base notes.

    Args:
        todo_id (str, required): The 'id' field from list_todo_items
        title (str, optional): New title
        description (str, optional): New description
        status (str, optional): New status ("open" or "complete")
        due_by (str, optional): New due date (YYYY-MM-DD)

    Returns:
        JSON string with the updated todo containing:
        - id: Task identifier
        - title: Updated title
        - description: Updated description
        - status: Updated status
        - due_by: Updated due date
        - updated_at: Modification timestamp

    IMPORTANT: Use the exact 'id' from list_todo_items, not the task title.

    Use when user wants to modify, mark complete, or correct a task.
    """
    logger.info(
        f"🛠 [server] update_todo_item called with todo_id: {todo_id}, title: {title}, description: {description}, status: {status}, due_date: {due_by}")
    result = update_todo(todo_id, title, description, status, due_by)
    return json.dumps(result, indent=2)


@mcp.tool()
def delete_todo_item(todo_id: str) -> str:
    """
    Delete a single todo item by its ID.

    Args:
        todo_id (str, required): The 'id' field from list_todo_items

    Returns:
        JSON string with:
        - success: Boolean indicating if deletion succeeded
        - deleted_id: ID of the deleted task
        - message: Confirmation or error message

    Use when user wants to remove a specific task.
    """
    logger.info(f"🛠 [server] delete_todo_item called with todo_id: {todo_id}")
    result = delete_todo(todo_id)
    return json.dumps(result, indent=2)


@mcp.tool()
def delete_all_todo_items() -> str:
    """
    Delete ALL todo items. Use with caution!

    Args:
        None

    Returns:
        JSON string with:
        - deleted_count: Number of tasks deleted
        - deleted_ids: List of all deleted task IDs

    Use when user explicitly wants to clear their entire task list.
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
    Read a code file and return a structured summary.

    Args:
        path (str, required): Absolute or relative file path
        max_bytes (int, optional): Maximum file size to read (default: 200,000)

    Returns:
        JSON string with:
        - path: File path
        - size: File size in bytes
        - num_lines: Total line count
        - imports: List of import statements
        - classes: List of class names
        - functions: List of function names
        - preview: First 20 lines of code
        - error: Error message if file cannot be read

    Works across Windows, Linux, and macOS.

    Use when user wants to summarize or review a specific code file.
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

        import re

        lines = text.splitlines()
        num_lines = len(lines)

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
            "preview": "\n".join(lines[:20])
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
    Search source code for text or regex patterns across multiple files.

    Args:
        query (str, required): Text or regex pattern to find (e.g., 'class Weather', 'to-do')
        extension (str, optional): Filter by file type (e.g., 'py', 'js', 'java')
        directory (str, optional): Starting folder path (default: current directory)

    Returns:
        JSON string with:
        - matches: Array of results, each containing:
          - file: File path
          - line_number: Line where match was found
          - line_text: The matching line content
          - context: Surrounding lines (if available)
        - total_matches: Number of matches found
        - files_searched: Number of files searched

    Use when user wants to locate code, patterns, class definitions, function calls, or text references.
    """
    logger.info(
        f"🛠 [server] search_code_in_directory called with query: {query}, extension: {extension}, directory: {directory}")
    result = search_code(query, extension, directory)
    return json.dumps(result, indent=2)


@mcp.tool()
def scan_code_directory(path: str) -> str:
    """
    Recursively scan a directory and summarize its code structure.

    Args:
        path (str, required): Directory path to scan

    Returns:
        JSON string with:
        - directory: Scanned path
        - total_files: Number of code files found
        - total_size_bytes: Total size of all files
        - languages: {language: file_count} breakdown
        - files: Array of file details:
          - path: File path
          - size: File size in bytes
          - language: Detected language
          - lines: Line count (if analyzed)

    Use when user wants an overview of a codebase or project folder.
    """
    logger.info(f"🛠 [server] scan_code_directory called with path: {path}")
    result = scan_directory(path)
    return json.dumps(result, indent=2)


@mcp.tool()
def summarize_code() -> str:
    """
    Generate a high-level summary of the entire codebase.

    Args:
        None (scans current project directory)

    Returns:
        JSON string with:
        - project_structure: Directory tree
        - language_breakdown: File counts by language
        - key_files: Important files identified
        - architecture_notes: High-level design observations
        - entry_points: Main/startup files
        - dependencies: External libraries detected

    Use when user wants a broad overview for onboarding, documentation, or quick understanding.
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
    Analyze a bug and propose fixes with root cause analysis.

    Args:
        error_message (str, required): The error message or exception text
        stack_trace (str, optional): Full stack trace if available
        code_snippet (str, optional): Relevant code that caused the error
        environment (str, optional): Environment details (OS, language version, etc.)

    Returns:
        JSON string with:
        - error_type: Classified error category
        - likely_causes: Array of potential root causes
        - suggested_fixes: Array of fix recommendations with code examples
        - references: Links to documentation or similar issues
        - severity: Estimated severity (low/medium/high/critical)

    Use when user wants help diagnosing, debugging, or fixing code issues.
    """
    logger.info(
        f"🛠 [server] debug_fix called with error_message: {error_message}, stack_trace: {stack_trace}, code_snippet: {code_snippet}, environment: {environment}")
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

    Args:
        city (str, optional): City name (e.g., "Surrey", "Tokyo")
        state (str, optional): State/province (e.g., "BC", "California", "Ontario")
        country (str, optional): Country name (e.g., "Canada", "Japan")

    All arguments are optional. If none provided, uses client's IP to determine location.
    Timezone is NEVER required - determined automatically.

    Returns:
        JSON string with:
        - city: City name
        - state: State/province/region
        - country: Country name
        - latitude: Geographic latitude
        - longitude: Geographic longitude
        - timezone: IANA timezone identifier
        - timezone_offset: UTC offset

    Use when user asks about where a place is, geographic context, or "my location".
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
    Get the current local time for any city in the world.

    Args:
        city (str, optional): City name (e.g., "London", "New York")
        state (str, optional): State/province (e.g., "NY", "Queensland")
        country (str, optional): Country name (e.g., "United States", "Australia")

    All arguments are optional. If none provided, uses client's IP to determine location.
    Timezone is NEVER required - determined automatically from location.

    Returns:
        JSON string with:
        - city: City name
        - state: State/province
        - country: Country name
        - current_time: Current time in HH:MM:SS format
        - date: Current date in YYYY-MM-DD format
        - timezone: IANA timezone identifier
        - day_of_week: Day name (Monday, Tuesday, etc.)

    Use when user asks "What time is it in X" or "What time is it here".
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

    Args:
        city (str, optional): City name (e.g., "Surrey", "Paris")
        state (str, optional): State/province/prefecture (e.g., "BC", "California", "Kanagawa")
        country (str, optional): FULL country name (e.g., "Canada", "Japan", "United States")

    All arguments are optional. If none provided, uses client's IP to determine location.

    IMPORTANT: Never put a province/state into the country field.

    Returns:
        JSON string with:
        - location: {city, state, country}
        - current: {
            temperature_c: Current temperature in Celsius
            temperature_f: Current temperature in Fahrenheit
            condition: Weather description
            humidity: Humidity percentage
            wind_speed_kph: Wind speed
            feels_like_c: Feels like temperature
          }
        - forecast: Array of upcoming days with high/low temps

    Use when user asks about weather, temperature, or forecast.
    """
    logger.info(f"🛠 [server] get_weather_tool called with city: {city}, state: {state}, country: {country}")
    logger.info(f"🌤️  get_weather_tool called with: city={city}, state={state}, country={country}")
    logger.info(f"🌤️  CLIENT_IP = {CLIENT_IP}")

    if not city and CLIENT_IP:
        logger.info(f"🌤️  No city provided, using IP geolocation...")
        loc = geolocate_ip(CLIENT_IP)
        logger.info(f"🌤️  Geolocation result: {loc}")
        if loc:
            city = loc.get("city")
            state = loc.get("region")
            country = loc.get("country")
            logger.info(f"🌤️  Resolved to: city={city}, state={state}, country={country}")

    result = get_weather_fn(city, state, country)
    logger.info(f"🌤️  Result: {result}")
    logger.info(f"🌤️  Returning weather result")
    return result


# ─────────────────────────────────────────────
# Text Tools
# ─────────────────────────────────────────────

@mcp.tool()
def split_text_tool(text: str, max_chunk_size: int = 2000) -> str:
    """
    Split long text into manageable chunks for processing.

    Args:
        text (str, required): The text to split
        max_chunk_size (int, optional): Maximum characters per chunk (default: 2000)

    Returns:
        JSON string with:
        - chunks: Array of text segments
        - total_chunks: Number of chunks created
        - original_length: Length of input text

    Use for breaking down large documents before summarization or analysis.
    """
    logger.info(f"🛠 [server] split_text_tool called with text: {text}, max_chunk_size: {max_chunk_size}")
    return json.dumps(split_text(text, max_chunk_size))


@mcp.tool()
def summarize_chunk_tool(chunk: str, style: str = "short") -> str:
    """
    Summarize a single text chunk.

    Args:
        chunk (str, required): Text segment to summarize
        style (str, optional): Summary style - "brief"/"short"/"medium"/"detailed" (default: "short")

    Returns:
        JSON string with:
        - summary: The generated summary
        - original_length: Length of input chunk
        - summary_length: Length of summary
        - compression_ratio: How much text was reduced

    Use for summarizing individual text segments or chunks.
    """
    logger.info(f"🛠 [server] summarize_chunk_tool called with chunk: {chunk}, style: {style}")
    return json.dumps(summarize_chunk(chunk, style))


@mcp.tool()
def merge_summaries_tool(summaries: List[str], style: str = "medium") -> str:
    """
    Combine multiple summaries into one cohesive summary.

    Args:
        summaries (List[str], required): Array of summary texts to merge
        style (str, optional): Output style - "short"/"medium"/"detailed" (default: "medium")

    Returns:
        JSON string with:
        - merged_summary: The combined summary
        - input_count: Number of summaries merged
        - total_input_length: Combined length of inputs
        - output_length: Length of merged summary

    Use for combining chunk summaries into a final document summary.
    """
    logger.info(f"🛠 [server] merge_summaries_tool called with summaries: {summaries}, style: {style}")
    return json.dumps(merge_summaries(summaries, style))


@mcp.tool()
def summarize_text_tool(text: str | None = None,
                        file_path: str | None = None,
                        style: str = "medium") -> str:
    """
    Summarize text from direct input or file.

    Args:
        text (str, optional): Direct text to summarize (mutually exclusive with file_path)
        file_path (str, optional): Path to text file to summarize
        style (str, optional): Summary style - "short"/"medium"/"detailed" (default: "medium")

    Must provide either text OR file_path, not both.

    Returns:
        JSON string with:
        - summary: The generated summary
        - source: "text" or file path
        - original_length: Length of input
        - chunks_processed: Number of chunks if text was split

    Use for comprehensive text summarization from various sources.
    """
    logger.info(f"🛠 [server] summarize_text_tool called with text: {text}, file_path: {file_path}, style: {style}")
    return json.dumps(summarize_text(text, file_path, style))


@mcp.tool()
def summarize_direct_tool(text: str, style: str = "medium") -> str:
    """
    Summarize text in a single LLM call (for shorter texts).

    Args:
        text (str, required): Text to summarize (should be under 4000 characters)
        style (str, optional): Summary style - "short"/"medium"/"detailed" (default: "medium")

    Returns:
        JSON string with:
        - summary: The generated summary
        - style_used: The style applied
        - original_length: Length of input text

    Use for quick summarization of shorter texts without chunking overhead.
    """
    logger.info(f"🛠 [server] summarize_direct_tool called with text: {text}, style: {style}")
    return json.dumps(summarize_direct(text, style))


@mcp.tool()
def explain_simplified_tool(concept: str) -> str:
    """
    Explain complex concepts using the Ladder of Abstraction.

    Args:
        concept (str, required): The concept or term to explain

    Returns:
        JSON string with three explanation levels:
        - analogy: Simple real-world comparison
        - simple_explanation: Plain language explanation
        - technical_definition: Precise technical definition
        - concept: The original concept

    Use when user wants to understand complex topics at multiple levels.
    """
    logger.info(f"🛠 [server] explain_simplified_tool called with concept: {concept}")
    result = explain_simplified(concept)
    return json.dumps(result)


@mcp.tool()
def concept_contextualizer_tool(concept: str) -> str:
    """
    Provide comprehensive context and background for a concept.

    Args:
        concept (str, required): The concept to contextualize

    Returns:
        JSON string with:
        - concept: The concept name
        - definition: Clear definition
        - context: Background and history
        - related_concepts: Connected ideas
        - applications: Real-world uses
        - examples: Concrete examples

    Use when user wants deep understanding with context and connections.
    """
    logger.info(f"🛠 [server] concept_contextualizer_tool called with concept: {concept}")
    result = concept_contextualizer(concept)
    return json.dumps(result)


# ─────────────────────────────────────────────
# RAG Tools
# ─────────────────────────────────────────────
@mcp.tool()
def rag_add_tool(text: str, source: str | None = None, chunk_size: int = 500) -> str:
    """
    Add text to the RAG (Retrieval-Augmented Generation) vector database.

    Args:
        text (str, required): Content to add (subtitles, articles, notes, etc.)
        source (str, optional): Source identifier (e.g., "movie:12345", "article:tech-news")
        chunk_size (int, optional): Words per chunk for embedding (default: 500)

    Returns:
        JSON string with:
        - chunks_added: Number of chunks created and stored
        - source: Source identifier used
        - total_text_length: Length of input text
        - embeddings_generated: Number of embeddings created

    Automatically chunks text, generates embeddings using bge-large model, and stores in vector database.

    Use when ingesting movie/TV subtitles, knowledge base articles, or any text for later semantic retrieval.
    """
    logger.info(f"🛠 [server] rag_add_tool called with text length: {len(text)}, source: {source}")
    result = rag_add(text, source, chunk_size)
    return json.dumps(result, indent=2)


@mcp.tool()
def rag_search_tool(query: str, top_k: int = 5, min_score: float = 0.0) -> str:
    """
    Search the RAG database using semantic similarity.

    Args:
        query (str, required): What to search for (e.g., "scenes about betrayal", "machine learning concepts")
        top_k (int, optional): Maximum number of results to return (default: 5)
        min_score (float, optional): Minimum similarity threshold 0.0-1.0 (default: 0.0)

    Returns:
        JSON string with:
        - results: Array of matches, each containing:
          - text: The matching text chunk
          - score: Similarity score (0-1, higher is better)
          - source: Source identifier
          - metadata: Additional context
        - query: The search query used
        - total_results: Number of results returned

    Uses bge-large embeddings for semantic matching. Returns most relevant text chunks with similarity scores.

    Use when looking for specific scenes/dialogue, finding relevant context, or answering questions about stored knowledge.
    """
    logger.info(f"🛠 [server] rag_search_tool called with query: {query}, top_k: {top_k}")
    result = rag_search(query, top_k, min_score)
    return json.dumps(result, indent=2)


@mcp.tool()
def rag_diagnose_tool() -> str:
    """
    Diagnose RAG database for incomplete or problematic entries.

    Args:
        None

    Returns:
        JSON string with:
        - total_items: Total Plex items available
        - ingested_count: Number of items successfully ingested
        - missing_subtitles: Array of items with no subtitle data:
          - title: Movie/episode title
          - id: Plex ratingKey
          - type: "movie" or "episode"
        - not_yet_ingested: Array of items not yet processed:
          - title: Movie/episode title
          - id: Plex ratingKey
          - type: "movie" or "episode"
        - statistics: Overall ingestion statistics

    Use to find which Plex items are missing subtitle data or haven't been ingested yet.
    Helps identify gaps in the RAG database.
    """
    logger.info(f"🛠 [server] rag_diagnose_tool called")
    result = diagnose_rag()
    return json.dumps(result, indent=2)

@mcp.tool()
def rag_status_tool() -> str:
    """
    Get quick status of RAG database without full diagnostics.

    Returns:
        JSON string with:
        - rag_documents: Number of documents in RAG database
        - total_words: Total words stored
        - unique_sources: Number of unique media items
        - ingestion_stats: Summary from storage tracking

    Use for quick checks of RAG database health.
    """
    logger.info(f"🛠 [server] rag_status_tool called")
    from tools.rag.rag_vector_db import get_rag_stats
    from tools.rag.rag_storage import get_ingestion_stats

    try:
        rag_stats = get_rag_stats()
        ingestion_stats = get_ingestion_stats()

        result = {
            "rag_database": {
                "total_documents": rag_stats.get("total_documents", 0),
                "total_words": rag_stats.get("total_words", 0),
                "unique_sources": rag_stats.get("unique_sources", 0)
            },
            "ingestion_tracking": {
                "total_plex_items": ingestion_stats["total_items"],
                "successfully_ingested": ingestion_stats["successfully_ingested"],
                "marked_no_subtitles": ingestion_stats["missing_subtitles"],
                "not_yet_processed": ingestion_stats["remaining"]
            },
            "summary": f"{ingestion_stats['successfully_ingested']} items ingested out of {ingestion_stats['total_items']} total ({round(ingestion_stats['successfully_ingested'] / ingestion_stats['total_items'] * 100, 1)}% complete)"
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"❌ Error getting RAG status: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def plex_ingest_batch(limit: int = 5, rescan_no_subtitles: bool = False) -> str:
    """
        Ingest Plex items into RAG
        Uses coroutines to parallelize Plex media into RAG database
    """
    logger.info(f"🛠 [server] plex_ingest_batch called with limit: {limit}, rescan: {rescan_no_subtitles}")

    # Must await the async function!
    result = await ingest_next_batch(limit, rescan_no_subtitles)

    logger.info(f"🛠 [server] plex_ingest_batch completed")
    return json.dumps(result, indent=2)

@mcp.tool()
def rag_rescan_no_subtitles() -> str:
    """
    Reset items that were marked as 'no subtitles' to allow re-scanning.

    Use this after you've added subtitle files to your Plex media and want
    to re-check items that were previously skipped.

    Returns:
        JSON string with:
        - reset_count: Number of items unmarked for re-scanning
        - message: Confirmation message
    """
    logger.info(f"🛠 [server] rag_rescan_no_subtitles called")
    from tools.rag.rag_storage import reset_no_subtitle_items
    count = reset_no_subtitle_items()
    return json.dumps({
        "reset_count": count,
        "message": f"Reset {count} items for re-scanning. Run plex_ingest_batch to check them again."
    }, indent=2)

# ─────────────────────────────────────────────
# Plex Tools
# ─────────────────────────────────────────────

@mcp.tool()
def semantic_media_search_text(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for movies and TV shows in the Plex library by title, genre, actor, or description.

    Args:
        query (str, required): Search terms (movie title, genre, actor name, description, etc.)
        limit (int, optional): Maximum number of results (default: 10)

    Returns:
        Dictionary with:
        - results: Array of matching media, each containing:
          - id: Plex ratingKey (CRITICAL: use this with scene_locator_tool)
          - title: Media title
          - summary: Description/plot summary
          - genres: Array of genre names
          - year: Release year
          - type: "movie" or "show"
          - score: Search relevance score
        - query: The search query used
        - total_results: Number of results returned

    REQUIRED FIRST STEP: When locating scenes, MUST call this tool first to get the ratingKey,
    then pass that ratingKey to scene_locator_tool.

    Use for finding media by any attribute - title, actor, genre, plot description, etc.
    """
    if not query or not query.strip():
        raise ValueError("semantic_media_search_text called with empty query")
    logger.info(f"🛠 [server] semantic_media_search called with query: {query}, limit: {limit}")
    return semantic_media_search(query=query, limit=limit)


@mcp.tool()
def scene_locator_tool(media_id: str, query: str, limit: int = 5):
    """
    Find specific scenes within a movie or TV show using subtitle search.

    Args:
        media_id (str, required): Plex ratingKey (numeric ID) - NOT the title
        query (str, required): Description of scene to find (e.g., "first confrontation", "final battle")
        limit (int, optional): Maximum number of scenes to return (default: 5)

    Returns:
        Array of matching scenes, each containing:
        - timestamp: When the scene occurs (HH:MM:SS format)
        - text: Subtitle text from that scene
        - score: Relevance score
        - context: Surrounding subtitle lines for context

    CRITICAL WORKFLOW:
    1. Call semantic_media_search_text with the movie/show title
    2. Extract the 'id' field (ratingKey) from results
    3. Pass that ratingKey to this tool as media_id

    WRONG: scene_locator_tool(media_id="3:10 to Yuma", ...)
    RIGHT: scene_locator_tool(media_id="12345", ...)

    Use for finding specific moments, dialogue, or scenes within media.
    """
    logger.info(f"🛠 [server] scene_locator_tool called with media_id: {media_id}, query: {query}, limit: {limit}")
    return scene_locator(media_id=media_id, query=query, limit=limit)


@mcp.tool()
def find_scene_by_title(movie_title: str, scene_query: str, limit: int = 5):
    """
    Find a specific scene in a movie - convenience tool combining search and scene location.

    Args:
        movie_title (str, required): Name of the movie or show (e.g., "3:10 to Yuma")
        scene_query (str, required): Description of the scene (e.g., "train station standoff")
        limit (int, optional): Number of scenes to return (default: 5)

    Returns:
        Dictionary with:
        - movie: The matched movie title
        - media_id: The Plex ratingKey used
        - scenes: Array of matching scenes with:
          - timestamp: Scene time (HH:MM:SS)
          - text: Subtitle text
          - score: Relevance score
          - context: Surrounding lines
        - error: Error message if movie not found

    This tool automatically handles the two-step process:
    1. Searches for the movie/show by title
    2. Locates the scene within that media

    Use when you have both a title and scene description - this simplifies the workflow.
    """
    logger.info(
        f"🛠 [server] find_scene_by_title called with movie_title: {movie_title}, query: {scene_query}, limit: {limit}")
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