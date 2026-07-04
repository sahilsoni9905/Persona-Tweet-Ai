import json
from pathlib import Path

import chromadb

import config
from services.embedding import get_embedding_model

CHROMA_DIR = config.DATA_DIR / "chroma_store"
CLUSTERED_PATH = config.DATA_DIR / "tweets_with_clusters.json"
COLLECTION_NAME = "tweets"

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
_collection = _client.get_or_create_collection(COLLECTION_NAME)


def add_tweet(tweet_id: str, text: str, cluster: int, embedding=None, source: str = "own"):
    if embedding is None:
        embedding = get_embedding_model().encode(text).tolist()
    _collection.upsert(
        ids=[f"{source}-{tweet_id}"],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"cluster": cluster, "source": source}],
    )


def add_reply_tweet(tweet_id: str, text: str, embedding=None):
    if embedding is None:
        embedding = get_embedding_model().encode(text).tolist()
    _collection.upsert(
        ids=[f"reply-{tweet_id}"],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"cluster": -1, "source": "reply"}],
    )


def add_reference_post(tweet_id: str, text: str, note: str = ""):
    embedding = get_embedding_model().encode(text).tolist()
    _collection.upsert(
        ids=[f"reference-{tweet_id}"],
        embeddings=[embedding],
        documents=[text],
        metadatas=[{"cluster": -1, "source": "reference", "note": note}],
    )


def query_similar(text: str, k: int = 5) -> list[dict]:
    embedding = get_embedding_model().encode(text).tolist()
    results = _collection.query(query_embeddings=[embedding], n_results=k)
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]


def query_reply_style(text: str, k: int = 5) -> list[dict]:
    try:
        embedding = get_embedding_model().encode(text).tolist()
        results = _collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where={"source": "reply"},
        )
        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(
                results["documents"][0], results["metadatas"][0], results["distances"][0]
            )
        ]
    except Exception:
        return []


def clear_own_tweets():
    _collection.delete(where={"source": "own"})


def clear_reply_tweets():
    _collection.delete(where={"source": "reply"})


def build_index_from_file(path: Path = CLUSTERED_PATH):
    with open(path, encoding="utf-8") as f:
        tweets = json.load(f)
    for tweet in tweets:
        add_tweet(tweet["id"], tweet["text"], tweet["cluster"], embedding=tweet.get("embedding"))
    return len(tweets)


def get_corpus_stats() -> dict:
    def _count(source: str) -> int:
        try:
            return len(_collection.get(where={"source": source})["ids"])
        except Exception:
            return 0
    return {
        "own_posts": _count("own") + _count("manual"),
        "reply_examples": _count("reply"),
        "references": _count("reference"),
    }
