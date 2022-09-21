""" a Type for Poshimo and their Moves """
from common import *
import csv

with open("pocket_shimodae/data/poshimo_types.csv") as file:
  csvdata = csv.DictReader(file)
  typedata = {}
  for row in csvdata:
    typedata[row["name"]] = {
      "name" : row["name"],
      "weakness" : row["weakness"] if row["weakness"] else None,
      "strength" : row["strength"] if row["strength"] else None
    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo types data loaded!{Fore.RESET}{Back.RESET}")

class PoshimoType(object):
  """
  a type for poshimo and their moves
  contains data about weaknesses & strengths
  if a poshimo of a type is weak against a move's type, the move will do 2x damage (super effective)
  if a poshimo is strong against it, the move will do 0.5x damage (not very effective)
  """
  def __init__(self, name:str=None) -> None:
    if not name:
      self.name:str = random.choice(typedata.keys())
    else:
      self.name:str = name.lower()
    self.typedata:dict = typedata[self.name]
    self.weakness:str = self.typedata.get("weakness")
    self.strength:str = self.typedata.get("strength")

  def __repr__(self) -> str:
    return f"{self.name.title()}"