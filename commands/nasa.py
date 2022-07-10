import requests
from common import *
from datetime import date as dtdate

from utils.check_channel_access import access_check

NASA_TOKEN = os.getenv('NASA_TOKEN')

# nasa() - Entrypoint for /nasa command
# This function is the main entrypoint of the /nasa command
@bot.slash_command(
  name="nasa",
  description="Get a random or specific 'Picture of the Day' from NASA"
)
@option(
  name="date",
  description="Date? ('today' or YYYY-MM-DD')",
  required=False
)
@commands.check(access_check)
async def nasa(ctx:discord.ApplicationContext, date:str):
  try:
    logger.info(f"{Fore.LIGHTBLUE_EX}NASA: Starting NASA API call{Fore.RESET}")
    if not NASA_TOKEN:
      logger.error(f"{Fore.RED}NASA_TOKEN not set{Fore.RESET}")
      await ctx.respond("NASA_TOKEN not set: https://api.nasa.gov/", ephemeral=True)
      return
    if date is None:
      start_date = dtdate(1996, 1, 1)
      logger.debug('starting from: ' + start_date.isoformat())
      end_date = dtdate(dtdate.today().year, dtdate.today().month, dtdate.today().day)
      logger.debug('today: ' + end_date.isoformat())

      time_between_dates = end_date - start_date
      days_between_dates = time_between_dates.days
      random_number_of_days = random.randrange(days_between_dates)
      target_date = start_date + timedelta(days=random_number_of_days)
    else:
      if date == "today":
        target_date = dtdate(dtdate.today().year, dtdate.today().month, dtdate.today().day)
      else:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            embed=discord.Embed(
              title="Invalid date format",
              url="https://i.imgur.com/quQnKnk.jpeg",
              description="https://api.nasa.gov/\nUsage: `/nasa [today|YYYY-MM-DD]`\nfor random date, pass no arguments `/nasa`",
              color=0x111111
            )
            embed.set_thumbnail(url="https://i.imgur.com/quQnKnk.jpeg")
            await ctx.respond(embed=embed)
            return
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
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
      embed=discord.Embed(
        title=title,
        url=image_url,
        description=data["explanation"],
        color=0x111111
      )
      embed.set_thumbnail(url=data["url"])
      await ctx.respond(embed=embed)
    else:
      embed=discord.Embed(
        title="No Nasa data for this date: " + target_date.isoformat(),
        url="https://i.imgur.com/quQnKnk.jpeg",
        description="https://api.nasa.gov/\nUsage: `/nasa [today|YYYY-MM-DD]`\nfor random date, pass no arguments `/nasa`",
        color=0x111111
      )
      embed.set_thumbnail(url="https://i.imgur.com/quQnKnk.jpeg")
      await ctx.respond(embed=embed)
  except BaseException as e:
    logger.info(traceback.format_exc())