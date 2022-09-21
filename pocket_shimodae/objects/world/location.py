from common import *
from . import PoshimoBiome, Weather

class PoshimoLocation:
  """ A location in our game world """
  def __init__(
      self, 
      name:str="", 
      biome:PoshimoBiome=None, 
      description=None, 
      color=f"{Fore.WHITE}",
      wild_poshimo=[],
      n=None, 
      e=None, 
      s=None, 
      w=None
    ):
    self.name:str = name
    self.wild_poshimo = {}
    self.weather:Weather = Weather.SUNNY
    self.biome:PoshimoBiome = biome
    self.fish = {}
    self.items = {}
    self.description = description
    self.quests = None
    self.shop = None
    self.color = color
    self.wild_poshimo = set(list(self.biome.wild_poshimo) + list(wild_poshimo))
    self.paths = {
      "n" : n,
      "e" : e,
      "s" : s,
      "w" : w
    }

  def __str__(self):
    return f"{self.biome} {self.name} {self.weather}"

  def set_weather(self, weather_choice):
    self.weather = weather_choice
    logger.info(f"Weather in {self.name} has been changed to {self.weather.name}")