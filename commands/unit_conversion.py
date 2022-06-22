from .common import *

from quantulum3 import parser
from pint import UnitRegistry

ureg = UnitRegistry()
uQ = ureg.Quantity
emojis = config["emojis"]

def format_trailing(value):
  return re.sub('\.0$', '', f"{value}")


async def handle_mentioned_units(message:discord.Message):

  if message.author.bot:
    return

  quants = parser.parse(message.content)
  if quants:
    for quant in quants:
      value = quant.value
      unit_name = quant.unit.name

      #logger.info(f"(value: {value}, unit_name: {unit_name})")

      embed = discord.Embed(color=discord.Color.greyple())
      # liters <-> gallons
      if 'litre' in unit_name and 'millilitre' not in unit_name:
        liters = value * ureg.liter
        embed.description = f"{format_trailing(value)} liters is {'{:.2f}'.format(liters.to('gallon').magnitude)} gallons!"
        await message.channel.send(embed=embed)
        continue
      if 'gallon' in unit_name:
        gallons = value * ureg.gallon
        embed.description = f"{format_trailing(value)} gallons is {'{:.2f}'.format(gallons.to('liter').magnitude)} liters!"
        await message.channel.send(embed=embed)
        continue
      # miles <-> kilometers
      if 'mile' in unit_name:
        miles = value * ureg.mile
        embed.description = f"{format_trailing(value)} miles is {'{:.2f}'.format(miles.to('kilometer').magnitude)} kilometers!"
        await message.channel.send(embed=embed)
        continue
      if 'kilometre' in unit_name:
        kilometers = value * ureg.kilometer
        embed.description = f"{format_trailing(value)} kilometers is {'{:.2f}'.format(kilometers.to('mile').magnitude)} miles!"
        await message.channel.send(embed=embed)
        continue
      # feet <-> meters
      if 'foot' in unit_name:
        feet = value * ureg.foot
        embed.description = f"{format_trailing(value)} feet is {'{:.2f}'.format(feet.to('meter').magnitude)} meters!"
        await message.channel.send(embed=embed)
        continue
      if 'metre' in unit_name and 'cubic' not in unit_name:
        meters = value * ureg.meter
        embed.description = f"{format_trailing(value)} meters is {'{:.2f}'.format(meters.to('foot').magnitude)} feet!"
        await message.channel.send(embed=embed)
        continue
      # pounds <-> kilograms
      if 'pound-mass' in unit_name:
        pounds = value * ureg.pound
        embed.description = f"{format_trailing(value)} pounds is {'{:.2f}'.format(pounds.to('kilogram').magnitude)} kilograms!"
        await message.channel.send(embed=embed)
        continue
      if 'kilogram' in unit_name:
        kilograms = value * ureg.kilogram
        embed.description = f"{format_trailing(value)} kilograms is {'{:.2f}'.format(kilograms.to('pound').magnitude)} pounds!"
        await message.channel.send(embed=embed)
        continue
      # celsius <-> fahrenheit
      if 'fahrenheit' in unit_name:
        degrees_f = uQ(value, ureg.degF)
        embed.description = f"{format_trailing(value)}°F is {'{:.2f}'.format(degrees_f.to('degC').magnitude)}°C!"
        await message.channel.send(embed=embed)
        continue
      if 'celsius' in unit_name:
        degrees_c = uQ(value, ureg.degC)
        embed.description = f"{format_trailing(value)}°C is {'{:.2f}'.format(degrees_c.to('degF').magnitude)}°F!"
        await message.channel.send(embed=embed)
        continue

    if embed.description:
      logger.info(f"Unit conversion for {Style.BRIGHT}{message.author.display_name}{Style.NORMAL} in #{Style.BRIGHT}{message.channel.name}{Style.NORMAL}! {Fore.LIGHTBLUE_EX}WOLOLOLOLOLO{Fore.RESET}")  
