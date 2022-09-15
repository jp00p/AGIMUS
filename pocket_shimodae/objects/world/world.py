from common import *
from random import Random
from datetime import date
from .biome import PoshimoBiome
from .weather import Weather
from .location import PoshimoLocation

class PoshimoWorld(object):
  """ The (a?) world of Poshimo! Contains all the Locations a trainer can visit """
  def __init__(self):
    # random seed is based on today's date + the current hour!
    # so if the bot restarts, weather and stuff will be the same for the time period.
    # and no need to save in db! wow!
    now = datetime.now()
    today_seed = f"{now.year}{now.month}{now.day}{now.hour}"
    self.random = Random(today_seed)
    logger.info(f"\nNOW: {now}\nSEED: {today_seed}\nRANDOM INT 1-100: {self.random.randint(1,100)} {self.random.randint(1,100)} {self.random.randint(1,100)}")

    self.biomes = {
      "grasslands" : PoshimoBiome("Grasslands", weather_types=[Weather.SUNNY, Weather.CLOUDY, Weather.PARTLY_CLOUDY, Weather.RAINY], emoji="🌼")
    }
    self.locations = {
      "starting_zone" : PoshimoLocation("Vertiform City", self)
    }