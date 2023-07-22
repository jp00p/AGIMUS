import datetime
import json
import random

import discord
from discord.ext.commands import Bot

from common import config, get_channel_ids_list, logger
from queries import birthdays as db


def birthdays_task(bot: Bot):
  """
  Every day, send out a birthday greeting to all users that have saved it to their settings, and also important people
  in Star Trek
  """
  
  with open(config['tasks']['birthdays']['data']) as f:
    trek_birthdays = json.load(f)
    
  birthday_messages = (
    "Everybody wish them well as you see them in the server",
    "Fun will now commence",
    "There will be cake",
    "One more trip around the sun",
  )
  
  async def birthdays():
    enabled = config["tasks"]["birthdays"]["enabled"]
    if not enabled:
      return

    header_image = "https://i.imgur.com/xMycyhz.png"
    
    today = datetime.date.today()
    user_ids = db.get_users_with_birthday(today.month, today.day)
    description = [
      f"<@{uid}>" for uid in user_ids
    ]
    
    celebrities = trek_birthdays[today.strftime('%b')].get(today.strftime('%d'), [])
    description.extend(celebrities)
      
    if today.month == 2 and today.day == 28 and today.year % 4 > 0:
      user_ids = db.get_users_with_birthday(2, 29)
      description.extend(
        f"<@{uid}>" for uid in user_ids
      )
      
    if len(description) == 0:
      logger.info("There were no birthdays today")
      return
    
    random.shuffle(description)
    
    embed = discord.Embed(
      title="Today's important Star Trek birthdays",
      description="\n\n".join(description),
      color=discord.Color.fuchsia()
    )
    embed.set_footer(text=random.choice(birthday_messages))
    channel_ids = get_channel_ids_list(config["tasks"]["birthdays"]["channels"])
    for channel_id in channel_ids:
      channel = bot.get_channel(channel_id)
      await channel.send(header_image)
      await channel.send(embed=embed)

  return {
    "task": birthdays,
    "crontab": config["tasks"]["birthdays"]["crontab"]
  }
