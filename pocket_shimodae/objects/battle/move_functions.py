from common import *
from ..poshimo import Poshimo, PoshimoStat, PoshimoMove
from ...utils import roll

'''

each function takes 0-x number of custom *params
each function can also take a chance param, float from 0.0 to 1.0  
each function MUST pass target and move_details params

'''

def reduce_stage(statname:str, reduction:int, chance:float=1.0, target:Poshimo=None, move_details:dict=None):
  ''' 
  reduce a stat's stage
  '''
  chance = float(chance)
  reduction = int(reduction)
  stat:PoshimoStat = getattr(target, statname)
  if stat.stage <= -6:
    return f"{target.display_name}'s {statname.title()} can't go any lower!"
  if roll(chance):
    stat.stage -= reduction
    setattr(target, statname, stat)
    return f"{target.display_name}'s {statname.title()} stage reduced by {reduction}!"
  return False

def increase_stage(statname:str, increase:int, chance:float=1.0, target:Poshimo=None, move_details:dict=None):
  ''' 
  increase a stat's stage
  '''
  chance = float(chance)
  increase = int(increase)
  stat:PoshimoStat = getattr(target, statname)
  if stat.stage >= 6:
    return f"{target.display_name}'s {statname.title()} can't increase any more!"
  if roll(chance):
    stat.stage += increase
    setattr(target, statname, stat)
    return f"{target.display_name}'s {statname.title()} stage increased by {increase}!"
  return False

def restore_half_damage(chance=None, target:Poshimo=None, move_details:dict=None):
  '''
  restore hp equal to half the damage
  '''
  damage = move_details["damage"]
  heal_amount = round(damage // 2)
  target.hp += heal_amount
  return f"{target.display_name} healed {heal_amount} hp!"

def raise_all_stats(increase:int, chance=1.0, target:Poshimo=None, move_details:dict=None):
  pass