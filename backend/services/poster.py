import logging
import os
from datetime import datetime, timezone

import tweepy
from fastapi import HTTPException

import config
from models.schemas import PostRequest
from utils.history import append_history

log = logging.getLogger("poster")


def get_twitter_client() -> tweepy.Client:
    return tweepy.Client(
        bearer_token=os.environ.get("TWITTER_BEARER_TOKEN"),
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def post_tweet(request: PostRequest):
    status_text = " ".join([request.text] + request.hashtags)
    entry = {
        "text": status_text,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "mode": config.POST_MODE,
    }

    if config.POST_MODE == "draft":
        log.info("[DRAFT] would have posted: %s", status_text)
        entry["status"] = "drafted"
        append_history(entry)
        return {"status": "drafted", "would_have_posted": status_text}

    log.info("[LIVE] attempting to post tweet: %s", status_text)
    client = get_twitter_client()
    try:
        response = client.create_tweet(text=status_text)
    except tweepy.errors.TweepyException as e:
        log.error("[LIVE] Twitter API REJECTED the post — %s", e)
        entry["status"] = "failed"
        entry["error"] = str(e)
        append_history(entry)
        raise HTTPException(502, f"Twitter API rejected the post: {e}")

    tweet_id = response.data["id"]
    log.info("[LIVE] tweet SENT successfully — tweet_id=%s url=https://twitter.com/i/web/status/%s", tweet_id, tweet_id)
    entry["status"] = "posted"
    entry["tweet_id"] = tweet_id
    append_history(entry)
    return {"status": "posted", "tweet_id": tweet_id}


def send_reply(text: str, hashtags: list[str], in_reply_to_id: str):
    status_text = " ".join([text] + hashtags)
    entry = {
        "text": f"[reply] {status_text}",
        "reply_to_id": in_reply_to_id,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "mode": config.POST_MODE,
    }

    if config.POST_MODE == "draft":
        log.info("[DRAFT] would have replied to %s: %s", in_reply_to_id, status_text)
        entry["status"] = "drafted"
        append_history(entry)
        return {"status": "drafted", "would_have_replied": status_text}

    log.info("[LIVE] attempting to reply to tweet_id=%s: %s", in_reply_to_id, status_text)
    client = get_twitter_client()
    try:
        response = client.create_tweet(
            text=status_text,
            in_reply_to_tweet_id=in_reply_to_id,
        )
    except tweepy.errors.TweepyException as e:
        log.error("[LIVE] Twitter API REJECTED the reply — %s", e)
        entry["status"] = "failed"
        entry["error"] = str(e)
        append_history(entry)
        raise HTTPException(502, f"Twitter API rejected the reply: {e}")

    tweet_id = response.data["id"]
    log.info("[LIVE] reply SENT successfully — tweet_id=%s url=https://twitter.com/i/web/status/%s", tweet_id, tweet_id)
    entry["status"] = "posted"
    entry["tweet_id"] = tweet_id
    append_history(entry)
    return {"status": "posted", "tweet_id": tweet_id}
