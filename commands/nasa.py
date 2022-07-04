import datetime
import json

# import re
# from os.path import exists
import requests
from common import *

NASA_TOKEN = os.getenv('NASA_TOKEN')

# nasa() - Entrypoint for !nasa command
# message[required]: discord.Message
# This function is the main entrypoint of the !nasa command
async def nasa(message:discord.Message):
  logger.info(f"{Fore.LIGHTBLUE_EX}NASA: Starting NASA API call{Fore.RESET}")
  if not NASA_TOKEN:
    logger.error(f"{Fore.RED}NASA_TOKEN not set{Fore.RESET}")
    await message.channel.send("NASA_TOKEN not set: https://api.nasa.gov/")
    return
  user_command = message.content.lower().split()
  logger.info(user_command)
  if len(user_command) == 1:
    start_date = datetime.date(1996, 1, 1)
    logger.debug('starting from: ' + start_date.isoformat())
    end_date = datetime.date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day)
    logger.debug('today: ' + end_date.isoformat())

    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    target_date = start_date + datetime.timedelta(days=random_number_of_days)
  elif len(user_command) > 1:
    if user_command[1].lower() == "today":
      target_date = datetime.date(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day)
    else:
      try:
          datetime.datetime.strptime(user_command[1], '%Y-%m-%d')
      except ValueError:
          embed=discord.Embed(title="Invalid date format", \
            url="https://i.imgur.com/quQnKnk.jpeg", \
            description="https://api.nasa.gov/\nUsage: `!nasa [today|YYYY-MM-DD]`\nfor random date, pass no arguments `!nasa`", \
            color=0x111111)
          embed.set_thumbnail(url="https://i.imgur.com/quQnKnk.jpeg")
          await message.channel.send(embed=embed)
          return
      target_date = datetime.datetime.strptime(user_command[1], '%Y-%m-%d').date()
  url = 'https://api.nasa.gov/planetary/apod?api_key='+NASA_TOKEN+'&date='+target_date.isoformat()
  logger.debug("url: " + url) # shows token in url
  r = requests.get(url)
  if r.status_code == 200:
    logger.info(r)
    data = json.loads(r.content.decode())
    #logger.info(data)
    logger.info(f"{Fore.LIGHTGREEN_EX}Done with NASA API call{Fore.RESET}")
    if "copyright" in data:
      title = data["date"] + ': ' + data["title"] + ' (' + data["copyright"] + ')'
    else:
      title = data["date"] + ': ' + data["title"]

    if "hdurl" in data:
      image_url = data["hdurl"]
    else:
      image_url = data["url"]
    embed=discord.Embed(title=title, \
      url=image_url, \
      description=data["explanation"], \
      color=0x111111)
    embed.set_thumbnail(url=data["url"])
    await message.channel.send(embed=embed)
  else:
    embed=discord.Embed(title="No Nasa data for this date: " + target_date.isoformat(), \
      url="https://i.imgur.com/quQnKnk.jpeg", \
      description="https://api.nasa.gov/\nUsage: `!nasa [today|YYYY-MM-DD]`\nfor random date, pass no arguments `!nasa`", \
      color=0x111111)
    embed.set_thumbnail(url="https://i.imgur.com/quQnKnk.jpeg")
    await message.channel.send(embed=embed)
