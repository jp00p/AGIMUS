from common import *
from enum import Enum, auto
import csv

with open("pocket_shimodae/data/poshimo_items.csv") as file:
  csvdata = csv.DictReader(file)
  item_data = {}
  for row in csvdata:
    item_data[row.get("name").lower()] = {
      "name": row.get("name", ""),
      "description": row.get("description", ""),
      "type": row.get("type", ""),
      "function_code": row.get("function_code", ""),
      "power": row.get("power", 0),
      "use_where": row.get("use_where", ""),
      "sell_price": row.get("sell_price", 0),
      "crafting_mats": row.get("crafting_mats", None)

    }
  ps_log(f"Items: {len(item_data)}")


class UseWhere(Enum):
  ''' where can this item be used? '''
  USE_ANYWHERE = auto()
  USE_IN_FIELD = auto()
  USE_IN_BATTLE = auto()
  NONE = auto()

class ItemTypes(Enum):
  ''' what kind of item is it? '''
  RESTORE = auto()
  MODIFY_STAGE = auto()
  CURE_STATUS = auto()
  CAPTURE = auto()
  CRAFTING = auto()
  RECIPE = auto()
  KEY = auto()
  NONE = auto()

class FunctionCodes(Enum):
  ''' what does the item do? '''
  HP = auto()
  HP_ALL = auto()
  STAMINA = auto()
  STAMINA_ALL = auto()
  NONE = auto()

class PoshimoItem(object):
  def __init__(self, name:str):
    self.name:str = name
    self.item_data:dict = item_data.get(self.name.lower())
    if not self.item_data:
      self.description = f"ERROR LOADING THIS ITEM {self.name} -- double check the spelling"
    self.description:str = self.item_data["description"]
    self.type:ItemTypes = ItemTypes[self.item_data["type"].upper()]
    self.use_where:UseWhere = UseWhere[self.item_data["use_where"].upper()]
    self.function_code:str = FunctionCodes[self.item_data["function_code"].upper()]
    self.power:int = int(self.item_data["power"])
    self.sell_price:int = int(self.item_data["sell_price"])
    self.crafting_mats = None
    if self.item_data["crafting_mats"] != '':
      self.crafting_mats = self.item_data["crafting_mats"].split("|")

  def __str__(self):
    return self.name.title()