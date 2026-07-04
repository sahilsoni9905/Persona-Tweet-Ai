import json
import logging
from datetime import datetime, timezone

import config

log = logging.getLogger("poster")


def append_history(entry: dict):
    history = []
    if config.HISTORY_PATH.exists():
        history = json.loads(config.HISTORY_PATH.read_text(encoding="utf-8"))
    history.append(entry)
    config.HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")


def log_cycle_failure(status: str, text: str, error: str):
    log.warning("[cycle] status=%s error=%s", status, error)
    append_history({
        "text": text,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "mode": config.POST_MODE,
        "status": status,
        "error": error,
    })
