import json
import math
from pathlib import Path
from collections import Counter, defaultdict

KB_DIR = Path("knowledge/entries")

def tokenize(text):
    return [w.lower() for w in text.split()]

def compute_tf(tokens):
    count = Counter(tokens)
    total = len(tokens)
    return {word: count[word] / total for word in count}

def compute_idf(all_docs):
    idf = {}
    total_docs = len(all_docs)

    # Count documents containing each word
    doc_freq = defaultdict(int)
    for doc in all_docs:
        for word in set(doc):
            doc_freq[word] += 1

    # Compute IDF
    for word, df in doc_freq.items():
        idf[word] = math.log((total_docs + 1) / (df + 1)) + 1

    return idf

def compute_tfidf(tf, idf):
    return {word: tf[word] * idf.get(word, 0) for word in tf}

def cosine_similarity(vec1, vec2):
    # Dot product
    dot = sum(vec1.get(w, 0) * vec2.get(w, 0) for w in vec1)

    # Magnitudes
    mag1 = math.sqrt(sum(v * v for v in vec1.values()))
    mag2 = math.sqrt(sum(v * v for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)

def kb_search_semantic(query, top_k=5):
    entries = []
    docs = []

    # Load entries and tokenize content
    for file in KB_DIR.glob("*.json"):
        with open(file) as f:
            entry = json.load(f)
            entries.append(entry)
            docs.append(tokenize(entry["content"]))

    if not entries:
        return []

    # Compute IDF across all documents
    idf = compute_idf(docs)

    # Compute TF-IDF for each document
    doc_vectors = []
    for tokens in docs:
        tf = compute_tf(tokens)
        tfidf = compute_tfidf(tf, idf)
        doc_vectors.append(tfidf)

    # Compute TF-IDF for query
    query_tokens = tokenize(query)
    query_tf = compute_tf(query_tokens)
    query_vec = compute_tfidf(query_tf, idf)

    # Score documents
    scored = []
    for entry, vec in zip(entries, doc_vectors):
        score = cosine_similarity(query_vec, vec)
        scored.append((score, entry))

    # Sort by similarity
    scored.sort(key=lambda x: x[0], reverse=True)

    return [entry for score, entry in scored[:top_k]]
