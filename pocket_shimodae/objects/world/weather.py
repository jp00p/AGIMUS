from common import *
from enum import Enum
weather_emoji = ["🌞","🌤","⛅","🌧","🌨","🍃","🌩","🌫"]

class Weather(Enum):
  SUNNY = 0
  PARTLY_CLOUDY = 1
  CLOUDY = 2
  RAINY = 3
  SNOWY = 4
  WINDY = 5
  STORMY = 6
  FOGGY = 7
  def __str__(self):
    return f"{weather_emoji[self.value]}"
  def full_name(self):
    return f"{self.name.replace('_', ' ').capitalize()} {weather_emoji[self.value]}"