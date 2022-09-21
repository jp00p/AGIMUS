from common import *
from random import Random
from datetime import date
from typing import Dict
from . import PoshimoBiome, Weather, PoshimoLocation


class PoshimoWorld(object):
  """ The (a?) world of Poshimo! Contains all the Locations a trainer can visit """
  def __init__(self):
    # random seed is based on today's date + the current hour!
    # so if the bot restarts, weather and stuff will be the same for the time period.
    # and no need to save in db! wow!
    now:datetime = datetime.now()
    today_seed:str = f"{now.year}{now.month}{now.day}{now.hour}"
    self.random:Random = Random(today_seed)
    #logger.info(f"\nNOW: {now}\nSEED: {today_seed}\nRANDOM INT 1-100: {self.random.randint(1,100)} {self.random.randint(1,100)} {self.random.randint(1,100)}")
    
    self.biomes:Dict[str, PoshimoBiome] = {
      "grasslands" : PoshimoBiome(
        name="Grasslands", 
        weather_types=[Weather.SUNNY, Weather.CLOUDY, Weather.PARTLY_CLOUDY, Weather.RAINY], 
        emoji="🌼",
        wild_poshimo=[
          (100, "Pikachu"),
        ]
      ),
      "wastelands" : PoshimoBiome(
        name="Wastelands", 
        weather_types=[Weather.STORMY], 
        emoji="🚧",
        wild_poshimo=[
          (100, "Pikachu"),
        ]
      ),
      "metropolis" : PoshimoBiome(
        name="Metropolis",
        weather_types=[Weather.CLOUDY, Weather.RAINY],
        emoji="🏙",
        wild_poshimo=[
          (100, "Pikachu"),
        ]
      ),
      "tundra" : PoshimoBiome(
        name="Snowy Tundra",
        weather_types=[Weather.SNOWY],
        emoji="⛰",
        wild_poshimo=[
          (100, "Pikachu"),
        ]
      )
    }
    self.locations : Dict[str, PoshimoLocation] = {
      "starter_zone" : PoshimoLocation(
        name="Vertiform City",
        biome=self.biomes["metropolis"], 
        description="The mysterious city of legend, where Poshimo are said to have been born.",
        s="test_zone"
      ),
      "test_zone" : PoshimoLocation(
        name="The Brown Fields", 
        biome=self.biomes["wastelands"], 
        description="A central juncture in this realm. No place for lovemaking.",
        n="starter_zone",
        e="field",
        w="plowland"
      ),
      "field" : PoshimoLocation(
        name="Field of Dreams",
        biome=self.biomes["grasslands"],
        description="They built it. You came.",
        w="test_zone"
      ),
      "plowland" : PoshimoLocation(
        name="Mr. Plow's Winter Wonderland",
        biome=self.biomes["tundra"],
        description="Pornography stores as far as the eye can see.  Open all night.",
        e="test_zone",
        wild_poshimo=[
          (100, "Pikachu"),
        ]
      )
    }

    self.set_weather() # set the initial weather on load
    logger.info(f"Poshimo World loaded!")
    # end of init


  def set_weather(self):
    """ sets the weather for every location in the world 
    
    possible weather types are determined by the location's biome!

    this uses its own random seed based on the hour, so it won't change on restart unless the hour changes
    """
    for location in self.locations.values():
      weather_choice = self.random.choice(location.biome.possible_weather_types)
      location.set_weather(weather_choice)