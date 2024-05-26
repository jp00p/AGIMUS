from common import *
from utils.check_role_access import role_check

@bot.command()
@commands.check(role_check)
async def nuke_maquis(ctx):
  await ctx.message.delete()
  enabled = config["commands"]["nuke_maquis"]["enabled"]
  if not enabled:
    return

  channel_id = get_channel_id("maquis-officers-club")
  if not channel_id:
      return

  channel = bot.get_channel(channel_id)

  # Just nuke the entire channel history
  await channel.purge(limit=1500, oldest_first=True, reason="Manual Purge")

  self_destruct_embed = discord.Embed(
    title="Channel Nuked From Orbit! 💥",
    color=discord.Color.dark_red()
  )
  self_destruct_embed.set_image(url="https://i.imgur.com/8W40YCG.gif")
  self_destruct_embed.set_footer(text="This message will self-destruct in 5 minutes... 💣")
  self_destruct_message = await channel.send(embed=self_destruct_embed)

  await asyncio.sleep(300)
  await self_destruct_message.delete()

