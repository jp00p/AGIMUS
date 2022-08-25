from math import sqrt, floor, log10
from enum import Enum
import item, move, personality, type

level_checkpoints = [2, 7, 10, 15, 18, 23, 30, 39, 46, 55, 60, 64, 67, 72, 78, 89, 95, 100] # growth checkpoints
xp_chart = [0] + [5 + 2 * (i + 1) ** 2 for i in range(100)] # xp starts at 0 and maxes out at 20005
base_growth_rates = {
  "slow":0.8,
  "normal":1,
  "fast":1.2
}

def load_poshimo_data_from_db(name):
  # returns all the data needed to initialize a poshimo object
  # return (name, level, character_data)
  pass

def load_poshimo_data_from_file(name, level):
  # returns all base poshimo data
  pass

class StatusEffect(Enum):
  BURN = 1
  CONFUSE = 2
  FAINTED = 3
  FLINCH = 4
  FREEZE = 5
  PARALYZE = 6
  POISON = 7
  SLEEP = 8

class Poshimo: 
  def __init__(self, name, owner=None):
    self.owner = owner
    self.name = name
    self._level = 0
    self._display_name = None
    self._status = None
    self._max_hp = 0
    self._hp = self._max_hp

    if self.owner != "human":
      self.poshimo_data = load_poshimo_data_from_file(self.name, self._level)
    else:
      self.poshimo_data = load_poshimo_data_from_db(self.name)
  
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

  def use_item(self, item):
    # apply item effect to this pocket poshimo
    pass

  def hold_item(self, item):
    # add item to held slot
    # return held item to bag if already holding
    pass

  def release_item(self, item):
    # return item to bag
    pass