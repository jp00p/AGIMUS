from common import *
from enum import Enum, auto

weather_emoji = ["🌞","🌤","⛅","🌧","🌨","🍃","🌩","🌫"]

class Weather(Enum):  
  SUNNY = 1
  PARTLY_CLOUDY = 2
  CLOUDY = 3
  RAINY = 4
  SNOWY = 5
  WINDY = 6
  STORMY = 7
  FOGGY = 8
  def __str__(self):
    return f'{self.name.lower().replace("_", " ").capitalize()} {weather_emoji[self.value-1]}'

class PoshimoLocation:
  """ A location in our game world """
  def __init__(self, name):
    self.location_data = {} # pull from file based on name
    self.wild_poshimo = {}
    self.weather = None
    self.biome = None
    self.fish = {}
    self.items = {}
    self.description = None
    self.quests = None
    self.shop = None
    self.paths = {}