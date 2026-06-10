"""Scheduler voor automatische koersupdates."""
import schedule
import threading
import time
import os
import logging

from app.services.price_service import run_price_update

logger = logging.getLogger(__name__)

_scheduler_thread = None
_running = False


def _run_scheduler():
    """Draai de scheduler in een aparte thread."""
    global _running
    while _running:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler():
    """Start de scheduler met geconfigureerde update-tijden."""
    global _scheduler_thread, _running

    update_time_1 = os.getenv("UPDATE_TIME_1", "08:00")
    update_time_2 = os.getenv("UPDATE_TIME_2", "13:00")

    schedule.every().day.at(update_time_1).do(run_price_update)
    schedule.every().day.at(update_time_2).do(run_price_update)

    logger.info(f"Scheduler gestart: updates om {update_time_1} en {update_time_2}")

    _running = True
    _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    _scheduler_thread.start()


def stop_scheduler():
    """Stop de scheduler."""
    global _running
    _running = False
    schedule.clear()
    logger.info("Scheduler gestopt")


def is_running() -> bool:
    """Controleer of de scheduler actief is."""
    return _running and _scheduler_thread is not None and _scheduler_thread.is_alive()
