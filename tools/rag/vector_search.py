import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer
import pandas as pd

# Connect to LanceDB
db = lancedb.connect("./rag_db")

# Define schema explicitly so LanceDB can create an empty table
schema = pa.schema([
    ("id", pa.string()),
    ("doc_id", pa.string()),
    ("text", pa.string()),
    ("vector", pa.list_(pa.float32()))
])

# Try to open table, otherwise create it
try:
    table = db.open_table("rag")
except:
    table = db.create_table("rag", schema=schema)

# Embedding model for queries
model = SentenceTransformer("all-MiniLM-L6-v2")

def vector_search(query: str, top_k: int = 5):
    """
    Search the RAG vector store using LanceDB.
    """
    # Embed the query
    q_vec = model.encode([query])[0].tolist()

    # Perform vector search
    results = table.search(q_vec).limit(top_k).to_pandas()

    formatted = []
    for _, row in results.iterrows():
        formatted.append({
            "id": row["id"],
            "doc_id": row["doc_id"],
            "text": row["text"],
            "score": float(row["_distance"])
        })

    return {"results": formatted}
