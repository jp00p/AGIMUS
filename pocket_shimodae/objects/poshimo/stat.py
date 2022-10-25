from common import * 
from functools import total_ordering

stage_values:dict = {
  -6: 0.25,
  -5: 0.2,
  -4: 0.3,
  -3: 0.4,
  -2: 0.5,
  -1: 0.75,
  0: 1,
  1: 1.5,
  2: 2,
  3: 2.5,
  4: 3,
  5: 3.5,
  6: 4
}

@total_ordering
class PoshimoStat(object):
  """ 
  A basic stat that can be affected in stages
  ----
  usage: `stat = PoshimoStat(x,y,z)`

  where `x` is the base stat value and `y` is the "stage" that stat is at, from -6 to 6

  `z` is the xp of this stat

  `stage` defaults to 0

  when used in expressions with other numbers, will return the modified value
  """
  
  def __init__(self, stat_value:int, stage:int=0, xp:int=0):
    self.stat_value:int = int(stat_value)
    self.stage:int = stage
    self.xp:int = xp

  def _is_valid_operand(self, other):
    return bool(isinstance(other, PoshimoStat) or isinstance(other, int) or isinstance(other, float))

  def value(self) -> int:
    """ returns the modified value """
    return int(round( self.stat_value * stage_values[self.stage] ) )

  def add_xp(self, val) -> int:
    ''' add xp to this stat, returns amt gained if leveled up '''
    self.xp = self.xp + val
    if self.xp >= 100:
      self.xp = self.xp - 100
      increase = random.choice([1,2,3])
      self.stat_value += increase
      return increase
    return 0
  
  def xp_progress(self) -> float:
    progress = (self.xp / 100)
    return progress

  def to_json(self) -> str:
    return json.dumps([int(self.stat_value), int(self.stage), int(self.xp)])
    
  def __eq__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() == other.value())
    else:
      return (self.value() == other)
  
  def __add__(self,other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() + other.value())
    else:
      return (self.value() + other)

  def __iadd__(self,other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() + other.value())
    else:
      return (self.value() + other)

  def __radd__(self,other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (other.value() + self.value())
    else:
      return (other + self.value())

  def __sub__(self,other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() - other.value())
    else:
      return (self.value() - other)

  def __isub__(self,other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() - other.value())
    else:
      return (self.value() - other)

  def __mul__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() * other.value())
    else:
      return (self.value() * other)

  def __truediv__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() / other.value())
    else:
      return (self.value() / other)
  
  def __floordiv__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() // other.value())
    else:
      return (self.value() // other)

  def __lt__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() < other.value())
    else:
      return (self.value() < other)

  def __gt__(self, other):
    if not self._is_valid_operand(other):
      return NotImplemented
    if isinstance(other, PoshimoStat):
      return (self.value() > other.value())
    else:
      return (self.value() > other)

  def __str__(self) -> str:
    return str(self.value())

  def __int__(self) -> int:
    return int(self.value())

  def __float__(self) -> float:
    return float(self.value())