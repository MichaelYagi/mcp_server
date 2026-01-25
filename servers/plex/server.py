"""
Plex MCP Server
Runs over stdio transport
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from servers.skills.skill_loader import SkillLoader

import inspect
import json
import logging
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

# Fix ML recommender import - use absolute path
sys.path.insert(0, str(Path(__file__).parent))
from ml_recommender import get_recommender

from client.stop_signal import is_stop_requested
from tools.plex.semantic_media_search import semantic_media_search
from tools.plex.scene_locator import scene_locator
from tools.plex.ingest import ingest_next_batch, ingest_batch_parallel_conservative, find_unprocessed_items, process_item_async

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
logging.getLogger("mcp_plex_server").setLevel(logging.INFO)

logger = logging.getLogger("mcp_plex_server")
logger.info("🚀 Server logging initialized - writing to logs/mcp-server.log")

mcp = FastMCP("plex-server")

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

    Example:
        item_ids=["4699", "4700"]

    Note: Get IDs from plex_find_unprocessed first
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

skill_registry = None

@mcp.tool()
def list_skills() -> str:
    """List all available skills for this server."""
    logger.info(f"🛠  list_skills called")
    if skill_registry is None:
        return json.dumps({
            "server": "plex-server",
            "skills": [],
            "message": "Skills not loaded"
        }, indent=2)

    return json.dumps({
        "server": "plex-server",
        "skills": skill_registry.list()
    }, indent=2)


@mcp.tool()
def read_skill(skill_name: str) -> str:
    """Read the full content of a skill."""
    logger.info(f"🛠  read_skill called")

    if skill_registry is None:
        return json.dumps({"error": "Skills not loaded"}, indent=2)

    content = skill_registry.get_skill_content(skill_name)
    if content:
        return content

    available = [s.name for s in skill_registry.skills.values()]
    return json.dumps({
        "error": f"Skill '{skill_name}' not found",
        "available_skills": available
    }, indent=2)

def get_tool_names_from_module():
    """Extract all function names from current module (auto-discovers tools)"""
    current_module = sys.modules[__name__]
    tool_names = []

    for name, obj in inspect.getmembers(current_module):
        if inspect.isfunction(obj) and obj.__module__ == __name__:
            if not name.startswith('_') and name != 'get_tool_names_from_module':
                tool_names.append(name)

    return tool_names


# ============================================================================
# ML RECOMMENDATION TOOLS
# ============================================================================

@mcp.tool()
def import_plex_history(limit: int = 50) -> dict:
    """
    Automatically import your Plex viewing history into the ML recommender

    This tool:
    1. Fetches your recently watched items from Plex
    2. Automatically records them as viewing events
    3. Returns stats on what was imported

    Args:
        limit: Number of recent items to import (default: 50)

    Returns:
        Stats on imported viewing history
    """
    logger.info(f"📥 Importing Plex viewing history (limit: {limit})")

    try:
        from tools.plex.plex_utils import get_plex_server

        plex = get_plex_server()
        recommender = get_recommender()

        # Get watch history from Plex
        # This gets items you've actually watched
        history = plex.history(maxresults=limit)

        imported_count = 0
        skipped_count = 0
        errors = []

        for item in history:
            try:
                # Extract metadata
                title = item.title
                year = getattr(item, 'year', 2020)

                # Get genre (first one if multiple)
                genres = getattr(item, 'genres', [])
                genre = genres[0].tag if genres else "Unknown"

                # Get rating
                rating = getattr(item, 'rating', 7.0)
                if rating is None:
                    rating = 7.0

                # Get runtime in minutes
                duration = getattr(item, 'duration', 0)
                runtime = int(duration / 60000) if duration else 120  # Convert ms to minutes

                # Check if fully watched (viewCount > 0 means finished)
                view_count = getattr(item, 'viewCount', 0)
                finished = view_count > 0

                # Record it
                recommender.record_view(title, genre, year, rating, runtime, finished)
                imported_count += 1

                logger.info(f"✅ Imported: {title} ({genre}, {year}) - {'Finished' if finished else 'Abandoned'}")

            except Exception as e:
                logger.error(f"❌ Failed to import {item.title}: {e}")
                skipped_count += 1
                errors.append(f"{item.title}: {str(e)}")

        # Get updated stats
        stats = recommender.get_stats()

        result = {
            "imported": imported_count,
            "skipped": skipped_count,
            "total_views_now": stats['total_views'],
            "can_train": stats['total_views'] >= 20,
            "errors": errors[:5]  # First 5 errors only
        }

        response = f"""
