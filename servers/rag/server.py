"""
RAG MCP Server
Runs over stdio transport
"""
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from client.stop_signal import is_stop_requested
from tools.plex import ingest_next_batch
from tools.rag.rag_add import rag_add
from tools.rag.rag_search import rag_search
from tools.rag.rag_diagnose import diagnose_rag

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
file_handler = logging.FileHandler(LOG_DIR / "mcp_rag_server.log", encoding="utf-8")
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
logging.getLogger("mcp_rag_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_rag_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp_rag_server.log")

mcp = FastMCP("rag-server")

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

if __name__ == "__main__":
    logger.info(f"🛠 [server] rag-server running with stdio enabled")
    mcp.run(transport="stdio")