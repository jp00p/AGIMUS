from enum import Enum

class BattleStates(Enum):
  ACTIVE = 1
  FINISHED = 2

# needs to handle pvp and npcs
class PoshimoBattle:
  def __init__(self, contender_1, contender_2, state=BattleStates.ACTIVE):
    pass