📥 Plex History Import Complete!

✅ Imported: {imported_count} viewing events
❌ Skipped: {skipped_count} items
📊 Total viewing history: {stats['total_views']}

"""

        if result['can_train']:
            response += "🎯 You have enough data! Run train_recommender() now!"
        else:
            needed = 20 - stats['total_views']
            response += f"📝 Need {needed} more views to train"

        logger.info(f"✅ Import complete: {imported_count} imported, {skipped_count} skipped")

        return {"message": response, **result}

    except Exception as e:
        logger.error(f"❌ Failed to import Plex history: {e}")
        return {
            "message": f"❌ Error importing Plex history: {str(e)}",
            "imported": 0,
            "error": str(e)
        }


@mcp.tool()
def auto_train_from_plex(import_limit: int = 50) -> dict:
    """
    ONE-CLICK: Import Plex history AND train the model automatically

    This convenience tool:
    1. Imports your recent Plex viewing history
    2. Automatically trains the ML model if enough data
    3. Returns training results

    Args:
        import_limit: Number of recent items to import (default: 50)

    Returns:
        Combined import + training results
    """
    logger.info("🚀 Auto-training from Plex history")

    # Step 1: Import history
    import_result = import_plex_history(import_limit)

    if import_result.get('imported', 0) == 0:
        return {
            "message": "❌ No viewing history imported. Cannot train.",
            "import_result": import_result
        }

    # Step 2: Auto-train if we have enough data
    if import_result.get('can_train', False):
        logger.info("✅ Enough data - auto-training model")
        train_result = train_recommender()

        combined_message = f"""
🎉 Auto-Training Complete!

📥 Import Stats:
   • Imported: {import_result['imported']} viewing events
   • Total history: {import_result['total_views_now']}

{train_result.get('message', '')}
"""

        return {
            "message": combined_message,
            "import_result": import_result,
            "train_result": train_result,
            "status": "success"
        }
    else:
        return {
            "message": f"""
📥 Imported {import_result['imported']} items

❌ Not enough data to train yet
   Current: {import_result['total_views_now']}
   Need: {20 - import_result['total_views_now']} more

Import more history or wait until you've watched more!
""",
            "import_result": import_result,
            "status": "insufficient_data"
        }


@mcp.tool()
def record_viewing(
        title: str,
        genre: str,
        year: int,
        rating: float,
        runtime: int,
        finished: bool = True
) -> dict:
    """
    Record that you watched something (for ML training)

    Args:
        title: Movie/show title (e.g. "The Matrix")
        genre: Genre (Action, Comedy, Drama, SciFi, Horror, etc.)
        year: Release year (e.g. 1999)
        rating: IMDb/audience rating 0-10 (e.g. 8.7)
        runtime: Runtime in minutes (e.g. 136)
        finished: Did you finish it? True=yes, False=abandoned

    Examples:
        - record_viewing("The Matrix", "SciFi", 1999, 8.7, 136, True)
        - record_viewing("Boring Movie", "Drama", 2020, 5.2, 145, False)
    """
    recommender = get_recommender()
    result = recommender.record_view(title, genre, year, rating, runtime, finished)

    response = f"✅ Recorded: {title}\n"
    response += f"Total views in history: {result['total_views']}\n"

    if result['can_train']:
        response += "\n🎯 You have enough data to train! Use train_recommender()"
    else:
        needed = 20 - result['total_views']
        response += f"\n📊 Need {needed} more views to train ML model"

    return {"message": response, **result}


@mcp.tool()
def train_recommender() -> dict:
    """
    Train the ML recommendation model on your viewing history

    Run this after you've recorded 20+ viewing events.
    The model learns what you like based on what you finish watching.

    Returns:
        Training results including accuracy and model info
    """
    recommender = get_recommender()
    result = recommender.train()

    if result['status'] == 'success':
        response = f"""
