from common import *
from .weather import Weather
from .biome import PoshimoBiome

class PoshimoLocation:
  """ A location in our game world """
  def __init__(self, name):
    self.name = name
    self.location_data = {} # pull from file based on name
    self.wild_poshimo = {}
    self.weather = Weather.SUNNY
    self.biome = PoshimoBiome("Default")
    self.fish = {}
    self.items = {}
    self.description = "A default description of a location"
    self.quests = None
    self.shop = None
    self.paths = {}

  def __str__(self):
    return f"{self.name} {self.weather} ({self.biome})"