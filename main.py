import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import TIMEZONE
from src.pipeline import analyze, refresh_caches

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    if "--now" in sys.argv:
        logger.info("Executando imediatamente (--now).")
        refresh_caches()
        analyze(collection_window=0)
        return

    scheduler = BlockingScheduler()

    scheduler.add_job(
        refresh_caches,
        CronTrigger(hour=1, minute=2, timezone=TIMEZONE),
        id="refresh_caches",
    )

    scheduler.add_job(
        analyze,
        CronTrigger(hour=23, minute=22, timezone=TIMEZONE),
        id="skin_analysis",
    )

    logger.info("Scheduler ativo. Caches: 00:45 | Análise: 11:00 (%s).", TIMEZONE)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler encerrado.")


if __name__ == "__main__":
    main()
