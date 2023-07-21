import datetime

import discord

from common import bot, config
from queries import birthdays as db

birthday_command_group = bot.create_group('birthday', "Set and clear your birthday")


@birthday_command_group.command(
  name='set',
  description="Set your birthday so that everyone can celebrate it"
)
@discord.commands.option(
  name='month',
  description="Choose a month",
  required=True
)
@discord.commands.option(
  name='day',
  description='Chose the day',
  required=True
)
async def birthday_set(ctx: discord.ApplicationContext, month: int, day: int):
  """
  For when a user wants the birthday greetings from AGIMUS
  """
  await ctx.defer(ephemeral=True)
  try:
    datetime.date(2020, month, day)  # Choose a leap day for all those that are Feb 29th
  except ValueError:
    await ctx.followup.send(embed=discord.Embed(
      title="That is not a valid birthday",
      color=discord.Color.red(),
    ))
    return
  
  user_id = ctx.user.id
  db.set_birthday(user_id, month, day)
  
  today = datetime.date.today()
  if month == 2 and day == 29:
    day -= 1
  if today > datetime.date(today.year, month, day):
    year = today.year + 1
  else:
    year = today.year
  
  (minute, hour, *_) = config["tasks"]["birthdays"]["crontab"].split(' ')
  birthday = datetime.datetime(year, month, day, int(hour), int(minute))  # Change this if the time changes
  
  embed = discord.Embed(
    title="AGIMUS has your birthday",
    description=f"On <t:{int(birthday.timestamp())}:F> we will celebrate you",
    color=discord.Color.blurple()
  )
  embed.set_footer(text="Make sure that is your actual birthday and timezones haven’t broken everything")
  await ctx.followup.send(embed=embed)


@birthday_command_group.command(
  name='clear',
  description="Make AGIMUS forgot your birthday"
)
async def birthday_clear(ctx: discord.ApplicationContext):
  """
  I never should have given this evil bot my birthday.
  """
  await ctx.defer(ephemeral=True)
  db.clear_birthday(ctx.user.id)
  
  await ctx.followup.send(embed=discord.Embed(
    title="AGIMUS does not know your birthday",
    description="I get it.  I wouldn’t wait a bunch of randos on the Internet to know my personal information either.",
    color=discord.Color.red()
  ))
