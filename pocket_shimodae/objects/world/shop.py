from common import *
import csv
from typing import List, Tuple
from ..trainer import PoshimoTrainer
from ..world import PoshimoItem

with open("pocket_shimodae/data/shops.csv") as file:
  # load the base biome data from file
  csvdata = csv.DictReader(file)
  sdata = {}
  for row in csvdata:
    sdata[row["name"].lower()] = {
      "name" : row.get("name", "").title(),
      "stock" : row.get("stock", "").split("|")
    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}SHOP DATA{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")
  logger.info(sdata)

class PoshimoShop(object):
  """ A shop! Lets players buy new items and stuff """
  def __init__(self, name:str):
    self.name = name
    self.stock:List[Tuple[PoshimoItem, int]] = []
    stockdata:List[str] = sdata[self.name.lower()]["stock"]
    for entry in stockdata:
      logger.info(f"ENTRY: {entry}")
      item = entry.split(":")
      self.stock.append( ( PoshimoItem(item[0].lower()), int(item[1]) ) )

  def buy(self, trainer:PoshimoTrainer, selection:int) -> bool:
    item = self.stock[selection][0]
    price = self.stock[selection][1]
    if trainer.scarves >= price:
      trainer.scarves -= price
      trainer.add_item(item)
      return True
    else:
      return False

  def sell(self, trainer:PoshimoTrainer, item:PoshimoItem):
    sell_price = item.sell_price
    trainer.scarves += sell_price
    trainer.inventory.pop(item.name)

  def list_inventory(self) -> str:
    results = ""
    for entry in self.stock:
      item = entry[0]
      price = entry[1]
      results += f"> **{item}** `{price} Scarves`\n*{item.description}*\n\n"
    return results