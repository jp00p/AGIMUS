from . import Weather

class PoshimoBiome(object):
  def __init__(self, name, fish=[], weather_types=[Weather.SUNNY], emoji="🌻", wild_poshimo=[]):
    self.name = name
    self.possible_weather_types = weather_types
    self.fish = fish
    self.emoji = emoji
    self.wild_poshimo = wild_poshimo

  def __str__(self):
    return f"{self.emoji}"