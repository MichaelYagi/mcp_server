from langchain_ollama import OllamaEmbeddings
from .vector_store import add_document

embedder = OllamaEmbeddings(model="bge-base")

def rag_add(text: str):
    embedding = embedder.embed_query(text)
    doc_id = str(hash(text))
    add_document(doc_id, text, embedding)
    return {"status": "ok", "id": doc_id}
