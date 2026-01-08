import os
import json
from pathlib import Path

from tools.rag.rag_add import rag_add
from tools.plex.scene_locator import _plex_get, _plex_download, _parse_srt
from tools.plex.semantic_media_search import _tokenize  # reuse tokenizer

PROGRESS_FILE = Path("plex_ingest_progress.json")


# ------------------------------------------------------------
# Progress tracking
# ------------------------------------------------------------
def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except:
            return {}
    return {}


def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


# ------------------------------------------------------------
# Chunking (reusing your tokenizer)
# ------------------------------------------------------------
def chunk_text(text, size=800, overlap=100):
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0

    return chunks


# ------------------------------------------------------------
# Metadata extraction (aligned with your semantic index)
# ------------------------------------------------------------
def extract_metadata(item):
    title = item.get("title", "")
    summary = item.get("summary", "")
    year = item.get("year", "")
    genres = [g["tag"] for g in item.get("Genre", [])]
    cast = [r["tag"] for r in item.get("Role", [])]

    parts = [
        f"Title: {title} ({year})",
        f"Summary: {summary}",
        f"Genres: {', '.join(genres)}",
        f"Cast: {', '.join(cast)}"
    ]

    return "\n".join([p for p in parts if p.strip()])


# ------------------------------------------------------------
# Subtitle extraction (using your existing subtitle logic)
# ------------------------------------------------------------
def extract_subtitles(rating_key):
    meta = _plex_get(f"/library/metadata/{rating_key}")
    media = meta["MediaContainer"]["Metadata"][0]

    subtitle_url = None

    for media_part in media.get("Media", []):
        for part in media_part.get("Part", []):
            for stream in part.get("Stream", []):
                if stream.get("streamType") == 3:
                    subtitle_url = stream.get("key")
                    break

    if not subtitle_url:
        return ""

    raw = _plex_download(subtitle_url)
    entries = _parse_srt(raw)

    if not entries:
        return ""

    # Combine all subtitle text into one block
    return " ".join([e["text"] for e in entries])


# ------------------------------------------------------------
# Main ingestion batch
# ------------------------------------------------------------
def ingest_next_batch(limit=5):
    progress = load_progress()

    # Fetch all Plex media using your semantic index fetcher
    from tools.plex.semantic_media_search import _fetch_all_media
    items = _fetch_all_media()

    unprocessed = [i for i in items if str(i["id"]) not in progress]
    batch = unprocessed[:limit]

    ingested_titles = []

    for item in batch:
        rating_key = str(item["id"])

        # Extract metadata
        meta_text = extract_metadata