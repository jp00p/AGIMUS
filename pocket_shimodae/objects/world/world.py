from common import *
from random import Random
from datetime import date

from pocket_shimodae.objects.poshimo.poshimo import Poshimo
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
      "grasslands" : PoshimoBiome(
        name="Grasslands", 
        weather_types=[Weather.SUNNY, Weather.CLOUDY, Weather.PARTLY_CLOUDY, Weather.RAINY], 
        emoji="🌼"
      ),
      "wastelands" : PoshimoBiome(
        name="Wastelands", 
        weather_types=[Weather.STORMY], 
        emoji="🚧"
      ),
      "metropolis" : PoshimoBiome(
        name="Metropolis",
        weather_types=[Weather.CLOUDY, Weather.RAINY],
        emoji="🏙"
      ),
      "tundra" : PoshimoBiome(
        name="Snowy Tundra",
        weather_types=[Weather.SNOWY],
        emoji="⛰"
      )
    }
    self.locations = {
      "starter_zone" : PoshimoLocation(
        name="Vertiform City",
        biome=self.biomes["metropolis"], 
        world=self,
        description="The mysterious city of legend, where Poshimo are said to have been born.",
        s="test_zone",
        color=f"{Fore.LIGHTBLUE_EX}"
      ),
      "test_zone" : PoshimoLocation(
        name="The Brown Fields", 
        biome=self.biomes["wastelands"], 
        world=self,
        description="A central juncture in this realm. No place for lovemaking.",
        n="starter_zone",
        e="field",
        w="plowland",
        color=f"{Fore.LIGHTMAGENTA_EX}"
      ),
      "field" : PoshimoLocation(
        name="Field of Dreams",
        biome=self.biomes["grasslands"],
        world=self,
        description="They built it. You came.",
        w="test_zone",
        color=f"{Fore.LIGHTGREEN_EX}"
      ),
      "plowland" : PoshimoLocation(
        name="Mr. Plow's Winter Wonderland",
        biome=self.biomes["tundra"],
        world=self,
        description="Pornography stores as far as the eye can see.  Open all night.",
        e="test_zone",
        color=f"{Fore.LIGHTWHITE_EX}"
      )
    }