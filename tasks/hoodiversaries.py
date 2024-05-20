from common import *

from utils.badge_utils import db_get_user_badges

def hoodiversary_task(bot):

  async def hoodiversary():
    header_image_url = "https://i.imgur.com/9aEHbYd.png"
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

      if not hoodiversary_members:
        return

      # Award special Captain Picard Day badge!
      for m in hoodiversary_members:
        existing_badges = await db_get_user_badges(m["member"].id)
        if "Captain Picard Day" not in [b['badge_name'] for b in existing_badges]:
          async with AgimusDB() as query:
            sql = "INSERT INTO badges (user_discord_id, badge_filename) VALUES (%s, %s)"
            vals = (m["member"].id, 'Captain_Picard_Day.png')
            await query.execute(sql, vals)

      emoji_list = [
        get_emoji('picard_yes_happy_celebrate'),
        get_emoji('picard_party_dance'),
        get_emoji('picard_dance'),
        get_emoji('picard_happy_excited_dance'),
        get_emoji('q_happy_yes_trumpet_celebrate')
      ]

      description = ""
      mentions_string = ""
      for m in hoodiversary_members:
        mentions_string += f"{m['member'].mention} "
        year_string = 'year' if m['age'] == 1 else 'years'
        description += f"{random.choice(emoji_list)} {m['member'].mention} has been aboard The Hood for {m['age']} {year_string}!\nJoined {m['member'].joined_at.strftime('%x')}\n\n"

      if len(description) > 4096:
        description = ""
        for m in hoodiversary_members:
          description += f"{m['member'].mention} Joined {m['member'].joined_at.strftime('%x')}\n"

      embed = discord.Embed(
        title="These FoDs Are Celebrating Their Hoodiversary!",
        description=description,
        color=discord.Color.random()
      )
      embed.set_thumbnail(url=random.choice(config["handlers"]["xp"]["celebration_images"]))
      embed.set_footer(text="If not already present, you've also been awarded a Captain Picard Day badge!\nUse '/badges showcase' to check it out!")
      channel_ids = get_channel_ids_list(config["tasks"]["hoodiversary"]["channels"])
      for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        await channel.send(f"{header_image_url}")
        await channel.send(f"Happy Hoodiversary to you {mentions_string}!")
        await channel.send(embed=embed)
    except Exception as e:
      logger.info(traceback.format_exc())

  return {
    "task": hoodiversary,
    "crontab": config["tasks"]["hoodiversary"]["crontab"]
  }