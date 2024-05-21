import pytz
from common import *

def channel_cleanup_task(bot):

  async def channel_cleanup():
    enabled = config["tasks"]["channel_cleanup"]["enabled"]
    if not enabled:
      return

    pst_tz = pytz.timezone('America/Los_Angeles')
    raw_now = datetime.utcnow().replace(tzinfo=pytz.utc))
    aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))

    two_days_ago = aware_now - timedelta(days=2)

    channel_ids = get_channel_ids_list(config["tasks"]["channel_cleanup"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)

      await channel.send(
        discord.Embed(
          title="Deleting previous messages...",
          color=discord.Color.dark_red()
        )
      )

      async for message in channel.history(before=two_days_ago):
        try:
          await message.delete()
        except Exception as e:
          logger.error(f"Error channel_cleanup_task: {e}")
          logger.info(traceback.format_exc())

  return {
    "task": channel_cleanup,
    "crontab": config["tasks"]["channel_cleanup"]["crontab"]
  }