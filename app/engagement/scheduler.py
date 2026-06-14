# app/engagement/scheduler.py
"""
Campaign Scheduler
"""

import asyncio
import signal
import logging

from app.engagement.engine import run_all_campaigns

logger = logging.getLogger("ENGAGEMENT")

stop_event = asyncio.Event()


# Graceful Shutdown Handler
def handle_shutdown():
    logger.info("Shutdown signal received. Stopping scheduler...")
    stop_event.set()


# Scheduler
async def scheduler():
    logger.info("Starting engagement scheduler")

    while not stop_event.is_set():

        logger.info("Running campaigns")

        try:
            await run_all_campaigns()
        except Exception as e:
            logger.error("Campaign execution failed: %s", str(e))

        logger.info("Campaign run complete. Sleeping...")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            # normal wakeup after 1 hour
            pass

    logger.info("Scheduler stopped gracefully.")


# Entry Point
if __name__ == "__main__":

    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())

    asyncio.run(scheduler())