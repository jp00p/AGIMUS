from common import *
import csv
from typing import List, Dict, TypedDict, Any
from . import PoshimoBiome, Weather, PoshimoShop

with open("pocket_shimodae/data/fishing_locations.csv") as file:
  csvdata = csv.DictReader(file)
  ldata = {}
  for row in csvdata:
    if not ldata.get(row["location"].lower()):
      ldata[row["location"].lower()] = []

    ldata[row["location"].lower()].append({
      "fish" : row.get("fish"),
      "months" : row.get("months").split("|"),
      "weather_types": row.get("weather_types").split("|")
    })

  ps_log(f"Fishing spots: {len(ldata)}")

FishingShapeDict = TypedDict('FishingShape', {'shape': List[List[int]], 'num_fish': int, 'shape_name':str})

fishing_shapes: dict = {
  "ocean" : {
    "shape": [
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
    ],
    "num_fish": 5,
    "shape_name":"ocean"
  },
  "lake" : {
    "shape": [
      [0,0,1,0,0],
      [0,1,1,1,0],
      [1,1,1,1,1],
      [0,1,1,1,0],
      [0,0,1,0,0],
    ],
    "num_fish":3,
    "shape_name":"lake"
  },
  "pond" : {
    "shape":[
      [0,0,0,0,0],
      [0,1,1,1,0],
      [0,1,1,1,0],
      [0,1,1,1,0],
      [0,0,0,0,0],
    ],
    "num_fish":2,
    "shape_name":"pond"
  },
  "river" : {
    "shape": [
      [0,0,0,0,1],
      [1,0,1,1,1],
      [1,1,1,1,0],
      [0,1,0,1,1],
      [0,0,0,0,1],
    ],
    "num_fish":3,
    "shape_name":"river"
  }
}
  

class PoshimoLocation(object):
  """ A location in the world, must have a biome, can have its own set of fish and poshimo """
  def __init__(
      self, 
      name:str="", 
      biome:PoshimoBiome=None, 
      description=None, 
      color=f"{Fore.WHITE}",
      wild_poshimo=[],
      n=None, 
      e=None, 
      s=None, 
      w=None,
      flags=[],
      image=None,
      fishing_shape=None,
      shop=None
    ):
    self.name:str = name
    self.weather:Weather = Weather.SUNNY
    self.biome:PoshimoBiome = biome
    self.fish:dict = {}
    self.items:dict = {}
    self.flags:list = flags
    self.description:str = description
    self.quests = None
    self.shop = None
    self.image:str = image
    self.fishing_data:dict = ldata.get(self.name.lower(), {})
    all_wild_poshimo = wild_poshimo + self.biome.wild_poshimo
    self.wild_poshimo:set = set(all_wild_poshimo)
    self.fishing_shape:FishingShapeDict = fishing_shapes.get(fishing_shape, None)
    self.shop = None
    if shop:
      self.shop = PoshimoShop(shop)
      
    self.paths = {
      "n" : n,
      "e" : e,
      "s" : s,
      "w" : w
    }

  def __str__(self):
    return f"{self.biome} {self.name} {self.weather}"

  def set_weather(self, weather_choice):
    """ set this location's weather """
    self.weather:Weather = weather_choice
    #logger.info(f"{Fore.CYAN}Weather{Fore.RESET} in {Style.BRIGHT}{self.name}{Style.RESET_ALL} has been changed to {Fore.LIGHTYELLOW_EX}{self.weather.name}{Fore.RESET}")

  def build_fish_list(self, fishdata:dict) -> list:
    """ builds the list of fish available for given dataset """
    current_month = datetime.now().month
    fishlist = []

    for f in fishdata:
      month_valid, weather_valid = False, False
      logger.info(f)
      if f.get("months") != [""]:
        if str(current_month) in f["months"]:
          month_valid = True
      else:
        month_valid = True # no month specified, it's every month!
      if f.get("weather_types") != [""]:
        if self.weather in f["weather_types"]:
          weather_valid = True
      else:
        weather_valid = True # no weather specified, it's every weather!
      if month_valid and weather_valid and f.get("fish"):
        fishlist.append(f["fish"])
    return fishlist

  def find_fish(self) -> set:
    """ figure out what kind of fish are available right now """
    biome_fishing_data = self.biome.fishing_data
    biome_list = self.build_fish_list(biome_fishing_data)
    location_list = self.build_fish_list(self.fishing_data)
    eligible_fish = biome_list + location_list
    return eligible_fish