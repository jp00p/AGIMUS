from common import *

def hoodiversary_task(bot):

  async def hoodiversary():
    try:
      enabled = config["tasks"]["hoodiversary"]["enabled"]
      if not enabled:
        return

      today = datetime.utcnow().date()
      members = await bot.current_guild.fetch_members().flatten()
      hoodiversary_members = [
        {
          "member": m,
          "age": today.year - m.joined_at.year
        } for m in members
        if m.joined_at.day == today.day and m.joined_at.month == today.month and m.joined_at.year != today.year
      ]

      logger.info(hoodiversary_members)

      if not hoodiversary_members:
        return

      emoji_list = [
        get_emoji('picard_yes_happy_celebrate'),
        get_emoji('picard_party_dance'),
        get_emoji('picard_dance'),
        get_emoji('picard_happy_excited_dance'),
        get_emoji('q_happy_yes_trumpet_celebrate')
      ]

      description = ""
      for m in hoodiversary_members:
        description += f"{random.choice(emoji_list)} {m['member'].mention} has been aboard The Hood for {m['age']} years!\nJoined {m['member'].joined_at.strftime('%x')}\n\n"

      embed = discord.Embed(
        title="These FoDs Are Celebrating Their Hoodiversary!",
        description=description,
        color=discord.Color.random()
      )
      channel_ids = get_channel_ids_list(config["tasks"]["hoodiversary"]["channels"])
      for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        await channel.send(embed=embed)
    except Exception as e:
      logger.info(traceback.format_exc())

  return {
    "task": hoodiversary,
    "crontab": config["tasks"]["hoodiversary"]["crontab"]
  }