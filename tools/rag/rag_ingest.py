import lancedb
from .chunk_text import chunk_text
from .embed_text import embed_text

# Limits
MAX_TEXT_CHARS = 20_000      # hard cap on input text length
MAX_CHUNKS = 500             # hard cap on number of chunks per ingestion

# Connect to LanceDB
db = lancedb.connect("./rag_db")

# Create or open table
try:
    table = db.open_table("rag")
except:
    table = db.create_table(
        "rag",
        data=[],
        mode="overwrite"
    )


def ingest_text_document(doc_id: str, text: str) -> dict:
    """
    Ingest a single text document into LanceDB with safety limits.

    Returns a dict with metadata about the ingestion:
    {
      "doc_id": ...,
      "truncated": bool,
      "num_chunks": int,
      "limited_by": "text_length" | "chunk_count" | None
    }
    """

    # Enforce character limit
    truncated = False
    limited_by = None

    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
        truncated = True
        limited_by = "text_length"

    # Chunk
    chunks = chunk_text(text)["chunks"]

    # Enforce chunk limit
    if len(chunks) > MAX_CHUNKS:
        chunks = chunks[:MAX_CHUNKS]
        truncated = True
        limited_by = "chunk_count"

    if not chunks:
        return {
            "doc_id": doc_id,
            "truncated": truncated,
            "num_chunks": 0,
            "limited_by": limited_by,
            "status": "no_chunks"
        }

    # Embed
    vectors = embed_text(chunks)["vectors"]

    # Prepare rows
    rows = []
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        rows.append({
            "id": f"{doc_id}-{i}",
            "doc_id": doc_id,
            "text": chunk,
            "vector": vec,
        })

    # Insert into LanceDB
    table.add(rows)

    return {
        "doc_id": doc_id,
        "truncated": truncated,
        "num_chunks": len(rows),
        "limited_by": limited_by,
        "status": "ok"
    }
