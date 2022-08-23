from math import sqrt, floor, log10

class Shimoda():
  __slots__ = 'name', 'type', 'level', 'xp', 'base_attack', 'base_defense', 'base_special_attack', 'base_special_defense', 'base_speed', 'attack', 'defense', 'special_attack', 'special_defense', 'speed', 'evasion', 'accuracy', 'move_list', 'held_item', 'evolve_at', 'evolve_to', 'learnable_moves', 'hp', 'max_hp', 'growth_rate', 'status', 'owner'
  level_checkpoints = [2, 7, 10, 15, 18, 23, 30, 39, 46, 55, 60, 64, 67, 72, 78, 89, 95, 100] # growth checkpoints
  xp_chart = [0] + [5 + 2 * (i + 1) ** 2 for i in range(100)] # xp starts at 0 and maxes out at 20005
  base_growth_rates = {
    "slow":0.8,
    "normal":1,
    "fast":1.2
  }
  def __init__(self, name, character_data, level=1, **kwargs):
    self.name = name
    self.level = level
    self.status = None
    self.owner = None
    self.next_level = self.xp_chart[level+1]
    self.display_name = character_data['display_name']
    self.type = character_data['type']
    self.xp = character_data['xp']
    self.max_hp = 15 + floor(log10(self.level * 23 + 1) * self.level ** 1.7)
    self.hp = self.max_hp
    self.base_attack = character_data['base_attack']
    self.base_defense = character_data['base_defense']
    self.base_special_attack = character_data['base_special_attack']
    self.base_special_defense = character_data['base_special_defense']
    self.base_speed = character_data['base_speed']
    self.attack = character_data['attack']
    self.defense = character_data['defense']
    self.special_attack = character_data['special_attack']
    self.special_defense = character_data['special_defense']
    self.speed = character_data['speed']
    self.evasion = character_data['evasion']
    self.move_list = character_data['move_list']
    self.evolve_at = character_data['evolve_at']
    self.evolve_to = character_data['evolve_to']
    self.growth_rate = self.base_growth_rates[character_data['growth']]

  def set_stat(self, stat, value):
    # update stat save to db
    pass

  def get_stat(self, stat):
    pass

  def set_xp(self, amt):
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

  def use_item(self, item):
    # apply item effect to this pocket shimoda
    pass

  def hold_item(self, item):
    # add item to held slot
    # return held item to bag if already holding
    pass

  def release_item(self, item):
    # return item to bag
    pass