""" a Move that a Poshimo can perform in combat """
from common import *
import csv
from enum import Enum, auto
from typing import List,Dict
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

# load all the flags for mapping to moves
with open("pocket_shimodae/data/move_flags.csv") as file:
  csvdata = csv.DictReader(file)
  flagdata = {}
  for id,flag in enumerate(csvdata):
    flagdata[id] = flag["name"]

  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}MOVE FLAGS{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")

######################################
#! also need to load move meta      #!
######################################

# load all the base move data from csv
with open("pocket_shimodae/data/poshimo_moves.csv") as file:
  csvdata = csv.DictReader(file)
  # id,name,type,kind,power,accuracy,stamina,description
  movedata = {}
  for row in csvdata:
    movedata[row["name"].lower()] = {
      "name" : row.get("name"),
      "type" : row.get("type"),
      "kind" : row.get("kind"),
      "power" : row.get("power"),
      "accuracy" : row.get("accuracy"),
      "stamina" : row.get("stamina"),
      "function_codes" : row.get("function_codes"),
      "flags" : row.get("flags"),
      "description" : row["description"]
    }
  logger.info(f"{Back.LIGHTMAGENTA_EX}{Fore.LIGHTYELLOW_EX}Poshimo {Style.BRIGHT}MOVES BASE DATA{Style.RESET_ALL} loaded!{Fore.RESET}{Back.RESET}")

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
    self.accuracy:int = self.movedata.get("accuracy", "").replace("%", "")
    self.max_stamina:int = int(self.movedata.get("stamina", 0))
    self._stamina:int = self.max_stamina
    self.function_codes:List[str] = None
    self.flags:list = []

    # split up the function codes (if any)
    func_codes:str = self.movedata.get("function_codes", "")
    if func_codes:
      self.function_codes:List[str] = [func for func in func_codes.split("|")]
    
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
    return {
      "name": self.name,
      "stamina" : self._stamina,
      "max_stamina" : self.max_stamina,
    }

  def button_label(self) -> str:
    label = f"{self.display_name}"
    if "no_stamina" not in self.flags:
      label += f" {self._stamina}/{self.max_stamina}"
    return label

  # these do not update the db!
  # instead you have to update Poshimo.move_list
  @property
  def stamina(self) -> int:
    return self._stamina
  
  @stamina.setter
  def stamina(self, val:int) -> None:
    if "no_stamina" in self.flags:
      return
    # clamp stamina between 0 and max_stamina
    self._stamina:int = utils.clamp(val, 0, self.max_stamina)