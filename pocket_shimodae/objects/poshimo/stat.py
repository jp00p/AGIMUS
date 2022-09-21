from common import * 

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

class PoshimoStat(object):
  """ A basic stat that can be affected in combat """
  
  def __init__(self, stat_value:int, stage:int=0):
    self.stat_value:int = int(stat_value)
    self.stage:int = stage
  
  def value(self) -> int:
    """ returns the modified value """
    return int(round(self.stat_value * stage_values[self.stage],0))

  def to_json(self) -> str:
    return json.dumps([int(self.stat_value), int(self.stage)])

  def __repr__(self) -> str:
    return self.value()