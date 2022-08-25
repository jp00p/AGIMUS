from common import *
import battle
import poshimo_trainer

# main poShimo game functionality
# probably some utility stuff too
class PoshimoGame:
  def __init__(self):
    self.active_battles = [] # need to load any battles that were in progress

  def register_battle(self, contender_1, contender_2):
    # add contenders to the db
    # return ID (?)
    pass

  def register_trainer(self, trainer_info):
    pass
