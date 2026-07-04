import re
import uuid

import tweepy
from fastapi import APIRouter, HTTPException

from models.schemas import AddPostRequest, AddReplyRequest, ReferencePost, TweetUrlRequest
from services.poster import get_twitter_client
from services.style_index import add_reference_post, add_reply_tweet, add_tweet, query_similar

router = APIRouter(prefix="/style")


def _extract_tweet_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    if not match:
        raise ValueError(f"could not extract tweet ID from URL: {url}")
    return match.group(1)


@router.post("/add_reference")
def add_reference(post: ReferencePost):
    add_reference_post(post.id, post.text, post.note)
    return {"status": "added", "id": post.id}


@router.post("/add_from_url")
def add_from_url(req: TweetUrlRequest):
    try:
        tweet_id = _extract_tweet_id(req.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        client = get_twitter_client()
        response = client.get_tweet(tweet_id)
        text = response.data.text
    except tweepy.errors.TweepyException as e:
        raise HTTPException(502, f"Twitter API error fetching tweet: {e}")

    add_reference_post(tweet_id, text, note=req.note)
    return {"status": "added", "id": tweet_id, "text": text}


@router.post("/add_post")
def add_post(req: AddPostRequest):
    tweet_id = uuid.uuid4().hex
    add_tweet(tweet_id, req.text, cluster=-1, source="manual")
    return {"status": "added", "id": tweet_id}


@router.post("/add_reply")
def add_reply_example(req: AddReplyRequest):
    tweet_id = uuid.uuid4().hex
    add_reply_tweet(tweet_id, req.text)
    return {"status": "added", "id": tweet_id}


@router.get("/query")
def query(text: str, k: int = 5):
    return {"results": query_similar(text, k)}
