import json
import re
from pathlib import Path

URL_RE = re.compile(r"https?://\S+")
WHITESPACE_RE = re.compile(r"\s+")


def is_retweet(tweet: dict) -> bool:
    return tweet.get("is_retweet", False) or tweet["text"].startswith("RT @")


def clean_text(text: str) -> str:
    text = URL_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def load_raw_tweets(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean_tweets(raw_tweets: list[dict]) -> list[dict]:
    seen_texts = set()
    cleaned = []
    for tweet in raw_tweets:
        if is_retweet(tweet):
            continue
        text = clean_text(tweet["text"])
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        cleaned.append({"id": tweet["id"], "text": text, "created_at": tweet.get("created_at")})
    return cleaned


def main():
    import sys
    from pathlib import Path as P
    if __package__ is None:
        sys.path.insert(0, str(P(__file__).parent.parent))
    import config
    raw = load_raw_tweets(config.DATA_DIR / "raw_tweets.json")
    cleaned = clean_tweets(raw)
    (config.DATA_DIR / "clean_tweets.json").write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    print(f"Loaded {len(raw)} raw tweets -> {len(cleaned)} cleaned tweets")


if __name__ == "__main__":
    main()
