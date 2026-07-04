import re

from fastapi import APIRouter, HTTPException

from models.schemas import PostRequest, ReplyToTweetRequest, SendReplyRequest
from services.generator import run_generate, run_generate_reply
from services.poster import post_tweet, send_reply

router = APIRouter()


def _extract_tweet_id(url: str) -> str:
    match = re.search(r"/status/(\d+)", url)
    if not match:
        raise ValueError(f"could not extract tweet ID from: {url}")
    return match.group(1)


def _extract_username(url: str) -> str:
    match = re.search(r"(?:twitter|x)\.com/([^/]+)/status", url)
    return match.group(1) if match else ""


@router.post("/generate")
def generate(n: int = 3):
    return run_generate(n)


@router.post("/generate/reply")
def generate_reply(req: ReplyToTweetRequest):
    tweet_text = req.tweet_text
    tweet_id = ""
    username = ""

    if req.tweet_url:
        try:
            tweet_id = _extract_tweet_id(req.tweet_url)
            username = _extract_username(req.tweet_url)
        except ValueError as e:
            raise HTTPException(400, str(e))

    if not tweet_text:
        raise HTTPException(400, "paste the tweet text — we don't fetch it via API to avoid paid read calls")

    result = run_generate_reply(tweet_text)
    result["original_tweet_id"] = tweet_id
    result["original_username"] = username
    return result


@router.post("/post/reply")
def post_reply(req: SendReplyRequest):
    if req.in_reply_to_id:
        try:
            return send_reply(req.text, req.hashtags, req.in_reply_to_id)
        except HTTPException as e:
            if e.status_code != 403:
                raise
    mention_text = f"@{req.mention_username} {req.text}" if req.mention_username else req.text
    result = post_tweet(PostRequest(text=mention_text, hashtags=req.hashtags))
    result["as_mention"] = True
    return result
