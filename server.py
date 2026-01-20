import json
import os
import httpx
import logging
import uuid

from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

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

A2A_ENDPOINT = os.getenv("A2A_ENDPOINT", "").strip()
A2A_AVAILABLE = False

# ─────────────────────────────────────────────
# Stop Signal Support
# ─────────────────────────────────────────────
from client.stop_signal import is_stop_requested
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
from tools.plex.ingest import ingest_next_batch, ingest_batch_parallel_conservative, find_unprocessed_items, process_item_async

mcp = FastMCP("MCP server")

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
    Search the RAG database using semantic similarity with STOP SIGNAL support.
    """
    logger.info(f"🛠 [server] rag_search_tool called with query: {query}, top_k: {top_k}")

    # Check stop BEFORE expensive search
    if is_stop_requested():
        logger.warning("🛑 rag_search_tool: Stop requested - skipping search")
        return json.dumps({
            "results": [],
            "query": query,
            "total_results": 0,
            "stopped": True,
            "message": "Search cancelled by user"
        }, indent=2)

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
    Ingest Plex items into RAG with STOP SIGNAL support
    Uses coroutines to parallelize Plex media into RAG database
    """
    logger.info(f"🛠 [server] plex_ingest_batch called with limit: {limit}, rescan: {rescan_no_subtitles}")

    # Check stop BEFORE starting
    if is_stop_requested():
        logger.warning("🛑 plex_ingest_batch: Stop requested - skipping ingestion")
        return json.dumps({
            "ingested": [],
            "remaining": 0,
            "total_ingested": 0,
            "stopped": True,
            "stop_reason": "Stopped before ingestion started"
        }, indent=2)

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

# TOOL 1: Find Unprocessed Items (Discovery Phase)
@mcp.tool()
def plex_find_unprocessed(limit: int = 5, rescan_no_subtitles: bool = False) -> str:
    """
    Find unprocessed Plex items that need ingestion.

    This is STEP 1 of the ingestion workflow. Use this to discover which items
    need to be processed. Returns a list of item IDs that can be processed in
    parallel by other agents.

    Args:
        limit: Maximum number of unprocessed items to find (default: 5)
        rescan_no_subtitles: Re-check items that previously had no subtitles (default: False)

    Returns:
        JSON with:
        - found_count: Number of items found
        - items: Array of {id, title, type} for each unprocessed item

    Example Response:
        {
          "found_count": 3,
          "items": [
            {"id": "12345", "title": "Zootopia (2016)", "type": "movie"},
            {"id": "12346", "title": "Avatar (2009)", "type": "movie"}
          ]
        }

    Multi-Agent Usage:
        Orchestrator uses this as Task 1, then creates parallel tasks for items found.
    """
    logger.info(f"🔍 [TOOL] plex_find_unprocessed called (limit: {limit})")

    try:
        items = find_unprocessed_items(limit, rescan_no_subtitles)

        # Simplify for multi-agent consumption
        simplified = [
            {
                "id": str(item["id"]),
                "title": item.get("title", "Unknown"),
                "type": item.get("type", "unknown")
            }
            for item in items
        ]

        result = {
            "found_count": len(simplified),
            "items": simplified,
            "message": f"Found {len(simplified)} unprocessed items ready for ingestion"
        }

        logger.info(f"✅ [TOOL] Found {len(simplified)} unprocessed items")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"❌ [TOOL] plex_find_unprocessed failed: {e}")
        return json.dumps({"error": str(e), "found_count": 0, "items": []})

