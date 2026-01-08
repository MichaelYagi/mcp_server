import lancedb
import pyarrow as pa

db = lancedb.connect("./rag_db")

# Define schema explicitly
schema = pa.schema([
    ("id", pa.string()),
    ("text", pa.string()),
    ("embedding", pa.list_(pa.float32()))
])

# Create or open table safely
if "kb" in db.table_names():
    table = db.open_table("kb")
else:
    table = db.create_table(
        "kb",
        schema=schema,
        mode="create"
    )


def add_document(doc_id, text, embedding):
    table.add([{
        "id": doc_id,
        "text": text,
        "embedding": embedding
    }])


def search(query_embedding, k=5):
    results = table.search(query_embedding).limit(k).to_list()
    return [r["text"] for r in results]
