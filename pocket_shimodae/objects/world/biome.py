from common import *
import csv
from . import Weather

with open("pocket_shimodae/data/fishing_biomes.csv") as file:
  csvdata = csv.DictReader(file)
  bdata = {}
  for row in csvdata:
    if not bdata.get(row["biome"].lower()):
      bdata[row["biome"].lower()] = []

    bdata[row["biome"].lower()].append({
      "fish" : row.get("fish"),
      "months" : row.get("months").split("|"),
      "weather_types": row.get("weather_types").split("|")
    })
  logger.info(bdata)
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}BIOME FISHING DATA{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")

class PoshimoBiome(object):
  """ an environment for locations, contains list of fish and wild poshimo and weather """
  def __init__(self, name:str, fish:list=[], weather_types:list=[Weather.SUNNY], emoji:str="🌻", wild_poshimo:list=[]) -> None:
    self.name = name
    self.possible_weather_types = weather_types
    self.fish = fish
    self.emoji = emoji
    self.wild_poshimo = wild_poshimo
    self.fishing_data = bdata.get(self.name.lower(), [])

  def __str__(self) -> str:
    return f"{self.emoji}"