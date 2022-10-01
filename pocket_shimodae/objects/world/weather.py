from common import *
from enum import Enum, auto

weather_emoji = [
  "🌞",
  "🌥",
  "🌦",
  "☁",
  "☔",
  "🌧",
  "⛈",
  "❄",
  "🌨",
  "🍃",
  "🌪",
  "🌫"
]

class Weather(Enum):
  SUNNY = auto()
  PARTLY_CLOUDY = auto()
  OVERCAST = auto()
  CLOUDY = auto()
  RAINY = auto()
  HEAVY_RAIN = auto()
  THUNDERSTORM = auto()
  SNOWY = auto()
  BLIZZARD = auto()
  WINDY = auto()
  WIND_STORM = auto()
  FOGGY = auto()

  def __str__(self):
    return f"{weather_emoji[self.value]}"
  def full_name(self):
    return f"{self.name.replace('_', ' ').capitalize()} {weather_emoji[self.value]}"