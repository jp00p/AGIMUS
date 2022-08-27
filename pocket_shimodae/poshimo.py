from math import sqrt, floor, log10
from enum import Enum
from .move import PoshimoMove
from .item import PoshimoItem
from .type import PoshimoType
from .personality import PoshimoPersonality
from .poshimo_trainer import PoshimoTrainer

MAX_LEVEL = 100

class Poshimo: 
  def __init__(self, name, is_human=False, owner=None, level=1):
    self.is_human = is_human 
    self.owner = owner
    
    self.name = name
    self.level = level
    self.xp = 0
    if self.owner:
      # load stats from db
      self.types = ()
      self.personality = None
      self.level = level
      self.status = None
      self.attack = 0
      self.defense = 0
      self.special_attack = 0
      self.special_defense = 0
      self.evasion = 0
      self.speed = 0
      self.hp = 0
      self.move_list = []
    else:
      # load stats from file, adjust for level
      self.types = ()
      self.personality = None
      self.level = level
      self.status = None
      self.attack = 0
      self.defense = 0
      self.special_attack = 0
      self.special_defense = 0
      self.evasion = 0
      self.speed = 0
      self.hp = 0
      self.move_list = []
    
  def save(self):
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