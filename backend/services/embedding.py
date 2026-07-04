import threading

from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_model = None
_lock = threading.Lock()


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model
