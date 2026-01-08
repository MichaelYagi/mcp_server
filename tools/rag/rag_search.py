from langchain_ollama import OllamaEmbeddings
from .vector_store import search

embedder = OllamaEmbeddings(model="bge-base")

def rag_search(query: str):
    query_embedding = embedder.embed_query(query)
    results = search(query_embedding, k=5)
    return {"chunks": results["documents"][0]}
