import pytz
from common import *

def channel_cleanup_task(bot):

  async def channel_cleanup():
    enabled = config["tasks"]["channel_cleanup"]["enabled"]
    if not enabled:
      return

    channel_ids = get_channel_ids_list(config["tasks"]["channel_cleanup"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)
      if not channel:
        continue

      # Just nuke the entire channel history
      await channel.purge()

      self_destruct_embed = discord.Embed(
        title="Channel Nuked From Orbit! 💥",
        color=discord.Color.dark_red()
      )
      self_destruct_embed.set_footer(text="This message will self-destruct in 10 minutes... 💣")
      self_destruct_message = await channel.send(embed=self_destruct_embed)

      await asyncio.sleep(600)
      await self_destruct_message.delete()

  return {
    "task": channel_cleanup,
    "crontab": config["tasks"]["channel_cleanup"]["crontab"]
  }