import threading

from fastapi import APIRouter

from models.schemas import FeedReplySchedulerStart, ReplySchedulerStart, SchedulerStart
from services.feed_replier import get_today_count, run_feed_reply_cycle, update_settings
from services.generator import run_cycle, run_reply_cycle
from services.scheduler_instance import scheduler

router = APIRouter(prefix="/scheduler")


@router.post("/start")
def start_scheduler(req: SchedulerStart):
    if scheduler.get_job("auto_post"):
        scheduler.remove_job("auto_post")
    if req.interval_seconds:
        scheduler.add_job(run_cycle, "interval", seconds=req.interval_seconds, id="auto_post", max_instances=3)
        return {"status": "started", "interval_seconds": req.interval_seconds}
    interval_hours = 24 / req.times_per_day
    scheduler.add_job(run_cycle, "interval", hours=interval_hours, id="auto_post", max_instances=3)
    return {"status": "started", "times_per_day": req.times_per_day}


@router.post("/stop")
def stop_scheduler():
    if scheduler.get_job("auto_post"):
        scheduler.remove_job("auto_post")
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.post("/run_now")
def run_now():
    threading.Thread(target=run_cycle, daemon=True).start()
    return {"status": "triggered"}


@router.post("/reply/start")
def start_reply_scheduler(req: ReplySchedulerStart):
    if scheduler.get_job("auto_reply"):
        scheduler.remove_job("auto_reply")
    scheduler.add_job(
        run_reply_cycle, "interval", minutes=req.interval_minutes,
        id="auto_reply", max_instances=1,
    )
    return {"status": "started", "interval_minutes": req.interval_minutes}


@router.post("/reply/stop")
def stop_reply_scheduler():
    if scheduler.get_job("auto_reply"):
        scheduler.remove_job("auto_reply")
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.post("/feed_reply/start")
def start_feed_reply(req: FeedReplySchedulerStart):
    update_settings(
        max_per_day=req.max_per_day,
        start_hour=req.active_hours_start,
        end_hour=req.active_hours_end,
    )
    if scheduler.get_job("feed_reply"):
        scheduler.remove_job("feed_reply")
    scheduler.add_job(
        run_feed_reply_cycle, "interval",
        minutes=req.interval_minutes,
        id="feed_reply", max_instances=1,
    )
    return {"status": "started", "interval_minutes": req.interval_minutes, "max_per_day": req.max_per_day}


@router.post("/feed_reply/stop")
def stop_feed_reply():
    if scheduler.get_job("feed_reply"):
        scheduler.remove_job("feed_reply")
        return {"status": "stopped"}
    return {"status": "not_running"}


@router.post("/feed_reply/run_now")
def feed_reply_now():
    threading.Thread(target=run_feed_reply_cycle, daemon=True).start()
    return {"status": "triggered"}


@router.get("/status")
def scheduler_status():
    post_job   = scheduler.get_job("auto_post")
    reply_job  = scheduler.get_job("auto_reply")
    feed_job   = scheduler.get_job("feed_reply")
    return {
        "post_running":       post_job is not None,
        "post_next_run":      post_job.next_run_time.isoformat() if post_job and post_job.next_run_time else None,
        "reply_running":      reply_job is not None,
        "reply_next_run":     reply_job.next_run_time.isoformat() if reply_job and reply_job.next_run_time else None,
        "feed_reply_running": feed_job is not None,
        "feed_reply_next_run":feed_job.next_run_time.isoformat() if feed_job and feed_job.next_run_time else None,
        "feed_reply_today":   get_today_count(),
    }
