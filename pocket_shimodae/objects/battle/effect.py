from common import *
from enum import Enum, auto

class EffectTypes(Enum):
  DAMAGE = auto() # 1
  HEAL = auto()   # 2
  STATUS = auto() # 3

class PoshimoEffect:
  """
    Does a single thing to a poshimo (damage, status, etc)
  """
  def __init__(self):
    self.name = ""
    self.type = "" # damage, heal, status
    self.verb = "" # how it gets described in combat
      