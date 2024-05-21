import pytz
from common import *

def channel_cleanup_task(bot):

  async def channel_cleanup():
    enabled = config["tasks"]["channel_cleanup"]["enabled"]
    if not enabled:
      return

    pst_tz = pytz.timezone('America/Los_Angeles')
    raw_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    aware_now = pst_tz.normalize(raw_now.astimezone(pst_tz))

    one_day_ago = aware_now - timedelta(days=1)

    channel_ids = get_channel_ids_list(config["tasks"]["channel_cleanup"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)

      self_destruct_embed = discord.Embed(
        title="Deleting previous messages...",
        color=discord.Color.dark_red()
      )
      self_destruct_embed.set_footer(text="This message will self-destruct in 10 minutes... 💣")
      self_destruct_message = await channel.send(embed=self_destruct_embed)

      async for message in channel.history(before=one_day_ago):
        try:
          await message.delete()
        except Exception as e:
          logger.error(f"Error channel_cleanup_task: {e}")
          logger.info(traceback.format_exc())

      await asyncio.sleep(600)
      await self_destruct_message.delete()

  return {
    "task": channel_cleanup,
    "crontab": config["tasks"]["channel_cleanup"]["crontab"]
  }