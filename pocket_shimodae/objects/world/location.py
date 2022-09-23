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
    self.weather:Weather = weather_choice
    logger.info(f"{Fore.CYAN}Weather{Fore.RESET} in {Style.BRIGHT}{self.name}{Style.RESET_ALL} has been changed to {Fore.LIGHTYELLOW_EX}{self.weather.name}{Fore.RESET}")