"""Sentence-transformer wrapper (SBERT, all-MiniLM-L6-v2 or multilingual variant) for similarity/retrieval used by clustering and active learning. Exposes embed(texts: list[str]) -> np.ndarray and most_similar(query: str, corpus_embeddings, k: int)."""

def embed(texts: list[str]):
    """Embed a sequence of texts."""
    raise NotImplementedError

def most_similar(query: str, corpus_embeddings, k: int):
    """Return the k most similar corpus entries."""
    raise NotImplementedError