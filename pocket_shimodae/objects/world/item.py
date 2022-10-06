from common import *
from enum import Enum, auto
import csv

with open("pocket_shimodae/data/poshimo_items.csv") as file:
  csvdata = csv.DictReader(file)
  idata = {}
  for row in csvdata:
    idata[row.get("name").lower()] = {
      "name":row.get("name", ""),
      "description":row.get("description", ""),
      "type":row.get("type", ""),
      "function_code":row.get("function_code", ""),
      "power":row.get("power", 0),
      "use_where":row.get("use_where", ""),
      "sell_price":row.get("sell_price", 0)

    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}ITEM DATA{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")
  logger.info(idata)


class UseWhere(Enum):
  USE_ANYWHERE = 0
  USE_IN_FIELD = 1
  USE_IN_BATTLE = 2

class ItemTypes(Enum):
  RESTORE = auto()
  MODIFY_STAGE = auto()
  CURE_STATUS = auto()
  NONE = auto()

class FunctionCodes(Enum):
  HP = auto()
  HP_ALL = auto()
  STAMINA = auto()
  STAMINA_ALL = auto()

class PoshimoItem(object):
  def __init__(self, name:str):
    self.name:str = name
    self.idata:dict = idata[self.name.lower()]
    self.description:str = self.idata["description"]
    self.type:ItemTypes = ItemTypes[self.idata["type"].upper()]
    self.use_where:UseWhere = UseWhere[self.idata["use_where"].upper()]
    self.function_code:str = FunctionCodes[self.idata["function_code"].upper()]
    self.power:int = self.idata["power"]
    self.sell_price:int = self.idata["sell_price"]