# TOOL 2: Ingest Multiple Items in Parallel (Batch Processing)
@mcp.tool()
async def plex_ingest_items(item_ids: str) -> str:
    """
    Ingest multiple Plex items in parallel (ASYNC) with STOP SIGNAL support.

    Args:
        item_ids: Comma-separated list of Plex media IDs (e.g., "12345,12346,12347")
                  OR "auto:N" to automatically find N unprocessed items

    Returns:
        JSON string with ingestion results
    """
    logger.info(f"🚀 [TOOL] plex_ingest_items called with IDs: {item_ids}")

    # Check stop BEFORE starting
    if is_stop_requested():
        logger.warning("🛑 plex_ingest_items: Stop requested - skipping ingestion")
        return json.dumps({
            "total_processed": 0,
            "ingested_count": 0,
            "skipped_count": 0,
            "stopped": True,
            "message": "Stopped before ingestion started"
        })

    try:
        # Check if using auto mode
        if item_ids.startswith("auto:"):
            limit = int(item_ids.split(":")[1])
            logger.info(f"🔍 Auto mode: finding {limit} unprocessed items")

            # Check stop BEFORE finding items
            if is_stop_requested():
                logger.warning("🛑 Stopped during item discovery")
                return json.dumps({
                    "total_processed": 0,
                    "stopped": True,
                    "message": "Stopped during item discovery"
                })

            media_items = find_unprocessed_items(limit, False)
            if not media_items:
                return json.dumps({
                    "total_processed": 0,
                    "ingested_count": 0,
                    "skipped_count": 0,
                    "message": "No unprocessed items found"
                })
        else:
            # Parse comma-separated IDs
            ids_list = [id.strip() for id in item_ids.split(",") if id.strip()]

            if not ids_list:
                return json.dumps({"error": "No item IDs provided", "total_processed": 0})

            logger.info(f"🔍 Fetching {len(ids_list)} items from Plex")

            # Fetch actual media items from Plex by ID
            from tools.plex.plex_utils import get_plex_server

            plex = get_plex_server()
            media_items = []

            for item_id in ids_list:
                # Check stop DURING item fetching
                if is_stop_requested():
                    logger.warning(f"🛑 Stopped while fetching items ({len(media_items)} fetched so far)")
                    # Return what we have so far
                    return json.dumps({
                        "total_processed": 0,
                        "items_fetched": len(media_items),
                        "stopped": True,
                        "message": f"Stopped while fetching items ({len(media_items)}/{len(ids_list)} fetched)"
                    })

                try:
                    # Fetch item from Plex
                    item = plex.fetchItem(int(item_id))

                    # Convert to our format
                    media_item = {
                        "id": item_id,
                        "title": item.title,
                        "type": item.type,  # "movie" or "episode"
                        "year": getattr(item, "year", None),
                    }

                    # Add episode-specific fields if needed
                    if item.type == "episode":
                        media_item["show_title"] = item.grandparentTitle
                        media_item["season"] = item.parentIndex
                        media_item["episode"] = item.index

                    media_items.append(media_item)
                    logger.info(f"✅ Fetched: {media_item['title']}")

                except Exception as e:
                    logger.error(f"❌ Failed to fetch item {item_id}: {e}")
                    # Add error item
                    media_items.append({
                        "id": item_id,
                        "title": f"Unknown Item {item_id}",
                        "type": "error",
                        "error": str(e)
                    })

        import asyncio
        import time

        # Check stop BEFORE processing
        if is_stop_requested():
            logger.warning("🛑 Stopped before processing items")
            return json.dumps({
                "total_processed": 0,
                "items_ready": len(media_items),
                "stopped": True,
                "message": f"Stopped before processing {len(media_items)} items"
            })

        start_time = time.time()

        logger.info(f"🚀 Processing {len(media_items)} items in parallel")

        # Process in parallel using existing parallelization
        # Note: ingest_batch_parallel_conservative should also check stop internally
        results = await ingest_batch_parallel_conservative(media_items)

        duration = time.time() - start_time

        # Check if stopped during processing
        stopped = is_stop_requested()

        # Categorize results
        ingested = [r for r in results if r.get("status") == "success"]
        skipped = [r for r in results if r.get("status") != "success"]

        summary = {
            "total_processed": len(results),
            "ingested_count": len(ingested),
            "skipped_count": len(skipped),
            "ingested": ingested,
            "skipped": skipped,
            "duration": round(duration, 2),
            "mode": "parallel",
            "concurrent_limit": 3,
            "stopped": stopped
        }

        if stopped:
            summary["stop_message"] = "Processing was stopped mid-execution"

        logger.info(
            f"✅ [TOOL] Batch complete: {len(ingested)} ingested, {len(skipped)} skipped in {duration:.2f}s (stopped={stopped})")
        return json.dumps(summary, indent=2)

    except Exception as e:
        logger.error(f"❌ [TOOL] plex_ingest_items failed: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e), "total_processed": 0})

# TOOL 3: Ingest Single Item (Granular Processing)
@mcp.tool()
async def plex_ingest_single(media_id: str) -> str:
    """
    Ingest a single Plex item with STOP SIGNAL support.

    Args:
        media_id: Plex media ID, or "auto" to automatically find one unprocessed item
    """
    logger.info(f"💾 [TOOL] plex_ingest_single called for media_id: {media_id}")

    # Check stop BEFORE starting
    if is_stop_requested():
        logger.warning("🛑 plex_ingest_single: Stop requested - skipping ingestion")
        return json.dumps({
            "title": f"Item {media_id}",
            "id": media_id,
            "status": "stopped",
            "reason": "Stopped before ingestion started"
        })

    try:
        # Handle auto mode
        if media_id == "auto" or media_id.startswith("auto"):
            logger.info("🔍 Auto mode: finding 1 unprocessed item")
            items = find_unprocessed_items(1, False)
            if not items:
                return json.dumps({
                    "title": "No items",
                    "id": "none",
                    "status": "error",
                    "reason": "No unprocessed items found"
                })
            media_item = items[0]
        else:
            # Fetch real item from Plex by ID
            from tools.plex.plex_utils import get_plex_server
            plex = get_plex_server()

            try:
                item = plex.fetchItem(int(media_id))
                media_item = {
                    "id": media_id,
                    "title": item.title,
                    "type": item.type,
                    "year": getattr(item, "year", None),
                }
            except Exception as e:
                logger.error(f"❌ Failed to fetch item {media_id}: {e}")
                return json.dumps({
                    "title": f"Item {media_id}",
                    "id": media_id,
                    "status": "error",
                    "reason": f"Could not fetch item: {str(e)}"
                })

        # Check stop BEFORE processing
        if is_stop_requested():
            logger.warning("🛑 Stopped before processing item")
            return json.dumps({
                "title": media_item.get("title", media_id),
                "id": media_id,
                "status": "stopped",
                "reason": "Stopped before processing"
            })

        # Process the item
        logger.info(f"📥 Extracting subtitles for: {media_item.get('title', media_id)}")
        result = await process_item_async(media_item)

        logger.info(f"✅ [TOOL] Ingested: {result.get('title', 'unknown')}")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"❌ [TOOL] plex_ingest_single failed for {media_id}: {e}")
        return json.dumps({
            "title": f"Item {media_id}",
            "id": media_id,
            "status": "error",
            "reason": str(e)
        })

