from common import *
import csv
from random import Random
from datetime import date
from typing import Dict
from . import PoshimoBiome, Weather, PoshimoLocation

#TODO: move csv readers back into their respective files (like with shop and fish)
# why did i think this was better in the first place???

with open("pocket_shimodae/data/biomes.csv") as file:
  # load the base biome data from file
  csvdata = csv.DictReader(file)
  bdata = {}
  for row in csvdata:
    bdata[row["name"].lower()] = {
      "name" : row.get("name", ""),
      "weather_types" : row.get("weather_types").split("|"),
      "emoji" : row.get("emoji", "❓"),
      "wild_poshimo" : row.get("wild_poshimo","").split("|")
    }
  ps_log(f"Biomes: {len(bdata)}")

with open("pocket_shimodae/data/locations.csv") as file:
  # load the base location data from file
  csvdata = csv.DictReader(file)
  ldata = {}
  for row in csvdata:
    ldata[row["name"].lower()] = {
      "name" : row.get("name", ""),
      "biome" : row.get("biome","").lower(),
      "description" : row.get("description", ""),
      "wild_poshimo" : row.get("wild_poshimo","").split("|"),
      "flags" : row.get("flags","").split("|"),
      "n" : row.get("n", "").lower(),
      "e" : row.get("e", "").lower(),
      "s" : row.get("s", "").lower(),
      "w" : row.get("w", "").lower(),
      "fishing_shape" : row.get("fishing_shape", None),
      "shop" : row.get("shop", "").lower()
    }
  ps_log(f"Locations: {len(ldata)}")


# don't reinstantiate this object during the game
class PoshimoWorld(object):
  """ The (a?) world of Poshimo! Contains all the Locations a trainer can visit """
  def __init__(self):
    # random seed is based on today's date + the current hour!
    # so if the bot restarts, weather and stuff will be the same for the time period.
    # and no need to save in db! wow!
    now:datetime = datetime.now()
    today_seed:str = f"{now.year}{now.month}{now.day}{now.hour}"
    self.random:Random = Random(today_seed)
    self.locations : Dict[str, PoshimoLocation] = {}
    self.biomes : Dict[str, PoshimoBiome] = {}
    
    
    for id,biome in bdata.items():
      biome_poshimo = []
      for b in biome["wild_poshimo"]:
        p = b.split(",")
        if len(p) > 1: 
          biome_poshimo.append((p[0],float(p[1])))

      self.biomes[id] = PoshimoBiome(
        name=biome["name"],
        weather_types=[Weather[w.upper()] for w in biome["weather_types"]],
        emoji=biome["emoji"],
        wild_poshimo=biome_poshimo
      )

    for id,location in ldata.items():
      location_poshimo = []
      for l in location["wild_poshimo"]:
        p = l.split(",")
        if len(p) > 1: 
          biome_poshimo.append((p[0],p[1]))

      self.locations[id] = PoshimoLocation(
        name=location["name"],
        biome=self.biomes[location["biome"]],
        description=location["description"],
        n=location["n"],
        e=location["e"],
        s=location["s"],
        w=location["w"],
        wild_poshimo=location_poshimo,
        flags=location["flags"],
        fishing_shape=location["fishing_shape"],
        shop=location["shop"]
      )
    

    ps_log("The world comes back to life!")
    self.set_weather() # set the initial weather on load
    # end of init


  def set_weather(self):
    """ sets the weather for every location in the world 
    
    possible weather types are determined by the location's biome!

    this uses its own random seed based on the hour, so it won't change on restart unless the hour changes
    """
    for location in self.locations.values():
      weather_choice = self.random.choice(location.biome.possible_weather_types)
      location.set_weather(weather_choice)