🎉 Training Complete!

📊 Stats:
   • Training samples: {result['training_samples']}
   • Train accuracy: {result['train_accuracy']}
   • Test accuracy: {result['test_accuracy']}

✅ Model saved to: {result['model_path']}

Now use recommend_content() to get personalized recommendations!
"""
    elif result['status'] == 'insufficient_data':
        response = f"""
❌ Not enough data yet

Current views: {result['current_views']}
Need: {result['views_needed']} more views

Keep recording what you watch with record_viewing()!
"""
    else:
        response = f"❌ {result['message']}"

    return {"message": response, **result}


@mcp.tool()
def recommend_content(
        available_items: list[dict]
) -> dict:
    """
    Get ML-powered recommendations from a list of items

    Each item should have: title, genre, year, rating, runtime
    Returns items ranked by predicted enjoyment (best first)

    Args:
        available_items: List of content to rank
            Example: [
                {"title": "Movie A", "genre": "Action", "year": 2023, "rating": 7.5, "runtime": 120},
                {"title": "Movie B", "genre": "Drama", "year": 2022, "rating": 8.2, "runtime": 145}
            ]

    Returns:
        Items ranked by ML score (best matches first)
    """
    recommender = get_recommender()
    result = recommender.predict_enjoyment(available_items)

    if result['status'] == 'no_model':
        return {
            "message": "❌ No trained model. Record viewing history and train first!",
            "status": "error"
        }

    # Format nice response
    response = "🎬 ML Recommendations (Best First):\n\n"

    for item in result['items'][:10]:  # Top 10
        score_pct = f"{item['ml_score']:.0%}"
        response += f"{item['ml_rank']}. {item['title']} ({item['year']})\n"
        response += f"   Genre: {item['genre']} | Rating: {item['rating']}/10\n"
        response += f"   ML Score: {score_pct} | Runtime: {item['runtime']}min\n\n"

    return {
        "message": response,
        "recommendations": result['items'],
        "status": "success"
    }


@mcp.tool()
def get_recommender_stats() -> dict:
    """
    Get statistics about your recommendation system

    Shows:
        - Whether model is trained
        - Total viewing history
        - Genres you've watched
        - Average ratings
        - Finish rate
    """
    recommender = get_recommender()
    stats = recommender.get_stats()

    response = f"""
📊 Recommender Statistics

Model Status: {'✅ Trained' if stats['model_trained'] else '❌ Not trained yet'}
Total Views: {stats['total_views']}
Genres Watched: {', '.join(stats['genres_seen']) if stats['genres_seen'] else 'None yet'}
Avg Rating: {stats['avg_rating']:.1f}/10
Finish Rate: {stats['finish_rate']}

"""

    if not stats['model_trained'] and stats['total_views'] >= 20:
        response += "💡 You have enough data! Run train_recommender()"
    elif not stats['model_trained']:
        response += f"📝 Record {20 - stats['total_views']} more views to enable training"

    return {"message": response, **stats}


@mcp.tool()
def reset_recommender() -> dict:
    """
    ⚠️ DANGER: Clear all viewing history and retrain from scratch

    This deletes:
        - All viewing history
        - Trained model
        - All encoders

    Use this if you want to start fresh.
    """
    recommender = get_recommender()
    result = recommender.reset()

    return {
        "message": "🗑️  All recommendation data cleared. Start fresh with record_viewing()",
        **result
    }

if __name__ == "__main__":
    # Auto-extract tool names - NO manual list needed!
    server_tools = get_tool_names_from_module()

    # Load skills
    skills_dir = Path(__file__).parent / "skills"
    loader = SkillLoader(server_tools)
    skill_registry = loader.load_all(skills_dir)

    logger.info(f"🛠  {len(server_tools)} tools: {', '.join(server_tools)}")
    logger.info(f"🛠  {len(skill_registry.skills)} skills loaded")
    mcp.run(transport="stdio")