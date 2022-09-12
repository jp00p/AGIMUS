from common import *

class PoshimoStatus:
  """
  A status that can be applied to poshimo in battle (can be good or bad!)
  Statuses are applied by Effects
  """
  def __init__(self):
    self.name = ""
    self.trigger = ""
    # possible triggers:
    # start of turn, end of turn, when hit (pre and post damage), when attacks (pre and post damage)
    # will need to create these checks in Move or Battle...
    self.effect = "" # what does this actually do to you
    self.verb = "" # how its described in combat
    self.expires = 0 # when does it expire