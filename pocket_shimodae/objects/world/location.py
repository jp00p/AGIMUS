from common import *
from .weather import Weather
from .biome import PoshimoBiome

class PoshimoLocation:
  """ A location in our game world """
  def __init__(self, name:str, world):
    self.name = name
    self.world = world
    self.location_data = {} # pull from file based on name
    self.wild_poshimo = {}
    self.weather:Weather = Weather.SUNNY
    self.biome:PoshimoBiome = self.world.biomes["grasslands"]
    self.fish = {}
    self.items = {}
    self.description = "A default description of a location"
    self.quests = None
    self.shop = None
    self.paths = {}
    self.set_weather()

  def __str__(self):
    return f"{self.biome} {self.name} {self.weather}"

  def set_weather(self):
    # this will need to happen every hour or so, as well
    weather_choice = self.world.random.choice(self.biome.possible_weather_types)
    self.weather = weather_choice
    logger.info(f"Weather in {self.name} has been changed to {self.weather.name}")