from common import *
from .weather import Weather
from .biome import PoshimoBiome

class PoshimoLocation:
  """ A location in our game world """
  def __init__(
      self, 
      name:str="", 
      biome:PoshimoBiome=None, 
      world=None, 
      description=None, 
      color=f"{Fore.WHITE}",
      n=None, 
      e=None, 
      s=None, 
      w=None
    ):
    self.name = name
    self.world = world
    self.wild_poshimo = {}
    self.weather:Weather = Weather.SUNNY
    self.biome:PoshimoBiome = biome
    self.fish = {}
    self.items = {}
    self.description = description
    self.quests = None
    self.shop = None
    self.color = color
    self.paths = {
      "n" : n,
      "e" : e,
      "s" : s,
      "w" : w
    }
    self.set_weather()

  def __str__(self):
    return f"{self.biome} {self.name} {self.weather}"

  def set_weather(self):
    #TODO: this will need to happen every hour or so, as well
    weather_choice = self.world.random.choice(self.biome.possible_weather_types)
    self.weather = weather_choice
    logger.info(f"Weather in {self.name} has been changed to {self.weather.name}")