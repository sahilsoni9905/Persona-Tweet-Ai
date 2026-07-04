import json

from fastapi import APIRouter, HTTPException

import config
from models.schemas import SettingsUpdate
from services.scheduler_instance import scheduler

router = APIRouter()


def _current_settings():
    post_job = scheduler.get_job("auto_post")
    reply_job = scheduler.get_job("auto_reply")
    return {
        "style_score_threshold": config.STYLE_SCORE_THRESHOLD,
        "max_retries": config.MAX_RETRIES,
        "post_mode": config.POST_MODE,
        "post_scheduler_running": post_job is not None,
        "reply_scheduler_running": reply_job is not None,
    }


@router.get("/settings")
def get_settings():
    return _current_settings()


@router.post("/settings")
def update_settings(update: SettingsUpdate):
    if update.post_mode is not None and update.post_mode not in ("draft", "live"):
        raise HTTPException(400, "post_mode must be 'draft' or 'live'")

    if update.style_score_threshold is not None:
        config.STYLE_SCORE_THRESHOLD = update.style_score_threshold
    if update.max_retries is not None:
        config.MAX_RETRIES = update.max_retries
    if update.post_mode is not None:
        config.POST_MODE = update.post_mode

    config.SETTINGS_PATH.write_text(
        json.dumps(
            {
                "style_score_threshold": config.STYLE_SCORE_THRESHOLD,
                "max_retries": config.MAX_RETRIES,
                "post_mode": config.POST_MODE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return _current_settings()
