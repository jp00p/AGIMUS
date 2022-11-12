from common import *
from enum import Enum, auto
import math

class LevelingType(Enum):
  slow = auto()
  medium_slow = auto()
  medium_fast = auto()
  fast = auto()
  def __str__(self) -> str:
    return self.name

class PoshimoExperience(object):

  def slow(self, level):
    return (1.25 * pow(level, 3))
  
  def medium_slow(self, level):
    return abs((1.2 * pow(level, 3)) - (15 * pow(level,2)) + (100 * level) - 140)
  
  def medium_fast(self, level):
    return pow(level, 3)
  
  def fast(self, level):
    return (0.8 * pow(level, 3))

def get_experience(leveling_type, level):
  return getattr(PoshimoExperience(), leveling_type)(int(level))





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
