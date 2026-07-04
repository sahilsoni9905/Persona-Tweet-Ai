from fastapi import APIRouter
from services.browser import get_login_status, start_login_flow

router = APIRouter(prefix="/browser")


@router.post("/login")
def browser_login():
    start_login_flow()
    return {"status": "opening", "message": "Browser opening on your screen — log in to Twitter, session saves automatically when you reach home"}


@router.get("/status")
def browser_status():
    return get_login_status()
