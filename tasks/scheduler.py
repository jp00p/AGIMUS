from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from commands.common import *

tz = os.getenv('TZ')

class Scheduler():
  def __init__(self):
    self.scheduler = AsyncIOScheduler(
      job_defaults={
        "coalesce": True,
        "max_instances": 5,
        "misfire_grace_time": 15,
        "replace_existing": True
      },
      timezone=tz
    )

    schedule_log = logging.getLogger("apscheduler")
    schedule_log.setLevel(logging.WARNING)

  def start(self):
    self.scheduler.start()

  def add_task(self, task, crontab):
    self.scheduler.add_job(task, CronTrigger.from_crontab(crontab, timezone=tz))
    logger.info(f"{Fore.CYAN}>> Added Scheduled Task: {Style.BRIGHT}{task.__name__}{Style.RESET_ALL}")