# TOOL 4: All-in-One Ingestion (Original - Keep for Simple Queries)
@mcp.tool()
async def plex_ingest_batch(limit: int = 5, rescan_no_subtitles: bool = False) -> str:
    """
    Ingest the NEXT unprocessed Plex items into RAG (ALL-IN-ONE).

    This is the ORIGINAL all-in-one tool that combines discovery, extraction,
    and ingestion in one call. Use this for simple single-agent queries.
    For multi-agent workflows, use the granular tools instead:
    - plex_find_unprocessed (discovery)
    - plex_ingest_items (batch parallel)
    - plex_ingest_single (granular parallel)

    Args:
        limit: Number of NEW items to ingest (default: 5)
        rescan_no_subtitles: Re-check items with no subtitles (default: False)

    Returns:
        JSON with complete ingestion report including stats

    Multi-Agent Usage:
        Single-agent mode uses this for simple queries like "Ingest 5 items".
        Multi-agent mode uses granular tools for complex workflows.
    """
    logger.info(f"🛠 [TOOL] plex_ingest_batch called (limit: {limit})")

    try:
        result = await ingest_next_batch(limit, rescan_no_subtitles)
        logger.info(f"✅ [TOOL] plex_ingest_batch completed")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"❌ [TOOL] plex_ingest_batch failed: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)})

