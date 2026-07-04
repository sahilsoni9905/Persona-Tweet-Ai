import json

from fastapi import APIRouter

import config

router = APIRouter()


@router.get("/history")
def get_history():
    if config.HISTORY_PATH.exists():
        return {"history": json.loads(config.HISTORY_PATH.read_text(encoding="utf-8"))}
    return {"history": []}
