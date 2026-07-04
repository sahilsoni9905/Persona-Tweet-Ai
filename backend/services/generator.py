import json
import logging
import random
from datetime import datetime, timezone

import tweepy

import config
from models.schemas import PostRequest
from services.llm import get_llm_client
from services.style_index import query_similar, query_reply_style
from services.scorer import score_candidates
from services.poster import get_twitter_client, post_tweet
from utils.history import append_history, log_cycle_failure

log = logging.getLogger("poster")


def _normalize_hashtags(candidates: list[dict]) -> list[dict]:
    for candidate in candidates:
        tags = candidate.get("hashtags", [])
        if isinstance(tags, str):
            candidate["hashtags"] = tags.split()
    return candidates


def get_style_examples(k: int = 8) -> list[str]:
    clean_path = config.DATA_DIR / "clean_tweets.json"
    if not clean_path.exists():
        return []
    with open(clean_path, encoding="utf-8") as f:
        tweets = json.load(f)
    if not tweets:
        return []
    clusters: dict[int, list[str]] = {}
    for t in tweets:
        c = t.get("cluster", 0)
        clusters.setdefault(c, []).append(t["text"])
    buckets = [list(v) for v in clusters.values()]
    result = []
    i = 0
    while len(result) < k and any(buckets):
        bucket = buckets[i % len(buckets)]
        if bucket:
            result.append(bucket.pop(random.randrange(len(bucket))))
        i += 1
    random.shuffle(result)
    return result


def get_reply_style_examples(mention_text: str, k: int = 6) -> list[str]:
    reply_results = query_reply_style(mention_text, k=k)
    if len(reply_results) >= 3:
        return [r["text"] for r in reply_results]
    general = query_similar(mention_text, k=k)
    return [r["text"] for r in general]


def run_generate(n: int = 3) -> dict:
    llm = get_llm_client()
    style_examples = get_style_examples(k=8)

    feedback = None
    attempts = 0
    while True:
        attempts += 1
        candidates = _normalize_hashtags(
            llm.generate_tweet(style_examples, n=n, feedback=feedback)
        )
        scores = score_candidates([c["text"] for c in candidates])
        ranked = sorted(
            (dict(c, style_score=s) for c, s in zip(candidates, scores)),
            key=lambda c: c["style_score"],
            reverse=True,
        )
        if ranked[0]["style_score"] >= config.STYLE_SCORE_THRESHOLD or attempts > config.MAX_RETRIES:
            break
        feedback = "these didn't sound like the user's real voice, lean more into their humour and tone"

    return {
        "style_examples": style_examples,
        "candidates": ranked,
        "attempts": attempts,
        "accepted": ranked[0]["style_score"] >= config.STYLE_SCORE_THRESHOLD,
    }


def run_generate_reply(tweet_text: str) -> dict:
    llm = get_llm_client()
    style_examples = get_reply_style_examples(tweet_text, k=6)
    raw = _normalize_hashtags([llm.generate_reply(tweet_text, style_examples)])[0]
    scores = score_candidates([raw["text"]])
    raw["style_score"] = scores[0]
    return {
        "reply": raw,
        "style_examples_used": style_examples,
        "tweet_text": tweet_text,
    }


def run_cycle():
    log.info("[cycle] starting post cycle (mode=%s)", config.POST_MODE)
    try:
        result = run_generate()
    except Exception as e:
        log.error("[cycle] generation failed — %s", e)
        log_cycle_failure("failed", "", f"generation error: {e}")
        return

    log.info("[cycle] generated %d candidate(s) in %d attempt(s), accepted=%s",
             len(result["candidates"]), result["attempts"], result["accepted"])

    if not result["accepted"]:
        top_text = result["candidates"][0]["text"] if result["candidates"] else ""
        log.warning("[cycle] SKIPPED — no candidate cleared style threshold %.2f", config.STYLE_SCORE_THRESHOLD)
        log_cycle_failure(
            "skipped", top_text,
            f"no candidate cleared the style threshold after {result['attempts']} attempt(s)",
        )
        return

    top = result["candidates"][0]
    log.info("[cycle] best candidate (score=%.3f): %s", top["style_score"], top["text"])
    try:
        post_tweet(PostRequest(text=top["text"], hashtags=top["hashtags"]))
    except Exception as e:
        log.error("[cycle] posting error — %s", e)
        log_cycle_failure("failed", top["text"], f"posting error: {e}")


def run_reply_cycle():
    log.info("[reply-cycle] checking @mentions (mode=%s)", config.POST_MODE)
    user_id = os.environ.get("TWITTER_USER_ID", "")
    if not user_id:
        log.warning("[reply-cycle] TWITTER_USER_ID not set in .env — skipping mention check to avoid paid API call")
        return
    try:
        client = get_twitter_client()
        mentions_response = client.get_users_mentions(
            user_id,
            max_results=5,
            tweet_fields=["text", "author_id"],
        )
    except tweepy.errors.TweepyException as e:
        log.error("[reply-cycle] could not fetch mentions — %s", e)
        log_cycle_failure("failed", "", f"mention fetch error: {e}")
        return

    if not mentions_response.data:
        log.info("[reply-cycle] no new mentions")
        return

    log.info("[reply-cycle] found %d mention(s)", len(mentions_response.data))

    replied_ids: set[str] = set(
        json.loads(config.REPLIED_PATH.read_text(encoding="utf-8"))
        if config.REPLIED_PATH.exists()
        else []
    )

    llm = get_llm_client()

    for mention in mentions_response.data:
        if str(mention.id) in replied_ids:
            continue

        style_examples = get_reply_style_examples(mention.text, k=6)

        try:
            reply = _normalize_hashtags([llm.generate_reply(mention.text, style_examples)])[0]
            reply_text = reply.get("text", "")
            log.info("[reply-cycle] mention_id=%s — generated reply: %s", mention.id, reply_text)

            if config.POST_MODE == "draft":
                log.info("[reply-cycle] [DRAFT] would have replied to mention_id=%s", mention.id)
                append_history({
                    "text": f"[reply] {reply_text}",
                    "reply_to_id": str(mention.id),
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "draft",
                    "status": "drafted",
                })
            else:
                log.info("[reply-cycle] [LIVE] sending reply to mention_id=%s", mention.id)
                response = client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=str(mention.id),
                )
                tweet_id = response.data["id"]
                log.info("[reply-cycle] [LIVE] reply SENT — tweet_id=%s url=https://twitter.com/i/web/status/%s", tweet_id, tweet_id)
                append_history({
                    "text": f"[reply] {reply_text}",
                    "reply_to_id": str(mention.id),
                    "tweet_id": tweet_id,
                    "posted_at": datetime.now(timezone.utc).isoformat(),
                    "mode": "live",
                    "status": "posted",
                })

            replied_ids.add(str(mention.id))
        except Exception as e:
            log.error("[reply-cycle] failed to reply to mention_id=%s — %s", mention.id, e)
            log_cycle_failure("failed", "", f"reply error for mention {mention.id}: {e}")

    config.REPLIED_PATH.write_text(json.dumps(list(replied_ids)), encoding="utf-8")
