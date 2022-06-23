import datetime
import pytz

from commands.common import *

tz = os.getenv('TZ')

def bingbong_task(client):

  async def bingbong():
    enabled = config["tasks"]["bingbong"]["enabled"]
    if not enabled:
      return

    current_time = datetime.datetime.now(pytz.timezone(tz)).strftime("%A, %b %-d - %I:%M %p")

    channel_ids = config["tasks"]["bingbong"]["channels"]
    for channel_id in channel_ids:
      channel = client.get_channel(id=channel_id)
      await channel.send(embed=discord.Embed(
        title="⏰ BING BONG! ⏰",
        description=f"**The Time Is:** {current_time}",
        color=discord.Color.blurple()
      ))

  return {
    "task": bingbong,
    "crontab": config["tasks"]["bingbong"]["crontab"]
  }

