import json
from .type import PoshimoType

"""
glass table toss
barrel slam
lock door
frontier medicine
big dog
leg over chair
squint
axe handle
flail

"""

f = open("./data/poshimo_moves.json")
movedata = json.load(f) # load personality data
f.close()

# moves are commands that pokemoda can use in battle
class PoshimoMove:
  def __init__(self, name, stamina=None):
    self.movedata = movedata.get(name)
    self.display_name = self.movedata["display_name"]
    self.type = PoshimoType(self.movedata["type"])
    self.kind = self.movedata["kind"]
    self.power = self.movedata["power"]
    self.accuracy = self.movedata["accuracy"]
    self.max_stamina = self.movedata["max_stamina"]
    if stamina:
      self.stamina = stamina
    else:
      self.stamina = self.movedata["max_stamina"]
    self.description = self.movedata["description"]


  def refill_stamina(self):
    self.stamina = self.max_stamina