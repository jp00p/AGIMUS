from .weather import Weather

class PoshimoBiome(object):
  def __init__(self, name, fish=[]):
    self.name = name
    self.possible_weather_types = [Weather.SUNNY]
    self.fish = fish

  def __str__(self):
    return f"{self.name}"