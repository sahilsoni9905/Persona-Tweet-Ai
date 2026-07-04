import json
import re
import sys
from pathlib import Path

MENTION_START_RE = re.compile(r'^(@\w+\s*)+')
URL_RE = re.compile(r'https?://\S+')
WHITESPACE_RE = re.compile(r'\s+')


def _clean_reply_text(text: str) -> str:
    text = MENTION_START_RE.sub('', text)
    text = URL_RE.sub('', text)
    return WHITESPACE_RE.sub(' ', text).strip()


def parse_archive_file(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    start = raw.index("[")
    entries = json.loads(raw[start:])
    converted = []
    for entry in entries:
        tweet = entry.get("tweet", entry)
        text = tweet.get("full_text", tweet.get("text", ""))
        is_retweet = bool(tweet.get("retweeted_status_id_str")) or text.startswith("RT @")
        in_reply_to = tweet.get("in_reply_to_status_id_str", "") or ""
        converted.append({
            "id": tweet.get("id_str", tweet.get("id", "")),
            "text": text,
            "created_at": tweet.get("created_at", ""),
            "is_retweet": is_retweet,
            "in_reply_to_id": in_reply_to if in_reply_to and in_reply_to != "0" else "",
        })
    return converted


def import_from_folder(archive_dir: Path) -> dict:
    candidates = [
        archive_dir / "data" / "tweets.js",
        archive_dir / "data" / "tweet.js",
        archive_dir / "tweets.js",
        archive_dir / "tweet.js",
    ]
    tweets_file = next((p for p in candidates if p.exists()), None)

    if tweets_file is None:
        found = list(archive_dir.rglob("tweets.js")) + list(archive_dir.rglob("tweet.js"))
        if found:
            tweets_file = found[0]

    if tweets_file is None:
        raise FileNotFoundError(
            f"tweets.js not found inside {archive_dir}. "
            "X archives are usually extracted as a subfolder like "
            "my_twitter_data/twitter-YYYY-MM-DD-.../data/tweets.js — "
            "make sure the extracted folder is placed inside my_twitter_data/."
        )

    all_tweets = parse_archive_file(tweets_file)

    posts = []
    replies = []
    for t in all_tweets:
        if t["is_retweet"]:
            continue
        if t["in_reply_to_id"]:
            cleaned = _clean_reply_text(t["text"])
            if cleaned:
                replies.append({"id": t["id"], "text": cleaned, "created_at": t["created_at"]})
        else:
            posts.append({"id": t["id"], "text": t["text"], "created_at": t["created_at"], "is_retweet": False})

    return {"posts": posts, "replies": replies}


def main():
    if len(sys.argv) != 2:
        print("usage: python utils/archive.py path/to/tweets.js")
        sys.exit(1)
    if __package__ is None:
        sys.path.insert(0, str(Path(__file__).parent.parent))
    import config
    out_path = config.DATA_DIR / "raw_tweets.json"
    converted = parse_archive_file(Path(sys.argv[1]))
    out_path.write_text(json.dumps(converted, indent=2), encoding="utf-8")
    print(f"Converted {len(converted)} tweets → {out_path}")


if __name__ == "__main__":
    main()
