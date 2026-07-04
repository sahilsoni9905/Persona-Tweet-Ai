import json

from fastapi import APIRouter, File, HTTPException, UploadFile

import config
from models.schemas import PostRequest
from services.clustering import cluster_embeddings, embed_tweets
from services.embedding import get_embedding_model
from services.poster import post_tweet
from services.preprocessing import clean_tweets
from services.scorer import train as train_scorer
from services.style_index import (
    add_reply_tweet,
    build_index_from_file,
    clear_own_tweets,
    clear_reply_tweets,
    get_corpus_stats,
)
from utils.archive import import_from_folder

router = APIRouter()


def _process_posts(posts: list[dict]) -> dict:
    cleaned = clean_tweets(posts)
    if not cleaned:
        return {"cleaned_count": 0, "cluster_count": 0, "indexed_count": 0, "scorer_metrics": None}

    model = get_embedding_model()
    embeddings = embed_tweets(cleaned, model)
    labels = cluster_embeddings(embeddings)
    for tweet, embedding, label in zip(cleaned, embeddings, labels):
        tweet["cluster"] = int(label)
        tweet["embedding"] = embedding.tolist()

    (config.DATA_DIR / "clean_tweets.json").write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    (config.DATA_DIR / "tweets_with_clusters.json").write_text(json.dumps(cleaned, indent=2), encoding="utf-8")

    clear_own_tweets()
    indexed_count = build_index_from_file()
    scorer_metrics = train_scorer()

    return {
        "cleaned_count": len(cleaned),
        "cluster_count": len(set(labels)),
        "indexed_count": indexed_count,
        "scorer_metrics": scorer_metrics,
    }


def _process_replies(replies: list[dict]) -> int:
    if not replies:
        return 0
    model = get_embedding_model()
    texts = [r["text"] for r in replies]
    embeddings = model.encode(texts)
    clear_reply_tweets()
    for reply, emb in zip(replies, embeddings):
        add_reply_tweet(reply["id"], reply["text"], emb.tolist())
    return len(replies)


@router.post("/tweets/import_archive")
def import_archive():
    if not config.ARCHIVE_DIR.exists():
        raise HTTPException(
            404,
            f"my_twitter_data/ folder not found. "
            f"Place your extracted X archive at: backend/my_twitter_data/",
        )
    try:
        data = import_from_folder(config.ARCHIVE_DIR)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    posts = data["posts"]
    replies = data["replies"]

    (config.DATA_DIR / "raw_tweets.json").write_text(
        json.dumps(posts, indent=2), encoding="utf-8"
    )

    post_result = _process_posts(posts)
    replies_indexed = _process_replies(replies)

    return {
        "posts_raw": len(posts),
        "posts_cleaned": post_result["cleaned_count"],
        "cluster_count": post_result["cluster_count"],
        "posts_indexed": post_result["indexed_count"],
        "replies_indexed": replies_indexed,
        "scorer_metrics": post_result["scorer_metrics"],
    }


@router.post("/tweets/import")
def import_tweets(file: UploadFile = File(...)):
    raw_tweets = json.loads(file.file.read())
    (config.DATA_DIR / "raw_tweets.json").write_text(json.dumps(raw_tweets, indent=2), encoding="utf-8")

    result = _process_posts(raw_tweets)
    if result["cleaned_count"] == 0:
        raise HTTPException(400, "no usable tweets after cleaning (all retweets/duplicates/empty?)")

    return {
        "raw_count": len(raw_tweets),
        **result,
    }


@router.post("/post")
def post_tweet_route(request: PostRequest):
    return post_tweet(request)


@router.get("/corpus/stats")
def corpus_stats():
    return get_corpus_stats()
