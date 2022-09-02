from math import sqrt, floor, log10
import csv
from enum import Enum
from .move import PoshimoMove
from .item import PoshimoItem
from .type import PoshimoType
from .personality import PoshimoPersonality
from .trainer import PoshimoTrainer

# load the base poshimo data from csv
with open("pocket_shimodae/data/shimodaepedia.csv") as file:
  csvdata = csv.DictReader(file)
  pdata = {}
  for id,row in enumerate(csvdata):
    pdata[row["name"]] = {
      "id" : id,
      "type1" : row["type1"],
      "type2" : row["type2"],
      "base_attack" : row["base_attack"],
      "base_defense" : row["base_defense"],
      "base_special_attack" : row["base_special_attack"],
      "base_special_defense" : row["base_special_defense"],
      "evasion" : row["evasion"],
      "speed" : row["speed"],
      "hp" : row["hp"],
      "move_list" : [
        row["move1"], row["move2"], row["move3"], row["move4"]
      ]
    }


MAX_LEVEL = 100

class Poshimo:
  """
  A Pocket Shimoda!\n
  You do not create these from scratch, they are predefined in the CSV or DB.\n
  Pass a name to get the base stats\n
  Pass a name and level to get level-adjusted stats (for wild Poshimo)\n
  Pass a name and owner to get the Poshimo stats from the DB (for player-owned Poshimo)
  """
  def __init__(self, name, owner=None, level=1):
    self.name = name
    if not pdata.get(self.name):
      return None
    self.poshimodata = pdata[self.name]
  
    self.types = (PoshimoType(self.poshimodata["type1"]), PoshimoType(self.poshimodata["type2"]))
    self.personality = None
    self.level = level
    self.status = None
    self.attack = self.poshimodata["base_attack"]
    self.defense = self.poshimodata["base_defense"]
    self.special_attack = self.poshimodata["base_special_attack"]
    self.special_defense = self.poshimodata["base_special_defense"]
    self.evasion = self.poshimodata["evasion"]
    self.speed = self.poshimodata["speed"]
    self.max_hp = self.poshimodata["hp"]
    self.hp = self.max_hp
    self.move_list = [PoshimoMove(i) for i in self.poshimodata["move_list"]]
  
  def __repr__(self) -> str:
    return f"{self.name}: (Types: {[t for t in list(self.types)]})"
  
  def save(self) -> None:
    # save to db
    pass
  
  def attempt_capture(self):
    # transfer to player
    pass

  def level_up(self):
    # increase max hp
    # increase stats
    # check to add moves
    # check to evolve
    pass

  def learn_move(self, move):
    # add move to move_list
    # can't know more than 4
    pass

  def forget_move(self, move):
    # remove a move from move_list
    pass

  def evolve(self):
    # evolve (if applicable)
    pass

  def perform_attack(self, target, move):
    # calculate attack
    pass

  def hold_item(self, item):
    # add item to held slot
    # return held item to bag if already holding
    pass

  def release_item(self, item):
    # return item to bag
    pass




""" from ultranurd 
  
import sys
import math
​
class Experience:
    def slow(self, level):
        return 5 * level3 / 4
​
    def medium_slow(self, level):
        return 6 * level3 / 5 - 15 * level2 + 100 * level - 140
​
    def medium_fast(self, level):
        return level3
​
    def fast(self, level):
        return 4 * level3 / 5
​
    def fluctuating(self, level):
        if level < 15:
            factor = (math.floor((level + 1)/3.0) + 24)/50
        elif level < 36:
            factor = (level + 14)/50
        elif level < 100:
            factor = (math.floor(level/2.0) + 32)/50
        return factor * level3
​
    def erratic(self, level):
        if level < 50:
            factor = (100 - level)/50
        elif level < 68:
            factor = (150 - level)/100
        elif level < 98:
            factor = math.floor((1911 - 10level)/3.0)/500
        elif level < 100:
            factor = (160 - level)/100
        return factor level*3
​
def experience(leveling, level):
    print(getattr(Experience(), leveling)(int(level)))
​
if name == "main":
    experience(sys.argv[1:])
  
  """