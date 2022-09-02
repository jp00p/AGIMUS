import json
import csv
from enum import Enum, auto
from .type import PoshimoType
from .effect import EffectTypes, PoshimoEffect

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
  movedata = {}
  for row in csvdata:
    movedata[row["name"]] = {
      "display_name" : row["display_name"],
      "type" : row["type"],
      "kind" : row["kind"],
      "power" : row["power"],
      "accuracy" : row["accuracy"],
      "max_stamina" : row["max_stamina"],
      #"effect" : row["effect"],
      #"effect_chance" : row["effect_chance"],
      #"flags" : row["flags"].split("|"),
      "description" : row["description"]
    }


class MoveTargets(Enum):
  """ Which entities a target can attack """
  OPPONENT = auto()
  SELF = auto()
  BOTH = auto()


class PoshimoMove:
  """
  A poShimo move that can be used in attack\n
  Moves can do multiple effects (damage, heal, or status)
  """
  def __init__(self, name, owner=None, stamina=None):
    self.movedata = movedata.get(name)
    self.display_name = self.movedata["display_name"]
    self.type = PoshimoType(self.movedata["type"])
    self.kind = self.movedata["kind"]
    self.power = self.movedata["power"]
    self.accuracy = self.movedata["accuracy"]
    self.max_stamina = self.movedata["max_stamina"]
    if stamina:
      self._stamina = stamina
    else:
      self._stamina = self.movedata["max_stamina"]
    self.description = self.movedata["description"]
    #self.effect = self.movedata["effect"] # what does this move do?
    #self.effect_chance = self.movedata["effect_chance"]
    #self.flags = self.movedata["flags"]

  def __repr__(self) -> str:
    return f"""
----
Name: {self.display_name}
Type: {self.type}
Kind: {self.kind}
Power: {self.power}
Accuracy: {self.accuracy}
Stamina: {self.stamina}
Description: {self.description}
----
    """

  @property
  def stamina(self):
    return self._stamina
  
  @stamina.setter
  def stamina(self, val):
    self._stamina = val
    # update db here

  def refill_stamina(self, amt=None) -> None:
    """ Refill a move's stamina """
    if not amt:
      self.stamina = self.max_stamina
    else:
      self.stamina = min(self.stamina + amt, self.max_stamina)

  