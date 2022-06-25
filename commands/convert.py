from quantulum3 import parser
from pint import UnitRegistry
import re

from .common import *
from utils.check_channel_access import *
from utils.timekeeper import *

ureg = UnitRegistry()
Q_ = ureg.Quantity

command_config = config["commands"]["convert"]
emojis = config["emojis"]

# Load JSON Data
f = open(command_config["data"])
convert_data = json.load(f)
f.close()


@slash.slash(
  name="convert",
  description="Convert an Imperial or Metric unit to its counterpart!",
  guild_ids=config["guild_ids"],
  options=[
    create_option(
      name="conversion",
      description="What conversion unit would you like? Example: 10km",
      required=True,
      option_type=3
    ),
    create_option(
      name="public",
      description="Send clip to the channel?",
      required=False,
      option_type=5,
    )
  ]
)
@slash_check_channel_access(command_config)
async def convert(ctx:SlashContext, **kwargs):
  conversion = kwargs.get('conversion')
  public = kwargs.get('public')
  private = not public

  if re.search('([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?( ?[AaPp][Mm])?', conversion) != None:
    time_embed = discord.Embed(
      title="Sorry, unable to convert times!",
      color=discord.Color.greyple()
    )
    await ctx.send(embed=time_embed, hidden=True)
    return

  # Private drops are not on the timer
  clip_allowed = True
  if not private:
    clip_allowed = await check_timekeeper(ctx)

  if not clip_allowed:
    await ctx.send(f"{emojis.get('ohno')} Someone in the channel has already requested a conversion too recently. Please wait a minute before another conversion!", hidden=True)
    return

  found_minimum_match = False
  quants = parser.parse(conversion)
  if quants:
    if len(quants) > 2:
      await ctx.send(f"{emojis.get('ohno')} Too many conversions values provided.", hidden=True)
      return

    for quant in quants:
      value = quant.value
      unit_name = quant.unit.name.lower()

      # logger.info(f"(value: {value}, unit_name: {unit_name})")

      # Unit parser sometimes catches some units we do not want to convert
      # an NFT = "newton foot" for example
      # So ignore the following list
      for partial in ['cubic', 'deci', 'deka', 'hecto', 'exa', 'newton']:
        if partial in unit_name:
          continue

      embed = discord.Embed(color=discord.Color.greyple())

      units = convert_data["units"]
      for unit_key in units:
        unit = units[unit_key]
        unit_names = unit_name.split()
        if any(x in unit_names for x in unit["matches"]) and not any(x in unit_names for x in unit["ignored_matches"]):
          converted_value = Q_(value, unit_key)
          embed.description = f"{format_trailing(value)} {unit['plural']} is {'{:.2f}'.format(converted_value.to(unit['convert_to']).magnitude)} {unit['convert_to_plural']}!"
          await ctx.send(embed=embed, hidden=private)
          found_minimum_match = True

      # Special casing for stone -> kilograms
      pound_match = re.search("(\d+.?\d+?) stone", conversion)
      if pound_match:
        value = pound_match.groups()[0]
        pound_value = int(value) * 14
        pounds = pound_value * ureg.pound
        embed.description = f"{format_trailing(value)} stone is {'{:.2f}'.format(pounds.to('kilogram').magnitude)} kilograms!"
        await ctx.send(embed=embed, hidden=public)
        found_minimum_match = True

      if embed.description:
        logger.info(f"Unit conversion for {Style.BRIGHT}{ctx.author.display_name}{Style.NORMAL} in #{Style.BRIGHT}{ctx.channel.name}{Style.NORMAL}! {Fore.LIGHTBLUE_EX}WOLOLOLOLOLO{Fore.RESET}")

      continue

  if not found_minimum_match:
    await ctx.send(embed=discord.Embed(
      title="No supported unit match found!",
      color=discord.Color.dark_red()
    ), hidden=True)
    return

  if not private:
    set_timekeeper(ctx)

def format_trailing(value):
  return re.sub('\.0$', '', f"{value}")
