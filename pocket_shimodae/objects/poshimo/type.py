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
  ps_log(f"Types: {len(typedata)}")

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

  def __str__(self) -> str:
    return self.name.title()

  def __eq__(self, other):
    return self.name == other

  def is_weak_against(self, other):
    if isinstance(other,list):
      return self.weakness in other
    return self.weakness == other

  def is_strong_against(self, other):
    if isinstance(other,list):
      return self.weakness in other
    return self.strength == other