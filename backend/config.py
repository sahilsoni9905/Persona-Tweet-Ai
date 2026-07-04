import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
ARCHIVE_DIR = Path(__file__).parent / "my_twitter_data"
HISTORY_PATH = DATA_DIR / "history.json"
SETTINGS_PATH = DATA_DIR / "settings.json"
REPLIED_PATH = DATA_DIR / "replied_mentions.json"

DATA_DIR.mkdir(exist_ok=True)

STYLE_SCORE_THRESHOLD = 0.6
MAX_RETRIES = 2
POST_MODE = os.environ.get("POST_MODE", "draft")

if SETTINGS_PATH.exists():
    _saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    STYLE_SCORE_THRESHOLD = _saved.get("style_score_threshold", STYLE_SCORE_THRESHOLD)
    MAX_RETRIES = _saved.get("max_retries", MAX_RETRIES)
    POST_MODE = _saved.get("post_mode", POST_MODE)
