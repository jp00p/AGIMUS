""" a Move that a Poshimo can perform in combat """
from common import *
import csv
from enum import Enum, auto
from . import PoshimoType
import pocket_shimodae.utils as utils

"""
glass table toss
barrel slam
lock door
frontier medicine
big dog
leg over chair
squint
axe handle
flail
"""

# load all the base move data from csv
with open("pocket_shimodae/data/poshimo_moves.csv") as file:
  csvdata = csv.DictReader(file)
  # id,name,type,kind,power,accuracy,stamina,description
  movedata = {}
  for row in csvdata:
    movedata[row["name"].lower()] = {
      "name" : row["name"],
      "type" : row["type"],
      "kind" : row["kind"],
      "power" : row["power"],
      "accuracy" : row["accuracy"],
      "stamina" : row["stamina"],
      #"effect" : row["effect"],
      #"effect_chance" : row["effect_chance"],
      #"flags" : row["flags"].split("|"),
      "description" : row["description"]
    }
  logger.info(f"Poshimo moves data loaded!")

class MoveTargets(Enum):
  """ Which entities a target can attack """
  OPPONENT = auto()
  SELF = auto()
  BOTH = auto()

class MoveKinds(Enum):
  PHYSICAL = 0 # basic attack, contacts the other poshimo
  SPECIAL = 1 # does something special besides contact

class PoshimoMove(object):
  """
  A poShimo move that can be used in attack\n
  Moves can do multiple effects (damage, heal, or status)\n
  When loading from the DB, pass stamina & max_stamina to get your custom move
  """
  def __init__(self, name:str, stamina:int=0, max_stamina:int=0) -> None:
    self.name:str = name.lower()
    self.movedata:dict = movedata[self.name]
    self.description:str = self.movedata.get("description")
    self.display_name:str = self.name.title()
    self.type:PoshimoType = PoshimoType(name=self.movedata.get("type")) #PoshimoType(self.movedata["type"])
    self.kind:str = self.movedata.get("kind")
    self.power:int = self.movedata.get("power")
    self.accuracy:int = self.movedata.get("accuracy").replace("%", "")
    self.max_stamina:int = int(self.movedata.get("stamina"))
    self._stamina:int = self.max_stamina
    
    if stamina is not None:
      # poshimo in the db need their stamina loaded
      self._stamina:int = stamina
    if max_stamina is not None:
      self.max_stamina:int = max_stamina
    
    #self.effect = self.movedata["effect"] # what does this move do?
    #self.effect_chance = self.movedata["effect_chance"]
    #self.flags = self.movedata["flags"]

  def __repr__(self) -> str:
    return f"{self.display_name}"

  def details_str(self) -> str:
    return f"""
Name: {self.display_name}
Type: {self.type}
Kind: {self.kind}
Power: {self.power}
Accuracy: {self.accuracy}
Stamina: {self.stamina}/{self.max_stamina}
Description: {self.description}
"""

  def to_json(self) -> dict:
    return {
      "name": self.name,
      "stamina" : self._stamina,
      "max_stamina" : self.max_stamina,
    }

  @property
  def stamina(self) -> int:
    return self._stamina
  
  @stamina.setter
  def stamina(self, val:int) -> None:
    # clamp stamina between 0 and max_stamina
    self._stamina = utils.clamp(val, 0, self.max_stamina)