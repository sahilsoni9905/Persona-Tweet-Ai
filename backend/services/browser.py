import logging
import threading
from pathlib import Path

import config

log = logging.getLogger("poster")

SESSION_PATH = config.DATA_DIR / "twitter_session.json"
_login_status = {"state": "idle", "message": ""}


def session_exists() -> bool:
    return SESSION_PATH.exists()


def get_login_status() -> dict:
    exists = session_exists()
    state = "done" if exists else _login_status["state"]
    message = "Connected to Twitter ✓" if exists else _login_status["message"]
    return {
        "session_exists": exists,
        "state": state,
        "message": message,
    }


def _do_login():
    from playwright.sync_api import sync_playwright
    _login_status["state"] = "waiting"
    _login_status["message"] = "Browser opened — log in to Twitter, session saves automatically"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="msedge",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()
            page.goto("https://x.com/login")
            log.info("[browser] waiting for user to log in...")
            page.wait_for_url("**/home", timeout=180000)
            context.storage_state(path=str(SESSION_PATH))
            _login_status["state"] = "done"
            _login_status["message"] = "Logged in and session saved"
            log.info("[browser] session saved to %s", SESSION_PATH)
            browser.close()
    except Exception as e:
        _login_status["state"] = "error"
        _login_status["message"] = f"Login failed: {e}"
        log.error("[browser] login error: %s", e)


def start_login_flow():
    if _login_status["state"] == "waiting":
        return
    threading.Thread(target=_do_login, daemon=True).start()


def get_browser_context(playwright):
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    if session_exists():
        context = browser.new_context(
            storage_state=str(SESSION_PATH),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        )
    else:
        context = browser.new_context()
    return browser, context
