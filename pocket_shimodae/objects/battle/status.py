from common import *
from enum import Enum, auto

class STATUS_TRIGGERS(Enum):
  TURN_START = auto()
  TURN_END = auto()
  PRE_ATTACK = auto()
  POST_ATTACK = auto()

class PoshimoStatus:
  """
  A status that can be applied to poshimo in battle (can be good or bad!)
  """
  def __init__(self):
    self.name = ""
    self.trigger = ""
    # possible triggers:
    # start of turn, end of turn, when hit (pre and post damage), when attacks (pre and post damage)
    # will need to create these checks in Move or Battle...
    self.effect = "" # what does this actually do to you
    self.verb = "" # how its described in combat
    self.expires = 0 # how many turns til it expires

  def proc(self):
    if self.expires > 0:
      self.expires -= 1
    pass