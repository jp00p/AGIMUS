from common import *

NUKE_CHANCE = 5

def channel_cleanup_task(bot):

  async def channel_cleanup():
    enabled = config["tasks"]["channel_cleanup"]["enabled"]
    if not enabled:
      return

    global NUKE_CHANCE

    channel_ids = get_channel_ids_list(config["tasks"]["channel_cleanup"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)
      if not channel:
        continue

      roll = random.randint(0, 100)

      if roll <= NUKE_CHANCE:
        # Nuke the "entire" channel history
        await channel.purge(limit=1500, oldest_first=True, reason="Periodic Purge")

        self_destruct_embed = discord.Embed(
          title="Channel Nuked From Orbit! 💥",
          color=discord.Color.dark_red()
        )
        self_destruct_embed.set_image(url="https://i.imgur.com/8W40YCG.gif")
        self_destruct_embed.set_footer(text=f"Rolled a {roll}. Nuke Chance was {NUKE_CHANCE}%, resetting to 5%. 🎲\nThis message will self-destruct in 5 minutes... 💣")
        self_destruct_message = await channel.send(embed=self_destruct_embed)

        NUKE_CHANCE = 5

        await asyncio.sleep(300)
        await self_destruct_message.delete()
      else:
        NUKE_CHANCE += 5

  return {
    "task": channel_cleanup,
    "crontab": config["tasks"]["channel_cleanup"]["crontab"]
  }