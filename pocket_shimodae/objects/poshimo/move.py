""" a Move that a Poshimo can perform in combat """
from common import *
import csv
from enum import Enum, auto
from typing import List,Dict,Any
from . import PoshimoType

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

######################################
#! also need to load move meta      #!
######################################

# load all the base move data from csv
with open("pocket_shimodae/data/Moves.csv") as file:
  csvdata = csv.DictReader(file)
  # id,name,type,kind,power,accuracy,stamina,description
  movedata = {}
  for row in csvdata:
    movedata[row["name"].lower()] = {
      "name" : row.get("name"),
      "type" : row.get("type"),
      "kind" : row.get("kind"),
      "power" : row.get("power"),
      "accuracy" : row.get("accuracy", 1.0),
      "stamina" : row.get("stamina"),
      "function_code" : row.get("function_code"),
      "function_target": row.get("function_target", ""),
      "function_params" : row.get("function_params"),
      "proc_chance" : row.get("proc_chance"),
      "flags" : row.get("flags"),
      "description" : row["description"]
    }
  ps_log(f"Moves: {len(movedata)}")

class MoveTargets(Enum):
  """ Which entities a target can attack """
  # NBU yet
  OPPONENT = auto()
  SELF = auto()
  BOTH = auto()

class MoveKinds(Enum):
  PHYSICAL = auto() # uses attack/defense
  SPECIAL = auto() # uses special attack/special defense
  STATUS = auto() # does something else!

class PoshimoMove(object):
  """
  A Poshimo Move!
  ----
  A move that can be used in combat by a Poshimo

  """
  def __init__(self, name:str, stamina:int=None, max_stamina:int=None) -> None:
    self.name:str = name.lower()
    self.movedata:dict = movedata.get(self.name, {})
    self.description:str = self.movedata.get("description","")
    self.display_name:str = self.name.title()
    self.type:PoshimoType = PoshimoType(name=self.movedata.get("type", "Drunk"))
    self.kind:MoveKinds = MoveKinds[self.movedata.get("kind", "Physical").upper()]
    self.power:int = self.movedata.get("power", 0)
    self.accuracy:float = self.movedata.get("accuracy", 1.0) #default 1.0
    self.max_stamina:int = int(self.movedata.get("stamina", 0))
    self._stamina:int = self.max_stamina
    self.function_code:str = self.movedata.get("function_code", "")
    self.function_target:str = self.movedata.get("function_target", "")
    self.proc_chance:float = self.movedata.get("proc_chance", 1.0) #default 1.0
    self.function_params:List[Any] = []
    if self.movedata.get("function_params"):
      self.function_params = self.movedata["function_params"].split(",")

    self.flags:list = []
    
    flags = self.movedata.get("flags", []) # list of flag ids
    if flags:
      for id in flags:
        self.flags.append(flagdata[id])

    if stamina is not None:
      # poshimo in the db need their stamina loaded
      self._stamina:int = stamina
    if max_stamina is not None:
      self.max_stamina:int = max_stamina

    if "no_stamina" in self.flags:
      self._stamina = 99
      self.max_stamina = 99

  def __str__(self) -> str:
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
    ''' 
    convert this move to a dict so it can be converted to json
    returns a dict representation of the move
    '''
    return {
      "name": self.name,
      "stamina" : self._stamina,
      "max_stamina" : self.max_stamina,
    }

  def button_label(self) -> str:
    ''' outputs a string suitable for use on buttons '''
    label = f"{self.display_name}"
    if "no_stamina" not in self.flags:
      label += f" {self._stamina}/{self.max_stamina}"
    return label

  # these do not update the db!
  # instead you have to update the Poshimo.move_list
  @property
  def stamina(self) -> int:
    return self._stamina
  
  @stamina.setter
  def stamina(self, val:int) -> None:
    if "no_stamina" in self.flags:
      return
    # clamp stamina between 0 and max_stamina
    self._stamina:int = max(0, min(val, self.max_stamina))