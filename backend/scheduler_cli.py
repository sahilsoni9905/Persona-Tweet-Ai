from apscheduler.schedulers.blocking import BlockingScheduler

from services.generator import run_cycle


def start(times_per_day: int = 5):
    sched = BlockingScheduler()
    interval_hours = 24 / times_per_day
    sched.add_job(run_cycle, "interval", hours=interval_hours)
    sched.start()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--times-per-day", type=int, default=5)
    args = parser.parse_args()
    start(times_per_day=args.times_per_day)
