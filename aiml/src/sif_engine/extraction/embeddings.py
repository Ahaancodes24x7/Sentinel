"""Sentence-transformer embeddings for similarity, retrieval and clustering.

Used for (i) nearest-neighbour label suggestion during annotation / active
learning and (ii) the precursor-clustering step — deliberately NOT as the
primary classifier, because embeddings alone cannot give the auditable
field-level extraction an HSE reviewer needs.

The model is loaded lazily and cached. If the transformer is unavailable
(offline first run, no cache), this module degrades to a hashed
character-n-gram TF-IDF projection rather than raising: the clustering layer
must still produce *something* inspectable on an air-gapped OIL deployment.
Callers can check :func:`backend_name` to report which path was used, so the
dashboard never silently misrepresents which model produced a result.
"""

from __future__ import annotations

import threading
from typing import Optional, Sequence

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_backend = "uninitialised"
_fallback_vectorizer = None
_lock = threading.Lock()


def _load_model(model_name: str = DEFAULT_MODEL):
    """Load (once) the sentence-transformer, or fall back to TF-IDF."""
    global _model, _backend
    if _model is not None or _backend == "tfidf-fallback":
        return _model
    with _lock:
        if _model is not None or _backend == "tfidf-fallback":
            return _model
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(model_name)
            _backend = f"sentence-transformers:{model_name}"
        except Exception:
            _model = None
            _backend = "tfidf-fallback"
    return _model


def backend_name() -> str:
    """Which embedding backend is actually in use — surfaced in model status."""
    if _backend == "uninitialised":
        _load_model()
    return _backend


def _fallback_embed(texts: Sequence[str]) -> np.ndarray:
    """Deterministic char-n-gram TF-IDF + SVD projection.

    Not as good as SBERT, but it is offline, dependency-light and — critically
    — still groups paraphrases better than bag-of-words alone.
    """
    global _fallback_vectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import Normalizer

    texts = list(texts)
    if _fallback_vectorizer is None:
        n_components = max(2, min(128, len(texts) - 1)) if len(texts) > 2 else 2
        _fallback_vectorizer = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1, max_features=20000),
            TruncatedSVD(n_components=n_components, random_state=42),
            Normalizer(copy=False),
        )
        return np.asarray(_fallback_vectorizer.fit_transform(texts), dtype=np.float32)
    return np.asarray(_fallback_vectorizer.transform(texts), dtype=np.float32)


def embed(texts: Sequence[str], model_name: str = DEFAULT_MODEL,
          batch_size: int = 64, normalize: bool = True) -> np.ndarray:
    """Embed a sequence of texts. Returns an (n, dim) float32 array."""
    texts = [t if isinstance(t, str) else "" for t in texts]
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)

    model = _load_model(model_name)
    if model is None:
        return _fallback_embed(texts)

    vecs = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
        show_progress_bar=False,
    )
    return np.asarray(vecs, dtype=np.float32)


def cosine_similarity_matrix(a: np.ndarray, b: Optional[np.ndarray] = None) -> np.ndarray:
    """Pairwise cosine similarity, safe against zero-norm rows."""
    b = a if b is None else b
    an = a / np.clip(np.linalg.norm(a, axis=1, keepdims=True), 1e-9, None)
    bn = b / np.clip(np.linalg.norm(b, axis=1, keepdims=True), 1e-9, None)
    return an @ bn.T


def most_similar(query: str, corpus_embeddings: np.ndarray, k: int = 5,
                 model_name: str = DEFAULT_MODEL) -> list[tuple[int, float]]:
    """Return the ``k`` most similar corpus rows as (index, cosine_similarity)."""
    if corpus_embeddings is None or len(corpus_embeddings) == 0:
        return []
    q = embed([query], model_name=model_name)
    sims = cosine_similarity_matrix(q, corpus_embeddings)[0]
    k = int(min(k, len(sims)))
    idx = np.argpartition(-sims, k - 1)[:k]
    idx = idx[np.argsort(-sims[idx])]
    return [(int(i), float(sims[i])) for i in idx]


__all__ = [
    "embed",
    "most_similar",
    "cosine_similarity_matrix",
    "backend_name",
    "DEFAULT_MODEL",
]
