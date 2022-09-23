""" a Personality, determines stat growth """
from common import *
import csv

with open("pocket_shimodae/data/poshimo_personalities.csv") as file:
  csvdata = csv.DictReader(file)
  persdata = {}
  for row in csvdata:
    persdata[row["name"]] = {
      "name" : row["name"],
      "bonus" : row.get("bonus_stat"),
      "penalty" : row.get("penalized_stat")
    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo personality data loaded!{Fore.RESET}{Back.RESET}")

class PoshimoPersonality:
  """ a personality determines how some stats grow when leveling up """
  def __init__(self, name=None):
    if not name:
      self.pdata=random.choice(list(persdata.values()))
    else:
      self.pdata = persdata[name]
    self.name:str = self.pdata["name"]
    self.bonus:str = self.pdata["bonus"]
    self.penalty:str = self.pdata["penalty"]

  def __str__(self):
    return f"{self.name.title()}"