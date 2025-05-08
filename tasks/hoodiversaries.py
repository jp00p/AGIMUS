from common import *

from queries.badge_info import db_get_badge_info_by_name
from queries.badge_instances import *
from queries.echelon_xp import db_get_echelon_progress
from utils.badge_instances import create_new_badge_instance_by_filename

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

      # Award special Captain Picard Day badge (at all prestige tiers the user does not currently possess it at)!
      picard_day_badge_info = await db_get_badge_info_by_name("Captain Picard Day")
      for m in hoodiversary_members:
        user_id = m["member"].id
        existing_badges = await db_get_user_badge_instances(user_id)
        existing_pairs = {(b['badge_name'], b['prestige_level']) for b in existing_badges}

        echelon_progress = await db_get_echelon_progress(user_id)
        current_prestige = echelon_progress.get('current_prestige_tier', 0)
        for prestige in range(current_prestige + 1):
          key = (picard_day_badge_info['badge_name'], prestige)
          if key not in existing_pairs:
            await create_new_badge_instance_by_filename(user_id, picard_day_badge_info['badge_filename'], prestige_level=prestige, event_type="prestige_echo")

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
      embed.set_footer(text="If not already present, you've also been awarded a Captain Picard Day badge (at all Prestige Tiers you have currently unlocked)!\nUse '/badges showcase' to check it out!")
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