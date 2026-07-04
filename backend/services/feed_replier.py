import json
import logging
import random
import time
from datetime import datetime, timezone, date

import config
from services.browser import get_browser_context, session_exists
from services.generator import run_generate_reply
from utils.history import append_history, log_cycle_failure

log = logging.getLogger("poster")

DAILY_LOG_PATH = config.DATA_DIR / "daily_reply_log.json"

_settings = {
    "max_per_day": 8,
    "active_hours_start": 9,
    "active_hours_end": 23,
}


def get_today_count() -> int:
    if not DAILY_LOG_PATH.exists():
        return 0
    data = json.loads(DAILY_LOG_PATH.read_text(encoding="utf-8"))
    return data.get(date.today().isoformat(), 0)


def _increment_today():
    today = date.today().isoformat()
    data = {}
    if DAILY_LOG_PATH.exists():
        data = json.loads(DAILY_LOG_PATH.read_text(encoding="utf-8"))
    data[today] = data.get(today, 0) + 1
    DAILY_LOG_PATH.write_text(json.dumps(data), encoding="utf-8")


def _is_active_hours() -> bool:
    h = datetime.now().hour
    return _settings["active_hours_start"] <= h <= _settings["active_hours_end"]


def run_feed_reply_cycle():
    max_per_day = _settings["max_per_day"]

    if not _is_active_hours():
        log.info("[feed-reply] outside active hours (%d-%d), skipping",
                 _settings["active_hours_start"], _settings["active_hours_end"])
        return

    today = get_today_count()
    if today >= max_per_day:
        log.info("[feed-reply] daily cap reached (%d/%d)", today, max_per_day)
        return

    if not session_exists():
        log.warning("[feed-reply] no session — click 'Login to Twitter' in the UI first")
        return

    log.info("[feed-reply] cycle starting (today: %d/%d)", today, max_per_day)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser, context = get_browser_context(p)
            page = context.new_page()

            page.goto("https://twitter.com/home", wait_until="load", timeout=30000)
            page.wait_for_timeout(4000)

            # check we didn't land on login page
            if "login" in page.url or "i/flow" in page.url:
                log.warning("[feed-reply] redirected to login — session expired, click 'Open Twitter Login' again")
                browser.close()
                return

            # wait until at least one tweet appears
            try:
                page.wait_for_selector('[data-testid="tweet"]', timeout=20000)
            except Exception:
                log.warning("[feed-reply] tweets never appeared — page may still be loading or layout changed")
                browser.close()
                return

            page.mouse.wheel(0, random.randint(800, 1800))
            page.wait_for_timeout(3000)

            tweets = page.query_selector_all('[data-testid="tweet"]')
            log.info("[feed-reply] found %d tweets on feed", len(tweets))

            replied = 0

            for tweet_el in tweets:
                if replied >= 3:
                    break
                if today + replied >= max_per_day:
                    break

                # skip some tweets naturally — humans don't reply to everything
                if random.random() < 0.30:
                    continue

                try:
                    text_el = tweet_el.query_selector('[data-testid="tweetText"]')
                    if not text_el:
                        continue

                    tweet_text = text_el.inner_text().strip()
                    if not tweet_text or len(tweet_text) < 15:
                        continue

                    # skip retweets and ads
                    outer_html = tweet_el.inner_html()
                    if "Retweeted" in outer_html or "Promoted" in outer_html:
                        continue

                    log.info("[feed-reply] selected tweet: %.60s...", tweet_text)

                    result = run_generate_reply(tweet_text)
                    reply_text = result["reply"]["text"]
                    score = result["reply"]["style_score"]
                    log.info("[feed-reply] generated reply (score=%.3f): %s", score, reply_text)

                    now = datetime.now(timezone.utc).isoformat()

                    if config.POST_MODE == "draft":
                        log.info("[feed-reply] [DRAFT] would reply: %s", reply_text)
                        append_history({
                            "text": f"[feed-reply] {reply_text}",
                            "reply_to": tweet_text[:80],
                            "posted_at": now,
                            "mode": "draft",
                            "status": "drafted",
                        })
                        replied += 1
                        _increment_today()
                        continue

                    # click reply button
                    reply_btn = tweet_el.query_selector('[data-testid="reply"]')
                    if not reply_btn:
                        continue
                    reply_btn.click()
                    page.wait_for_timeout(2000)

                    # find reply textarea
                    reply_box = (
                        page.query_selector('[data-testid="tweetTextarea_0"]')
                        or page.query_selector('[data-testid="tweetTextarea"]')
                        or page.query_selector('.public-DraftEditor-content')
                    )
                    if not reply_box:
                        log.warning("[feed-reply] reply box not found, closing modal")
                        page.keyboard.press("Escape")
                        continue

                    reply_box.click()
                    page.wait_for_timeout(500)

                    # type with human-like random speed
                    page.keyboard.type(reply_text, delay=random.randint(40, 90))
                    page.wait_for_timeout(random.randint(800, 1500))

                    # click Post
                    post_btn = (
                        page.query_selector('[data-testid="tweetButton"]')
                        or page.query_selector('[data-testid="tweetButtonInline"]')
                    )
                    if not post_btn:
                        log.warning("[feed-reply] post button not found, closing")
                        page.keyboard.press("Escape")
                        continue

                    post_btn.click()
                    page.wait_for_timeout(3000)

                    log.info("[feed-reply] [LIVE] reply posted")
                    append_history({
                        "text": f"[feed-reply] {reply_text}",
                        "reply_to": tweet_text[:80],
                        "posted_at": now,
                        "mode": "live",
                        "status": "posted",
                    })
                    replied += 1
                    _increment_today()

                except Exception as e:
                    log.error("[feed-reply] error on tweet: %s", e)
                    try:
                        page.keyboard.press("Escape")
                    except Exception:
                        pass
                    continue

            browser.close()
            log.info("[feed-reply] cycle done — replied %d, total today: %d/%d",
                     replied, get_today_count(), max_per_day)

    except Exception as e:
        log.error("[feed-reply] cycle crashed: %s", e)
        log_cycle_failure("failed", "", f"feed reply crash: {e}")


def update_settings(max_per_day: int = None, start_hour: int = None, end_hour: int = None):
    if max_per_day is not None:
        _settings["max_per_day"] = max_per_day
    if start_hour is not None:
        _settings["active_hours_start"] = start_hour
    if end_hour is not None:
        _settings["active_hours_end"] = end_hour
