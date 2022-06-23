from commands.common import *

from quantulum3 import parser
from pint import UnitRegistry

ureg = UnitRegistry()
uQ = ureg.Quantity
emojis = config["emojis"]

def format_trailing(value):
  return re.sub('\.0$', '', f"{value}")


async def handle_mentioned_units(message:discord.Message):

  if message.author.bot or message.content.startswith('http'):
    return

  quants = parser.parse(message.content)
  if quants:
    logger.info(quants)
    for quant in quants:
      value = quant.value
      unit_name = quant.unit.name.lower()

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
      # inches <-> centimeters
      if 'inch' in unit_name:
        inches = value * ureg.inch
        embed.description = f"{format_trailing(value)} inches is {'{:.2f}'.format(inches.to('centimeter').magnitude)} centimeters!"
        await message.channel.send(embed=embed)
        continue
      if 'centimetre' in unit_name:
        centimeters = value * ureg.centimeter
        embed.description = f"{format_trailing(value)} centimeters is {'{:.2f}'.format(centimeters.to('inch').magnitude)} inches!"
        await message.channel.send(embed=embed)
        continue
      # feet <-> meters
      if 'foot' in unit_name:
        feet = value * ureg.foot
        embed.description = f"{format_trailing(value)} feet is {'{:.2f}'.format(feet.to('meter').magnitude)} meters!"
        await message.channel.send(embed=embed)
        continue
      if 'metre' in unit_name:
        # 'metre' might catch some other stuff we don't want,
        # so early continue if one of these is in here
        should_ignore = False
        ignored_matches = ['cubic', 'deci', 'deka', 'hecto']
        for partial in ignored_matches:
          if partial in unit_name:
            should_ignore = True

        if should_ignore:
          continue

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
      # ounces <-> grams
      if 'ounce' in unit_name:
        ounces = value * ureg.ounce
        embed.description = f"{format_trailing(value)} ounces is {'{:.2f}'.format(ounces.to('gram').magnitude)} grams!"
        await message.channel.send(embed=embed)
        continue
      if 'gram' in unit_name:
        grams = value * ureg.gram
        embed.description = f"{format_trailing(value)} grams is {'{:.2f}'.format(grams.to('ounce').magnitude)} ounces!"
        await message.channel.send(embed=embed)
        continue
      # celsius <-> fahrenheit
      if 'fahrenheit' in unit_name or 'farad' in unit_name:
        # I don't think anyone's going to mention farads,
        # but farenheit keeps getting interpreted at it so catch it
        degrees_f = uQ(value, ureg.degF)
        embed.description = f"{format_trailing(value)}°F is {'{:.2f}'.format(degrees_f.to('degC').magnitude)}°C!"
        await message.channel.send(embed=embed)
        continue
      if 'celsius' in unit_name or 'centavo' in unit_name:
        # I don't think anyone's going to mention centavo,
        # but farenheit keeps getting interpreted at it so catch it
        degrees_c = uQ(value, ureg.degC)
        embed.description = f"{format_trailing(value)}°C is {'{:.2f}'.format(degrees_c.to('degF').magnitude)}°F!"
        await message.channel.send(embed=embed)
        continue

      # Special casing for stone -> kilograms
      stone_match = re.search(r"(\d+.?\d+?) stone", message.content.lower())
      if stone_match:
        value = stone_match.groups()[0]
        pound_value = int(value) * 14
        pounds = pound_value * ureg.pound
        embed.description = f"{format_trailing(value)} stone is {'{:.2f}'.format(pounds.to('kilogram').magnitude)} kilograms!"
        await message.channel.send(embed=embed)
        continue

    if embed.description:
      logger.info(f"Unit conversion for {Style.BRIGHT}{message.author.display_name}{Style.NORMAL} in #{Style.BRIGHT}{message.channel.name}{Style.NORMAL}! {Fore.LIGHTBLUE_EX}WOLOLOLOLOLO{Fore.RESET}")  
