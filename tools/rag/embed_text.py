from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(texts: list[str]):
    vectors = model.encode(texts).tolist()
    return {"vectors": vectors}
