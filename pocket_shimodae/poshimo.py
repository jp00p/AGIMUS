from math import sqrt, floor, log10

def load_poshimo_data_from_db(poshimo_id):
  # returns all the data needed to initialize a poshimo object
  # return (name, level, character_data)
  pass

class Poshimo:
  __slots__ = 'name', 'type', 'level', 'xp', 'base_attack', 'base_defense', 'base_special_attack', 'base_special_defense', 'base_speed', 'attack', 'defense', 'special_attack', 'special_defense', 'speed', 'evasion', 'accuracy', 'move_list', 'held_item', 'evolve_at', 'evolve_to', 'learnable_moves', 'hp', 'max_hp', 'growth_rate', 'status', 'owner'
  level_checkpoints = [2, 7, 10, 15, 18, 23, 30, 39, 46, 55, 60, 64, 67, 72, 78, 89, 95, 100] # growth checkpoints
  xp_chart = [0] + [5 + 2 * (i + 1) ** 2 for i in range(100)] # xp starts at 0 and maxes out at 20005
  base_growth_rates = {
    "slow":0.8,
    "normal":1,
    "fast":1.2
  }
  def __init__(self, name, owner=None):
    self.owner = owner
    self.name = name
    self.poshimo_data = load_poshimo_data_from_db(self.name)
    self._display_name = None
    self._level = 0

  def set_stat(self, stat, value):
    # update stat save to db
    pass

  def get_stat(self, stat):
    return self.get(stat)
  
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