# TOOL 5: Get Ingestion Statistics (Monitoring)
@mcp.tool()
def plex_get_stats() -> str:
    """
    Get overall Plex ingestion statistics.

    Returns statistics about the entire Plex library ingestion progress.
    Useful for monitoring and reporting.

    Returns:
        JSON with:
        - total_items: Total items in Plex library
        - successfully_ingested: Items successfully added to RAG
        - missing_subtitles: Items without subtitle files
        - remaining_unprocessed: Items not yet attempted

    Multi-Agent Usage:
        Writer agent can use this to create progress reports or summaries.
    """
    logger.info(f"📊 [TOOL] plex_get_stats called")

    try:
        from tools.rag.rag_storage import get_ingestion_stats

        stats = get_ingestion_stats()

        result = {
            "total_items": stats["total_items"],
            "successfully_ingested": stats["successfully_ingested"],
            "missing_subtitles": stats["missing_subtitles"],
            "remaining_unprocessed": stats["remaining"],
            "completion_percentage": round(
                (stats["successfully_ingested"] / stats["total_items"] * 100)
                if stats["total_items"] > 0 else 0,
                1
            )
        }

        logger.info(f"📊 [TOOL] Stats: {result['completion_percentage']}% complete")
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"❌ [TOOL] plex_get_stats failed: {e}")
        return json.dumps({"error": str(e)})


# ─────────────────────────────────────────────
# A2A tools (with validation)
# ─────────────────────────────────────────────
def get_a2a_endpoint():
    endpoint = os.getenv("A2A_ENDPOINT")
    if not endpoint:
        raise ValueError("A2A_ENDPOINT environment variable is not set")
    return endpoint

def validate_a2a_endpoint(endpoint: str, timeout: float = 5.0) -> dict:
    """
    Validate that the A2A endpoint is reachable and returns a valid agent card.

    Args:
        endpoint: The A2A base URL (e.g., "http://localhost:8010")
        timeout: Request timeout in seconds

    Returns:
        dict with:
        - valid: Boolean indicating if endpoint is valid
        - card: Agent card if valid
        - error: Error message if invalid
    """
    try:
        # Construct the well-known agent card URL
        agent_card_url = f"{endpoint.rstrip('/')}/.well-known/agent-card.json"

        with httpx.Client(timeout=timeout) as client:
            resp = client.get(agent_card_url)
            resp.raise_for_status()
            card = resp.json()

            # Validate card has required fields
            if not isinstance(card, dict):
                return {
                    "valid": False,
                    "error": "Agent card is not a valid JSON object"
                }

            # Check for required fields
            required_fields = ["name", "description", "version"]
            missing_fields = [f for f in required_fields if f not in card]

            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Agent card missing required fields: {', '.join(missing_fields)}"
                }

            # Check for A2A endpoint
            endpoints = card.get("endpoints", {})
            if "a2a" not in endpoints:
                return {
                    "valid": False,
                    "error": "Agent card does not advertise an A2A endpoint"
                }

            return {
                "valid": True,
                "card": card,
                "error": None
            }

    except httpx.TimeoutException:
        return {
            "valid": False,
            "error": f"Connection timeout - A2A server not responding at {endpoint}"
        }
    except httpx.HTTPError as e:
        return {
            "valid": False,
            "error": f"HTTP error connecting to A2A server: {str(e)}"
        }
    except json.JSONDecodeError:
        return {
            "valid": False,
            "error": "A2A server returned invalid JSON"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Failed to validate A2A endpoint: {str(e)}"
        }

