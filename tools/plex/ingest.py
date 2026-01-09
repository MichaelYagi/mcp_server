import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("mcp_server")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROGRESS_FILE = PROJECT_ROOT / "data" / "plex_ingest_progress.json"
PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Import Plex utilities
from .plex_utils import stream_all_media, extract_metadata, stream_subtitles, chunk_stream

# Import RAG add function
from tools.rag.rag_add import rag_add


def load_progress() -> Dict[str, bool]:
    """Load ingestion progress from disk"""
    if not PROGRESS_FILE.exists():
        return {}

    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_progress(progress: Dict[str, bool]) -> None:
    """Save ingestion progress to disk"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def ingest_next_batch(limit: int = 5) -> Dict[str, Any]:
    """
    Ingest the next batch of Plex items into RAG.

    Args:
        limit: Maximum number of items to ingest

    Returns:
        Dictionary with ingested items, remaining count, and total ingested
    """
    try:
        progress = load_progress()
        ingested = []
        remaining = 0
        count = 0

        media_stream = stream_all_media()

        for item in media_stream:
            rating_key = str(item["id"])

            # Skip already ingested items
            if rating_key in progress:
                continue

            # Count remaining items after limit
            if count >= limit:
                remaining += 1
                continue

            logger.info(f"📀 Ingesting: {item['title']}")

            # 1. Add metadata to RAG
            meta_text = extract_metadata(item)
            rag_add(
                text=meta_text,
                source=f"plex:metadata:{rating_key}",
                chunk_size=200
            )

            # 2. Add subtitles to RAG (if available)
            try:
                subtitle_chunks = list(chunk_stream(stream_subtitles(rating_key)))

                if subtitle_chunks:
                    for chunk in subtitle_chunks:
                        rag_add(
                            text=chunk,
                            source=f"plex:subtitles:{rating_key}",
                            chunk_size=500
                        )
                    logger.info(f"  ✓ Added {len(subtitle_chunks)} subtitle chunks")
                else:
                    logger.info(f"  ⚠ No subtitles found")

            except Exception as e:
                logger.warning(f"  ⚠ Could not process subtitles: {e}")

            # Mark as ingested
            progress[rating_key] = True
            ingested.append(item["title"])
            count += 1

        # Save progress
        save_progress(progress)

        logger.info(f"✅ Ingested {len(ingested)} items, {remaining} remaining")

        return {
            "ingested": ingested,
            "remaining": remaining,
            "total_ingested": len(progress)  # Add this line
        }

    except Exception as e:
        logger.error(f"❌ Error in ingest_next_batch: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "ingested": [],
            "remaining": 0,
            "total_ingested": 0  # Add this line
        }