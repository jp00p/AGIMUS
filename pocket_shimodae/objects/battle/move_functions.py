from common import *
from ..poshimo import Poshimo, PoshimoStat, PoshimoMove
from ...utils import roll

def reduce_stage(statname:str, reduction:int, chance:float=1.0, target:Poshimo=None):
  ''' 
  reduce a stat's stage
  returns True if successful
  '''
  chance = float(chance)
  reduction = int(reduction)
  stat:PoshimoStat = getattr(target, statname)
  if roll(chance):
    stat.stage -= reduction
    setattr(target, statname, stat)
    return f"{target.display_name}'s {statname.title()} stage reduced by {reduction}!"
  return False

def increase_stage(statname:str, increase:int, chance:float=1.0, target:Poshimo=None):
  ''' 
  increase a stat's stage
  returns True if successful
  '''
  chance = float(chance)
  increase = int(increase)
  stat:PoshimoStat = getattr(target, statname)
  if roll(chance):
    stat.stage += increase
    setattr(target, statname, stat)
    return f"{target.display_name}'s {statname.title()} stage increased by {increase}!"
  return False