if A2A_ENDPOINT:
    logger.info(f"🔍 Validating A2A endpoint: {A2A_ENDPOINT}")
    validation = validate_a2a_endpoint(A2A_ENDPOINT)

    if validation["valid"]:
        A2A_AVAILABLE = True
        logger.info(f"✅ A2A endpoint validated: {validation['card'].get('name', 'Unknown')}")
    else:
        logger.warning(f"⚠️ A2A endpoint validation failed: {validation['error']}")
        logger.warning(f"   A2A tools will not be registered")

if A2A_AVAILABLE:
    @mcp.tool()
    def discover_a2a() -> str:
        """
        Fetch the remote agent's Agent Card from A2A_ENDPOINT.

        Returns:
            JSON string with agent card containing:
            - name: Agent name
            - description: Agent description (includes available tools)
            - version: Agent version
            - capabilities: Available capabilities
            - endpoints: Available A2A endpoints

        Use to discover what tools are available on the remote A2A agent.
        """
        logger.info(f"🛠 [server] discover_a2a called")

        try:
            endpoint = get_a2a_endpoint()

            # Validate endpoint before proceeding
            validation = validate_a2a_endpoint(endpoint)

            if not validation["valid"]:
                logger.error(f"❌ A2A endpoint validation failed: {validation['error']}")
                return json.dumps({
                    "error": validation["error"],
                    "endpoint": endpoint,
                    "suggestion": "Check if the A2A server is running and A2A_ENDPOINT is correct"
                }, indent=2)

            logger.info(f"✅ A2A endpoint validated: {endpoint}")
            return json.dumps(validation["card"], indent=2)

        except ValueError as e:
            logger.error(f"❌ Configuration error: {e}")
            return json.dumps({
                "error": str(e),
                "suggestion": "Set A2A_ENDPOINT environment variable to your A2A server URL"
            }, indent=2)
        except Exception as e:
            logger.error(f"❌ Unexpected error in discover_a2a: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": str(e)}, indent=2)


    @mcp.tool()
    def send_a2a(tool: str, arguments: dict = None) -> str:
        """
        Call a tool on the remote A2A agent.
        ...
        """
        logger.info(f"🛠 [server] send_a2a called with tool: {tool}, arguments: {arguments}")

        try:
            # 1. Get and validate endpoint
            A2A_ENDPOINT = os.getenv("A2A_ENDPOINT", "").strip()
            if not A2A_ENDPOINT:
                return json.dumps({
                    "error": "A2A_ENDPOINT not configured",
                    "suggestion": "Set A2A_ENDPOINT environment variable"
                })

            validation = validate_a2a_endpoint(A2A_ENDPOINT)

            if not validation["valid"]:
                logger.error(f"❌ A2A endpoint validation failed: {validation['error']}")
                return json.dumps({
                    "error": validation["error"],
                    "endpoint": A2A_ENDPOINT,
                    "suggestion": "Check if the A2A server is running"
                }, indent=2)

            card = validation["card"]
            logger.info(f"✅ A2A endpoint validated")

            # 2. Extract RPC endpoint and handle relative URLs
            rpc_url = card.get("endpoints", {}).get("a2a")
            if not rpc_url:
                return json.dumps({"error": "No A2A endpoint in agent card"})

            # Handle relative URLs by joining with base URL
            from urllib.parse import urljoin
            rpc_url = urljoin(A2A_ENDPOINT.rstrip('/') + '/', rpc_url)

            # 3. Build JSON-RPC payload for tool call
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "a2a.call",
                "params": {
                    "tool": tool,
                    "arguments": arguments or {}
                }
            }

            logger.info(f"📤 Calling remote tool '{tool}' via A2A at {rpc_url}")
            logger.debug(f"📤 Payload: {json.dumps(payload, indent=2)}")

            # 4. Send RPC request
            resp = httpx.post(rpc_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # 5. Handle response
            if "error" in data:
                error_msg = data["error"]
                logger.error(f"❌ A2A error: {error_msg}")
                return json.dumps({"error": f"Remote agent error: {error_msg}"})

            result = data.get("result")
            logger.info(f"✅ A2A call successful, result: {str(result)[:200]}...")

            # Return the result as JSON string
            return json.dumps({"success": True, "result": result}, indent=2)

        except httpx.TimeoutException as e:
            logger.error(f"❌ A2A timeout: {e}")
            return json.dumps({
                "error": "Request timed out",
                "suggestion": "A2A server may be overloaded or not responding"
            })
        except httpx.HTTPError as e:
            logger.error(f"❌ A2A HTTP error: {e}")
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "suggestion": "Check A2A server logs for details"
            })
        except Exception as e:
            logger.error(f"❌ A2A call failed: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def send_a2a_streaming(tool: str, arguments: dict = None) -> str:
        """
        Call a tool on the remote A2A agent with STREAMING support.

        This is useful for long-running operations or large responses where you want
        to see progress in real-time.

        Args:
            tool (str, required): Name of the remote MCP tool to call
                Examples: 'plex_ingest_batch', 'rag_search_tool'
            arguments (dict, optional): Arguments to pass to the remote tool

        Returns:
            JSON string with:
            - success: Boolean indicating success
            - result: The complete result from streaming
            - chunks_received: Number of chunks received
            - total_bytes: Total bytes received

        Use for long-running A2A operations where you want real-time progress.
        """
        logger.info(f"🛠 [server] send_a2a_streaming called with tool: {tool}, arguments: {arguments}")

        try:
            # 1. Get and validate endpoint
            A2A_ENDPOINT = os.getenv("A2A_ENDPOINT", "").strip()
            if not A2A_ENDPOINT:
                return json.dumps({
                    "error": "A2A_ENDPOINT not configured",
                    "suggestion": "Set A2A_ENDPOINT environment variable"
                })

            # Use async validation for streaming context
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    card_resp = await client.get(A2A_ENDPOINT)
                    card_resp.raise_for_status()
                    card = card_resp.json()

                    # Quick validation
                    if not isinstance(card, dict) or "endpoints" not in card:
                        return json.dumps({
                            "error": "Invalid agent card received",
                            "endpoint": A2A_ENDPOINT,
                            "suggestion": "Check if A2A server is running"
                        })

                    if "a2a" not in card.get("endpoints", {}):
                        return json.dumps({
                            "error": "Agent card does not advertise an A2A endpoint",
                            "suggestion": "Verify A2A server configuration"
                        })

                    logger.info(f"✅ A2A endpoint validated")

                except httpx.TimeoutException:
                    return json.dumps({
                        "error": "Connection timeout - A2A server not responding",
                        "endpoint": A2A_ENDPOINT,
                        "suggestion": "Check if A2A server is running"
                    })
                except Exception as e:
                    logger.error(f"❌ Endpoint validation failed: {e}")
                    return json.dumps({
                        "error": f"Failed to validate endpoint: {str(e)}",
                        "suggestion": "Check if A2A server is running"
                    })

            # 2. Extract RPC endpoint
            rpc_url = card.get("endpoints", {}).get("a2a")

            # 3. Build JSON-RPC payload
            payload = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "a2a.call",
                "params": {
                    "tool": tool,
                    "arguments": arguments or {}
                }
            }

            logger.info(f"📤 Streaming call to remote tool '{tool}' via A2A at {rpc_url}")

            # 4. Stream the response
            chunks = []
            chunk_count = 0
            total_bytes = 0

            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", rpc_url, json=payload) as response:
                    response.raise_for_status()

                    async for chunk in response.aiter_bytes():
                        if chunk:
                            chunk_str = chunk.decode('utf-8')
                            chunks.append(chunk_str)
                            chunk_count += 1
                            total_bytes += len(chunk)

                            # Log progress every 10 chunks
                            if chunk_count % 10 == 0:
                                logger.info(f"📊 Streaming progress: {chunk_count} chunks, {total_bytes} bytes")

            # 5. Combine and parse response
            full_response = ''.join(chunks)

            logger.info(f"✅ Streaming complete: {chunk_count} chunks, {total_bytes} bytes")

            try:
                data = json.loads(full_response)

                # Handle JSON-RPC error
                if "error" in data:
                    error_msg = data["error"]
                    logger.error(f"❌ A2A error: {error_msg}")
                    return json.dumps({"error": f"Remote agent error: {error_msg}"})

                result = data.get("result")

                return json.dumps({
                    "success": True,
                    "result": result,
                    "chunks_received": chunk_count,
                    "total_bytes": total_bytes
                }, indent=2)

            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse streaming response as JSON: {e}")
                return json.dumps({
                    "error": "Invalid JSON response",
                    "raw_preview": full_response[:500]
                })

        except httpx.TimeoutException as e:
            logger.error(f"❌ A2A streaming timeout: {e}")
            return json.dumps({
                "error": "Request timed out",
                "suggestion": "Increase timeout or check server performance"
            })
        except httpx.HTTPError as e:
            logger.error(f"❌ A2A streaming HTTP error: {e}")
            return json.dumps({
                "error": f"HTTP error: {str(e)}",
                "suggestion": "Check A2A server logs"
            })
        except Exception as e:
            logger.error(f"❌ A2A streaming failed: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": str(e)})

    @mcp.tool()
    async def send_a2a_batch(calls: list) -> str:
        """
        Execute multiple A2A tool calls concurrently.

        Args:
            calls (list, required): List of dicts with 'tool' and 'arguments' keys
                Example: [
                    {"tool": "list_todo_items", "arguments": {}},
                    {"tool": "get_weather_tool", "arguments": {"city": "Vancouver"}}
                ]

        Returns:
            JSON string with array of results, one per call

        Use when you need to call multiple remote tools at once for efficiency.
        """
        logger.info(f"🛠 [server] send_a2a_batch called with {len(calls)} calls")

        if not isinstance(calls, list):
            return json.dumps({"error": "calls must be a list"})

        # Validate calls
        for i, call in enumerate(calls):
            if not isinstance(call, dict) or "tool" not in call:
                return json.dumps({"error": f"Call {i} missing 'tool' key"})

        # Validate endpoint once for all calls
        try:
            A2A_ENDPOINT = os.getenv("A2A_ENDPOINT", "").strip()
            if not A2A_ENDPOINT:
                return json.dumps({
                    "error": "A2A_ENDPOINT not configured",
                    "suggestion": "Set A2A_ENDPOINT environment variable"
                })

            validation = validate_a2a_endpoint(A2A_ENDPOINT)

            if not validation["valid"]:
                logger.error(f"❌ A2A endpoint validation failed: {validation['error']}")
                return json.dumps({
                    "error": validation["error"],
                    "suggestion": "Check if A2A server is running"
                })

            logger.info(f"✅ A2A endpoint validated for batch operation")

        except Exception as e:
            return json.dumps({"error": f"Endpoint validation failed: {str(e)}"})

        try:
            # Execute all calls concurrently
            async def execute_call(call):
                tool = call["tool"]
                args = call.get("arguments", {})

                try:
                    # Use the non-streaming version for batch
                    result_json = send_a2a(tool, args)
                    result = json.loads(result_json)
                    return {
                        "tool": tool,
                        "success": result.get("success", False),
                        "result": result.get("result"),
                        "error": result.get("error")
                    }
                except Exception as e:
                    logger.error(f"❌ Batch call to {tool} failed: {e}")
                    return {
                        "tool": tool,
                        "success": False,
                        "error": str(e)
                    }

            # Run all calls concurrently
            results = await asyncio.gather(*[execute_call(call) for call in calls])

            logger.info(f"✅ Batch A2A complete: {len(results)} results")

            return json.dumps({
                "success": True,
                "results": results,
                "total_calls": len(calls)
            }, indent=2)

        except Exception as e:
            logger.error(f"❌ Batch A2A failed: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logger.info(f"🛠 [server] mcp server running with stdio enabled")
    mcp.run(transport="stdio")